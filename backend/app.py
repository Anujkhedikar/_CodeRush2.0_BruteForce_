# app.py
# FastAPI backend for CodeMentor AI.

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from mentor import CodeMentor

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="CodeMentor AI",
    description="Single-agent AI mentor for code explanation, error review, generation, and optimization.",
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
    language: str
    input_text: str


@app.get("/health")
async def health():
    return {"message": "CodeMentor AI is running. Use /mentor to interact."}


@app.post("/mentor")
async def mentor_agent(request: MentorRequest):
    if not request.input_text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    response = mentor.mentor_response(request.mode, request.language, request.input_text)
    return response


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
