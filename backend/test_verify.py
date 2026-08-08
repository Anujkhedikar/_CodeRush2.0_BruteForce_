# test_verify.py
# Tests for the verification-first layer: code extraction, static checks
# per language, and the CLI/API wiring that shows verdicts to the user.

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from backend.verify import (
    extract_code_blocks,
    syntax_issues,
    verify_code,
    verify_text,
)
from backend import cli
import backend.session as session_mod
import backend.mentor as mentor_mod

STORE = Path(tempfile.mkdtemp()) / "sessions.json"


@pytest.fixture(autouse=True)
def isolated_store():
    session_mod._store = None
    session_mod.STORE_PATH = STORE
    if STORE.exists():
        STORE.unlink()
    yield
    session_mod._store = None


# ---------- code block extraction ----------

def test_extract_code_blocks_with_languages():
    text = ("intro\n```python\nprint(1)\n```\nmore\n```js\nconst a = 1;\n```")
    blocks = extract_code_blocks(text)
    assert [b["language"] for b in blocks] == ["python", "javascript"]
    assert blocks[0]["code"] == "print(1)"


def test_extract_code_blocks_without_language():
    blocks = extract_code_blocks("```\nx = 1\n```")
    assert len(blocks) == 1
    assert blocks[0]["language"] == ""
    assert blocks[0]["code"] == "x = 1"


def test_extract_code_blocks_none():
    assert extract_code_blocks("no fences here") == []


def test_extract_code_blocks_ignores_empty():
    assert extract_code_blocks("```python\n```") == []


# ---------- python checks ----------

def test_python_clean_code():
    report = verify_code("python", "def add(a, b):\n    return a + b\nprint(add(1, 2))")
    assert report["status"] == "ok"
    assert report["checks"] == ["syntax", "undefined names"]


def test_python_syntax_error():
    report = verify_code("python", "def add(:\n    pass")
    assert report["status"] == "issues"
    assert report["issues"][0]["line"] == 1
    assert "syntax error" in report["issues"][0]["message"]


def test_python_undefined_name_module_level():
    report = verify_code("python", "print(add(1, missing))")
    assert report["status"] == "issues"
    messages = [i["message"] for i in report["issues"]]
    assert "undefined name 'missing'" in messages
    assert "undefined name 'add'" in messages, "call before definition is a real NameError"


def test_python_function_defined_later_resolves():
    report = verify_code("python", "def add(a, b):\n    return a + b\nprint(add(1, 2))")
    assert report["status"] == "ok"


def test_python_function_args_are_defined():
    report = verify_code("python", "def add(a, b):\n    return a + b")
    assert report["status"] == "ok", report


def test_python_builtins_not_flagged():
    report = verify_code("python", "print(len([1, 2]))\nvalue = int('3')")
    assert report["status"] == "ok"


def test_python_nested_scope():
    report = verify_code(
        "python",
        "def outer():\n    x = 1\n    def inner():\n        return x + y\n",
    )
    assert report["status"] == "issues"
    assert any("undefined name 'y'" in i["message"] for i in report["issues"])
    assert not any("'x'" in i["message"] for i in report["issues"]), "closure var must resolve"


def test_python_import_resolves():
    report = verify_code("python", "import math\nprint(math.sqrt(4))")
    assert report["status"] == "ok"


# ---------- javascript ----------

@mock.patch("backend.verify.shutil.which")
def test_javascript_uses_node_check(mock_which):
    mock_which.return_value = "C:\\node.exe"
    with mock.patch("backend.verify.subprocess.run") as mock_run:
        ok = mock.MagicMock()
        ok.returncode = 0
        mock_run.return_value = ok
        report = verify_code("javascript", "const x = 1;")
        assert report["status"] == "ok"
        assert report["checks"] == ["node --check"]
        assert mock_run.call_args[0][0][:2] == ["node", "--check"]


@mock.patch("backend.verify.shutil.which")
def test_javascript_node_finds_syntax_error(mock_which):
    mock_which.return_value = "C:\\node.exe"
    bad = mock.MagicMock()
    bad.returncode = 1
    bad.stderr = "C:\\tmp\\file.js:2:5\nSyntaxError: Unexpected token\n"
    with mock.patch("backend.verify.subprocess.run", return_value=bad):
        report = verify_code("javascript", "const x = ;")
    assert report["status"] == "issues"
    assert report["issues"][0]["line"] == 2


@mock.patch("backend.verify.shutil.which")
def test_javascript_fallback_without_node(mock_which):
    mock_which.return_value = None
    report = verify_code("javascript", "const x = 1;")
    assert report["status"] == "ok"
    assert report["checks"] == ["delimiter balance"]


# ---------- delimiter fallback for other languages ----------

def test_cpp_delimiters_balanced_ignoring_strings():
    code = 'int main() { printf("}"); return 0; } // {'
    report = verify_code("cpp", code)
    assert report["status"] == "ok"


def test_java_unbalanced_reported():
    report = verify_code("java", "class A { int x;")
    assert report["status"] == "issues"
    assert "unbalanced delimiter" in report["issues"][0]["message"]


# ---------- syntax_issues (input pre-check) ----------

def test_syntax_issues_reports_only_syntax():
    issues = syntax_issues("python", "def add(:\n    pass")
    assert len(issues) == 1
    assert "syntax error" in issues[0]["message"]


def test_syntax_issues_ignores_undefined_names():
    assert syntax_issues("python", "print(undefined_var)") == []


def test_syntax_issues_java_uses_delimiters():
    assert len(syntax_issues("java", "class A { int x;")) == 1


# ---------- verify_text aggregation ----------

def test_verify_text_aggregates_blocks():
    text = ("```python\nprint(missing)\n```\n```python\nx = 1\n```")
    report = verify_text(text, "python")
    assert report["status"] == "issues"
    assert len(report["blocks"]) == 2
    assert report["blocks"][0]["status"] == "issues"
    assert report["blocks"][1]["status"] == "ok"


def test_verify_text_no_code():
    assert verify_text("just prose")["status"] == "no_code"


# ---------- language hint wins over miscapped fences ----------

def test_verify_text_hint_wins_over_miscapped_fence():
    """Model caps C++ code as ```python: the user's 'cpp' choice must win."""
    text = "```python\n#include <iostream>\nint main() { return 0; }\n```"
    report = verify_text(text, "cpp")
    assert report["status"] == "ok"
    block = report["blocks"][0]
    assert block["language"] == "cpp"
    assert block["checks"] == ["delimiter balance"]


def test_verify_text_hint_prevents_wrong_python_check():
    cpp_code = "int main() { int x = 5; return x; }"
    report = verify_text(f"```python\n{cpp_code}\n```", "cpp")
    assert report["status"] == "ok"
    assert not any("undefined name" in i["message"]
                   for b in report["blocks"] for i in b.get("issues", []))


def test_verify_text_no_hint_uses_fence_language():
    text = "```python\nprint(missing)\n```"
    report = verify_text(text)
    assert report["blocks"][0]["language"] == "python"
    assert report["status"] == "issues"


def test_verify_text_hint_still_uses_fence_when_matching():
    text = "```c++\nint main() { return 0; }\n```"
    report = verify_text(text, "cpp")
    assert report["blocks"][0]["language"] == "cpp"


def test_cli_cpp_generate_shows_cpp_not_python():
    content = "```python\nint main() { return missing; }\n```"
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        text = _run_cli("3\n4\n\nwrite a cpp program\n\nn\n")
    assert "Verification (cpp)" in text
    assert "Verification (python)" not in text
    assert "undefined name" not in text


# ---------- CLI wiring ----------

def _fake_call(content, model="llama-3.3-70b-versatile"):
    def fake(messages, max_tokens=900, **kwargs):
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": model,
        }
    return fake


def _run_cli(piped):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        sys.stdin = io.StringIO(piped)
        try:
            cli.run_cli(None, None, None)
        except SystemExit as exc:
            pass
    return out.getvalue()


def test_cli_generate_shows_verification_and_stores_it():
    content = "Here you go:\n```python\ndef f():\n    return missing\n```"
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        text = _run_cli("3\n\nwrite a function\n\nn\n")
    assert "Verification (python)" in text
    assert "undefined name 'missing'" in text

    session = list(session_mod._load()["sessions"].values())[0]
    assistant_turn = session["turns"][-1]
    assert assistant_turn["verification"]["status"] == "issues"
    assert assistant_turn["verification"]["blocks"][0]["issues"][0]["line"] == 2


def test_cli_generate_clean_code_verified_ok():
    content = "```python\nx = 1\nprint(x)\n```"
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        text = _run_cli("3\n\nwrite a function\n\nn\n")
    assert "Verification (python): 1 code block(s) checked" in text
    assert "block 1: OK" in text


def test_cli_generate_no_code_skips_verification():
    content = "Just prose, no code here."
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        text = _run_cli("3\n\nwrite a function\n\nn\n")
    assert "Verification" not in text


def test_cli_error_finder_prechecks_input_syntax():
    content = "The bug is on line 1."
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        text = _run_cli("2\n\nif True print('bad')\n\nn\n")
    assert "Input syntax check: 1 issue(s) found before asking the model" in text

    session = list(session_mod._load()["sessions"].values())[0]
    user_turn = session["turns"][0]
    assert user_turn["input_check"][0]["line"] == 1


def test_cli_view_shows_verification_status():
    content = "```python\nx = missing\n```"
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        _run_cli("3\n\nwrite a function\n\nn\n")
    sid = list(session_mod._load()["sessions"])[0]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli._cmd_view(sid)
    assert "[verification: 1 issue(s)]" in out.getvalue()


# ---------- API wiring ----------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("backend.session.STORE_PATH", STORE)
    monkeypatch.setattr("backend.session._store", None)
    from backend.app import app
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client


def test_api_mentor_returns_verification(client):
    content = "```python\ndef f():\n    return missing\n```"
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        response = client.post("/mentor", json={
            "mode": "generate", "language": "python", "input_text": "write a function",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["verification"]["status"] == "issues"
    assert body["verification"]["blocks"][0]["language"] == "python"


def test_api_mentor_input_check_on_error_finder(client):
    content = "Line 1 is broken."
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        response = client.post("/mentor", json={
            "mode": "error_finder", "language": "python",
            "input_text": "if True print('bad')",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["input_check"] and body["input_check"][0]["line"] == 1


def test_api_mentor_explain_mode_no_verification(client):
    content = "```python\nprint('ok')\n```"
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call(content)):
        response = client.post("/mentor", json={
            "mode": "explain", "language": "python", "input_text": "print(1)",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["verification"] is None
    assert body["input_check"] is None


# ---------- language must reach the model prompt ----------

def _fake_call_capturing(captured):
    def fake(messages, max_tokens=900, **kwargs):
        captured["messages"] = messages
        return {
            "choices": [{"message": {"content": "answer"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "llama-3.3-70b-versatile",
        }
    return fake


def test_api_mentor_sends_selected_language_to_model(client):
    captured = {}
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call_capturing(captured)):
        response = client.post("/mentor", json={
            "mode": "generate", "language": "cpp", "input_text": "create a heart",
        })
    assert response.status_code == 200
    user_content = captured["messages"][-1]["content"]
    assert "Language: C++" in user_content
    assert "Feature: Generate" in user_content
    assert "create a heart" in user_content

    session = session_mod.get_session(response.json()["session_id"])
    assert session["turns"][0]["content"] == "create a heart", "stored turn keeps raw input"


def test_api_mentor_omits_language_line_when_empty(client):
    captured = {}
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call_capturing(captured)):
        response = client.post("/mentor", json={
            "mode": "explain", "language": "", "input_text": "what is this",
        })
    assert response.status_code == 200
    user_content = captured["messages"][-1]["content"]
    assert "Language:" not in user_content
    assert "Feature: Explain" in user_content


def test_cli_sends_selected_language_to_model():
    captured = {}
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call_capturing(captured)):
        _run_cli("3\n4\n\ncreate a heart\n\nn\n")
    user_content = captured["messages"][-1]["content"]
    assert "Language: C++" in user_content
    assert "create a heart" in user_content

    session = list(session_mod._load()["sessions"].values())[0]
    assert session["turns"][0]["content"] == "create a heart", "stored turn keeps raw input"


def test_cli_repo_mode_sends_summary_unwrapped():
    captured = {}
    repo_path = Path(tempfile.mkdtemp()) / "repo"
    repo_path.mkdir()
    (repo_path / "main.py").write_text("print('hi')", encoding="utf-8")
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call_capturing(captured)):
        _run_cli(f"5\n{repo_path}\nn\n")
    user_content = captured["messages"][-1]["content"]
    assert user_content.startswith("# Repository Snapshot")
    assert "Language:" not in user_content


# ---------- a language mentioned in the text wins over the selection ----------

def test_detect_language_mentions():
    mentor = mentor_mod.CodeMentor()
    assert mentor.detect_language("create a heart in python") == "python"
    assert mentor.detect_language("write it in Java please") == "java"
    assert mentor.detect_language("convert this to c++") == "cpp"
    assert mentor.detect_language("do it in C") == "c"
    assert mentor.detect_language("explain this code") == ""


def test_detect_language_cpp_not_swallowed_by_c():
    mentor = mentor_mod.CodeMentor()
    assert mentor.detect_language("a C++ program using C") == "cpp"


def test_api_mention_overrides_selection(client):
    captured = {}
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call_capturing(captured)):
        response = client.post("/mentor", json={
            "mode": "generate", "language": "cpp", "input_text": "create a heart in python",
        })
    assert response.status_code == 200
    user_content = captured["messages"][-1]["content"]
    assert "Language: Python" in user_content
    assert "Language: C++" not in user_content
    assert response.json()["language"] == "python"


def test_api_no_mention_uses_selection(client):
    captured = {}
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call_capturing(captured)):
        client.post("/mentor", json={
            "mode": "generate", "language": "cpp", "input_text": "create a heart",
        })
    user_content = captured["messages"][-1]["content"]
    assert "Language: C++" in user_content


def test_cli_mention_overrides_selection():
    captured = {}
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call_capturing(captured)):
        _run_cli("3\n4\n\ncreate a heart in python\n\nn\n")
    user_content = captured["messages"][-1]["content"]
    assert "Language: Python" in user_content
    assert "Language: C++" not in user_content


def test_verification_uses_effective_language(client):
    content = "```python\ndef f():\n    return missing\n```"
    captured = {}
    def fake(messages, max_tokens=900, **kwargs):
        captured["messages"] = messages
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "llama-3.3-70b-versatile",
        }
    with mock.patch.object(mentor_mod, "call_openai", side_effect=fake):
        response = client.post("/mentor", json={
            "mode": "generate", "language": "cpp", "input_text": "write this in python",
        })
    body = response.json()
    assert body["verification"]["blocks"][0]["language"] == "python"
    assert "undefined name 'missing'" in body["verification"]["blocks"][0]["issues"][0]["message"]
