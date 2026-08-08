# run.py
# Unified launcher for CodeMentor AI.
# One command, two front ends (web app / CLI) and a choice of LLM providers.

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import List

try:
    from backend.llm import PROVIDERS, get_provider
except ImportError:  # pragma: no cover - fallback when run from inside the repo
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from backend.llm import PROVIDERS, get_provider

PROJECT_ROOT = Path(__file__).resolve().parent
WEB_URL = "http://127.0.0.1:8000"


def _interpreter() -> str:
    """Prefer the project venv interpreter so the CLI window has all deps."""
    candidates = [
        PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _choose_interface() -> str:
    print("CodeMentor AI - how do you want to run it?")
    print("  1. Web app (GUI)")
    print("  2. CLI (terminal)")
    while True:
        choice = input("Select [1]: ").strip().lower()
        if not choice or choice in {"1", "web", "gui", "w"}:
            return "web"
        if choice in {"2", "cli", "c", "terminal", "t"}:
            return "cli"
        print(f"Invalid choice '{choice}'. Pick 1 or 2.")


def _choose_provider() -> str:
    provider_names = list(PROVIDERS.keys())
    print("CodeMentor AI - select the LLM provider:")
    for index, name in enumerate(provider_names, start=1):
        label = PROVIDERS[name]["label"]
        default_note = " (default)" if index == 1 else ""
        print(f"  {index}. {label}{default_note}")
    while True:
        raw = input(f"Enter your choice (1-{len(provider_names)}) [1]: ").strip().lower()
        if not raw:
            return provider_names[0]
        if raw in provider_names:
            return raw
        if raw.isdigit() and 1 <= int(raw) <= len(provider_names):
            return provider_names[int(raw) - 1]
        print(f"Invalid choice '{raw}'. Pick a number from 1-{len(provider_names)} or one of: {', '.join(provider_names)}")


def _apply_provider(provider: str) -> bool:
    """Mark the provider as active and verify its API key is configured."""
    try:
        active = get_provider(provider)
    except RuntimeError as exc:
        print(f"Provider not ready: {exc}")
        return False
    os.environ["LLM_PROVIDER"] = provider
    print(f"Using LLM provider: {active.name} (model: {active.model})")
    return True


def _start_web(provider: str) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Missing dependencies. Run: pip install -r backend/requirements.txt")
        return 1

    import backend.app  # loads .env; the chosen provider is applied after this

    os.environ["LLM_PROVIDER"] = provider

    threading.Timer(1.5, lambda: webbrowser.open(WEB_URL)).start()
    print(f"CodeMentor AI web app starting at {WEB_URL}")
    print("Close this window or press Ctrl+C to stop the server.")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000)
    return 0


def _open_cli_window(provider: str) -> bool:
    command = [_interpreter(), "-m", "backend.cli", "--provider", provider]

    if os.name == "nt":
        subprocess.Popen(
            ["cmd", "/k"] + command,
            cwd=PROJECT_ROOT,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return True

    terminals: List[List[str]] = [
        ["gnome-terminal", "--"] + command,
        ["konsole", "-e"] + command,
        ["x-terminal-emulator", "-e"] + command,
        ["xfce4-terminal", "-e"] + command,
    ]
    for launch in terminals:
        try:
            subprocess.Popen(launch, cwd=PROJECT_ROOT)
            return True
        except OSError:
            continue
    return False


def _start_cli(provider: str) -> int:
    if _open_cli_window(provider):
        print("CLI opened in a new window. Close this window when you are done.")
        return 0
    print("Could not open a terminal window automatically.")
    print(f"Run it manually from the project root: {_interpreter()} -m backend.cli --provider {provider}")
    return 1


def main() -> None:
    interface = _choose_interface()
    provider = _choose_provider()

    if not _apply_provider(provider):
        sys.exit(1)

    if interface == "web":
        sys.exit(_start_web(provider))
    sys.exit(_start_cli(provider))


if __name__ == "__main__":
    main()
