import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

try:
    import openai
except ImportError:
    openai = None

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_PROVIDER = os.getenv("OPENAI_API_PROVIDER", "openai").strip().lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_BASE = os.getenv(
    "OPENAI_API_BASE",
    "https://models.github.ai/inference" if OPENAI_API_PROVIDER == "github" else "https://api.openai.com/v1",
)

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment variables.")

if OPENAI_API_PROVIDER == "openai" and openai is None:
    raise RuntimeError("openai package is required for OPENAI_API_PROVIDER=openai.")

if OPENAI_API_PROVIDER == "openai":
    openai.api_key = OPENAI_API_KEY


def _github_model_id(model: str) -> str:
    if "/" in model:
        return model
    return f"openai/{model}"


def call_openai(messages: List[Dict], model: str = OPENAI_MODEL, temperature: float = 0.3) -> Dict:
    if OPENAI_API_PROVIDER == "github":
        url = f"{OPENAI_API_BASE.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2026-03-10",
        }
        payload = {
            "model": _github_model_id(model),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 900,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json()

    if OPENAI_API_PROVIDER == "openai":
        return openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=900,
            n=1,
        )

    raise RuntimeError("Unsupported OPENAI_API_PROVIDER. Use 'openai' or 'github'.")


def build_message(system_prompt: str, user_input: str) -> List[Dict]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
