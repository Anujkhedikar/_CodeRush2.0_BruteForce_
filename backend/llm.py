# llm.py
# Handles API communication for the CodeMentor AI backend using Groq.

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Force reload variables to ensure the new token is picked up
load_dotenv(BACKEND_DIR / ".env", override=True)
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _load_config() -> Dict[str, str]:
    """Load Groq model settings from environment variables."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY. Set GROQ_API_KEY in backend/.env.")

    # Groq's OpenAI-compatible endpoint
    api_base = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1").strip().rstrip("/")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

    return {
        "api_key": api_key,
        "api_base": api_base,
        "model": model,
    }


def _build_headers(config: Dict[str, str]) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }


def _build_payload(config: Dict[str, str], messages: List[Dict[str, str]], temperature: float) -> Dict[str, Any]:
    # Groq does not support a temperature of exactly 0. 
    # If it is 0, they convert it to 1e-8, so we'll just use a small float.
    safe_temp = max(temperature, 0.00001)
    
    return {
        "model": config["model"],
        "messages": messages,
        "temperature": safe_temp,
        "max_tokens": 900,
    }


def _raise_for_http_error(status_code: int, response_text: str) -> None:
    message = response_text.strip() or "No response body returned by the API."

    if status_code == 401:
        detail = f"Invalid or expired credentials ({status_code})."
    elif status_code == 403:
        detail = f"Access forbidden ({status_code})."
    elif status_code in {404, 410}:
        detail = f"Invalid model or endpoint ({status_code}). Check GROQ_MODEL and GROQ_API_BASE."
    elif status_code == 429:
        detail = f"Rate limit exceeded ({status_code}). Please try again later."
    elif status_code in {500, 503}:
        detail = f"Service unavailable ({status_code}). The provider may be temporarily down."
    else:
        detail = f"Unexpected API error ({status_code})."

    raise RuntimeError(f"Groq API error ({status_code}): {detail}\nResponse body: {message}")


def _send_request(messages: List[Dict[str, str]], temperature: float = 0.3) -> Dict[str, Any]:
    config = _load_config()
    headers = _build_headers(config)
    payload = _build_payload(config, messages, temperature)

    url = f"{config['api_base']}/chat/completions"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.Timeout as exc:
        raise RuntimeError("The request timed out. Please try again later.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Network error while contacting the API: {exc}") from exc

    if not response.ok:
        try:
            response_body = response.json()
            response_text = json.dumps(response_body, indent=2, ensure_ascii=False)
        except ValueError:
            response_text = response.text
        _raise_for_http_error(response.status_code, response_text)

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("The API returned an invalid JSON response.") from exc


def call_openai(messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.3) -> Dict[str, Any]:
    """Send a chat completion request to the Groq endpoint."""
    # Keeping the function name 'call_openai' so mentor.py doesn't break
    return _send_request(messages, temperature=temperature)


def build_message(system_prompt: str, user_input: str) -> List[Dict[str, str]]:
    """Construct standardized prompt messages for the AI agent."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]