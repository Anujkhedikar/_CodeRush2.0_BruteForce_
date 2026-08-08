# cli.py
# Command-line interface for CodeMentor AI.
# Shares the same core (CodeMentor) as the web app, just with a terminal front end.

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from .context import build_context
    from .memory import build_memory_summary
    from .mentor import CodeMentor
    from .observability import estimate_cost, overview
    from .prompts import LANGUAGE_LABELS, MODE_DESCRIPTIONS, MODE_PROMPTS
    from .repo import build_repo_summary, scan_repo
    from .session import (
        append_turn,
        create_session,
        delete_session,
        get_memory,
        get_session,
        has_repo_snapshot,
        history,
        list_sessions,
        set_memory,
    )
    from .verify import syntax_issues, verify_text
except ImportError:  # pragma: no cover - fallback for direct execution
    from context import build_context
    from memory import build_memory_summary
    from mentor import CodeMentor
    from observability import estimate_cost, overview
    from prompts import LANGUAGE_LABELS, MODE_DESCRIPTIONS, MODE_PROMPTS
    from repo import build_repo_summary, scan_repo
    from session import (
        append_turn,
        create_session,
        delete_session,
        get_memory,
        get_session,
        has_repo_snapshot,
        history,
        list_sessions,
        set_memory,
    )
    from verify import syntax_issues, verify_text

REPO_MODE = "repo_report"
REPO_MAX_TOKENS = 4096
DEFAULT_MAX_TOKENS = 900
MAX_HISTORY_MESSAGES = 12

# Modes whose answers are expected to contain code and therefore get
# verified locally before the user sees the result.
VERIFY_MODES = {"generate", "error_finder", "optimize"}
INPUT_SYNTAX_CHECK_MODE = "error_finder"

COMMAND_ALIASES = {"h": "help", "sessions": "history", "quit": "exit"}
KNOWN_COMMANDS = {"help", "history", "view", "resume", "delete", "new", "back", "exit", "stats"}

COMMAND_HELP = """Available commands:
  /help              show this help
  /history           list all sessions (id, turns, tokens, preview)
  /view <id>         show a session's conversation with per-turn usage details
  /resume <id>       continue a previous session (its history is loaded into this chat)
  /back              return to the chat prompt
  /new               start a new session
  /delete <id>       delete a session
  /stats             show usage analytics (tokens, cost, breakdowns)
  /exit              quit the CLI"""


def _parse_command(raw: str) -> Optional[Tuple[str, str]]:
    """Recognize a slash command. Returns (name, argument) or None."""
    parts = raw.strip().split(None, 1)
    if not parts or not parts[0].startswith("/"):
        return None
    name = COMMAND_ALIASES.get(parts[0][1:].lower(), parts[0][1:].lower())
    if name not in KNOWN_COMMANDS:
        return None
    arg = parts[1].strip() if len(parts) > 1 else ""
    return name, arg


def _shorten(text: str, limit: int = 220) -> str:
    text = text.strip().replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "..."


def _fmt_time(timestamp: Optional[float]) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
    except (TypeError, ValueError):
        return "?"


def _print_session_list() -> None:
    sessions = list_sessions()
    if not sessions:
        print("No sessions yet. Your chats are saved automatically.")
        return
    print()
    print(f"{'ID':<6}{'TURNS':<7}{'TOKENS':<10}PREVIEW")
    for item in sessions:
        preview = item["preview"] or "(empty session)"
        print(f"{item['id']:<6}{item['turn_count']:<7}{item['total_tokens']:<10}{preview}")
    print("Use /view <id> to inspect, /resume <id> to continue, /delete <id> to remove.")


def _cmd_view(session_id: str) -> None:
    session = get_session(session_id)
    if not session:
        print(f"No session with id '{session_id}'.")
        return
    print(f"\n=== Session {session_id} (started {_fmt_time(session['created_at'])}) ===")
    memory = session.get("memory")
    if memory and memory.get("summary"):
        print(
            f"Memory: {_shorten(memory['summary'], 160)} "
            f"[summarizes {memory.get('turns_summarized', 0)} turn(s)]"
        )
    for turn in session.get("turns", []):
        role = "USER" if turn["role"] == "user" else "AI  "
        content = turn.get("content", "")
        if turn["role"] == "user" and content.startswith("# Repository Snapshot"):
            content = f"[repository snapshot - {len(content)} chars]"
        print(f"{role} | {_shorten(content)}")
        if turn["role"] == "assistant":
            usage = turn.get("usage") or {}
            prompt = usage.get("prompt_tokens", "?")
            completion = usage.get("completion_tokens", "?")
            total = usage.get("total_tokens", "?")
            context = turn.get("context_turns", "?")
            model = turn.get("model") or "?"
            duration = turn.get("duration_ms")
            duration_text = f" | {duration / 1000:.1f}s" if duration else ""
            cost = estimate_cost(turn.get("model") or "", usage)
            cost_text = f" | est. ${cost:.4f}" if cost else ""
            print(
                f"      [tokens: {prompt} in / {completion} out (total {total}) | "
                f"ctx {context} turn(s) | {model}{duration_text}{cost_text} | "
                f"{_fmt_time(turn.get('timestamp'))}]"
            )
            verification = turn.get("verification")
            if verification and verification.get("blocks"):
                issues = sum(len(b.get("issues") or []) for b in verification["blocks"])
                status = "OK" if verification["status"] == "ok" else f"{issues} issue(s)"
                print(f"      [verification: {status}]")
            context = turn.get("context") or {}
            if context.get("trimmed_turns"):
                print(
                    f"      [context: {context['kept_turns']} turn(s) kept, "
                    f"{context['trimmed_turns']} trimmed | budget {context['budget_tokens']} tokens]"
                )
        if turn["role"] == "user" and turn.get("input_check"):
            print(f"      [input syntax check: {len(turn['input_check'])} issue(s)]")
    print("Use /back to return to the chat, /resume <id> to continue this session.")


def _fmt_cost(cost: float) -> str:
    if cost >= 0.01:
        return f"${cost:.3f}"
    return f"${cost:.4f}"


def _print_stats() -> None:
    """Show aggregate usage: totals, breakdowns, daily series, top sessions."""
    stats = overview()
    totals = stats["totals"]
    print("\n=== Usage Analytics ===")
    if totals["sessions"] == 0:
        print("No usage recorded yet. Send a message first.")
        return
    print(
        f"{totals['sessions']} session(s), {totals['turns']} turn(s) | "
        f"{totals['total_tokens']} tokens in/out | est. cost {_fmt_cost(totals['cost'])}"
    )
    print(
        f"  prompt: {totals['prompt_tokens']} tokens | "
        f"completion: {totals['completion_tokens']} tokens"
    )
    if stats["by_mode"]:
        print("\nBy mode:")
        for row in stats["by_mode"]:
            print(f"  {row['name']:<14} {row['turns']:>4} turn(s) {row['tokens']:>8} tokens {_fmt_cost(row['cost']):>8}")
    if stats["by_provider"]:
        print("\nBy provider:")
        for row in stats["by_provider"]:
            print(f"  {row['name']:<10} {row['turns']:>4} turn(s) {row['tokens']:>8} tokens {_fmt_cost(row['cost']):>8}")
    if stats["top_sessions"]:
        print("\nMost expensive sessions:")
        for row in stats["top_sessions"][:5]:
            preview = _shorten(row["preview"], 40) or "(empty session)"
            print(f"  #{row['id']:<4} {row['tokens']:>8} tokens {_fmt_cost(row['cost']):>8} | {preview}")
    print("\nUse /view <id> for per-turn details.")


def _handle_command(cmd: str, arg: str, state: Dict[str, Any]) -> Optional[str]:
    """Run a slash command. Returns 'exit', 'resumed', 'new', or None."""
    if cmd == "help":
        print(COMMAND_HELP)
    elif cmd == "history":
        _print_session_list()
    elif cmd == "view":
        if not arg:
            print("Usage: /view <session id> (see /history for ids)")
        else:
            _cmd_view(arg)
    elif cmd == "back":
        print("Back to the chat.")
    elif cmd == "new":
        state["session_id"] = create_session()
        state["repo_context"] = None
        state["repo_path"] = None
        print(f"New session {state['session_id']} started - previous history is kept.")
        return "new"
    elif cmd == "resume":
        if not arg:
            print("Usage: /resume <session id> (see /history for ids)")
            return None
        if not get_session(arg):
            print(f"No session with id '{arg}'.")
            return None
        state["session_id"] = arg
        state["repo_context"] = None
        state["repo_path"] = None
        print(f"Resumed session {arg} - its previous history is now part of this chat.")
        return "resumed"
    elif cmd == "delete":
        if not arg:
            print("Usage: /delete <session id> (see /history for ids)")
            return None
        if delete_session(arg):
            print(f"Deleted session {arg}.")
            if state["session_id"] == arg:
                state["session_id"] = create_session()
                state["repo_context"] = None
                state["repo_path"] = None
                print(f"Started new session {state['session_id']}.")
        else:
            print(f"No session with id '{arg}'.")
    elif cmd == "stats":
        _print_stats()
    elif cmd == "exit":
        return "exit"
    return None


def _read_line(state: Dict[str, Any], prompt: str = "") -> str:
    """Read one line; slash commands are handled inline and never returned.

    Commands work at every prompt (mode menu, language menu, repo path, code
    input, continue question). /exit raises SystemExit(0) to quit cleanly.
    Returns the raw line only when it is not a recognized command.
    """
    while True:
        try:
            line = input(prompt)
        except EOFError:
            return ""
        if line.strip().startswith("/"):
            parsed = _parse_command(line)
            if parsed is not None:
                action = _handle_command(parsed[0], parsed[1], state)
                if action == "exit":
                    raise SystemExit(0)
                continue
        return line


def _ask_continue(state: Dict[str, Any]) -> bool:
    """Ask whether to continue the chat. Accepts y/n and slash commands.

    Returns True to continue the loop, False to leave the CLI.
    """
    print()
    while True:
        try:
            raw = input("Continue the chat? [y/N] - or type /help for commands: ").strip()
        except EOFError:
            return False
        low = raw.lower()
        if low in {"", "n", "no"}:
            return False
        if low in {"y", "yes"}:
            return True
        parsed = _parse_command(raw)
        if parsed:
            action = _handle_command(parsed[0], parsed[1], state)
            if action == "exit":
                return False
            if action in {"resumed", "new"}:
                return True
            continue
        print("Answer y or n, or type /help for commands.")


def _print_verification(report: Dict[str, Any]) -> None:
    """Print a compact per-block verification verdict for an AI answer."""
    blocks = report.get("blocks") or []
    if not blocks:
        return
    langs = ", ".join(sorted({b["language"] or "?" for b in blocks}))
    print(f"\nVerification ({langs}): {len(blocks)} code block(s) checked")
    for block in blocks:
        issues = block.get("issues") or []
        if block["status"] == "ok":
            print(f"  block {block['index']}: OK ({', '.join(block['checks'])})")
            continue
        print(
            f"  block {block['index']}: {len(issues)} issue(s) "
            f"({', '.join(block['checks'])})"
        )
        for issue in issues[:10]:
            line = f"line {issue['line']}: " if issue.get("line") else ""
            print(f"    {line}{issue['message']}")


def _print_usage(stats: Dict[str, object]) -> None:
    usage = stats.get("usage") or {}
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", 0)
    model = stats.get("model") or "unknown"
    duration = stats.get("duration_ms")
    context_turns = stats.get("context_turns", 0)
    duration_text = f" | {duration / 1000:.1f}s" if duration else ""
    cost = stats.get("cost")
    cost_text = f" | est. cost {_fmt_cost(float(cost))}" if cost else ""
    print(
        f"\n[context: {context_turns} turn(s) | tokens: {prompt} in / "
        f"{completion} out (total {total}) | model: {model}{duration_text}{cost_text}]"
    )


def _prompt_choice(
    prompt: str,
    options: List[str],
    default: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None,
) -> str:
    while True:
        raw = _read_line(state, prompt).strip().lower()
        if not raw and default:
            return default
        if raw in options:
            return raw
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"Invalid choice '{raw}'. Pick a number from 1-{len(options)} or one of: {', '.join(options)}")


def _ask_mode(state: Dict[str, Any]) -> str:
    modes = list(MODE_PROMPTS.keys())
    print("Select a mode (what do you want the mentor to do?):")
    for index, mode in enumerate(modes, start=1):
        description = MODE_DESCRIPTIONS.get(mode, "")
        print(f"  {index}. {mode} - {description}")
    print("  (you can also type a command like /history or /help here)")
    mode = _prompt_choice(
        f"Enter your choice (1-{len(modes)}) [1]: ", modes, default="explain", state=state
    )
    print(f"You selected: {mode}\n")
    return mode


def _ask_language(state: Dict[str, Any]) -> str:
    languages = list(LANGUAGE_LABELS.keys())
    print("Select a programming language:")
    for index, lang in enumerate(languages, start=1):
        print(f"  {index}. {LANGUAGE_LABELS.get(lang, lang)}")
    language = _prompt_choice(
        f"Enter your choice (1-{len(languages)}) [1]: ",
        languages,
        default="python",
        state=state,
    )
    print(f"You selected: {LANGUAGE_LABELS.get(language, language)}\n")
    return language


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError as exc:
        print(f"Could not read file '{path}': {exc}")
        return None


def _resolve_input(text: str) -> Optional[str]:
    stripped = text.strip()
    if stripped.startswith("@"):
        return _read_file(stripped[1:].strip())
    return text


def _pick_folder_dialog() -> Optional[str]:
    """Open a native folder picker dialog, if tkinter is available."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("Folder dialog unavailable (tkinter is not installed).")
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="Select the repository folder")
        root.destroy()
        return path or None
    except Exception as exc:
        print(f"Folder dialog failed: {exc}")
        return None


def _ask_repo_path(state: Dict[str, Any]) -> Optional[str]:
    print("Enter the path of the repository folder to analyze.")
    print("Tip: press Enter to open a folder picker dialog, or type /help for commands.")
    raw = _read_line(state, "Repository path: ").strip().strip('"').strip("'")
    if not raw:
        picked = _pick_folder_dialog()
        if picked:
            return picked
        print("No folder selected via the dialog.")
        return None
    return os.path.abspath(os.path.expandvars(os.path.expanduser(raw)))


def run_cli(
    mode: Optional[str],
    language: Optional[str],
    input_text: Optional[str],
    repo_path: Optional[str] = None,
) -> int:
    """Interactive conversational loop with slash commands.

    Modes 1-4 re-ask mode/language/input on each round, carrying the previous
    chat history into the new round to create a flow. In repo_report mode the
    repository is scanned once, then the user can ask follow-up questions
    about it until they choose to stop. Type /help at any prompt for commands
    (/history, /view, /resume, /new, /back, /delete, /exit).
    """
    mentor = CodeMentor()
    state: Dict[str, Any] = {
        "session_id": create_session(),
        "repo_context": None,
        "repo_path": None,
    }
    first_round = True
    mode = mode or _ask_mode(state)
    print(f"[session {state['session_id']} started - type /help for commands, /history to view sessions]")

    while True:
        if mode != REPO_MODE and not first_round:
            mode = _ask_mode(state)

        if mode == REPO_MODE:
            effective_language = ""
            if state["repo_context"] is None and has_repo_snapshot(state["session_id"]):
                state["repo_context"] = "loaded"
            if state["repo_context"] is None:
                if language:
                    print(
                        f"Note: '--language {language}' is ignored for {REPO_MODE} mode, "
                        "because a repository can contain many languages."
                    )
                path = state["repo_path"] or repo_path or _ask_repo_path(state)
                if not path:
                    print("No repository path provided. Nothing to do.")
                    return 1
                if not os.path.isdir(path):
                    print(f"'{path}' is not a folder.", file=sys.stderr)
                    return 1
                print(f"Scanning repository: {path}")
                try:
                    summary = build_repo_summary(scan_repo(path))
                except OSError as exc:
                    print(f"Failed to scan repository: {exc}", file=sys.stderr)
                    return 1
                state["repo_context"] = summary
                state["repo_path"] = path
                user_message = summary
                max_tokens = REPO_MAX_TOKENS
                print(f"Mode: {REPO_MODE} | Repository: {path}")
                print("Generating report...\n")
            else:
                user_message = _ask_input(
                    "Ask a follow-up question about this repository "
                    "(press Enter twice to finish, or type /help for commands):",
                    state=state,
                )
                if not user_message:
                    print("No question provided. Nothing to do.")
                    return 1
                max_tokens = DEFAULT_MAX_TOKENS
                print("Generating response...\n")
        else:
            if not first_round:
                language = _ask_language(state)
            else:
                language = language or _ask_language(state)
            if first_round and input_text is not None:
                user_message = _resolve_input(input_text)
            else:
                user_message = _resolve_input(_ask_input(state=state))
            if not user_message:
                print("No input provided. Nothing to do.")
                return 1
            cmd = _parse_command(user_message) if user_message.startswith("/") else None
            if cmd:
                action = _handle_command(cmd[0], cmd[1], state)
                if action == "exit":
                    return 0
                continue
            effective_language = mentor.detect_language(user_message) or language
            input_check: Optional[List[Dict[str, Any]]] = None
            if mode == INPUT_SYNTAX_CHECK_MODE and effective_language:
                input_check = syntax_issues(effective_language, user_message)
                if input_check:
                    print(f"Input syntax check: {len(input_check)} issue(s) found before asking the model.")
                    for issue in input_check[:5]:
                        line = f"line {issue['line']}: " if issue.get("line") else ""
                        print(f"  {line}{issue['message']}")
            max_tokens = DEFAULT_MAX_TOKENS
            print(f"Mode: {mode} | Language: {effective_language}")
            print("Generating response...\n")

        prompt_message = (
            user_message
            if mode == REPO_MODE
            else mentor.format_request(mode, effective_language, user_message)
        )
        try:
            history_part, ctx_info = build_context(
                mentor.get_prompt(mode),
                history(state["session_id"]),
                prompt_message,
                memory=get_memory(state["session_id"]),
            )
            if ctx_info["note"]:
                prompt_message = ctx_info["note"] + "\n\n" + prompt_message
            stats = mentor.ask(
                mentor.get_prompt(mode),
                history_part,
                prompt_message,
                max_tokens=max_tokens,
            )
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        result = stats["content"]
        print(result)
        _print_usage(stats)

        verification: Optional[Dict[str, Any]] = None
        if mode in VERIFY_MODES:
            verification = verify_text(result, effective_language)
            if verification["status"] != "no_code":
                _print_verification(verification)
            else:
                verification = None

        if ctx_info["trimmed_turns"] > 0:
            existing = get_memory(state["session_id"]) or {}
            summary = build_memory_summary(
                mentor,
                ctx_info["trimmed_messages"],
                existing_summary=existing.get("summary", ""),
            )
            if summary and summary != existing.get("summary", ""):
                set_memory(
                    state["session_id"],
                    summary,
                    int(existing.get("turns_summarized") or 0) + ctx_info["trimmed_turns"],
                )
                print(
                    f"Memory: {ctx_info['trimmed_turns']} trimmed turn(s) "
                    "folded into the session memory summary."
                )

        user_turn = {
            "role": "user",
            "content": user_message,
            "mode": mode,
            "language": effective_language,
            "timestamp": time.time(),
        }
        if "input_check" in locals() and input_check:
            user_turn["input_check"] = input_check
        assistant_turn = {
            "role": "assistant",
            "content": result,
            "mode": mode,
            "language": effective_language,
            "model": stats.get("model"),
            "provider": stats.get("provider"),
            "usage": stats.get("usage"),
            "context_turns": ctx_info["context_turns"],
            "context": ctx_info,
            "duration_ms": stats.get("duration_ms"),
            "cost": stats.get("cost"),
            "timestamp": time.time(),
        }
        if verification:
            assistant_turn["verification"] = verification
        append_turn(state["session_id"], user_turn)
        append_turn(state["session_id"], assistant_turn)
        first_round = False

        if not _ask_continue(state):
            return 0


def _ask_input(
    prompt: str = "Now enter your code or query (press Enter twice to finish, or use @path/to/file, or type /help for commands):",
    state: Optional[Dict[str, Any]] = None,
) -> str:
    print(prompt)
    lines: List[str] = []
    while True:
        line = _read_line(state)
        stripped = line.strip()
        if stripped.startswith("@"):
            content = _resolve_input(line)
            if content is not None:
                return content
            continue
        if not stripped and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CodeMentor AI - programming mentor from the terminal",
    )
    parser.add_argument(
        "--provider",
        help="LLM provider (default: LLM_PROVIDER env var or groq)",
    )
    parser.add_argument(
        "--mode",
        choices=list(MODE_PROMPTS.keys()),
        help="Task mode (interactive menu if omitted)",
    )
    parser.add_argument(
        "--language",
        choices=list(LANGUAGE_LABELS.keys()),
        help="Programming language (interactive menu if omitted; "
             "not used with --mode repo_report)",
    )
    parser.add_argument(
        "--input",
        help="Code or prompt text (prompted interactively if omitted)",
    )
    parser.add_argument(
        "--repo",
        help="Path to a repository folder to analyze (used with --mode repo_report; "
             "prompted interactively if omitted)",
    )
    args = parser.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    sys.exit(run_cli(args.mode, args.language, args.input, args.repo))


if __name__ == "__main__":
    main()
