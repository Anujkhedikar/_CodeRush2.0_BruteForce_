# test_context.py
# Tests for the context manager: token-budget selection of history,
# snapshot preservation, trimming feedback, and CLI/API wiring.

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from backend.context import build_context, context_budget, estimate_tokens
from backend import cli
import backend.session as session_mod
import backend.mentor as mentor_mod

STORE = Path(tempfile.mkdtemp()) / "sessions.json"
BIG = "x" * 40_000  # ~10_000 estimated tokens


@pytest.fixture(autouse=True)
def isolated_store():
    session_mod._store = None
    session_mod.STORE_PATH = STORE
    if STORE.exists():
        STORE.unlink()
    yield
    session_mod._store = None


def _history(size_chars, snapshot=False, count=4):
    turns = []
    if snapshot:
        turns.append({"role": "user", "content": "# Repository Snapshot\n" + "y" * 4_000})
    for i in range(count):
        turns.append({"role": "user", "content": f"q{i}" + "a" * size_chars})
        turns.append({"role": "assistant", "content": "answer" * 20})
    return turns


# ---------- estimates and budget ----------

def test_estimate_tokens_chars_over_four():
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("") == 1


def test_context_budget_env_override(monkeypatch):
    monkeypatch.setenv("CONTEXT_BUDGET_TOKENS", "500")
    assert context_budget() == 500


def test_context_budget_invalid_env(monkeypatch):
    monkeypatch.setenv("CONTEXT_BUDGET_TOKENS", "banana")
    assert context_budget() == 12_000


# ---------- build_context ----------

def test_build_context_empty_history():
    part, info = build_context("sys", [], "hello")
    assert part == []
    assert info["context_turns"] == 0
    assert info["trimmed_turns"] == 0
    assert info["note"] == ""


def test_build_context_keeps_everything_when_fitting():
    history = _history(50, count=3)
    part, info = build_context("sys", history, "hello", budget_tokens=10_000)
    assert len(part) == 6
    assert info["kept_turns"] == 3
    assert info["trimmed_turns"] == 0
    assert info["note"] == ""
    assert part[0]["content"] == "q0" + "a" * 50


def test_build_context_trims_oldest_when_over_budget():
    history = _history(2_000, count=4)
    part, info = build_context("sys", history, "hello", budget_tokens=1_500)
    assert len(part) == 4
    assert info["trimmed_turns"] == 2
    assert info["note"]
    assert "memory budget" in info["note"]
    assert part[0]["content"] == "q2" + "a" * 2_000
    assert part[2]["content"] == "q3" + "a" * 2_000, "most recent turn must be kept"
    assert part[-1]["role"] == "assistant"


def test_build_context_never_exceeds_budget():
    history = _history(500, count=6)
    _, info = build_context("sys", history, "hello", budget_tokens=2_000)
    assert info["estimated_tokens"] <= 2_000 + 200  # small slack for message overhead


def test_build_context_snapshot_always_kept():
    history = _history(2_000, count=4, snapshot=True)
    part, info = build_context("sys", history, "hello", budget_tokens=500)
    assert part and part[0]["content"].startswith("# Repository Snapshot")
    assert info["kept_turns"] < 4
    assert info["trimmed_turns"] >= 1


def test_build_context_snapshot_only_over_budget():
    history = _history(2_000, count=4, snapshot=True)
    part, info = build_context("sys", history, "hello", budget_tokens=100)
    assert len(part) == 1
    assert part[0]["content"].startswith("# Repository Snapshot")
    assert info["kept_turns"] == 0
    assert info["trimmed_turns"] == 4


# ---------- CLI wiring ----------

def _fake_call(content="answer"):
    def fake(messages, max_tokens=900, **kwargs):
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "llama-3.3-70b-versatile",
        }
    return fake


def _run_cli(piped, budget=None):
    out = io.StringIO()
    sent = []

    def fake(messages, max_tokens=900, **kwargs):
        sent.append(messages)
        return {
            "choices": [{"message": {"content": "answer"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "llama-3.3-70b-versatile",
        }

    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        sys.stdin = io.StringIO(piped)
        with mock.patch.object(mentor_mod, "call_openai", side_effect=fake):
            try:
                cli.run_cli(None, None, None)
            except SystemExit:
                pass
    return out.getvalue(), sent


def test_cli_trims_context_and_tells_model():
    budget = "500"
    os.environ["CONTEXT_BUDGET_TOKENS"] = budget
    try:
        # round 1: big input (no history to trim), round 2: another big input
        out, sent = _run_cli(f"1\n\n{BIG}\n\ny\n1\n\n{BIG}\n\nn\n")
    finally:
        os.environ.pop("CONTEXT_BUDGET_TOKENS", None)

    assert len(sent) == 3, "two mentor asks plus one memory summarization"
    assert "Note:" in sent[1][-1]["content"], "model must be told history was trimmed"
    assert "memory budget" in sent[1][-1]["content"]
    assert "tiered memory" in sent[2][0]["content"], "trimmed turns are summarized"
    assert "folded into the session memory summary" in out

    session = list(session_mod._load()["sessions"].values())[0]
    second_assistant = session["turns"][-1]
    assert second_assistant["context"]["trimmed_turns"] >= 1
    assert second_assistant["context"]["kept_turns"] < second_assistant["context"]["trimmed_turns"]


def test_cli_no_trimming_when_context_fits():
    out, sent = _run_cli("1\n\nshort query\n\ny\n1\n\nanother short query\n\nn\n")
    assert len(sent) == 2
    assert "Note:" not in sent[1][-1]["content"]
    session = list(session_mod._load()["sessions"].values())[0]
    assert session["turns"][-1]["context"]["trimmed_turns"] == 0


# ---------- API wiring ----------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("backend.session.STORE_PATH", STORE)
    monkeypatch.setattr("backend.session._store", None)
    from backend.app import app
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client


def test_api_returns_context_info(client):
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call()):
        response = client.post("/mentor", json={
            "mode": "explain", "language": "python", "input_text": "short",
        })
    assert response.status_code == 200
    body = response.json()
    assert body["context"]["kept_turns"] == 0
    assert body["context"]["trimmed_turns"] == 0
    assert body["context"]["budget_tokens"] == 12_000


def test_api_trims_second_round(client, monkeypatch):
    monkeypatch.setenv("CONTEXT_BUDGET_TOKENS", "200")
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call()):
        first = client.post("/mentor", json={
            "mode": "explain", "language": "python", "input_text": BIG,
        })
        sid = first.json()["session_id"]
        second = client.post("/mentor", json={
            "mode": "explain", "language": "python", "input_text": BIG, "session_id": sid,
        })
    body = second.json()
    assert body["context"]["trimmed_turns"] >= 1
    assert "memory budget" in body["context"]["note"]

    session = session_mod.get_session(sid)
    assert session["turns"][-1]["context"]["trimmed_turns"] == body["context"]["trimmed_turns"]


def test_api_repo_report_keeps_snapshot(client, monkeypatch):
    monkeypatch.setenv("CONTEXT_BUDGET_TOKENS", "200")
    repo_path = Path(tempfile.mkdtemp()) / "repo"
    repo_path.mkdir()
    for i in range(6):
        (repo_path / f"file{i}.py").write_text(f"def f{i}():\n    return '{'x' * 3000}'\n", encoding="utf-8")
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call()):
        first = client.post("/mentor", json={
            "mode": "repo_report", "language": "", "input_text": str(repo_path),
        })
        sid = first.json()["session_id"]
        assert first.json()["context"]["kept_turns"] == 0

        second = client.post("/mentor", json={
            "mode": "repo_report", "language": "", "input_text": "more?",
            "session_id": sid,
        })
    session = session_mod.get_session(sid)
    snapshot_turn = session["turns"][0]
    assert snapshot_turn["content"].startswith("# Repository Snapshot")
    assert second.json()["context"]["kept_turns"] == 0
    assert second.json()["context"]["trimmed_turns"] == 1
