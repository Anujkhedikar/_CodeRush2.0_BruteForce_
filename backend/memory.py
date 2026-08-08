# memory.py
# Tiered memory: when older turns are trimmed out of the context budget,
# they are folded into a condensed session memory summary instead of being
# lost. The summary (tier 2) travels with every request so the agent still
# knows what was discussed even after the raw turns are gone; sessions.json
# (tier 3) keeps the full conversation archive.

import os
from typing import Any, Dict, List

MAX_MEMORY_CHARS = 1_800  # ~450 estimated tokens


def _flatten(messages: List[Dict[str, str]], max_chars: int = 6_000) -> str:
    lines = []
    for message in messages:
        role = message.get("role", "?")
        content = (message.get("content") or "").strip()
        lines.append(f"{role}: {content[:800]}")
    text = "\n\n".join(lines)
    return text[:max_chars]


def extractive_summary(
    messages: List[Dict[str, str]],
    existing: str = "",
    max_chars: int = MAX_MEMORY_CHARS,
) -> str:
    """Deterministic fallback: bullet previews of each trimmed user message."""
    previews = []
    seen = set()
    for message in messages:
        if message.get("role") != "user":
            continue
        content = (message.get("content") or "").strip().replace("\n", " ")
        if content.startswith("# Repository Snapshot"):
            continue
        key = content[:80]
        if key in seen:
            continue
        seen.add(key)
        preview = content if len(content) <= 100 else content[:100] + "..."
        previews.append(f"- {preview}")
    parts = []
    if existing.strip():
        parts.append(existing.strip())
    parts.extend(previews)
    text = "\n".join(parts).strip()
    return text[:max_chars]


def build_memory_summary(
    mentor: Any,
    trimmed_messages: List[Dict[str, str]],
    existing_summary: str = "",
) -> str:
    """Condense trimmed turns into the session memory summary.

    Tries the LLM first (set MEMORY_SUMMARIZATION=0 to disable); falls back to
    the deterministic extractive summary when the call fails or returns
    nothing. Returns the existing summary unchanged when nothing was trimmed.
    """
    if not trimmed_messages:
        return existing_summary
    summary = ""
    if os.getenv("MEMORY_SUMMARIZATION", "1").strip() != "0":
        try:
            candidate = mentor.summarize(_flatten(trimmed_messages), existing_summary)
            summary = (candidate or "").strip()
        except RuntimeError:
            summary = ""
    if not summary:
        summary = extractive_summary(trimmed_messages, existing_summary)
    return summary[:MAX_MEMORY_CHARS]
