# Pro Code CLI (`procode`)

**Pro Code CLI** is a blazing-fast, production-grade terminal AI coding companion built using only the Python standard library. It connects to Google AI Studio's OpenAI-compatible endpoint (`gemini-4-hydrogen`) with out-of-the-box zero-auth defaults.

---

## 🚀 Quick Setup & Installation Guide

### 1. Requirements
* Python 3.9 or higher
* Termux (on Android) or any standard Linux/macOS terminal.

### 2. Global Installation via GitHub
You can install or update the tool directly from your repository using `pip`:
```bash
pip install --force-reinstall git+https://github.com/superneo121-byte/Pro-Code-CLI-procode-.git
```

### 3. Authentication Setup
Google AI Studio requires an API key to communicate with the model. You can authenticate using either method:
* **Interactive Login:** Run `procode`, then type:
  ```text
  /login
  ```
  *(Paste your Google AI Studio API key when prompted).*
* **Environment Variable:** Set it in your shell configuration:
  ```bash
  export GEMINI_API_KEY="your_actual_api_key_here"
  ```

---

## 💡 Usage Examples

* **Launch Interactive REPL:**
  ```bash
  procode
  ```
* **Run a Single Prompt:**
  ```bash
  procode "Explain how async/await works in Python"
  ```
* **Pipe Code for Review / Conversion:**
  ```bash
  procode "Review this legacy function and convert it into a clean, zero-dependency single-file module:" < old_function.py
  ```

---

## 🛠️ Complete Command Reference (160+ Commands)

### Session & Control
* `/session` – Show or manage the current session
* `/clear` – Clear terminal screen
* `/reset` – Erase conversation history
* `/exit`, `/quit`, `/q` – Quit Pro Code CLI
* `/history` – List or search message history
* `/export` – Export session data (JSON, YAML, Markdown)
* `/import` – Import session data or load files as context
* `/save`, `/load` – Save and load sessions
* `/config` – View or edit configuration
* `/status` – Display current model, token usage, and flags
* `/doctor` – Run environment and connectivity diagnostics
* `/stats` – View session token usage and timing statistics
* `/budget` – Set spending limits

### Interface & UI
* `/theme` – Switch color themes (`midnight`, `ember`, `forest`, `paper`, `neon`)
* `/color`, `/monochrome` – Toggle color and monochrome modes
* `/font` – Choose glyph sets (`unicode` or `ascii`)
* `/layout` – Change status-bar layout
* `/clipboard` – Interact with system clipboards

### AI & Agents
* `/model` – Switch active AI model
* `/thinking`, `/think` – Adjust reasoning depth (`off`, `low`, `medium`, `high`, `max`)
* `/thoughts` – Inspect model reasoning/thinking blocks
* `/system` – Manage system prompts
* `/attach` – Queue local files as prompt context
* `/index` – Manage local workspace indexing
* `/write`, `/extract` – Auto-extract and write code blocks to files
* `/agents` – Spawn parallel subagents (`ui`, `security`, `review`, `arch`, `tests`, `docs`, `perf`, `refactor`)
* `/plan`, `/decompose` – Break complex goals into task graphs
* `/review`, `/explain`, `/refactor`, `/gentest` – Quick code workflows

### Files, Git & Dev Workflow
* `/cat`, `/head`, `/tail` – Inspect files
* `/grep`, `/find` – Search workspace files
* `/diff`, `/patch`, `/apply` – Code diffing and patching
* `/commit` – Generate conventional commit messages
* `/test`, `/build`, `/compile`, `/run` – Run project workflows

### Network & Utilities
* `/ip`, `/host`, `/dns`, `/ping`, `/port` – Network diagnostics
* `/curl`, `/fetch`, `/download`, `/upload` – Web requests and file transfers
* `/zip`, `/unzip`, `/tar`, `/gzip` – Archive management
* `/encrypt`, `/decrypt` – Secure file and text encryption
* `/eval`, `/exec`, `/shell`, `/python` – Execution environments

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.
