# ProCode CLI (agy / pro-code-cli) v2.0

> **The Ultimate Terminal-Based AI Coding Assistant & Enterprise Development Suite**  
> *Engineered specifically for mobile-first development environments (Termux, Android), scalable across local GGUF execution and cloud-hosted AI APIs.*

---

## ðŸŒŸ Overview & Philosophy

**ProCode CLI** (`pro-code-cli` / `agy`) is an advanced, self-contained terminal assistant built entirely on Python's standard library. It bridges the gap between powerful desktop-class AI development workflows and mobile terminals. Whether you are running quantized local models via llama.cpp/GGUF or dispatching multi-agent swarms across cloud providers (OpenRouter, Groq, Gemini AI Studio, Hugging Face), ProCode provides a zero-friction, production-grade development suite right in your pocket.

---

## ðŸ“‹ A-Z Comprehensive Feature Index

Here is the exhaustive A-Z feature breakdown of everything packed into ProCode CLI:

*   **A - Agent Swarms & Autonomy**: Autonomous multi-agent coordination pipelines that delegate coding, testing, debugging, and documentation tasks concurrently.
*   **B - Board Management (`board.json`)**: Integrated task tracking, Kanban-style status boards, and milestone progression directly within your project directory.
*   **C - Codebase Indexing & AST Analysis**: Deep parsing of source files using Abstract Syntax Trees to map symbols, dependencies, and code structures instantly.
*   **D - Diff Engine & Multi-File Transactions**: Atomic file updates with precise unified diff generation, previewing, rollback protection, and multi-file transactional commits.
*   **E - Embedding & Vector Search (`VectorStore`)**: Local vector embeddings powered by lightweight SQLite storage for semantic code search, retrieval-augmented generation (RAG), and context recall.
*   **F - File Operations & Sandbox Safety**: Robust file system navigation, automated code scaffolding, template generation, and safe path traversal checks.
*   **G - GGUF Local Model Inference**: Direct execution of quantized GGUF models on mobile CPU hardware with thread capping, context window management, and memory safety guards.
*   **H - Hardware Monitoring (`/hwmon`)**: Real-time tracking of memory consumption, CPU thread allocation, and session resource utilization to prevent Android OOM crashes.
*   **I - Interactive REPL & Command Router**: A rich, lightning-fast command-line interface supporting command history, tab-completion, multi-line prompts, and dynamic routing.
*   **J - JSON State Persistence**: Human-readable, atomic state storage across sessions using safe write patterns (temp-file rename) to eliminate data corruption.
*   **K - Key Management & API Vault**: Secure credential storage and provider routing supporting dynamic failover across OpenRouter, Groq, Google Gemini, and Hugging Face.
*   **L - LSP-Lite Code Navigation**: Lightweight Language Server Protocol features providing symbol definition lookup, reference tracing, and structural code insights without heavy daemon overhead.
*   **M - Memory Graphs (`memory_graph.json`)**: Persistent relational memory tracking code decisions, user preferences, bug histories, and architectural notes across long-term sessions.
*   **N - Network & Proxy Adaptation**: Resilient API call handling with automatic retry logic, exponential backoff, timeout handling, and offline fallback modes.
*   **O - Optimized Prompt Templates**: Curated system prompts engineered to squeeze maximum reasoning performance out of both small local models and frontier LLMs.
*   **P - Project Scaffolding & Boilerplates**: Instant generation of complete project layouts, web apps (`Aura Weather`, `Omni AI`, `Vault.ai`), and CLI utilities.
*   **Q - Quantization & Memory Tuning**: Granular controls for CPU thread bounding (`n_threads`), context window sizing (`n_ctx`), and memory reclamation (`gc.collect()`).
*   **R - Repository Management (`Git` & `GitHub CLI`)**: Seamless integration with Git workflows and GitHub CLI authentication for rapid staging, committing, and remote syncing.
*   **S - Self-Test Suite (`/selftest`)**: Comprehensive automated diagnostic suite validating 50+ internal subsystems, dependencies, and environment variables on startup.
*   **T - Termux & Mobile Optimization**: Tailored specifically for Android Termux environments, accounting for mobile shell limitations, storage permissions, and resource constraints.
*   **U - Unified Logging & Audit Trails**: Detailed session logging and error tracking for debugging failed generations or reviewing past agent transactions.
*   **V - Version Control Integration**: Built-in diff viewers, patch appliers, and backup checkpoints to ensure you never lose working code during agent refactors.
*   **W - Web & API Scraping Tools**: Built-in utilities for fetching remote documentation, parsing markdown/HTML snippets, and integrating external context into prompts.
*   **X - XML / Structured Output Parsers**: Robust parsing engines designed to extract clean tool calls, code blocks, and structured JSON from raw LLM text streams.
*   **Y - YAML / Config Management**: Flexible configuration loading for custom profiles, model parameters, system prompts, and environment overrides.
*   **Z - Zero-Dependency Core**: Built purely on Python's standard library for core execution, eliminating cumbersome pip installation hurdles in restricted environments.

---

## âš™ï¸ Complete Installation & Setup Guide

### 1. Prerequisites
*   **Termux** (recommended for Android mobile development) or any standard Linux, macOS, or Windows terminal environment.
*   **Python 3.10 or higher** installed on your system.

### 2. Setting Up Termux (Android Mobile Environment)
If you are running ProCode CLI on an Android device via Termux, run the following commands to set up your storage, update packages, and install Python:

```bash
# Setup phone storage access
termux-setup-storage

# Update package repositories
pkg update && pkg upgrade -y

# Install essential development packages (Python, Git, build tools)
pkg install python git clang make libffi openssl -y

# Upgrade pip to the latest version
pip install --upgrade pip
```

### 3. Downloading and Preparing ProCode CLI
1. Place your ProCode script file (`procode_2.py`) into your desired working directory (e.g., `~/projects/procode`).
2. Navigate to the directory:
   ```bash
   cd ~/projects/procode
   ```
3. Make the script executable (optional, but convenient):
   ```bash
   chmod +x procode_2.py
   ```

### 4. Running System Diagnostics (`--selftest`)
Before launching your interactive session, verify that all internal subsystems and Python dependencies are fully operational:
```bash
python3 procode_2.py --selftest
```
This runs an automated validation across 50+ internal modules, ensuring your environment is ready.

### 5. Launching the Interactive REPL
To start the ProCode CLI assistant:
```bash
python3 procode_2.py
```
*(Tip: You can set up a shell alias in your `.bashrc` or `.zshrc` for instant access: `alias agy="python3 /path/to/procode_2.py"`)*

---

## ðŸš€ Core Commands Reference

| Command / Flag | Action / Description |
| :--- | :--- |
| `agy` / `pro-code-cli` | Launch the main interactive terminal agent REPL. |
| `/selftest` | Run complete system diagnostics and verify all internal subsystems. |
| `/hwmon` | Display current CPU, thread utilization, and memory metrics. |
| `/board` | Open or inspect the active project Kanban/Task tracking board. |
| `/index` | Trigger incremental codebase AST parsing and vector store embedding. |
| `/help` | Display available commands and interactive shortcuts inside the REPL. |

---

## ðŸ“± Mobile Architecture & Performance Best Practices

*   **Strict Thread Bounding**: `n_threads` is automatically capped ($\le 4$ by default on mobile CPU setups) to prevent thermal throttling, excessive battery drain, and CPU locking.
*   **Atomic State Protection**: All configuration files, memory graphs, and task boards use atomic temporary file renames (`.tmp` $
ightarrow$ final) to eliminate data corruption if Termux is abruptly closed or OOM-killed.
*   **Zero External Bloat**: The core engine requires zero external `pip` packages, allowing it to run smoothly even in heavily restricted sandbox environments.

---

## ðŸ“œ License & Contribution

Maintained under personal development. Engineered for high-performance mobile engineering, edge AI exploration, and autonomous terminal workflows.
