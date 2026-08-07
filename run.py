# run.py
# Unified launcher for CodeMentor AI.
# One command, two front ends: the web app (GUI) or the CLI.

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

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


def _start_web() -> int:
    try:
        import uvicorn
    except ImportError:
        print("Missing dependencies. Run: pip install -r backend/requirements.txt")
        return 1

    threading.Timer(1.5, lambda: webbrowser.open(WEB_URL)).start()
    print(f"CodeMentor AI web app starting at {WEB_URL}")
    print("Close this window or press Ctrl+C to stop the server.")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000)
    return 0


def _open_cli_window() -> bool:
    command = [_interpreter(), "-m", "backend.cli"]

    if os.name == "nt":
        subprocess.Popen(
            ["cmd", "/k"] + command,
            cwd=PROJECT_ROOT,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return True

    terminals = [
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


def _start_cli() -> int:
    if _open_cli_window():
        print("CLI opened in a new window. Close this window when you are done.")
        return 0
    print("Could not open a terminal window automatically.")
    print(f"Run it manually from the project root: {_interpreter()} -m backend.cli")
    return 1


def _choose() -> str:
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


def main() -> None:
    if _choose() == "web":
        sys.exit(_start_web())
    sys.exit(_start_cli())


if __name__ == "__main__":
    main()
