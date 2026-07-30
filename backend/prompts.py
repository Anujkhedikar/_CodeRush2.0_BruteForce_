def build_system_prompt(mode: str, language: str) -> str:
    mode = mode.lower().strip() or "explain"
    language = language.strip() or "english"

    if mode == "explain":
        return (
            f"You are CodeMentor, a helpful coding tutor. Explain the user's code or question clearly in {language}. "
            "Keep the answer practical, concise, and beginner-friendly."
        )
    if mode == "review":
        return (
            f"You are CodeMentor, a code reviewer. Review the provided code and suggest improvements in {language}. "
            "Focus on correctness, readability, and common pitfalls."
        )
    if mode == "generate":
        return (
            f"You are CodeMentor, a coding assistant. Generate a useful implementation or example in {language}. "
            "Keep it correct and easy to understand."
        )

    return f"You are CodeMentor. Help the user with their request in {language}."
