# test_memory.py
# Tests for tiered memory: LLM condensation of trimmed turns with a
# deterministic fallback, session persistence, and CLI/API wiring.

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from backend.memory import (
    MAX_MEMORY_CHARS,
    build_memory_summary,
    extractive_summary,
)
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


def _fake_call(content="answer"):
    def fake(messages, max_tokens=900, **kwargs):
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "llama-3.3-70b-versatile",
        }
    return fake


# ---------- extractive summary (deterministic fallback) ----------

def test_extractive_summary_bullets_user_previews():
    messages = [
        {"role": "user", "content": "how do I fix a segfault in c"},
        {"role": "assistant", "content": "check your pointers"},
    ]
    result = extractive_summary(messages)
    assert result.startswith("- how do I fix a segfault in c")


def test_extractive_summary_keeps_existing_first():
    messages = [{"role": "user", "content": "new question"}]
    result = extractive_summary(messages, existing="old memory")
    assert result.startswith("old memory")
    assert "- new question" in result


def test_extractive_summary_skips_snapshot():
    messages = [
        {"role": "user", "content": "# Repository Snapshot\nlots of files"},
        {"role": "user", "content": "the real question"},
    ]
    result = extractive_summary(messages)
    assert "Snapshot" not in result
    assert "the real question" in result


def test_extractive_summary_caps_length():
    result = extractive_summary([{"role": "user", "content": "y" * 50_000}])
    assert len(result) <= MAX_MEMORY_CHARS


# ---------- LLM summarization and fallback ----------

def test_build_memory_summary_uses_llm_and_merges_existing():
    mentor = mentor_mod.CodeMentor()
    sent = []

    def fake(messages, max_tokens=900, **kwargs):
        sent.append(messages)
        return {
            "choices": [{"message": {"content": "merged summary"}}],
            "usage": {},
            "model": "x",
        }

    with mock.patch.object(mentor_mod, "call_openai", side_effect=fake):
        result = build_memory_summary(
            mentor, [{"role": "user", "content": "q"}], existing_summary="old"
        )
    assert result == "merged summary"
    assert sent and sent[0][0]["role"] == "system"
    assert "tiered memory" in sent[0][0]["content"]
    assert "old" in sent[0][-1]["content"], "existing memory is folded in"


def test_build_memory_summary_falls_back_when_llm_fails():
    mentor = mentor_mod.CodeMentor()
    with mock.patch.object(mentor_mod, "call_openai", side_effect=RuntimeError("no key")):
        result = build_memory_summary(
            mentor, [{"role": "user", "content": "question about arrays"}]
        )
    assert result.startswith("- question about arrays")


def test_build_memory_summary_falls_back_when_empty():
    mentor = mentor_mod.CodeMentor()
    with mock.patch.object(
        mentor_mod, "call_openai", side_effect=_fake_call(content="")
    ):
        result = build_memory_summary(mentor, [{"role": "user", "content": "q"}])
    assert result.startswith("- q")


def test_build_memory_summary_empty_input_keeps_existing():
    mentor = mentor_mod.CodeMentor()
    assert build_memory_summary(mentor, [], existing_summary="keep me") == "keep me"


def test_build_memory_summary_extractive_when_disabled(monkeypatch):
    monkeypatch.setenv("MEMORY_SUMMARIZATION", "0")
    mentor = mentor_mod.CodeMentor()

    def fail(messages, max_tokens=900, **kwargs):
        raise AssertionError("LLM must not be called")

    with mock.patch.object(mentor_mod, "call_openai", side_effect=fail):
        result = build_memory_summary(mentor, [{"role": "user", "content": "disable me"}])
    assert result.startswith("- disable me")


# ---------- session persistence ----------

def test_set_and_get_memory():
    sid = session_mod.create_session()
    assert session_mod.get_memory(sid) is None
    assert session_mod.set_memory(sid, "summary text", 3)
    memory = session_mod.get_memory(sid)
    assert memory["summary"] == "summary text"
    assert memory["turns_summarized"] == 3
    assert "updated_at" in memory


def test_set_memory_unknown_session():
    assert not session_mod.set_memory("nope", "x", 1)


# ---------- context integration ----------

def test_build_context_includes_memory_message():
    from backend.context import build_context

    history = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
    part, info = build_context(
        "sys",
        history,
        "hello",
        memory={"summary": "remember the c work", "turns_summarized": 4},
    )
    assert part[0]["role"] == "system"
    assert "[Memory summary" in part[0]["content"]
    assert "remember the c work" in part[0]["content"]
    assert info["memory_turns"] == 4
    assert info["memory_summary"]


def test_build_context_trim_note_mentions_memory():
    from backend.context import build_context

    history = []
    for i in range(4):
        history.append({"role": "user", "content": f"q{i}" + "a" * 2_000})
        history.append({"role": "assistant", "content": "answer" * 20})
    part, info = build_context(
        "sys", history, "hello", budget_tokens=1_500,
        memory={"summary": "old", "turns_summarized": 2},
    )
    assert info["trimmed_turns"] >= 1
    assert "folded into your memory summary" in info["note"]


# ---------- CLI wiring ----------

def _run_cli(piped, budget):
    out = io.StringIO()
    sent = []

    def fake(messages, max_tokens=900, **kwargs):
        sent.append(messages)
        return {
            "choices": [{"message": {"content": "answer"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "llama-3.3-70b-versatile",
        }

    os.environ["CONTEXT_BUDGET_TOKENS"] = budget
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            sys.stdin = io.StringIO(piped)
            with mock.patch.object(mentor_mod, "call_openai", side_effect=fake):
                try:
                    cli.run_cli(None, None, None)
                except SystemExit:
                    pass
    finally:
        os.environ.pop("CONTEXT_BUDGET_TOKENS", None)
    return out.getvalue(), sent


def test_cli_memory_grows_and_rides_next_round():
    # Round 1: big input (nothing to trim yet). Round 2: big input -> trim -> memory.
    # Round 3: short input -> the memory summary must ride with the request.
    out, sent = _run_cli(
        f"1\n\n{BIG}\n\ny\n1\n\n{BIG}\n\ny\n1\n\nshort\n\nn\n", budget="500"
    )
    assert len(sent) == 5, "three mentor asks plus two summarizations"
    assert "folded into the session memory summary" in out

    session = list(session_mod._load()["sessions"].values())[0]
    memory = session.get("memory")
    assert memory and memory["summary"]
    assert memory["turns_summarized"] >= 1

    third = sent[3]  # round 3 request (round 2's fold is sent[2])
    memory_messages = [
        m for m in third
        if m.get("role") == "system" and "[Memory summary" in m.get("content", "")
    ]
    assert memory_messages, "memory summary must ride with later requests"
    assert "answer" in memory_messages[0]["content"], "folded summary reached the model"
    assert "folded into your memory summary" in third[-1]["content"]


def test_cli_no_memory_when_nothing_trimmed():
    _run_cli("1\n\nshort\n\nn\n", budget="500")
    session = list(session_mod._load()["sessions"].values())[0]
    assert "memory" not in session


def test_cli_view_shows_memory():
    sid = session_mod.create_session()
    session_mod.set_memory(sid, "long memory content " * 20, 4)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli._cmd_view(sid)
    text = out.getvalue()
    assert "Memory:" in text
    assert "summarizes 4 turn(s)" in text


# ---------- API wiring ----------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("backend.session.STORE_PATH", STORE)
    monkeypatch.setattr("backend.session._store", None)
    from backend.app import app
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client


def test_api_memory_rides_later_requests(client, monkeypatch):
    monkeypatch.setenv("CONTEXT_BUDGET_TOKENS", "200")
    with mock.patch.object(mentor_mod, "call_openai", side_effect=_fake_call()):
        first = client.post("/mentor", json={
            "mode": "explain", "language": "python", "input_text": BIG,
        })
        sid = first.json()["session_id"]
        second = client.post("/mentor", json={
            "mode": "explain", "language": "python", "input_text": BIG, "session_id": sid,
        })
        third = client.post("/mentor", json={
            "mode": "explain", "language": "python", "input_text": "short", "session_id": sid,
        })
    body = third.json()
    assert body["context"]["memory_turns"] >= 1
    assert "memory budget" in body["context"]["note"]

    session = session_mod.get_session(sid)
    assert session["memory"]["turns_summarized"] == body["context"]["memory_turns"]
