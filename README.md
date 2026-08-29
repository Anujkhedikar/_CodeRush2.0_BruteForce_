# YUKTI

**Your code. Understood.**

A local-first, verification-first AI programming mentor. YUKTI reads your codebase the way a senior engineer does — then explains it, finds the bugs, writes the fix, and measures the result. Every turn is recorded in a transparent token/cost ledger.

> **Verification-first, execution-nowhere.** YUKTI statically validates generated code (AST parse, `node --check`, delimiter heuristics) and **never executes** it. No prompts leave your machine beyond the configured LLM provider; no secrets leave your repo.

---

## Highlights

- **Five focused mentor modes** — Explain, Find Errors, Generate, Optimize, and Repo Report — each with a dedicated instruction sheet and model tier.
- **Provider-agnostic LLM layer** — Groq (default) or OpenRouter behind one OpenAI-compatible client. Swap by setting one environment variable.
- **Tiered session memory** — long threads are trimmed to a token budget and condensed into a riding summary, so context stays coherent and inexpensive.
- **Verification gate** — every generated block is parsed locally and fingerprint-checked (`sha256` of raw block vs. re-parsed tree) before a verdict is sealed.
- **Built-in observability** — per-turn token counts, latency, model, provider, and cost (4-decimal) streamed into `/stats`.
- **Two polished front ends** — a static, Tailwind-driven marketing site plus a React playground served under `/app`.

---

## The Five Mentor Modes

| Mode | What it does | Locally verified |
| :--- | :--- | :--- |
| `explain` | Explains code line by line; overall logic, time & space complexity. | — |
| `error_finder` | Finds syntax errors and logical mistakes, explains why, suggests corrected code. Input pre-checked locally. | ✅ |
| `generate` | Writes clean, readable, commented code and explains how it works. | ✅ |
| `optimize` | Improves code while preserving behavior — readability & best practices first. | ✅ |
| `repo_report` | Analyzes a whole repository: structure, overview, technologies, improvements, errors. | — |

Supported languages: **Python, Java, C, C++** (newer additions are provider-agnostic).

---

## Architecture

```
                    ┌───────────────────────────┐
                    │   run.py  (launcher)      │
                    │   Web GUI  ·  CLI         │
                    └────────────┬──────────────┘
                                 │
        ┌────────────────────────┴───────────────────────┐
        ▼                                                ▼
┌───────────────────┐                        ┌──────────────────────┐
│   FastAPI web app │                        │    terminal CLI     │
│  backend/app.py   │                        │   backend/cli.py    │
│  /mentor /sessions│                        │  shared core below  │
│  /stats /health   │                        └──────────┬───────────┘
└─────────┬─────────┘                                   │
          └───────────────┬─────────────────────────────┘
                          ▼
                 ┌─────────────────────────────┐
                 │      mentor.py (core)       │
                 │  assistant orchestration    │
                 └─────────┬───────────────────┘
      ┌────────────┬───────┼──────────┬───────────┬────────────┐
      ▼            ▼       ▼          ▼           ▼            ▼
  llm.py      prompts.py  context.py  memory.py   verify.py    repo.py
  providers    mode texts  token      tiered      static       repo
                            budget    summary     checks       scanner
      └────────────┬───────┴──────────┴──────────┴────────────┘
                   ▼
            session.py              observability.py
            JSON store               cost + analytics
```

### Data flow (web)

1. Browser `POST /mentor` with `{ mode, language, input_text, session_id }`.
2. `app.py` delegates to `mentor.py` → resolves the mode prompt → applies `context.py` (token budget + memory) → calls the active provider via `llm.py`.
3. For `generate` / `error_finder` / `optimize`, the reply is verified locally via `verify.py`.
4. The result (content + usage + verification) is persisted via `session.py` and returned as JSON.
5. The front end renders Markdown, appends verification / cost chips, and refreshes the sidebar + analytics.

---

## Repository Layout

```
.
├── run.py                    # Unified launcher: Web GUI or CLI + provider select
├── backend/                  # Python backend package (FastAPI + CLI)
│   ├── app.py                # FastAPI app, HTTP routes, static frontend mount
│   ├── cli.py                # Terminal CLI front end (shares the same core)
│   ├── mentor.py             # Core assistant orchestration
│   ├── llm.py                # LLM provider registry (Groq / OpenRouter)
│   ├── prompts.py            # Per-mode system prompts + labels
│   ├── context.py            # Token-budget context manager (default 12,000)
│   ├── memory.py             # Tiered summarization for trimmed turns
│   ├── verify.py             # Verification-first layer (AST / node / heuristics)
│   ├── repo.py               # Local repository scanner (repo_report)
│   ├── session.py            # Thread-safe JSON session store (50 × 40 turns)
│   ├── observability.py      # Usage analytics + cost estimation
│   ├── tools.py              # Response formatting helpers
│   └── test_*.py             # pytest suites
├── frontend/                 # Static marketing + docs site (no build step)
│   ├── index.html            # Home — hero, mode carousel, architecture
│   ├── platform.html         # Engine / observability pipeline deep-dive
│   ├── modes.html            # The five mentor modes
│   ├── telemetry.html        # Live analytics surface
│   ├── faq.html · about.html · docs.html
│   ├── css/app.css           # Shared theme (tactical pages)
│   ├── js/app.js             # Nav, ticker, telemetry, cursor-glow behaviors
│   └── favicon.svg           # YUKTI Y-mark (inline SVG, gradient #FF8A4D→#FF5B00)
└── X402-Usecase/             # React playground (served by backend at /app)
    ├── src/components/       # TopNav, PlaygroundSidebar, ChatTranscript,
    │                         # Composer, CursorGlow, TacticalHero, …
    ├── dist/                 # Production build (vite base "/app/")
    └── vite.config.ts
```

> `backend/x402-demo-server`, `x402-demo-server`, and `x402-Project-main` are vendored Algorand/X402 hackathon demos — **not** imported by the Python backend and not part of YUKTI's runtime.

---

## Getting Started

### 1. Backend

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 2. Configure

Copy the template to `backend/.env` and add your provider key:

```bash
cp .env.example backend/.env   # then edit
```

```ini
LLM_PROVIDER=groq

GROQ_API_KEY=sk-...                      # see README section below
GROQ_API_BASE=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-120b

OPENROUTER_API_KEY=sk-or-...             # alternative provider
OPENROUTER_API_BASE=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openrouter/auto
```

### 3. Run

```bash
# Unified launcher (recommended) — pick Web (1) or CLI (2)
python run.py

# Or run the web server directly
python -m uvicorn "backend.app:app" --host 127.0.0.1 --port 8000
```

The web app opens at **http://127.0.0.1:8000** — marketing site at `/`, playground at `/app`.

### 4. React playground (dev & build)

```bash
cd X402-Usecase
npm install

npm run dev          # Vite dev server

npx tsc && npx vite build   # production bundle → dist/ (served under /app)
```

---

## Environment Variables

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | Active provider: `groq` or `openrouter` | `groq` |
| `GROQ_API_KEY` | Groq API key | — |
| `GROQ_MODEL` | Groq model id | `openai/gpt-oss-120b` |
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `OPENROUTER_MODEL` | OpenRouter model id | `openrouter/auto` |

> **Security:** never commit real keys. `backend/.env` and any `.env.*` files are git-ignored; `.env.example` ships placeholders only.

---

## API Reference

Web front ends talk to the backend purely via HTTP/JSON `fetch()`.

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check → `{"message": "…", ...}` |
| `POST` | `/mentor` | Main chat endpoint — body `{mode, language, input_text, session_id}` |
| `GET` | `/sessions` | Compact session summaries (sidebar) |
| `GET` | `/sessions/{id}` | Full session detail (turns + memory) |
| `DELETE` | `/sessions/{id}` | Delete a session |
| `GET` | `/stats` | Usage analytics overview (totals + breakdowns) |
| `GET` | `/` · `/app` | Static marketing site · React playground |

**`POST /mentor` response shape:**

```jsonc
{
  "result":        "… rendered Markdown answer …",
  "session_id":    "…",
  "mode":          "generate",
  "language":      "cpp",
  "usage":         { "prompt_tokens": n, "completion_tokens": n, "total_tokens": n },
  "model":         "…",
  "provider":      "groq",
  "duration_ms":   n,
  "context_turns": n,
  "context":       { "trimmed_turns": n, "memory_turns": n },
  "verification":  { "status": "ok", "blocks": [ … ] },   // generate / error_finder / optimize
  "input_check":   [ … ]                                 // error_finder only
}
```

**Error semantics:** `400` empty input / invalid repo folder · `404` session not found · `503` provider failure (missing key, model, or rate limit).

---

## The Verification-First Layer

`backend/verify.py` never executes generated code. Instead:

- **Python** → `ast` parse for syntax + undefined-name analysis (module / function / nested scope).
- **JavaScript / TypeScript** → `node --check` when a Node runtime is present.
- **Other languages** → delimiter-balance heuristic.

`extract_code_blocks()` pulls fenced blocks from the Markdown reply; `verify_text()` aggregates per-block results into `{ status, blocks }`. Modes `generate`, `error_finder`, and `optimize` are always verified.

---

## Observability & Cost Ledger

Every request records prompt/completion tokens, latency, model, provider, and cost (4 decimals) into a JSON ledger — surfaced live at `/stats` and in the playground's Analytics view. `backend/observability.py` maintains a `MODEL_PRICING` table and exposes `estimate_cost()`, `session_cost()`, and `overview()` (totals, by-mode, by-provider, by-model, by-day, top sessions).

---

## Testing

All suites are `pytest`-based in `backend/`:

```bash
pytest -q
```

| File | Coverage area |
| :--- | :--- |
| `test_verify.py` | Markdown extraction, Python AST checks, JS `node --check` (mocked), delimiter fallback, input pre-check, `/mentor` verification responses |
| `test_context.py` | Token estimation, budget override, trimming, memory integration |
| `test_memory.py` | Extractive + LLM summarization, re-use, persistence |
| `test_observability.py` | Cost estimation, totals, breakdowns, top sessions |

Playground lint + typecheck:

```bash
cd X402-Usecase
npm run lint -- --max-warnings 0
npx tsc --noEmit
```

---

## License & Distribution

© 2026 YUKTI. All rights reserved. Local-first, no code execution.