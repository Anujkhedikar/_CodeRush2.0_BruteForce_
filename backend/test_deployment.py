import sys
from pathlib import Path


def test_app_imports_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_PROVIDER", raising=False)

    backend_dir = Path(__file__).resolve().parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    for name in ("app", "mentor", "llm"):
        sys.modules.pop(name, None)

    import app

    assert app.app is not None
    assert app.app.title == "CodeMentor AI"
