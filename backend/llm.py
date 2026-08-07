# llm.py
# Unified LLM provider layer for the CodeMentor AI backend.
# Every supported backend (Groq today; Gemini and OpenRouter later)
# exposes an OpenAI-compatible chat completions endpoint,
# so a single client class serves them all.

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

# Provider registry: name -> env var names and defaults for that backend.
# New providers are added here, no other code changes needed.
PROVIDERS = {
    "groq": {
        "env_api_key": "GROQ_API_KEY",
        "env_api_base": "GROQ_API_BASE",
        "env_model": "GROQ_MODEL",
        "default_api_base": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
    },
}


class LLMProvider:
    """OpenAI-compatible chat completions client for one model backend."""

    def __init__(self, name: str, api_key: str, api_base: str, model: str) -> None:
        self.name = name
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        # Providers reject a temperature of exactly 0, so use a small float.
        safe_temp = max(temperature, 0.00001)

        return {
            "model": self.model,
            "messages": messages,
            "temperature": safe_temp,
            "max_tokens": max_tokens,
        }

    def _raise_for_http_error(self, status_code: int, response_text: str) -> None:
        message = response_text.strip() or "No response body returned by the API."

        if status_code == 401:
            detail = f"Invalid or expired credentials ({status_code})."
        elif status_code == 403:
            detail = f"Access forbidden ({status_code})."
        elif status_code in {404, 410}:
            detail = (
                f"Invalid model or endpoint ({status_code}). "
                f"Check {self.name.upper()}_MODEL and {self.name.upper()}_API_BASE."
            )
        elif status_code == 429:
            detail = f"Rate limit exceeded ({status_code}). Please try again later."
        elif status_code in {500, 503}:
            detail = f"Service unavailable ({status_code}). The provider may be temporarily down."
        else:
            detail = f"Unexpected API error ({status_code})."

        raise RuntimeError(f"{self.name} API error ({status_code}): {detail}\nResponse body: {message}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 900,
    ) -> Dict[str, Any]:
        """Send a chat completion request and return the full provider response."""
        url = f"{self.api_base}/chat/completions"

        try:
            response = requests.post(
                url,
                headers=self._build_headers(),
                json=self._build_payload(messages, temperature, max_tokens),
                timeout=60,
            )
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
            self._raise_for_http_error(response.status_code, response_text)

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError("The API returned an invalid JSON response.") from exc


def get_provider(name: Optional[str] = None) -> LLMProvider:
    """Build the active provider from environment variables."""
    provider_name = (name or os.getenv("LLM_PROVIDER", "groq")).strip().lower()

    if provider_name not in PROVIDERS:
        supported = ", ".join(sorted(PROVIDERS))
        raise RuntimeError(
            f"Unknown LLM provider '{provider_name}'. Set LLM_PROVIDER to one of: {supported}."
        )

    spec = PROVIDERS[provider_name]
    api_key = os.getenv(spec["env_api_key"], "").strip()
    if not api_key:
        raise RuntimeError(
            f"Missing {spec['env_api_key']}. Set it in backend/.env (or the project root .env)."
        )

    api_base = os.getenv(spec["env_api_base"], spec["default_api_base"]).strip().rstrip("/")
    model = os.getenv(spec["env_model"], spec["default_model"]).strip()

    return LLMProvider(provider_name, api_key, api_base, model)


def call_openai(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """Send a chat completion request to the active provider."""
    # Keeping the function name 'call_openai' so mentor.py doesn't break
    provider = get_provider()
    if model:
        provider.model = model
    return provider.chat(messages, temperature=temperature)


def build_message(system_prompt: str, user_input: str) -> List[Dict[str, str]]:
    """Construct standardized prompt messages for the AI agent."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
