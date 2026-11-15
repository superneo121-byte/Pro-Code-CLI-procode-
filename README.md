# Pro Code CLI (`procode`)

**Pro Code CLI** (`procode`) is a lightning-fast, robust, standard-library-only terminal AI coding companion designed for developers who want a powerful multi-provider assistant right inside their shell. Built with pure Python, it features zero-dependency execution, an interactive permission guardrails system, local GGUF offline model execution, workspace indexing, Git auto-bootstrap, background agent swarms, worktree isolation, AST-aware symbol patching, self-inspection capabilities, and over 150+ built-in slash commands.

---

## 🚀 Key Features & Architectural Capabilities

* **Universal Multi-Provider Support:** Seamlessly connect to Google AI Studio, OpenRouter, OpenAI, Anthropic (via proxy), DeepSeek, Groq, xAI, Ollama, and LocalAI. Switch providers instantly with `/provider` or fallback chains (`/provider fallback`).
* **Local GGUF Model Inference:** Scan your device downloads folder (`/sdcard/Download` or `PROCODE_GGUF_DIR`) for `.gguf` quantized models and run them entirely offline using `llama-cpp-python` with strict safety thread/context bounds and restricted mode.
* **Smart Permission Guardrails (OpenCode / Antigravity Style):** Interactive approval gates that classify shell commands (safe, caution, dangerous) and block unauthorized destructive actions (like recursive `rm -rf`, raw disk writes, or piped remote scripts) while gracefully prompting for confirmation.
* **Git & GitHub Integration & Auto-Bootstrap:** Automatically detects `git` on startup, offers to install it via system package managers (such as Termux `pkg install git` or Linux `apt`/`dnf`/`pacman`/`apk`) when missing, and provides conventional commit generators (`/commit`), worktrees, and GitHub CLI (`/gh`) integration.
* **Device Storage & File Management:** Full file reading, writing, exact string patching, AST symbol extraction/editing (`/patch-symbol`), diffing, searching, and secure storage root scoping (`/storage`).
* **Background Agent Swarms & Task Graphs:** Run specialist subagents (`/swarm run`) concurrently in background threads, monitor them live (`/swarm watch`), synthesize reports (`/swarm merge`), or decompose big goals into execution waves (`/plan`).
* **Self-Inspection & Self-Modification (Dev Mode):** Inspect and safely patch Pro Code CLI itself (`/self`), compile-check changes, backup, diff, and restart.

---

## 📦 Complete Installation Guide

### Prerequisites
* Python 3.9 or higher (`python --version`)
* Pip package manager (`pip --version`)
* Git (`git --version` — *recommended; procode will offer to auto-install it on Termux/Linux if missing*)

### Method 1: Install Directly from GitHub (Recommended)
```bash
pip install --upgrade --force-reinstall git+https://github.com/superneo121-byte/Pro-Code-CLI-procode-.git
```

### Method 2: Local Installation from Source
1. Clone or navigate to your `Pro-Code-CLI-procode-` directory containing `pyproject.toml`, `setup.py`, and `procode.py`:
   ```bash
   cd Pro-Code-CLI-procode-
   ```
2. Install in editable or standard mode:
   ```bash
   pip install --upgrade --force-reinstall .
   ```

### Optional Extras
* **GGUF Local Inference:**
  ```bash
  pip install pro-code-cli[gguf]
  ```
* **Cryptography (Fernet encryption):**
  ```bash
  pip install pro-code-cli[crypto]
  ```
* **All Extras:**
  ```bash
  pip install pro-code-cli[all]
  ```

---

## 🔑 Configuration & API Keys

Pro Code CLI requires an API key to communicate with cloud providers (Google AI Studio, OpenRouter, OpenAI, etc.). Local endpoints (Ollama, LocalAI) and local GGUF models require no key.

Set your API key as an environment variable in your shell configuration (`~/.bashrc` or `~/.zshrc`):
```bash
export GEMINI_API_KEY="your-api-key-here"
# or
export OPENROUTER_API_KEY="your-api-key-here"
```
*(Alternatively, store your key securely inside the app using `/login`).*

---

## 🛠️ Quick Start & Usage

Launch the interactive REPL by typing:
```bash
procode
```

### Passing prompts directly or via pipes:
```bash
# Ask a direct question
procode "Explain the architecture of this project"

# Pipe code into procode for refactoring
cat app.py | procode "Refactor this script for better performance"

# Run doctor diagnostics
procode /doctor
```

---

## 🕹️ Comprehensive A-Z Slash Command Reference

Pro Code CLI includes over 150+ built-in slash commands organized by domain. Type `/help` inside the REPL to list them at any time.

### 1. Session & Control (`/session`)
* `/session [new [name]|list|rename NAME]` — Manage or list saved sessions.
* `/clear` — Clear the terminal screen.
* `/reset` — Erase conversation history and start fresh.
* `/exit` (or `/quit`, `/q`) — Leave Pro Code CLI.
* `/history [N|search TEXT]` — List messages or search history.
* `/export [json|yaml|md] [path]` — Export session data.
* `/import FILE` — Import a session JSON export or queue a text file as context.
* `/save [name]` — Save the session to disk.
* `/load [name]` — Load a saved session.
* `/config [path|edit|reset]` — Inspect, edit, or reset configuration settings.
* `/status` — View active model, endpoint, auth source, and session stats.
* `/reload` — Reload configuration from disk.
* `/doctor` — Run environment, auth, and network diagnostics.
* `/debug` — Toggle debug output.
* `/logs [N|clear|path]` — Show log tail or clear logs.
* `/version` — Show version info.
* `/update` (or `/upgrade`) — Upgrade via pip.
* `/rollback VERSION` — Install a specific earlier version.
* `/backup` — Back up configuration, sessions, and templates.
* `/restore [file]` — Restore from a backup archive.
* `/clean [all]` — Delete cached responses and old logs.
* `/cache [on|off|stats|clear]` — Control response caching.
* `/stats` — View session usage statistics.
* `/benchmark [N]` — Time requests to test latency.
* `/latency` — Measure round-trip time to the models endpoint.
* `/tokens` — Show token usage and context size.
* `/cost` — Show estimated spending.
* `/budget [USD|off]` — Set a spending cap.
* `/limit [max_tokens|off]` — Cap model output tokens.
* `/timeout [seconds]` — Set network timeout.

### 2. Interface & UI (`/theme`)
* `/verbose` — Toggle verbose output.
* `/quiet` — Hide banners and footers.
* `/silent` — Print only responses and errors.
* `/theme [name]` — Switch color theme (`midnight`, `ember`, `forest`, `paper`, `neon`).
* `/color` — Toggle ANSI colors.
* `/monochrome` — Toggle monochrome mode.
* `/font [unicode|ascii]` — Choose glyph set.
* `/layout [wide|compact|plain]` — Choose status bar layout.
* `/banner [on|off]` — Show or toggle startup banner.
* `/sound` — Toggle terminal audio bell on finish.
* `/bell` — Ring terminal bell.
* `/notify` — Toggle desktop notifications.
* `/clipboard [copy|code|paste]` — Copy response or code blocks to clipboard.
* `/paste [instruction]` — Send clipboard contents to the model.

### 3. AI, Agents & Workflows (`/agents`)
* `/provider [NAME]` — Switch OpenAI-compatible provider (`google`, `openrouter`, `openai`, `anthropic`, `deepseek`, `groq`, `xai`, `ollama`, `localai`, `gguf`).
* `/gguf [list|use NAME|off|threads N|ctx N|status]` — Scan downloads and run local offline GGUF models.
* `/model [name]` — Show or switch model.
* `/models` — List available models at endpoint.
* `/thinking [off|low|medium|high|max]` — Set reasoning depth.
* `/thoughts [on|off|show]` — Show model reasoning blocks.
* `/system [text|reset]` — Show or set system prompt.
* `/temp [0-2]` — Set sampling temperature.
* `/undo` — Remove last exchange.
* `/retry` — Regenerate last response.
* `/compact` — Condense older turns to free context.
* `/edit` — Compose multi-line prompt in `$EDITOR`.
* `/attach [paths...|clear]` — Queue files as context (or use `@path`).
* `/index [on|off|rebuild|status|query TEXT]` — Workspace indexing and semantic context retrieval.
* `/write [on|off|N path]` — Auto-extract code blocks and write to files.
* `/agents [list|run ROLE[,ROLE] TASK]` — Spawn parallel subagents (`ui`, `security`, `review`, `arch`, `tests`, `docs`, `perf`, `refactor`, `debugger`, `devops`).
* `/plan GOAL` — Decompose goal into task graphs and run in parallel waves.
* `/template [list|show N|save N TEXT|rm N|use N [input]]` — Manage prompt templates.
* `/hooks [list|set EVENT CMD|rm EVENT|run EVENT]` — Manage shell hooks.
* `/sanitize` — Toggle automatic secret redacting.
* `/profile` — Speed profile of recent requests.
* `/review [file]` — Code review.
* `/explain [file]` — Code explanation.
* `/refactor FILE [instructions]` — Refactor code.
* `/gentest FILE` — Generate unit tests.
* `/squash` — Summarize conversation into a concise memory memo.
* `/ctx QUERY` — Preview injected workspace context and token count.

### 4. Files, Storage & Patching (`/view`)
* `/cat FILE... [-n]` — Print files.
* `/head FILE [N]` — First N lines.
* `/tail FILE [N]` — Last N lines.
* `/grep PATTERN [PATH] [-i]` — Search files with regex.
* `/find GLOB [PATH]` — Find files by glob.
* `/ls [PATH]` — List directory.
* `/view FILE [START] [END]` — Page through file with line numbers.
* `/write-file PATH` — Compose and write text file.
* `/edit-file FILE 'OLD' 'NEW'` — Exact string replacement with unified diff preview.
* `/del PATH... [-r] [--trash]` — Delete files or move to trash.
* `/cp SRC... DST` — Copy files.
* `/mv SRC... DST` — Move/rename files.
* `/mkdir PATH...` — Create directories.
* `/storage [list|add PATH|rm PATH]` — Manage allowed device storage roots.
* `/diff [A B | git-args]` — Diff files or git diff.
* `/patch FILE INSTRUCTIONS` — Ask model for unified diff.
* `/apply [patchfile]` — Apply patch via git.
* `/applydiff [patchfile] [--dry]` — Apply patch with built-in pure-Python patcher.
* `/outline FILE` — List classes/functions (AST-aware for Python).
* `/symbol FILE NAME` — Print specific Python function or class.
* `/patch-symbol FILE NAME INSTRUCTIONS` — AST-aware precise symbol rewriting with validation and backup.

### 5. Git & GitHub (`/commit`)
* `/commit [-a] [--dry]` — Generate conventional commit message and commit.
* `/push`, `/pull`, `/remote`, `/branch`, `/tag`, `/clone`, `/init`, `/log`, `/add`, `/rm`, `/mv` — Git command passthroughs.
* `/gh [args]` — GitHub CLI passthrough.
* `/sync` — Pull rebase and push.
* `/worktree [list|add NAME [BASE]|rm NAME|cd NAME|back|path NAME|merge NAME]` — Git worktree isolation for concurrent tasks.

### 6. Swarm & Background Agents (`/swarm`)
* `/swarm [run ROLE[,ROLE]|team|all TASK]` — Run specialist agents concurrently in background threads.
* `/swarm status` — Live table of background jobs.
* `/swarm watch` — Live interactive monitoring dashboard.
* `/swarm show N` — View completed job output.
* `/swarm stop N` — Cancel running background jobs.
* `/swarm merge` — Synthesize all specialist reports into an action plan.
* `/swarm clear` — Clear finished jobs.
* `/swarm history` — View persisted job logs.
* `/swarm roles` — List available swarm roles.
* `/monitor` — Live monitor table.

### 7. Dev Workflow & Testing (`/test`)
* `/test` — Run project tests (auto-detected: pytest, cargo, go test, npm test, make).
* `/build` — Build project.
* `/compile` — Syntax-check/compile.
* `/package` — Package distribution.
* `/publish` — Publish package.
* `/run FILE|CMD` — Execute script or command.
* `/deploy` — Run deploy hook.
* `/serve [port] [dir]` — Serve directory over HTTP.
* `/proxy [URL|off]` — Configure HTTP proxy.
* `/tunnel PORT` — Expose local port via cloudflared.

### 8. Network & Web (`/fetch`)
* `/host [NAME]` — Hostname info.
* `/ip [public]` — Show IP addresses.
* `/dns NAME` — Resolve hostname.
* `/ping [HOST[:PORT]]` — TCP latency probe.
* `/pong` — Echo.
* `/port HOST PORT` — Check if TCP port is open.
* `/curl [args|URL]` — Curl passthrough / HTTP GET.
* `/fetch URL [--ctx]` — Fetch web page text (and queue as context).
* `/download URL [dest]` — Download file.
* `/upload FILE URL [--put]` — Upload file.

### 9. Archives, Crypto & Hashes (`/zip`)
* `/zip OUT.zip PATH...` — Create zip archive.
* `/unzip FILE [dest]` — Extract zip safely.
* `/tar c|x|t ARCHIVE [PATHS]` — Tar archives.
* `/gzip [-d] FILE` — Gzip compression.
* `/base64 [-d] TEXT|FILE` — Base64 encode/decode.
* `/md5`, `/sha256` — Checksums.
* `/encrypt FILE|TEXT` — Encrypt with Fernet + PBKDF2 passphrase.
* `/decrypt FILE.enc|TOKEN` — Decrypt.

### 10. Auth, Config & Aliases (`/key`)
* `/key [show|set|rm]` — Manage API key.
* `/token TEXT|FILE` — Estimate token count.
* `/auth` — Test authentication.
* `/login` — Store API key securely.
* `/logout` — Remove API key.
* `/whoami` — User & endpoint summary.
* `/env` — Environment variables (secrets masked).
* `/set KEY VALUE` — Set config setting.
* `/unset KEY` — Reset config setting.
* `/alias [NAME = TEXT | -d NAME]` — Define command shortcuts.

### 11. Shells & Interpreters (`/eval`)
* `/eval EXPR` — Evaluate safe math expression.
* `/exec CMD` — Run program directly.
* `/shell [cmd]` — Run shell line or subshell.
* `/python`, `/bash`, `/sh`, `/zsh`, `/fish`, `/node`, `/ruby`, `/perl` — Interactive REPLs or script execution.

### 12. Permissions & Safety (`/perm`)
* `/perm [strict|balanced|autonomous]` — Set guardrail mode (`strict` = prompt all, `balanced` = prompt cautious, `autonomous` = auto-allow cautious). Dangerous actions (like `rm -rf` or raw disk writes) *always* prompt interactively.
* `/guard CMD LINE` — Dry-run the risk classifier on any command.

### 13. Self-Inspection & Dev Mode (`/self`)
* `/self info` — Inspect Pro Code CLI source stats.
* `/self check` — Syntax compile-check and documentation coverage.
* `/self source [A B]` — View source lines.
* `/self backup` — Create a self-backup.
* `/self diff` — Diff against latest self-backup.
* `/self patch SYMBOL INSTRUCTIONS` — Guarded AST symbol patch on Pro Code CLI itself.
* `/self restore` — Restore from self-backup.
* `/self restart` — Restart Pro Code CLI (autosaves and resumes session).

---

## ⚙️ Storage & Configuration Paths

* **Config File:** `~/.config/pro-code-cli/config.json`
* **Data, Sessions & Swarm logs:** `~/.local/share/pro-code-cli/`
* **Local GGUF Models:** `/sdcard/Download` or `PROCODE_GGUF_DIR`

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.
