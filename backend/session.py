# session.py
# Persistent session store for the CodeMentor AI harness.
# Every conversation turn is recorded with metadata (query, mode, model,
# token usage, context size, duration, timestamp) so both the CLI and the
# web app can inspect history and memory/token usage of each query.
#
# Data is kept in backend/sessions.json (git-ignored).

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

STORE_PATH = Path(__file__).resolve().parent / "sessions.json"

MAX_SESSIONS = 50
MAX_TURNS_PER_SESSION = 40

REPO_SNAPSHOT_MARKER = "# Repository Snapshot"

_lock = threading.Lock()
_store: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    global _store
    if _store is None:
        _store = {}
        if STORE_PATH.exists():
            try:
                _store = json.loads(STORE_PATH.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                _store = {}
        _store.setdefault("sessions", {})
        _store.setdefault("next_id", 1)
    return _store


def _save() -> None:
    try:
        STORE_PATH.write_text(
            json.dumps(_store, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass  # non-fatal: history simply does not persist


def _prune() -> None:
    sessions = _load()["sessions"]
    while len(sessions) > MAX_SESSIONS:
        oldest = min(sessions, key=lambda sid: sessions[sid]["updated_at"])
        del sessions[oldest]


def create_session() -> str:
    """Create a new session and return its id."""
    with _lock:
        store = _load()
        sid = str(store["next_id"])
        store["next_id"] += 1
        now = time.time()
        store["sessions"][sid] = {
            "id": sid,
            "created_at": now,
            "updated_at": now,
            "turns": [],
        }
        _prune()
        _save()
        return sid


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return _load()["sessions"].get(session_id)


def history(session_id: str) -> List[Dict[str, str]]:
    """The message history (role/content only) used to build LLM requests."""
    session = get_session(session_id)
    if not session:
        return []
    return [
        {"role": turn["role"], "content": turn["content"]}
        for turn in session["turns"]
    ]


def trim_history(history: List[Dict[str, str]], max_messages: int = 12) -> List[Dict[str, str]]:
    """Keep the first turn (e.g. a repository snapshot) and the most recent turns."""
    if len(history) <= max_messages:
        return history
    return history[:1] + history[-(max_messages - 1):]


def append_turn(session_id: str, turn: Dict[str, Any]) -> bool:
    """Record one turn (user or assistant) with its metadata."""
    with _lock:
        session = get_session(session_id)
        if not session:
            return False
        session["turns"].append(turn)
        session["updated_at"] = time.time()
        turns = session["turns"]
        if len(turns) > MAX_TURNS_PER_SESSION:
            session["turns"] = turns[:1] + turns[-(MAX_TURNS_PER_SESSION - 1):]
        _save()
        return True


def total_tokens(session: Dict[str, Any]) -> int:
    return sum(
        (turn.get("usage") or {}).get("total_tokens", 0)
        for turn in session.get("turns", [])
    )


def get_memory(session_id: str) -> Optional[Dict[str, Any]]:
    """The tiered-memory summary of a session, or None.

    Memory is a condensed paragraph of the turns that were trimmed from the
    active context; it travels with every request so the agent still knows
    what was discussed even after the raw turns are gone.
    """
    session = get_session(session_id)
    return session.get("memory") if session else None


def set_memory(session_id: str, summary: str, turns_summarized: int) -> bool:
    """Persist the memory summary (and how many turns it covers)."""
    with _lock:
        session = get_session(session_id)
        if not session:
            return False
        session["memory"] = {
            "summary": summary,
            "turns_summarized": turns_summarized,
            "updated_at": time.time(),
        }
        _save()
        return True


def list_sessions() -> List[Dict[str, Any]]:
    """Compact session summaries for the sidebar (no full message contents)."""
    sessions = _load()["sessions"]
    summaries = []
    for session in sorted(
        sessions.values(), key=lambda s: s["updated_at"], reverse=True
    ):
        turns = session.get("turns", [])
        preview = ""
        for turn in turns:
            if turn.get("role") == "user":
                preview = turn["content"].strip()
                break
        preview = preview[:90] + "..." if len(preview) > 90 else preview
        summaries.append(
            {
                "id": session["id"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "turn_count": len(turns),
                "total_tokens": total_tokens(session),
                "preview": preview,
            }
        )
    return summaries


def delete_session(session_id: str) -> bool:
    with _lock:
        sessions = _load()["sessions"]
        if session_id not in sessions:
            return False
        del sessions[session_id]
        _save()
        return True


def has_repo_snapshot(session_id: str) -> bool:
    """True if this session already contains the repository snapshot turn."""
    turns = get_session(session_id).get("turns", []) if get_session(session_id) else []
    for turn in turns:
        if turn.get("content", "").startswith(REPO_SNAPSHOT_MARKER):
            return True
    return False
