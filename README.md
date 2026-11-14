# Pro Code CLI (`procode`)

**Pro Code CLI** is a robust, lightning-fast terminal AI coding companion designed for developers who want a powerful, multi-provider AI assistant right inside their terminal. Built with pure Python (standard library only, with optional GGUF and cryptography extras), it features zero-dependency execution, an interactive permission guardrail system, local GGUF model support, workspace indexing, and Git auto-bootstrap.

---

## 🚀 Key Features

* **Universal Multi-Provider Support:** Seamlessly connect to Google AI Studio, OpenRouter, OpenAI, Anthropic (via proxy), DeepSeek, Groq, xAI, Ollama, and LocalAI. Switch providers instantly with `/provider`.
* **Local GGUF Model Execution:** Scan your local downloads folder for `.gguf` quantized models and run them locally using `llama-cpp-python` with strict safety bounds and thread caps.
* **Smart Permission Guardrails:** OpenCode-style interactive approval gates that block unauthorized destructive actions (like recursive `rm -rf`, raw disk operations, or unverified remote piped scripts) while gracefully handling interactive confirmations.
* **Git & GitHub Integration & Auto-Bootstrap:** Automatically detects `git` on startup, offers to install it via system package managers (such as Termux `pkg install git` on Android or Linux) when missing, and provides conventional commit generators, cloning, and remote management.
* **Device Storage & File Management:** Full file reading, writing, patching, diffing, searching, and workspace indexing with secure permission scoping.
* **Interactive REPL & Slash Commands:** Over 180+ built-in slash commands for session management, file operations, web fetching, git workflows, and subagent orchestration.

---

## 📦 Installation

Install Pro Code CLI directly from PyPI or your local development repository:

```bash
# Standard installation
pip install pro-code-cli

# With optional extras (GGUF local inference / cryptography)
pip install pro-code-cli[gguf,crypto]
```

---

## 🛠️ Quick Start

Run `procode` directly in your terminal, or pass a prompt as an argument:

```bash
# Start the interactive REPL
procode

# Ask a direct question
procode "Explain the architecture of this project"

# Pipe code into Pro Code CLI for refactoring
cat app.py | procode "Refactor this script for better performance"
```

---

## 🕹️ Essential Slash Commands

* `/help` — List all available commands and group references.
* `/provider [name]` — Switch between OpenAI-compatible AI providers.
* `/gguf` — Scan downloads and load local `.gguf` models.
* `/status` — View active session, model, provider, and configuration state.
* `/doctor` — Run environment, auth, and connectivity diagnostics.
* `/commit` — Generate a conventional commit message from staged changes and commit.
* `/agents [roles] [task]` — Spawn parallel subagents (security, review, arch, tests, perf, refactor).
* `/index on` — Enable automatic local workspace indexing and code context retrieval.
* `/exit` — Leave the Pro Code CLI session.

---

## ⚙️ Configuration

Pro Code CLI stores its configuration at:
* **Linux/Termux/macOS:** `~/.config/pro-code-cli/config.json`
* **Data/Sessions:** `~/.local/share/pro-code-cli/`

Override any endpoint or model on the fly using environment variables:
* `PROCODE_PROVIDER`
* `PROCODE_BASE_URL`
* `PROCODE_MODEL`
* `PROCODE_API_KEY` (or provider-specific keys like `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`)

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.
