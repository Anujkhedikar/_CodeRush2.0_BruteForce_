# context.py
# Context manager: keeps the conversation inside a token budget.
#
# Instead of a fixed message count, every request is built by estimating
# the tokens of the system prompt, the repository snapshot (always kept),
# the most recent turns, and the current message. Older turns are trimmed
# only when they would exceed the budget, and the model is told how many
# turns were trimmed so it knows the conversation is not lossless.

import os
from typing import Any, Dict, List, Optional

REPO_SNAPSHOT_MARKER = "# Repository Snapshot"

DEFAULT_BUDGET_TOKENS = 12_000


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token, always >= 1)."""
    return max(1, len(text or "") // 4)


def context_budget() -> int:
    """The token budget for one request, from CONTEXT_BUDGET_TOKENS or default."""
    raw = os.getenv("CONTEXT_BUDGET_TOKENS", "").strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_BUDGET_TOKENS
    return value if value > 0 else DEFAULT_BUDGET_TOKENS


def build_context(
    system_prompt: str,
    history: List[Dict[str, str]],
    current_message: str,
    budget_tokens: Optional[int] = None,
    memory: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Select the history messages that fit the budget.

    Returns (history_part, info):
      history_part - messages to pass to the model (memory summary first,
                     then the repo snapshot, then the most recent turns
                     that fit)
      info - {"context_turns", "kept_turns", "trimmed_turns",
              "estimated_tokens", "budget_tokens", "note",
              "trimmed_messages", "memory_summary", "memory_turns"}

    The tiered-memory summary (when present) and the repository snapshot
    are kept unconditionally; the rest are the most recent turns that
    still fit. The dropped messages are returned so callers can fold
    them into the memory summary.
    """
    budget = budget_tokens or context_budget()
    snapshot: Optional[Dict[str, str]] = None
    rest = history
    if history and history[0].get("content", "").startswith(REPO_SNAPSHOT_MARKER):
        snapshot = history[0]
        rest = history[1:]

    memory_message: Optional[Dict[str, str]] = None
    memory_turns = 0
    if memory and memory.get("summary"):
        memory_message = {
            "role": "system",
            "content": f"[Memory summary of earlier conversation]\n{memory['summary']}",
        }
        memory_turns = int(memory.get("turns_summarized") or 0)

    used = estimate_tokens(system_prompt) + estimate_tokens(current_message)
    if memory_message:
        used += estimate_tokens(memory_message["content"])
    if snapshot:
        used += estimate_tokens(snapshot["content"])

    # Walk turns from the most recent backwards, keeping whole
    # user/assistant pairs (or the single trailing assistant message that
    # completes the snapshot turn) so context order never breaks mid-turn.
    tail: List[Dict[str, str]] = []
    idx = len(rest)
    while idx > 0:
        start = idx - 2 if idx >= 2 else 0
        chunk = rest[start:idx]
        cost = sum(estimate_tokens(m.get("content", "")) for m in chunk)
        if used + cost > budget:
            break
        used += cost
        tail = chunk + tail
        idx = start

    history_part: List[Dict[str, str]] = []
    if memory_message:
        history_part.append(memory_message)
    if snapshot:
        history_part.append(snapshot)
    history_part.extend(tail)

    prior_turns = (len(rest) + 1) // 2
    kept_turns = (len(tail) + 1) // 2
    trimmed_turns = max(0, prior_turns - kept_turns)
    note = ""
    if trimmed_turns:
        note = (
            f"Note: {trimmed_turns} earlier turn(s) were trimmed from your context "
            f"to stay within the {budget} token memory budget"
        )
        if memory_message:
            note += ", folded into your memory summary"
        note += "."

    info = {
        "context_turns": kept_turns,
        "kept_turns": kept_turns,
        "trimmed_turns": trimmed_turns,
        "estimated_tokens": used,
        "budget_tokens": budget,
        "note": note,
        "trimmed_messages": rest[: len(rest) - len(tail)],
        "memory_summary": (memory_message["content"] if memory_message else None),
        "memory_turns": memory_turns,
    }
    return history_part, info
