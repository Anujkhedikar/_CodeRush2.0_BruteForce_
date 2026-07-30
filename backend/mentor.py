from llm import build_message, call_openai
from prompts import build_system_prompt
from tools import format_response


class CodeMentor:
    def mentor_response(self, mode: str, language: str, input_text: str) -> dict:
        system_prompt = build_system_prompt(mode, language)
        messages = build_message(system_prompt, input_text)

        try:
            response = call_openai(messages)
            return {
                "mode": mode,
                "language": language,
                "input_text": input_text,
                "response": format_response(response),
            }
        except Exception as exc:  # pragma: no cover - fallback path
            return {
                "mode": mode,
                "language": language,
                "input_text": input_text,
                "response": f"The AI service is unavailable right now: {exc}",
            }
