# test_observability.py
# Tests for the usage analytics layer: cost estimation and aggregates
# across the session store, plus the /stats endpoint and CLI /stats command.

import contextlib
import io
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

import backend.session as session_mod
from backend.observability import (
    DEFAULT_PRICE,
    MODEL_PRICING,
    estimate_cost,
    overview,
    session_cost,
)
from backend import cli

STORE = Path(tempfile.mkdtemp()) / "sessions.json"
MODEL = "llama-3.3-70b-versatile"


@pytest.fixture(autouse=True)
def isolated_store():
    session_mod._store = None
    session_mod.STORE_PATH = STORE
    if STORE.exists():
        STORE.unlink()
    yield
    session_mod._store = None


def make_session(model=MODEL, prompt=1000, completion=500, mode="explain",
                 provider="groq", timestamp=None):
    sid = session_mod.create_session()
    session_mod.append_turn(sid, {
        "role": "user", "content": "query", "mode": mode,
        "language": "python", "timestamp": timestamp or time.time(),
    })
    session_mod.append_turn(sid, {
        "role": "assistant", "content": "answer", "mode": mode,
        "model": model, "provider": provider,
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion,
                  "total_tokens": prompt + completion},
        "context_turns": 1, "duration_ms": 100.0, "timestamp": timestamp or time.time(),
    })
    return sid


# ---------- cost estimation ----------

def test_estimate_cost_known_model():
    cost = estimate_cost(MODEL, {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert cost == round(MODEL_PRICING[MODEL]["input"] + MODEL_PRICING[MODEL]["output"], 6)


def test_estimate_cost_unknown_model_uses_default():
    cost = estimate_cost("openrouter/auto", {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
    assert cost == round(DEFAULT_PRICE["input"] + DEFAULT_PRICE["output"], 6)


def test_estimate_cost_empty_usage_is_zero():
    assert estimate_cost(MODEL, None) == 0.0
    assert estimate_cost(MODEL, {}) == 0.0


# ---------- aggregates ----------

def test_overview_totals():
    make_session(prompt=1000, completion=500)
    make_session(prompt=2000, completion=500, mode="error_finder")
    stats = overview()

    assert stats["totals"]["sessions"] == 2
    assert stats["totals"]["turns"] == 2
    assert stats["totals"]["prompt_tokens"] == 3000
    assert stats["totals"]["completion_tokens"] == 1000
    assert stats["totals"]["total_tokens"] == 4000
    expected_cost = (3000 * MODEL_PRICING[MODEL]["input"]
                     + 1000 * MODEL_PRICING[MODEL]["output"]) / 1_000_000
    assert stats["totals"]["cost"] == round(expected_cost, 6)


def test_overview_empty_store():
    stats = overview()
    assert stats["totals"]["sessions"] == 0
    assert stats["totals"]["turns"] == 0
    assert stats["totals"]["total_tokens"] == 0
    assert stats["by_day"] and len(stats["by_day"]) == 14
    assert stats["by_mode"] == []
    assert stats["top_sessions"] == []


def test_overview_breakdowns_by_mode_provider_and_day():
    ts = time.time() - 3600
    make_session(mode="explain", timestamp=ts)
    make_session(mode="explain", timestamp=ts)
    make_session(mode="generate", provider="openrouter",
                 model="openrouter/auto", timestamp=ts)
    stats = overview()

    by_mode = {row["name"]: row for row in stats["by_mode"]}
    assert by_mode["explain"]["turns"] == 2
    assert by_mode["generate"]["turns"] == 1
    assert by_mode["explain"]["tokens"] == 3000

    by_provider = {row["name"]: row for row in stats["by_provider"]}
    assert by_provider["groq"]["turns"] == 2
    assert by_provider["openrouter"]["turns"] == 1

    active_days = [day for day in stats["by_day"] if day["turns"]]
    assert len(active_days) == 1
    assert active_days[0]["tokens"] == 4500


def test_overview_top_sessions_sorted_by_cost():
    make_session(prompt=1000, completion=500)
    make_session(prompt=4000, completion=2000)
    stats = overview()
    top = stats["top_sessions"]
    assert len(top) == 2
    assert top[0]["tokens"] == 6000
    assert top[0]["cost"] >= top[1]["cost"]


def test_session_cost_matches_turn_sum():
    sid = make_session(prompt=1000, completion=500)
    session = session_mod.get_session(sid)
    assert session_cost(session) == estimate_cost(
        MODEL, {"prompt_tokens": 1000, "completion_tokens": 500}
    )


# ---------- CLI /stats command ----------

def run_cli_stats():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli._handle_command("stats", "", {"session_id": "1"})
    return out.getvalue()


def test_cli_stats_empty():
    text = run_cli_stats()
    assert "No usage recorded yet" in text


def test_cli_stats_shows_aggregates():
    make_session(prompt=1000, completion=500)
    text = run_cli_stats()
    assert "1 session(s)" in text
    assert "Usage Analytics" in text
    assert "By mode" in text
    assert "explain" in text
    assert "$" in text


def test_cli_stats_unknown_command_rejected():
    assert cli._parse_command("/nosuchcommand") is None


def test_cli_view_shows_cost_per_turn():
    sid = make_session(prompt=1000, completion=500)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli._cmd_view(sid)
    text = out.getvalue()
    assert "est. $" in text
    assert "tokens: 1000 in / 500 out" in text


# ---------- /stats API endpoint ----------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("backend.session.STORE_PATH", STORE)
    monkeypatch.setattr("backend.session._store", None)
    from backend.app import app
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client


def test_stats_endpoint_empty(client):
    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["sessions"] == 0
    assert len(body["by_day"]) == 14


def test_stats_endpoint_after_usage(client):
    make_session(prompt=1000, completion=500)
    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["turns"] == 1
    assert body["totals"]["total_tokens"] == 1500
    assert body["totals"]["cost"] > 0
    assert body["by_mode"][0]["name"] == "explain"
