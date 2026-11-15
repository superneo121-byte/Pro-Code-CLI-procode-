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

## ðŸš€ Quick Start Guide

### Prerequisites
*   **Termux** (recommended for mobile Android environments) or any standard Linux/macOS/Windows terminal.
*   **Python 3.10+**

### Installation & Setup

1. Clone or place your ProCode script (`procode_2.py`) into your workspace directory.
2. Grant execution permissions and verify your environment:
   ```bash
   python3 procode_2.py --selftest
   ```
3. Launch the interactive CLI REPL:
   ```bash
   python3 procode_2.py
   ```

---

## ðŸ› ï¸ Core Commands Reference

| Command / Flag | Description |
| :--- | :--- |
| `agy` / `pro-code-cli` | Launch the main interactive terminal agent. |
| `/selftest` | Run complete system diagnostics and verify all 50+ subsystems. |
| `/hwmon` | Display current CPU, memory, and thread utilization metrics. |
| `/board` | Open or inspect the active project Kanban/Task board. |
| `/index` | Trigger incremental codebase AST & vector store indexing. |
| `/help` | Display available commands and interactive shortcuts inside the REPL. |

---

## ðŸ“± Mobile Architecture (Termux)

ProCode is built from the ground up to respect mobile hardware boundaries:
*   **Strict Thread Bounding**: `n_threads` is automatically capped ($\le 4$ by default on mobile) to prevent thermal throttling and CPU locking.
*   **Atomic State Protection**: All configuration and state files use atomic rename writes (`.tmp` $
ightarrow$ final) to protect against unexpected process kills or power drops.
*   **Zero External Bloat**: No heavy native compilation requirements for core features, ensuring smooth execution right inside Android's restricted sandbox.

---

## ðŸ“œ License & Contribution

Maintained under personal development. Designed for high-performance mobile engineering, edge AI exploration, and autonomous terminal workflows.
