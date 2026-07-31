# mentor.py
# Routes requests to the correct prompt mode for the single-agent mentor.

from typing import Dict, Any

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
        """Create a user request string including the selected programming language."""
        language_name = LANGUAGE_LABELS.get(language, language.capitalize())
        return (
            f"Language: {language_name}\n"
            f"Feature: {mode.replace('_', ' ').title()}\n\n"
            f"User Input:\n{content.strip()}"
        )

    def get_prompt(self, mode: str) -> str:
        """Return the system prompt for the requested mode."""
        return self.modes.get(mode, self.modes["explain"])

    def mentor_response(self, mode: str, language: str, content: str) -> Dict[str, Any]:
        """Return the assistant response from the AI model."""
        system_prompt = self.get_prompt(mode)
        user_request = self.format_request(mode, language, content)
        messages = build_message(system_prompt, user_request)
        response = call_openai(messages)
        response_text = response["choices"][0]["message"]["content"].strip()

        return {
            "mode": mode,
            "language": language,
            "content": content,
            "result": response_text,
        }
