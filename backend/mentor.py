# mentor.py
# Routes requests to the correct prompt mode for the single-agent mentor.

import os
import re
import time
from typing import Any, Dict, List, Optional

try:
    from .llm import build_message, call_openai, get_provider
    from .observability import estimate_cost
    from .prompts import LANGUAGE_LABELS, MODE_PROMPTS, SUMMARIZE_PROMPT
except ImportError:  # pragma: no cover - fallback for direct execution
    from llm import build_message, call_openai, get_provider
    from observability import estimate_cost
    from prompts import LANGUAGE_LABELS, MODE_PROMPTS, SUMMARIZE_PROMPT

# Mention patterns checked in order; 'c++'/'cpp' must precede 'c' so a
# standalone word 'c' never swallows them.
_LANGUAGE_PATTERNS: List[Any] = [
    ("python", re.compile(r"\bpython\b", re.IGNORECASE)),
    ("java", re.compile(r"\bjava\b", re.IGNORECASE)),
    ("cpp", re.compile(r"\bc\+\+|cpp", re.IGNORECASE)),
    ("c", re.compile(r"\bc(?!\+)\b", re.IGNORECASE)),
]


class CodeMentor:
    """Single AI agent that switches behavior using prompt modes."""

    def __init__(self) -> None:
        self.modes = MODE_PROMPTS

    def format_request(self, mode: str, language: str, content: str) -> str:
        """Create a user request string including the selected programming language.

        The language line is omitted when no language is supplied, which is the
        case for the repo_report mode (a repository can contain many languages).
        """
        lines: list[str] = []
        if language:
            language_name = LANGUAGE_LABELS.get(language, language.capitalize())
            lines.append(f"Language: {language_name}")
        lines.append(f"Feature: {mode.replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"User Input:\n{content.strip()}")
        return "\n".join(lines)

    def detect_language(self, text: str) -> str:
        """Return a language mentioned in the user's text, or ''.

        A mention in the request wins over the selection: if the user wrote
        "create a heart in python" the model must be told Python even when
        the UI defaulted to C++, and vice versa.
        """
        for key, pattern in _LANGUAGE_PATTERNS:
            if pattern.search(text or ""):
                return key
        return ""

    def get_prompt(self, mode: str) -> str:
        """Return the system prompt for the requested mode."""
        return self.modes.get(mode, self.modes["explain"])

    def mentor_response(
        self,
        mode: str,
        language: str,
        content: str,
        max_tokens: int = 900,
    ) -> Dict[str, Any]:
        """Return the assistant response from the AI model."""
        system_prompt = self.get_prompt(mode)
        user_request = self.format_request(mode, language, content)
        messages = build_message(system_prompt, user_request)
        response = call_openai(messages, max_tokens=max_tokens)
        message = response["choices"][0].get("message") or {}
        response_text = (message.get("content") or "").strip()

        return {
            "mode": mode,
            "language": language,
            "content": content,
            "result": response_text,
        }

    def chat_response(
        self,
        system_prompt: str,
        history: List[Dict[str, str]],
        user_input: str,
        max_tokens: int = 900,
    ) -> str:
        """Send a history-aware message and return only the assistant text.

        history is a list of {'role': 'user'|'assistant', 'content': ...} turns
        from previous rounds, so the conversation keeps its flow.
        """
        return self.ask(system_prompt, history, user_input, max_tokens=max_tokens)["content"]

    def summarize(self, text: str, existing: str = "") -> str:
        """Condense conversation turns into a memory summary (tier 2).

        Called when turns are trimmed from the context budget; the summary is
        stored on the session and included in later requests so the agent
        keeps remembering what was discussed after the raw turns are gone.
        """
        if existing.strip():
            content = f"Existing memory:\n{existing}\n\nNew conversation turns to fold in:\n{text}"
        else:
            content = text
        messages = [
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": content},
        ]
        response = call_openai(messages, max_tokens=250)
        message = response["choices"][0].get("message") or {}
        return (message.get("content") or "").strip()

    def ask(
        self,
        system_prompt: str,
        history: List[Dict[str, str]],
        user_input: str,
        max_tokens: int = 900,
    ) -> Dict[str, Any]:
        """Send a history-aware message and return content plus usage details.

        The returned dict includes the assistant text ('content'), the provider
        token usage ('usage': prompt/completion/total tokens), the model name,
        and the request duration, so callers can record context/memory stats.
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        started = time.perf_counter()
        response = call_openai(messages, max_tokens=max_tokens)
        duration_ms = (time.perf_counter() - started) * 1000

        text = ""
        if response["choices"]:
            message = response["choices"][0].get("message") or {}
            text = (message.get("content") or "").strip()
        try:
            provider = get_provider().name
        except RuntimeError:
            provider = os.getenv("LLM_PROVIDER", "groq")

        return {
            "content": text,
            "usage": response.get("usage") or {},
            "model": response.get("model") or "",
            "provider": provider,
            "duration_ms": round(duration_ms, 1),
            "context_turns": len(history) // 2,
            "cost": estimate_cost(response.get("model") or "", response.get("usage")),
        }
