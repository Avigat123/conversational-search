# Conversational Search Engine
 
A search system that remembers the conversation, understands follow-up questions, and answers with cited evidence. It runs on free APIs and works on Windows and Linux.
 
- **"What is the capital of France?"** → a cited answer with sources.
- **"What about its population?"** → rewritten as *"What is the population of Paris?"*, reusing evidence it already has and searching only if it needs more.
| Component | Role |
|---|---|
| **LLM** (OpenAI-compatible API with tool calling) | Rewrites follow-ups, decides what to search, writes the answer |
| **RAG** (retrieval-augmented generation) | Stores pages and snippets gathered in the conversation in a vector index, so later turns reuse them |
| **Agentic search** | The model chooses tools in a loop (`search_memory`, `web_search`, `fetch_page`) and stops when it has enough evidence |
 
Every factual claim is tied to a numbered source. Citations are checked in code, and any marker that points at a source the system never retrieved is removed before you see the answer.
 
---
 
## Free stack
 
| Need | Option | Key? | Notes |
|---|---|---|---|
| LLM | **Google Gemini** (recommended) | Free key from Google AI Studio | Get it at https://aistudio.google.com/apikey |
| LLM | **Groq** | Free key | https://console.groq.com/keys. Fast, but tighter per-minute limits. |
| LLM | **OpenRouter** (`:free` models) | Free key | https://openrouter.ai/keys. Free model list changes often. |
| LLM | **Ollama** (local) | No | https://ollama.com. Needs a model that supports tool calling, such as `llama3.1`. Slow without a GPU. |
| Search | **DuckDuckGo** (`ddgs`) | No | Default. Unofficial client, so it can be rate limited under heavy use. |
| Search | **Wikipedia** API | No | Official. Good for encyclopedic facts, not news. |
| Search | **SearXNG** (self-hosted) | No | Most reliable for heavy use. Needs a server or Docker. |
 
Switching LLM provider means changing three values in `.env`: `LLM_BASE_URL`, `LLM_API_KEY`, and `CONSEARCH_MODEL`.
 
> Free-tier limits and model names change often. Check the provider's current docs before you rely on one.
 
---
 
## Setup
 
You need Python 3.10 or newer. Python 3.11 or 3.12 is recommended, since every dependency has prebuilt packages for those versions.
 
### Windows
 
**1. Install Python.** Download it from https://www.python.org/downloads/windows/. On the first installer screen, tick **"Add python.exe to PATH"** before clicking Install. Check the install in a new PowerShell window:
 
```powershell
py --version
```
 
**2. Get the project.** Unzip `conversational-search.zip` somewhere easy to find, such as `C:\Users\<you>\conversational-search`, then open PowerShell in that folder. In File Explorer, open the folder and type `powershell` in the address bar.
 
**3. Create a virtual environment and install the dependencies.**
 
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
 
If activation fails with an "running scripts is disabled" error, allow local scripts for your user account once, then try again:
 
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
 
If you use Command Prompt (cmd) instead of PowerShell, activate with `.venv\Scripts\activate.bat`. Your prompt shows `(.venv)` when the environment is active.
 
**4. Create your `.env` file.** Copy the template, then open the copy in Notepad or any editor:
 
```powershell
copy .env.example .env
notepad .env
```
 
Set your key (see [Configuration](#configuration) for the full list):
 
```
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=paste-your-gemini-key-here
CONSEARCH_MODEL=gemini-2.5-flash
SEARCH_PROVIDER=duckduckgo
```
 
Save the file. Make sure it is named `.env` and not `.env.txt`. In Notepad, choose **Save as type: All files** if needed.
 
The app reads `.env` itself, so you don't need to load it into the shell.
 
**5. Run it.**
 
```powershell
python -m consearch
```
 
### Linux (Ubuntu / Debian)
 
**1. Install Python and the venv module.** Most distributions include Python 3. On Debian and Ubuntu, you may also need the venv package:
 
```bash
python3 --version
sudo apt update && sudo apt install -y python3-venv python3-pip
```
 
On Fedora, use `sudo dnf install python3`. On Arch, `python` is already installed.
 
**2. Get the project.**
 
```bash
unzip conversational-search.zip
cd conversational-search
```
 
**3. Create a virtual environment and install the dependencies.**
 
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```
 
Your prompt shows `(.venv)` when the environment is active. Run `source .venv/bin/activate` again in each new terminal.
 
**4. Create your `.env` file.**
 
```bash
cp .env.example .env
nano .env        # or any editor
```
 
Set your key, the same as in the Windows section:
 
```
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=paste-your-gemini-key-here
CONSEARCH_MODEL=gemini-2.5-flash
SEARCH_PROVIDER=duckduckgo
```
 
**5. Run it.**
 
```bash
python -m consearch
```
 
### Notes on `.env`
 
- Write `KEY=value` with no spaces around `=` and no quotes unless the value contains spaces.
- Lines starting with `#` are comments. A trailing `# comment` after a value is also ignored.
- Real environment variables override `.env`. This matters if a value is already set in your shell.
- Never commit `.env` or share it. It holds your API key. The included `.gitignore` already excludes it.
---
 
## Usage
 
### Interactive chat
 
Windows and Linux use the same commands:
 
```
python -m consearch
```
 
```
you> What is retrieval-augmented generation?
... answer with [1][2] markers ...
Sources:
  [1] Retrieval-augmented generation - Wikipedia - https://en.wikipedia.org/...
 
you> How does it differ from fine-tuning?
... answer that reuses earlier evidence ...
```
 
Commands inside the chat: `/sources` lists everything gathered, `/reset` starts a new conversation, `/quit` exits.
 
### One-shot question
 
```
python -m consearch -q "Who designed the Eiffel Tower?" -v
```
 
`-v` shows each tool call and the step count.
 
### Search your own documents
 
Windows:
```
python -m consearch --ingest notes\architecture.md specs\api.txt
```
 
Linux:
```
python -m consearch --ingest notes/architecture.md specs/api.txt
```
 
Ingested files become numbered sources, searched alongside the web. Only `.txt` and `.md` files are supported.
 
### HTTP API
 
```
pip install uvicorn            # already in requirements.txt
uvicorn consearch.api:app --reload
```
 
Then open http://127.0.0.1:8000/docs for the interactive API page. On Windows PowerShell, use `Invoke-RestMethod` instead of `curl`:
 
```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask -ContentType "application/json" `
  -Body '{"session_id":"demo","question":"Who created the Rust programming language?"}'
```
 
On Linux:
 
```bash
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"session_id":"demo","question":"Who created the Rust programming language?"}'
```
 
### Tests
 
```
pytest -q tests
```
 
The tests run offline with a scripted LLM and fake search, so they need no keys and no network.
 
---
 
## Ollama (fully local, no key)
 
Install Ollama from https://ollama.com (Windows installer, or `curl -fsSL https://ollama.com/install.sh | sh` on Linux). Then pull a model that supports tool calling:
 
```
ollama pull llama3.1
```
 
In `.env`, use:
 
```
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=
CONSEARCH_MODEL=llama3.1
SEARCH_PROVIDER=duckduckgo
```
 
Leave `LLM_API_KEY` empty. Ollama runs as a background service after install. If the app cannot connect, check that Ollama is running (the tray icon on Windows, or `ollama serve` on Linux).
 
---
 
## Configuration
 
| Variable | Default | Purpose |
|---|---|---|
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Any OpenAI-compatible endpoint |
| `LLM_API_KEY` | none | Provider key (leave empty for Ollama) |
| `CONSEARCH_MODEL` | `openai/gpt-oss-20b` | Model for condensing and answering. Must support tool calling. |
| `SEARCH_PROVIDER` | `duckduckgo` | `duckduckgo`, `wikipedia`, or `searxng` |
| `SEARXNG_URL` | none | Base URL of your SearXNG instance, e.g. `http://localhost:8080` |
| `CONSEARCH_MAX_STEPS` | `6` | Maximum tool-use rounds per question |
| `CONSEARCH_TOP_K` | `5` | Results per search or memory lookup |
| `CONSEARCH_HISTORY_TURNS` | `6` | Past exchanges included in context |
| `CONSEARCH_EMBEDDER` | `tfidf` | `tfidf` (no downloads) or `sentence-transformers` (semantic) |
| `CONSEARCH_CHUNK_WORDS` / `CONSEARCH_CHUNK_OVERLAP` | `180` / `30` | Chunk size and overlap |
| `CONSEARCH_FETCH_CHARS` | `4000` | Characters of a fetched page returned to the model |
 
---
 
## Troubleshooting
 
**Windows**
 
- **`python` or `py` is not recognized.** Reinstall Python and tick "Add python.exe to PATH", or open a new PowerShell window after installing.
- **Activation says scripts are disabled.** Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- **Installing `scikit-learn` or `numpy` fails.** You are probably on a very new or very old Python. Install Python 3.11 or 3.12 and recreate `.venv`.
- **`.env` not picked up.** Check the file name is `.env` and not `.env.txt`. Turn on file extensions in File Explorer's View menu to see it.
- **Unicode or odd characters in `.env`.** Save it as UTF-8. The app accepts a BOM, but other encodings can break keys.
**Linux**
 
- **`ensurepip is not available`.** Install `python3-venv` as shown above.
- **`command not found: python`.** Use `python3`. Inside the activated `.venv`, `python` works.
- **Permission errors on install.** Don't use `sudo pip`. Stay inside the virtual environment.
**Both**
 
- **`401` or `invalid API key`.** Check `LLM_API_KEY` for stray spaces or a missing character.
- **`model not found`.** The model name is wrong or unavailable on your key. Look up the current name in the provider's docs and update `CONSEARCH_MODEL`.
- **`429` or rate-limit errors.** Free tiers have per-minute and daily caps. The app retries with backoff. Wait a few minutes, lower `CONSEARCH_MAX_STEPS`, or switch provider.
- **Empty or thin web results.** DuckDuckGo may be throttling you. Try `SEARCH_PROVIDER=wikipedia` for factual questions, or run SearXNG.
---
 
## Project structure
 
```
conversational-search/
├── consearch/
│   ├── config.py     # settings and .env loading
│   ├── llm.py        # OpenAI-compatible client with tool calling and rate-limit retries
│   ├── agent.py      # agentic loop, system prompt, step budget
│   ├── tools.py      # tool schemas and dispatch (web_search, fetch_page, search_memory)
│   ├── search.py     # free search providers (DuckDuckGo, Wikipedia, SearXNG) and page fetcher
│   ├── rag.py        # chunking, embedders (TF-IDF / sentence-transformers), vector index
│   ├── sources.py    # source registry and citation verification
│   ├── session.py    # conversation memory, follow-up condensation, entry point
│   ├── cli.py        # terminal app
│   └── api.py        # FastAPI endpoint
├── tests/test_core.py
├── .env.example
├── .gitignore
└── requirements.txt
```
 
---
 
## Limitations
 
- **Free tiers have limits.** Expect rate-limit waits and daily caps. Heavy use needs a paid plan or a local model.
- **DuckDuckGo access is unofficial** and may throttle. SearXNG is more reliable.
- **Free models are weaker at tool calling** than frontier models. If the agent loops, set `CONSEARCH_MAX_STEPS=3` or try another model.
- **Sessions are in memory.** A restart clears them. The API has no authentication or rate limiting, so add both before exposing it publicly.
- **Only `.txt` and `.md` files are ingested.**
- **Answer quality is not benchmarked yet.**
---
 
## License
 
Add a license before distributing.
 
