# mentor.py
# Routes requests to the correct prompt mode for the single-agent mentor.

from typing import Any, Dict, List

try:
    from .llm import build_message, call_openai
    from .prompts import LANGUAGE_LABELS, MODE_PROMPTS
except ImportError:  # pragma: no cover - fallback for direct execution
    from llm import build_message, call_openai
    from prompts import LANGUAGE_LABELS, MODE_PROMPTS


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
        response_text = response["choices"][0]["message"]["content"].strip()

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
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        response = call_openai(messages, max_tokens=max_tokens)
        return response["choices"][0]["message"]["content"].strip()
