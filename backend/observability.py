# observability.py
# Usage analytics for the CodeMentor AI harness.
# Recomputes aggregates on the fly from the session store, so nothing
# needs to be written at request time: every turn already records its
# model, provider, token usage, duration, and timestamp.
#
# Cost estimation uses public list prices per 1M tokens; unknown models
# fall back to a conservative estimate so totals stay roughly right.

from typing import Any, Dict, List, Optional

try:
    from .session import list_sessions
except ImportError:  # pragma: no cover - fallback for direct execution
    from session import list_sessions

# Price per 1M tokens in USD for models this harness actually uses.
# Missing entries fall back to _DEFAULT_PRICE.
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.2-3b-preview": {"input": 0.03, "output": 0.06},
    "llama-3.2-1b-preview": {"input": 0.02, "output": 0.03},
    "deepseek-r1-distill-llama-70b": {"input": 0.75, "output": 0.99},
    "gemma2-9b-it": {"input": 0.20, "output": 0.20},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    "mistral-saba-24b": {"input": 0.15, "output": 0.15},
    "qwen-2.5-coder-32b": {"input": 0.79, "output": 0.79},
    "qwen-qwq-32b": {"input": 0.29, "output": 0.39},
}

# Conservative default for models without a listed price.
DEFAULT_PRICE = {"input": 0.50, "output": 1.50}

PER_MILLION = 1_000_000


def estimate_cost(model: str, usage: Optional[Dict[str, Any]]) -> float:
    """Estimated USD cost of one API call, based on model and token usage."""
    if not usage:
        return 0.0
    prompt = usage.get("prompt_tokens") or 0
    completion = usage.get("completion_tokens") or 0
    price = MODEL_PRICING.get((model or "").strip(), DEFAULT_PRICE)
    return round((prompt * price["input"] + completion * price["output"]) / PER_MILLION, 6)


def session_cost(session: Dict[str, Any]) -> float:
    """Total estimated cost across every assistant turn of a session."""
    return sum(
        estimate_cost(turn.get("model") or "", turn.get("usage"))
        for turn in session.get("turns", [])
        if turn.get("role") == "assistant"
    )


def _day_key(timestamp: Optional[float]) -> str:
    """Local calendar day as 'YYYY-MM-DD' (or '' for missing timestamps)."""
    import time

    try:
        return time.strftime("%Y-%m-%d", time.localtime(float(timestamp)))
    except (TypeError, ValueError):
        return ""


def _bucketed_days(series: Dict[str, Dict[str, float]], last_days: int = 14) -> List[Dict[str, Any]]:
    """Pad the daily series with zero entries so charts render full bars."""
    from datetime import date, timedelta

    days = []
    today = date.today()
    for offset in range(last_days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        entry = series.get(day) or {}
        days.append(
            {
                "day": day,
                "turns": entry.get("turns", 0),
                "tokens": entry.get("tokens", 0),
                "cost": entry.get("cost", 0.0),
            }
        )
    return days


def overview(last_days: int = 14) -> Dict[str, Any]:
    """Aggregate usage across all stored sessions.

    Returns totals (sessions, turns, prompt/completion/total tokens, cost),
    breakdowns by mode and provider, a per-day series, and the most
    expensive sessions.
    """
    sessions = list_sessions()

    totals = {
        "sessions": len(sessions),
        "turns": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost": 0.0,
    }
    by_mode: Dict[str, Dict[str, Any]] = {}
    by_provider: Dict[str, Dict[str, Any]] = {}
    by_model: Dict[str, Dict[str, Any]] = {}
    by_day: Dict[str, Dict[str, float]] = {}
    top_sessions: List[Dict[str, Any]] = []

    try:
        from .session import get_session
    except ImportError:  # pragma: no cover - fallback for direct execution
        from session import get_session

    for summary in sessions:
        session = get_session(summary["id"]) or {}
        turns = session.get("turns", [])
        cost = session_cost(session)
        for turn in turns:
            if turn.get("role") != "assistant":
                continue
            usage = turn.get("usage") or {}
            prompt = usage.get("prompt_tokens") or 0
            completion = usage.get("completion_tokens") or 0
            total = usage.get("total_tokens") or (prompt + completion)
            turn_cost = estimate_cost(turn.get("model") or "", usage)
            mode = turn.get("mode") or "unknown"
            provider = turn.get("provider") or "unknown"
            model = turn.get("model") or "unknown"
            day = _day_key(turn.get("timestamp"))

            totals["turns"] += 1
            totals["prompt_tokens"] += prompt
            totals["completion_tokens"] += completion
            totals["total_tokens"] += total
            totals["cost"] += turn_cost

            for bucket, key in (
                (by_mode, mode),
                (by_provider, provider),
                (by_model, model),
            ):
                entry = bucket.setdefault(
                    key, {"turns": 0, "tokens": 0, "cost": 0.0}
                )
                entry["turns"] += 1
                entry["tokens"] += total
                entry["cost"] += turn_cost

            if day:
                entry = by_day.setdefault(day, {"turns": 0, "tokens": 0, "cost": 0.0})
                entry["turns"] += 1
                entry["tokens"] += total
                entry["cost"] += turn_cost

        top_sessions.append(
            {
                "id": summary["id"],
                "preview": summary.get("preview") or "",
                "updated_at": summary.get("updated_at"),
                "turns": summary.get("turn_count", 0),
                "tokens": summary.get("total_tokens", 0),
                "cost": cost,
            }
        )

    totals["cost"] = round(totals["cost"], 6)
    top_sessions.sort(key=lambda item: item["cost"], reverse=True)

    return {
        "totals": totals,
        "by_mode": _ranked(by_mode),
        "by_provider": _ranked(by_provider),
        "by_model": _ranked(by_model),
        "by_day": _bucketed_days(by_day, last_days),
        "top_sessions": top_sessions[:10],
    }


def _ranked(bucket: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bucket dict -> sorted list (most tokens first) with the key inline."""
    rows = [{"name": name, **values} for name, values in bucket.items()]
    rows.sort(key=lambda row: row["tokens"], reverse=True)
    return rows
