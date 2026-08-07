# repo.py
# Local repository scanner powering the repo_report mode.
# Builds a compact, LLM-friendly snapshot of a folder: file tree, detected
# languages, key configuration files, source contents (size-capped), and
# quick local static checks for obvious errors. Sensitive files (secrets)
# are never read.

import json
import os
import fnmatch
from collections import Counter
from typing import Any, Dict, List, Tuple

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".github", ".tox", ".nox",
    "node_modules", "venv", ".venv", "env", "dist", "build", "target",
    "out", "bin", "obj", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".cache", "coverage", ".next", ".nuxt", "vendor", "site-packages",
    ".eggs", ".terraform", ".serverless",
}

SENSITIVE_PATTERNS = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*",
    ".netrc", "credentials.json", "service-account*.json", "secrets*.json",
]

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".class", ".jar", ".pyc", ".pyo",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".mp3", ".mp4", ".avi",
    ".mov", ".wav", ".flac", ".ogg", ".db", ".sqlite", ".sqlite3", ".map",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp",
    ".hpp", ".cc", ".go", ".rs", ".rb", ".php", ".sh", ".bash", ".ps1",
    ".sql", ".html", ".htm", ".css", ".scss", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".xml", ".md", ".txt", ".ipynb",
}

KEY_FILE_NAMES = {
    "README.md", "README.rst", "README.txt", "readme.md",
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "pom.xml", "build.gradle", "Cargo.toml", "go.mod",
    "Gemfile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", "CMakeLists.txt", "tsconfig.json", "composer.json",
    ".env.example", ".gitignore", "manage.py", "main.py", "app.py",
    "index.js", "index.ts", "server.py", "app.js", "wsgi.py", "asgi.py",
}

MAX_CONTENT_CHARS = 120_000
MAX_FILE_CHARS = 30_000
MAX_TREE_ENTRIES = 500
MAX_CHECK_FILES = 300

LANGUAGE_LABELS = {
    "py": "Python", "js": "JavaScript", "ts": "TypeScript", "jsx": "React (JSX)",
    "tsx": "React (TSX)", "java": "Java", "c": "C", "h": "C header",
    "cpp": "C++", "hpp": "C++ header", "go": "Go", "rs": "Rust", "rb": "Ruby",
    "php": "PHP", "sh": "Shell", "ps1": "PowerShell", "sql": "SQL",
    "html": "HTML", "css": "CSS", "json": "JSON", "yaml": "YAML",
    "yml": "YAML", "toml": "TOML", "ini": "INI", "xml": "XML", "md": "Markdown",
}


def _is_sensitive(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in SENSITIVE_PATTERNS)


def _is_skippable(rel: str) -> bool:
    base = os.path.basename(rel)
    ext = os.path.splitext(base)[1].lower()
    return (
        ext in SKIP_EXTENSIONS
        or base.endswith(".min.js")
        or base.endswith(".min.css")
    )


def _detect_languages(all_files: List[Tuple[str, str]]) -> Dict[str, int]:
    counts: Counter = Counter()
    for rel, _ in all_files:
        ext = os.path.splitext(rel)[1].lower().lstrip(".")
        if ext and len(ext) <= 4:
            counts[ext] += 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def _build_tree(root_name: str, rel_files: List[str], max_entries: int = MAX_TREE_ENTRIES) -> str:
    root: Dict[str, Any] = {}
    for rel in sorted(rel_files):
        node = root
        for part in rel.split(os.sep):
            node = node.setdefault(part, {})

    lines: List[str] = [f"{root_name}/"]
    omitted = 0

    def render(prefix: str, node: Dict[str, Any]) -> None:
        nonlocal omitted
        items = sorted(node.items(), key=lambda item: (not item[1], item[0].lower()))
        for index, (name, children) in enumerate(items):
            if len(lines) >= max_entries:
                omitted += len(items) - index
                return
            last = index == len(items) - 1
            branch = "`-- " if last else "|-- "
            if children:
                lines.append(f"{prefix}{branch}{name}/")
                render(prefix + ("    " if last else "|   "), children)
            else:
                lines.append(f"{prefix}{branch}{name}")

    render("", root)
    if omitted:
        lines.append(f"... {omitted} more entries omitted")
    return "\n".join(lines)


def _read_into(scan: Dict[str, Any], section: str, rel: str, full: str, budget: int) -> int:
    try:
        size = os.path.getsize(full)
        with open(full, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
    except OSError:
        return 0

    scan["total_lines"] += content.count("\n") + 1

    chunk = content
    if len(chunk) > MAX_FILE_CHARS:
        chunk = chunk[:MAX_FILE_CHARS] + "\n... [file content truncated]"
        scan["truncated"] = True
    if len(chunk) > budget:
        chunk = chunk[:budget] + "\n... [file content truncated to fit context]"
        scan["truncated"] = True

    scan[section].append(
        {"rel": rel, "lines": content.count("\n") + 1, "size": size, "content": chunk}
    )
    return len(chunk)


def _static_check(rel: str, full: str) -> str:
    base = os.path.basename(rel)
    ext = os.path.splitext(base)[1].lower()
    try:
        if os.path.getsize(full) > 1_000_000:
            return ""
        with open(full, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
    except OSError:
        return ""

    if ext == ".py":
        try:
            compile(content, rel, "exec")
        except SyntaxError as exc:
            return f"SyntaxError in {rel}: {exc.msg} (line {exc.lineno})"
    elif ext == ".json" or base.endswith(".ipynb"):
        try:
            json.loads(content)
        except ValueError as exc:
            return f"Invalid JSON in {rel}: {exc}"
    return ""


def scan_repo(repo_path: str, max_chars: int = MAX_CONTENT_CHARS) -> Dict[str, Any]:
    """Scan a repository folder and return a snapshot dict for the AI."""
    repo_path = os.path.abspath(repo_path)

    scan: Dict[str, Any] = {
        "root": repo_path,
        "total_files": 0,
        "languages": {},
        "tree": "",
        "key_files": [],
        "source_files": [],
        "local_errors": [],
        "total_lines": 0,
        "truncated": False,
    }

    all_files: List[Tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = sorted(
            d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")
        )
        for filename in filenames:
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, repo_path)
            all_files.append((rel, full))

    scan["total_files"] = len(all_files)
    scan["languages"] = _detect_languages(all_files)
    scan["tree"] = _build_tree(os.path.basename(repo_path), [rel for rel, _ in all_files])

    key_files: List[Tuple[str, str]] = []
    source_files: List[Tuple[str, str]] = []
    for rel, full in all_files:
        base = os.path.basename(rel)
        if _is_sensitive(base) or _is_skippable(rel):
            continue
        if base in KEY_FILE_NAMES:
            key_files.append((rel, full))
        elif os.path.splitext(base)[1].lower() in SOURCE_EXTENSIONS or base.startswith("Dockerfile"):
            source_files.append((rel, full))

    key_files.sort(key=lambda item: (not item[0].lower().startswith("readme"), item[0]))
    source_files.sort(key=lambda item: os.path.getsize(item[1]))

    budget = max_chars
    for rel, full in key_files:
        if budget <= 0:
            break
        budget -= _read_into(scan, "key_files", rel, full, budget)
    for rel, full in source_files:
        if budget <= 0:
            break
        budget -= _read_into(scan, "source_files", rel, full, budget)

    for rel, full in (key_files + source_files)[:MAX_CHECK_FILES]:
        error = _static_check(rel, full)
        if error:
            scan["local_errors"].append(error)

    return scan


def _format_languages(languages: Dict[str, int]) -> str:
    if not languages:
        return "none detected"
    top = list(languages.items())[:12]
    return ", ".join(
        f"{LANGUAGE_LABELS.get(ext, ext)}: {count}" for ext, count in top
    )


def build_repo_summary(scan: Dict[str, Any]) -> str:
    """Render a scan snapshot into a single text block for the AI model."""
    parts = [
        "# Repository Snapshot",
        f"Root: {scan['root']}",
        f"Total files: {scan['total_files']}",
        f"Detected languages: {_format_languages(scan['languages'])}",
        "",
        "## File Tree",
        scan["tree"],
        "",
    ]

    if scan["local_errors"]:
        parts.append("## Local Static Checks (found without AI)")
        for error in scan["local_errors"]:
            parts.append(f"- {error}")
        parts.append("")

    for section, heading in (
        ("key_files", "## Key and Configuration Files"),
        ("source_files", "## Source File Contents"),
    ):
        if not scan[section]:
            continue
        parts.append(heading)
        for entry in scan[section]:
            parts.append(
                f"===== {entry['rel']} ({entry['lines']} lines, {entry['size']} bytes) ====="
            )
            parts.append(entry["content"])
            parts.append("")

    if scan["truncated"]:
        parts.append("(Note: some file contents were truncated to fit the model context.)")
    parts.append("--- End of repository snapshot ---")
    return "\n".join(parts)
