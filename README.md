# CodeMentor AI

CodeMentor AI is a single-agent programming mentor web application that helps users explain code, find errors, generate solutions, and optimize existing programs. The project is designed as a simple but practical example of how a frontend can communicate with a backend AI service through a clean request-response pipeline.

This repository currently uses a lightweight full-stack structure:
- a frontend built with plain HTML, CSS, and JavaScript
- a backend built with Python and FastAPI
- an AI model connection through an OpenAI-compatible API provider, currently configured for Groq

---

## 1. Project Goal

The purpose of this project is to demonstrate how a single AI assistant can act like a programming mentor for different tasks:
- explain code in simple language
- identify possible bugs and logic issues
- generate code from user requirements
- improve existing code for clarity and performance
- analyze a whole repository (structure, overview, improvements, and an error report)

The app is intentionally simple so that beginners can understand the flow between the user interface, backend logic, and AI model.

---

## 2. High-Level Architecture

The system works in three main layers:

1. Frontend layer
   - the browser collects user input and sends it to the backend
   - it displays the AI response in a readable format

2. Backend layer
   - FastAPI handles incoming requests
   - the application routes the request to the correct prompt category
   - the backend prepares the message payload for the AI provider

3. AI provider layer
   - the backend sends the prompt to the configured model endpoint
   - the provider returns a response that is passed back to the frontend

### Request Flow

```text
User -> Frontend Form -> POST /mentor -> FastAPI app -> CodeMentor logic -> AI model -> Response -> Frontend display
```

---

## 3. Folder Structure

```text
CodeMentor/
├── backend/
│   ├── app.py
│   ├── cli.py
│   ├── llm.py
│   ├── mentor.py
│   ├── prompts.py
│   ├── requirements.txt
│   ├── test_features.py
│   └── tools.py
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── run.py
├── .env.example
├── README.md
└── venv/
```

---

## 4. Technologies Used

### Frontend
- HTML: structure of the web page
- CSS: styling for the user interface
- JavaScript: handles form submission and API communication
- Marked.js: renders AI responses as Markdown in the browser

### Backend
- Python: main programming language for the server logic
- FastAPI: web framework for routing and API handling
- Pydantic: request validation and model parsing
- python-dotenv: loads environment variables from .env files
- requests: sends HTTP requests to the AI provider

### AI Integration
- OpenAI-compatible API provider
- Current configuration uses Groq through an OpenAI-style endpoint

---

## 5. Frontend Documentation

The frontend is a simple single-page interface that allows the user to choose:
- programming language
- task mode
- code or prompt input

### Files in the frontend folder

#### frontend/index.html
This is the UI structure.

Why it exists:
- it provides the input form, dropdowns, textarea, and result area
- it connects the page to the JavaScript logic and CSS styling

Main parts:
- language selector
- mode selector
- code input textarea
- submit button
- response container

#### frontend/script.js
This file contains the browser-side logic.

Why it exists:
- it collects the selected values from the form
- it builds a JSON payload for the backend
- it sends a POST request to the /mentor endpoint
- it handles success and error responses
- it renders the returned output in the browser

Key behavior:
- uses the Fetch API to send HTTP requests
- uses Marked.js to render Markdown nicely
- shows a loading message while waiting for the AI response

#### frontend/style.css
This file styles the app.

Why it exists:
- it makes the interface look clean and modern
- it improves readability of code and Markdown output
- it gives the page a card-based layout and responsive behavior

---

## 6. Backend Documentation

The backend is responsible for receiving the request from the frontend, deciding which prompt to use, and sending the content to the AI model.

### Files in the backend folder

#### backend/app.py
This is the main FastAPI application file.

Why it exists:
- it creates the web server
- it defines the API endpoints
- it serves the frontend files as a static site

Important parts:
- /health: simple health check endpoint
- /mentor: POST endpoint that accepts the user request
- CORS middleware: allows browser requests from the frontend
- static file mounting: serves the frontend page when the app runs

The request model uses a Pydantic class named MentorRequest, which validates the incoming JSON fields:
- mode
- language
- input_text

#### backend/mentor.py
This file contains the core “single-agent” behavior.

Why it exists:
- it picks the correct prompt style based on the selected mode
- it formats the user request into a structured message
- it passes the prepared messages to the AI layer

The class CodeMentor acts as the central decision point.

How it works:
- get_prompt(mode) selects the system prompt for the chosen function
- format_request(...) adds language and mode information to the user content
- mentor_response(...) builds the final structure and returns the AI output

This is the place where the app behaves like a single intelligent assistant rather than a collection of separate services.

#### backend/llm.py
This file handles the connection to the AI provider.

Why it exists:
- it loads API configuration from environment variables
- it builds the request headers and payload
- it sends the prompt to the provider
- it handles errors such as invalid credentials, bad requests, and network issues

Key responsibilities:
- a unified provider layer: the `LLMProvider` class speaks the OpenAI-compatible
  chat completions protocol, so the same client can serve multiple backends
- a provider registry (`PROVIDERS`) maps names such as `groq` to their env vars
- `get_provider()` builds the active provider from `LLM_PROVIDER` and the
  matching `*_API_KEY`, `*_API_BASE`, and `*_MODEL` variables
- `call_openai()` keeps the old function name so `mentor.py` stays unchanged
- `build_message()` constructs the standard system/user message pair

This file is the bridge between your application logic and the external AI service.

#### backend/cli.py
This file provides a command-line interface for the same mentor core.

Why it exists:
- it lets you talk to the assistant from the terminal, without the web app
- it reuses the exact same `CodeMentor` logic as the API, so both front ends behave identically

How it works:
- interactive mode asks for the task mode, programming language, and input
- non-interactive mode accepts `--mode`, `--language`, and `--input` flags
- input can be typed directly (press Enter twice to finish) or read from a
  file with `@path/to/file.py`
- errors such as missing API keys are printed to stderr with a clear message

#### backend/prompts.py
This file stores the system prompts for each mode.

Why it exists:
- it keeps the AI instructions separate from the application logic
- it makes the assistant behavior easy to edit or expand
- it allows each mode to have a slightly different style of response

The supported modes are:
- explain
- error_finder
- generate
- optimize
- repo_report

Each mode has a tailored prompt so the AI behaves differently depending on the task.

The `repo_report` mode has an extra piece of logic in `backend/repo.py`, a local
scanner that walks the repository folder and builds a compact snapshot for the AI:
a file tree, detected languages, key configuration files, source contents
(size-capped to fit the model context), and quick local static checks (Python
`SyntaxError`s and invalid JSON) so the AI can report on them. Sensitive files
such as `.env` or `*.pem` are never read.

#### backend/session.py
This file stores the conversation history of every session (CLI and web) in
`backend/sessions.json` (git-ignored).

Why it exists:
- every turn is recorded with metadata: the query, mode, language, model,
  provider, token usage (`prompt_tokens` / `completion_tokens` / `total_tokens`),
  context size (how many previous turns were in the request), duration, and
  timestamp
- the web app shows this history in a sidebar, and each answer displays its
  token usage and context info under the response
- sessions are trimmed (oldest first) and capped so the file stays small

#### backend/tools.py
This file contains a small helper for extracting the assistant content from the API response.

Why it exists:
- it simplifies response parsing
- it can be reused if the response structure changes

#### backend/test_features.py
This file is a simple test script.

Why it exists:
- it verifies whether the AI API credentials and connection are working
- it prints the response status and body from the provider

It is useful for debugging provider connectivity before using the web app.

#### backend/requirements.txt
This file lists the Python packages required to run the backend.

Why it exists:
- it makes installation reproducible
- it ensures the project has the required dependencies when set up on another machine

---

## 7. How the App Connects Together

The connection between the frontend and backend is simple:

1. The user types code or a prompt in the frontend.
2. The frontend sends a JSON body to the /mentor endpoint.
3. FastAPI receives the request and validates it.
4. The backend route calls the CodeMentor logic.
5. The assistant selects the correct prompt based on the chosen mode.
6. The backend sends the message to the AI provider.
7. The AI provider returns a response.
8. The backend sends the result back as JSON.
9. The frontend renders the result in the output panel.

This is the core architecture of the project.

---

## 8. Environment Configuration

The project expects environment variables to be defined before running the backend.

A template file is available at .env.example.

### Example variables

```env
LLM_PROVIDER=groq

# Groq
GROQ_API_KEY=your_api_key_here
GROQ_API_BASE=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile

# OpenRouter
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_API_BASE=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openrouter/auto
```

These values are loaded by the backend using python-dotenv.

`LLM_PROVIDER` selects which backend the unified provider layer uses.
Each provider has its own `*_API_KEY`, `*_API_BASE`, and `*_MODEL` variables
(e.g. `GROQ_API_KEY` for `groq`, `OPENROUTER_API_KEY` for `openrouter`).
The launcher (`python run.py`) also asks which provider to use at startup;
that choice only applies to the current session.

> Important: the AI provider needs a valid API key in order for the app to return real responses.

---

## 9. How to Run the Project

### 1. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

On Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your values:

```bash
copy .env.example .env
```

### 4. Start the app (one command)

Run the unified launcher from the project root:

```bash
python run.py
```

It asks two questions:

1. which front end you want: **1. Web app (GUI)** or **2. CLI (terminal)**
2. which LLM provider to use: **1. Groq** (default) or **2. OpenRouter**

- **Web app (GUI)** starts the FastAPI server and opens the browser automatically
- **CLI (terminal)** opens a new terminal window with the command-line mentor

### 5. Open the frontend

The web app opens your browser at:

```text
http://127.0.0.1:8000/
```

If you prefer running the server directly (e.g. for development with auto-reload):

```bash
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### 6. Use the CLI (optional)

The same mentor core is available from the terminal.

Easiest way: run `python run.py` and choose **2. CLI (terminal)**.
It opens a new terminal window with the interactive menu.

Directly from the terminal, interactive mode (asks for mode, language, and input):

```bash
python -m backend.cli
```

Non-interactive mode:

```bash
python -m backend.cli --mode explain --language python --input "print('hello')"
```

Read input from a file instead of typing it:

```bash
python -m backend.cli --mode optimize --language python --input @backend/mentor.py
```

Analyze a whole repository (no language is asked in this mode, since a repo can
contain many languages; the path can be typed or picked from a folder dialog by
pressing Enter):

```bash
python -m backend.cli --mode repo_report --repo C:\path\to\your\project
```

The CLI is conversational: after every answer it asks "Continue the chat?" If you
say yes, the previous chat history is carried into the next round (for modes 1-4
it re-asks mode/language/input). In repo_report mode, the repository is scanned
once and follow-up questions keep the repository snapshot in context.

Slash commands work at any prompt (also at the "Continue the chat?" question):

```text
/help              show all commands
/history           list all sessions (id, turns, total tokens, preview)
/view <id>         show a session's conversation with per-turn token usage,
                   context size, model, and duration
/resume <id>       continue a previous session (its history becomes the chat context)
/back              return to the chat prompt
/new               start a new session
/delete <id>       delete a session
/exit              quit the CLI
```

Example: type `/history`, note a session id, then `/view 3` to inspect it, and
`/resume 3` to keep chatting with its history loaded. All sessions (CLI and web)
are stored in `backend/sessions.json`.

---

## 10. Example Request

The frontend sends a JSON body like this:

```json
{
  "mode": "explain",
  "language": "python",
  "input_text": "print('Hello')",
  "session_id": ""
}
```

`session_id` is optional: empty creates a new session, and passing an existing
id continues that conversation with history. The response includes the
`session_id` plus per-turn metadata (`usage`, `model`, `provider`,
`duration_ms`, `context_turns`).

History endpoints:
- `GET /sessions` - compact list of all sessions (preview, turn count, total tokens)
- `GET /sessions/{id}` - full conversation with per-turn metadata
- `DELETE /sessions/{id}` - remove a session

The backend returns a JSON object containing the result field with the AI-generated response.

---

## 11. Why This Project Is Useful

This project is a good learning example because it shows:
- how a web app can interact with an AI API
- how to separate frontend, backend, and AI logic cleanly
- how prompt engineering can change the behavior of the same assistant
- how a simple app can be extended into a more advanced AI tool later

---

## 12. Possible Future Improvements

Possible next steps for the project:
- add authentication
- support file upload for code analysis
- add conversation history
- support more languages and coding tasks
- add a database for saved chats
- move from a single-agent design to a multi-agent architecture

---

## 13. Summary

CodeMentor AI is a beginner-friendly, practical example of a single-agent coding assistant built with:
- HTML/CSS/JavaScript for the frontend
- FastAPI for the backend
- Python logic for prompt routing
- an external AI model for intelligent responses

It is simple enough to understand quickly, but structured well enough to grow into a more advanced AI-powered coding tool.
