# app.py
# FastAPI routes for the CodeMentor AI backend.
# Serves the mentor endpoint (session-aware) plus session history endpoints
# that expose per-turn metadata: query, mode, model, token usage, context
# size, duration, and timestamp.

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from .context import build_context
    from .memory import build_memory_summary
    from .mentor import CodeMentor
    from .observability import overview
    from .repo import build_repo_summary, scan_repo
    from .session import (
        append_turn,
        create_session,
        delete_session,
        get_memory,
        get_session,
        has_repo_snapshot,
        history,
        list_sessions,
        set_memory,
    )
    from .verify import syntax_issues, verify_text
except ImportError:  # pragma: no cover - fallback for direct execution
    from context import build_context
    from memory import build_memory_summary
    from mentor import CodeMentor
    from observability import overview
    from repo import build_repo_summary, scan_repo
    from session import (
        append_turn,
        create_session,
        delete_session,
        get_memory,
        get_session,
        has_repo_snapshot,
        history,
        list_sessions,
        set_memory,
    )
    from verify import syntax_issues, verify_text

logger = logging.getLogger("codementor")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _console = logging.StreamHandler()
    _console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_console)
    _logs_dir = Path(__file__).resolve().parent.parent / "logs"
    try:
        _logs_dir.mkdir(exist_ok=True)
        _file = logging.FileHandler(_logs_dir / "backend.log", encoding="utf-8")
        _file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(_file)
    except OSError:
        pass  # logging stays console-only if the file cannot be created

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

REPO_MODE = "repo_report"
REPO_MAX_TOKENS = 4096
DEFAULT_MAX_TOKENS = 900
MAX_HISTORY_MESSAGES = 12

# Modes whose answers are expected to contain code: verified locally
# before the result is returned to the caller.
VERIFY_MODES = {"generate", "error_finder", "optimize"}
INPUT_SYNTAX_CHECK_MODE = "error_finder"

app = FastAPI(
    title="CodeMentor AI",
    description="Single-agent AI mentor for code explanation, error review, "
                "generation, optimization, and repository analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mentor = CodeMentor()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, status, and duration."""
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "%s %s -> %s (%.0f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


class MentorRequest(BaseModel):
    mode: str
    language: str = ""
    input_text: str
    session_id: str = ""


def _record(session_id: str, role: str, content: str, mode: str, language: str,
            stats: Optional[Dict[str, Any]] = None,
            verification: Optional[Dict[str, Any]] = None,
            input_check: Optional[List[Dict[str, Any]]] = None,
            context_info: Optional[Dict[str, Any]] = None) -> None:
    turn: Dict[str, Any] = {
        "role": role,
        "content": content,
        "mode": mode,
        "language": language,
        "timestamp": time.time(),
    }
    if verification:
        turn["verification"] = verification
    if input_check:
        turn["input_check"] = input_check
    if context_info:
        turn["context"] = context_info
        turn["context_turns"] = context_info.get("context_turns", 0)
    if stats:
        turn.update(
            {
                "model": stats.get("model"),
                "provider": stats.get("provider"),
                "usage": stats.get("usage"),
                "context_turns": stats.get("context_turns"),
                "duration_ms": stats.get("duration_ms"),
                "cost": stats.get("cost"),
            }
        )
    append_turn(session_id, turn)


def _fold_memory(session_id: str, ctx_info: Dict[str, Any]) -> None:
    """Fold turns trimmed from the context into the session memory summary."""
    if not ctx_info.get("trimmed_turns"):
        return
    existing = get_memory(session_id) or {}
    summary = build_memory_summary(
        mentor,
        ctx_info.get("trimmed_messages", []),
        existing_summary=existing.get("summary", ""),
    )
    if summary and summary != existing.get("summary", ""):
        set_memory(
            session_id,
            summary,
            int(existing.get("turns_summarized") or 0) + ctx_info["trimmed_turns"],
        )


def _repo_report(request: MentorRequest, session_id: str) -> Dict[str, Any]:
    snapshot_present = has_repo_snapshot(session_id)
    if snapshot_present:
        user_message = request.input_text.strip()
        max_tokens = DEFAULT_MAX_TOKENS
    else:
        path = os.path.abspath(
            os.path.expandvars(os.path.expanduser(request.input_text.strip()))
        )
        if not os.path.isdir(path):
            raise HTTPException(
                status_code=400,
                detail=f"'{path}' is not a valid folder path.",
            )
        try:
            user_message = build_repo_summary(scan_repo(path))
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to scan repository: {exc}",
            ) from exc
        max_tokens = REPO_MAX_TOKENS

    _record(session_id, "user", user_message, REPO_MODE, "")
    try:
        history_part, ctx_info = build_context(
            mentor.get_prompt(REPO_MODE),
            history(session_id)[:-1],
            user_message,
            memory=get_memory(session_id),
        )
        if ctx_info["note"]:
            user_message = ctx_info["note"] + "\n\n" + user_message
        stats = mentor.ask(
            mentor.get_prompt(REPO_MODE),
            history_part,
            user_message,
            max_tokens=max_tokens,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    _fold_memory(session_id, ctx_info)
    _record(session_id, "assistant", stats["content"], REPO_MODE, "", stats,
            context_info=ctx_info)
    return {
        "session_id": session_id,
        "mode": REPO_MODE,
        "language": "",
        "result": stats["content"],
        "usage": stats.get("usage"),
        "model": stats.get("model"),
        "provider": stats.get("provider"),
        "duration_ms": stats.get("duration_ms"),
        "context_turns": stats.get("context_turns"),
        "context": ctx_info,
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"message": "CodeMentor AI is running. Use /mentor to interact."}


@app.post("/mentor")
async def mentor_agent(request: MentorRequest) -> Dict[str, Any]:
    if not request.input_text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    session_id = request.session_id
    if not session_id or not get_session(session_id):
        session_id = create_session()

    if request.mode == REPO_MODE:
        return _repo_report(request, session_id)

    user_message = request.input_text.strip()
    effective_language = mentor.detect_language(user_message) or request.language
    input_check = None
    if request.mode == INPUT_SYNTAX_CHECK_MODE and effective_language:
        input_check = syntax_issues(effective_language, user_message)
    _record(session_id, "user", user_message, request.mode, effective_language,
            input_check=input_check)
    prompt_message = mentor.format_request(request.mode, effective_language, user_message)
    try:
        history_part, ctx_info = build_context(
            mentor.get_prompt(request.mode),
            history(session_id)[:-1],
            prompt_message,
            memory=get_memory(session_id),
        )
        if ctx_info["note"]:
            prompt_message = ctx_info["note"] + "\n\n" + prompt_message
        stats = mentor.ask(
            mentor.get_prompt(request.mode),
            history_part,
            prompt_message,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    verification = None
    if request.mode in VERIFY_MODES:
        check = verify_text(stats["content"], effective_language)
        if check["status"] != "no_code":
            verification = check

    _fold_memory(session_id, ctx_info)
    _record(session_id, "assistant", stats["content"], request.mode, effective_language, stats,
            verification=verification, context_info=ctx_info)
    return {
        "session_id": session_id,
        "mode": request.mode,
        "language": effective_language,
        "result": stats["content"],
        "usage": stats.get("usage"),
        "model": stats.get("model"),
        "provider": stats.get("provider"),
        "duration_ms": stats.get("duration_ms"),
        "context_turns": stats.get("context_turns"),
        "context": ctx_info,
        "verification": verification,
        "input_check": input_check,
    }


@app.get("/sessions")
async def sessions() -> Dict[str, Any]:
    return {"sessions": list_sessions()}


@app.get("/stats")
async def stats() -> Dict[str, Any]:
    """Usage analytics: totals, per-mode/provider/model breakdowns, daily series."""
    return overview()


@app.get("/sessions/{session_id}")
async def session_detail(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@app.delete("/sessions/{session_id}")
async def session_delete(session_id: str) -> Dict[str, Any]:
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": session_id}


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
