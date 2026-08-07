# app.py
# FastAPI routes for the CodeMentor AI backend.

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from .mentor import CodeMentor
    from .repo import build_repo_summary, scan_repo
except ImportError:  # pragma: no cover - fallback for direct execution
    from mentor import CodeMentor
    from repo import build_repo_summary, scan_repo

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

REPO_MODE = "repo_report"
REPO_MAX_TOKENS = 4096

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


class MentorRequest(BaseModel):
    mode: str
    language: str = ""
    input_text: str


def _repo_report(path: str) -> Dict[str, Any]:
    path = os.path.abspath(os.path.expandvars(os.path.expanduser(path.strip())))
    if not os.path.isdir(path):
        raise HTTPException(
            status_code=400,
            detail=f"'{path}' is not a valid folder path.",
        )
    try:
        summary = build_repo_summary(scan_repo(path))
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan repository: {exc}",
        ) from exc
    return mentor.mentor_response(REPO_MODE, "", summary, max_tokens=REPO_MAX_TOKENS)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"message": "CodeMentor AI is running. Use /mentor to interact."}


@app.post("/mentor")
async def mentor_agent(request: MentorRequest) -> Dict[str, Any]:
    if not request.input_text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    try:
        if request.mode == REPO_MODE:
            return _repo_report(request.input_text)
        return mentor.mentor_response(request.mode, request.language, request.input_text)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

