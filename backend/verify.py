# verify.py
# Verification-first layer for the CodeMentor AI harness.
# After the model produces an answer, the code blocks it emitted are
# checked locally before the user is shown the result:
#   - Python: AST syntax check + undefined-name analysis (no execution)
#   - JavaScript: real syntax check via `node --check` when Node is installed
#   - other languages: delimiter-balance heuristic when no compiler exists
# Nothing is ever executed, so this is safe for arbitrary model output.

import ast
import builtins
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

_FENCE_RE = re.compile(r"```([a-zA-Z0-9+#_-]*)[^\n]*\n(.*?)```", re.DOTALL)

_LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "c++": "cpp",
    "csharp": "csharp",
    "cs": "csharp",
    "shell": "bash",
    "sh": "bash",
    "bash": "bash",
    "text": "",
    "txt": "",
}

if isinstance(builtins, dict):
    _BUILTIN_NAMES = set(builtins)
else:
    _BUILTIN_NAMES = set(dir(builtins))


def normalize_language(language: Optional[str]) -> str:
    lang = (language or "").strip().lower()
    return _LANGUAGE_ALIASES.get(lang, lang)


def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """Pull fenced code blocks from a response as [{'language', 'code'}]."""
    blocks: List[Dict[str, str]] = []
    for match in _FENCE_RE.finditer(text):
        lang = normalize_language(match.group(1))
        code = match.group(2).rstrip("\n")
        if code.strip():
            blocks.append({"language": lang, "code": code})
    return blocks


# ---------- delimiter balance (fallback for languages without a local tool) ----------

_STRING_COMMENT_RE = [
    re.compile(r"//[^\n]*"),
    re.compile(r"/\*.*?\*/", re.DOTALL),
    re.compile(r'"(?:\\.|[^"\\])*"'),
    re.compile(r"'(?:\\.|[^'\\])*'"),
]
_OPENERS = {"(": ")", "[": "]", "{": "}"}


def _strip_strings_and_comments(code: str) -> str:
    for pattern in _STRING_COMMENT_RE:
        code = pattern.sub("", code)
    return code


def _delimiter_issues(code: str) -> List[Dict[str, Any]]:
    """Report unbalanced () [] {} pairs. Best-effort; no line info."""
    stack: List[str] = []
    for char in _strip_strings_and_comments(code):
        if char in _OPENERS:
            stack.append(char)
        elif char in _OPENERS.values():
            if not stack or _OPENERS[stack.pop()] != char:
                return [{"line": None, "message": f"unbalanced delimiter '{char}'"}]
    if stack:
        return [{"line": None, "message": f"unbalanced delimiter '{_OPENERS[stack[-1]]}' (never closed)"}]
    return []


# ---------- Python AST checks ----------

def _target_names(targets: Any) -> List[str]:
    names: List[str] = []
    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            names.extend(_target_names(target.elts))
        elif isinstance(target, ast.Starred):
            names.extend(_target_names([target.value]))
    return names


def _bound_names(tree: ast.AST) -> set:
    """Names bound anywhere in a scope (imports, assigns, defs, targets...)."""
    names: set = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if node.__class__ is ast.Import:
                    names.add(alias.asname or alias.name.split(".")[0])
                else:
                    names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(_target_names(node.targets))
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            names.update(_target_names([node.target]))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            names.update(_target_names([node.target]))
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    names.update(_target_names([item.optional_vars]))
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                names.add(node.name)
        elif isinstance(node, ast.NamedExpr):
            names.update(_target_names([node.target]))
        elif isinstance(node, ast.comprehension):
            names.update(_target_names([node.target]))
        elif isinstance(node, ast.Global):
            names.update(node.names)
        elif isinstance(node, ast.Nonlocal):
            names.update(node.names)
        elif isinstance(node, ast.MatchAs) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchStar) and node.name:
            names.add(node.name)
    return names


def _undefined_names(nodes, bound: set) -> List[Dict[str, Any]]:
    """Report Name loads in the given scope that resolve to nothing.

    `nodes` is the already-flattened scope (see _top_level_nodes), so this
    is a pure filter: it must not walk children again.
    """
    return [
        {"line": node.lineno, "message": f"undefined name '{node.id}'"}
        for node in nodes
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
        and node.id not in bound
        and node.id not in _BUILTIN_NAMES
    ]


def _top_level_nodes(tree: ast.AST):
    """Yield nodes of a scope without descending into nested defs/classes.

    Function and class definitions are yielded as bindings but their
    bodies are analyzed by their own scope passes.
    """
    stack = [tree]
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not tree:
            continue
        for child in ast.iter_child_nodes(node):
            stack.append(child)


def _verify_python(code: str) -> Dict[str, Any]:
    """AST-based checks: syntax validity and undefined names."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {
            "status": "issues",
            "checks": ["syntax"],
            "issues": [{"line": exc.lineno, "message": f"syntax error: {exc.msg}"}],
        }

    global_bound = _bound_names(tree)
    issues: List[Dict[str, Any]] = list(_undefined_names(_top_level_nodes(tree), global_bound))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        scope_bound = set(global_bound)
        scope_bound.update(_bound_names(node))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            scope_bound.update(arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs)
            if args.vararg:
                scope_bound.add(args.vararg.arg)
            if args.kwarg:
                scope_bound.add(args.kwarg.arg)
        issues.extend(_undefined_names(_top_level_nodes(node), scope_bound))

    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for issue in issues:
        key = (issue["line"], issue["message"])
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return {
        "status": "issues" if unique else "ok",
        "checks": ["syntax", "undefined names"],
        "issues": unique,
    }


# ---------- JavaScript via node, others via heuristic ----------

def _node_syntax_issues(code: str) -> Optional[List[Dict[str, Any]]]:
    """Real syntax check using `node --check`; None if node is unavailable."""
    if not shutil.which("node"):
        return None
    path = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".js", encoding="utf-8", delete=False
        ) as handle:
            handle.write(code)
            path = handle.name
        result = subprocess.run(
            ["node", "--check", path],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    if result.returncode == 0:
        return []
    # node prints a `<path>:<line>[:<column>]` frame followed by the source
    # line; take the line number from that first frame only.
    first_frame = (result.stderr or "").splitlines()[0] if result.stderr else ""
    match = re.search(r":(\d+)(?::\d+)?\s*$", first_frame)
    if match:
        return [{"line": int(match.group(1)), "message": "syntax error"}]
    return [{"line": None, "message": "syntax error"}]


def _verify_fallback(language: str, code: str) -> Dict[str, Any]:
    """Delimiter-balance heuristic for languages without a local checker."""
    issues = _delimiter_issues(code)
    return {
        "status": "issues" if issues else "ok",
        "checks": ["delimiter balance"],
        "issues": issues,
    }


def verify_code(language: str, code: str) -> Dict[str, Any]:
    """Run the best available static checks for one code block."""
    lang = normalize_language(language)
    if lang == "python":
        return _verify_python(code)
    if lang in {"javascript", "typescript"}:
        node_issues = _node_syntax_issues(code)
        if node_issues is not None:
            return {
                "status": "issues" if node_issues else "ok",
                "checks": ["node --check"],
                "issues": node_issues,
            }
        return _verify_fallback(lang, code)
    return _verify_fallback(lang, code)


def syntax_issues(language: str, code: str) -> List[Dict[str, Any]]:
    """Syntax-only check (used for quick pre-checks of user input).

    Unlike verify_code, this reports only syntax problems, not semantic
    issues like undefined names, so buggy-but-parseable user code is not
    pre-empted before the model gets to explain it.
    """
    lang = normalize_language(language)
    if lang == "python":
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return [{"line": exc.lineno, "message": f"syntax error: {exc.msg}"}]
        return []
    if lang in {"javascript", "typescript"}:
        node_issues = _node_syntax_issues(code)
        if node_issues is not None:
            return node_issues
    return _delimiter_issues(code)


def verify_text(text: str, language_hint: str = "") -> Dict[str, Any]:
    """Verify every code block inside a response or input text.

    The language hint (the user's selected language) wins over the model's
    fence label: models sometimes miscap fences (e.g. ```python around C++
    code), which would run the wrong checker and produce a misleading
    verdict. The fence label is used only when no hint is available.
    """
    blocks = extract_code_blocks(text)
    if not blocks:
        return {"status": "no_code", "blocks": []}

    hint = normalize_language(language_hint)
    results: List[Dict[str, Any]] = []
    for index, block in enumerate(blocks, start=1):
        lang = hint or block["language"]
        report = verify_code(lang, block["code"])
        results.append(
            {
                "index": index,
                "language": lang,
                "status": report["status"],
                "checks": report["checks"],
                "issues": report["issues"],
            }
        )
    any_issues = any(result["status"] == "issues" for result in results)
    return {"status": "issues" if any_issues else "ok", "blocks": results}
