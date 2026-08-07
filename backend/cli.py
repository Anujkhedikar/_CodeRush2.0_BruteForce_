# cli.py
# Command-line interface for CodeMentor AI.
# Shares the same core (CodeMentor) as the web app, just with a terminal front end.

import argparse
import os
import sys
from typing import List, Optional

try:
    from .mentor import CodeMentor
    from .prompts import LANGUAGE_LABELS, MODE_DESCRIPTIONS, MODE_PROMPTS
    from .repo import build_repo_summary, scan_repo
except ImportError:  # pragma: no cover - fallback for direct execution
    from mentor import CodeMentor
    from prompts import LANGUAGE_LABELS, MODE_DESCRIPTIONS, MODE_PROMPTS
    from repo import build_repo_summary, scan_repo

REPO_MODE = "repo_report"
REPO_MAX_TOKENS = 4096


def _prompt_choice(prompt: str, options: List[str], default: Optional[str] = None) -> str:
    while True:
        raw = input(prompt).strip().lower()
        if not raw and default:
            return default
        if raw in options:
            return raw
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print(f"Invalid choice '{raw}'. Pick a number from 1-{len(options)} or one of: {', '.join(options)}")


def _ask_mode() -> str:
    modes = list(MODE_PROMPTS.keys())
    print("Select a mode (what do you want the mentor to do?):")
    for index, mode in enumerate(modes, start=1):
        description = MODE_DESCRIPTIONS.get(mode, "")
        print(f"  {index}. {mode} - {description}")
    mode = _prompt_choice(f"Enter your choice (1-{len(modes)}) [1]: ", modes, default="explain")
    print(f"You selected: {mode}\n")
    return mode


def _ask_language() -> str:
    languages = list(LANGUAGE_LABELS.keys())
    print("Select a programming language:")
    for index, lang in enumerate(languages, start=1):
        print(f"  {index}. {LANGUAGE_LABELS.get(lang, lang)}")
    language = _prompt_choice(
        f"Enter your choice (1-{len(languages)}) [1]: ", languages, default="python"
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


def _ask_repo_path() -> Optional[str]:
    print("Enter the path of the repository folder to analyze.")
    print("Tip: press Enter to open a folder picker dialog instead.")
    raw = input("Repository path: ").strip().strip('"').strip("'")
    if not raw:
        picked = _pick_folder_dialog()
        if picked:
            return picked
        print("No folder selected via the dialog.")
        return None
    return os.path.abspath(os.path.expandvars(os.path.expanduser(raw)))


def _run_repo_report(repo_path: Optional[str]) -> int:
    path = repo_path or _ask_repo_path()
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

    mentor = CodeMentor()
    print(f"Mode: {REPO_MODE} | Repository: {path}")
    print("Generating report...\n")

    try:
        result = mentor.mentor_response(REPO_MODE, "", summary, max_tokens=REPO_MAX_TOKENS)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result["result"])
    return 0


def run_cli(
    mode: Optional[str],
    language: Optional[str],
    input_text: Optional[str],
    repo_path: Optional[str] = None,
) -> int:
    mode = mode or _ask_mode()

    if mode == REPO_MODE:
        if language:
            print(
                f"Note: '--language {language}' is ignored for {REPO_MODE} mode, "
                "because a repository can contain many languages."
            )
        return _run_repo_report(repo_path)

    language = language or _ask_language()
    input_text = input_text or _ask_input()
    input_text = _resolve_input(input_text)

    if not input_text:
        print("No input provided. Nothing to do.")
        return 1

    mentor = CodeMentor()
    print(f"Mode: {mode} | Language: {language}")
    print("Generating response...\n")

    try:
        result = mentor.mentor_response(mode, language, input_text)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result["result"])
    return 0


def _ask_input() -> str:
    print("Now enter your code or query (press Enter twice to finish, or use @path/to/file):")
    lines: List[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
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
