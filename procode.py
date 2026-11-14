#!/usr/bin/env python3
"""Pro Code CLI - a terminal AI coding companion.

Talks to Google AI Studio's OpenAI-compatible endpoint (model: gemini-4-hydrogen)
using only the Python standard library. Run `procode "hello"` or just `procode`.
"""
from __future__ import annotations

import argparse
import ast
import base64
import concurrent.futures as cf
import difflib
import fnmatch
import getpass
import glob
import gzip
import hashlib
import http.client
import json
import math
import operator
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

try:
    import readline  # noqa: F401
except ImportError:  # pragma: no cover (Windows)
    readline = None  # type: ignore

__version__ = "1.0.0"
APP_NAME = "Pro Code CLI"
HOMEPAGE = "https://github.com/your-org/pro-code-cli"  # edit before publishing

CONFIG_DIR = Path(os.environ.get("PROCODE_CONFIG_DIR", Path.home() / ".config" / "pro-code-cli"))
DATA_DIR = Path(os.environ.get("PROCODE_DATA_DIR", Path.home() / ".local" / "share" / "pro-code-cli"))
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSIONS_DIR = DATA_DIR / "sessions"
CACHE_DIR = DATA_DIR / "cache"
TEMPLATES_DIR = DATA_DIR / "templates"
LOGS_DIR = DATA_DIR / "logs"
BACKUPS_DIR = DATA_DIR / "backups"
REPORTS_DIR = DATA_DIR / "reports"
LOG_FILE = LOGS_DIR / "procode.log"

DEFAULTS = {
    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "model": "gemini-4-hydrogen",
    "fallback_models": [],
    "api_key": "",
    "temperature": 0.7,
    "max_tokens": 0,
    "timeout": 120,
    "retries": 3,
    "thinking": "medium",
    "show_thoughts": False,
    "stream": True,
    "max_context_tokens": 24000,
    "max_parallel": 4,
    "theme": "midnight",
    "glyphs": "unicode",
    "layout": "wide",
    "banner": True,
    "verbose": False,
    "quiet": False,
    "silent": False,
    "debug": False,
    "sound": False,
    "notify": False,
    "cache": False,
    "sanitize": True,
    "auto_write": False,
    "index_workspace": False,
    "budget_usd": 0.0,
    "price_in_per_mtok": 0.0,
    "price_out_per_mtok": 0.0,
    "proxy": "",
    "system_prompt": "",
    "hooks": {},
    "aliases": {},
}

FLAGS = {"yes": False}

SYSTEM_DEFAULT = (
    "You are Pro Code CLI, an expert pair-programming assistant running inside a terminal. "
    "Be concise and precise. Prefer working code over prose. Use fenced code blocks with language tags. "
    "When asked to change code, return complete, runnable results."
)
EXTRACT_HINT = (
    "When you output a complete file, begin its fenced block with a first-line comment of the form "
    "`# file: relative/path.ext` (using the comment syntax of the language) so it can be written to disk."
)

# --------------------------------------------------------------------------- #
# Terminal UI
# --------------------------------------------------------------------------- #
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
THEMES = {
    "midnight": {"accent": 75, "accent2": 141, "muted": 244, "ok": 78, "warn": 214, "err": 203, "code": 151, "head": 117},
    "ember": {"accent": 209, "accent2": 215, "muted": 243, "ok": 114, "warn": 220, "err": 196, "code": 223, "head": 216},
    "forest": {"accent": 71, "accent2": 108, "muted": 243, "ok": 120, "warn": 179, "err": 167, "code": 151, "head": 114},
    "paper": {"accent": 25, "accent2": 90, "muted": 240, "ok": 28, "warn": 130, "err": 124, "code": 24, "head": 18},
    "neon": {"accent": 51, "accent2": 201, "muted": 245, "ok": 46, "warn": 226, "err": 197, "code": 159, "head": 87},
}
GLYPHS = {
    "unicode": {"dot": "●", "arrow": "❯", "bar": "│", "top": "╭", "bot": "╰", "h": "─", "ok": "✓", "x": "✗",
                "warn": "▲", "bullet": "•", "tool": "⚙", "spin": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", "blk": "█"},
    "ascii": {"dot": "*", "arrow": ">", "bar": "|", "top": "+", "bot": "+", "h": "-", "ok": "+", "x": "x",
              "warn": "!", "bullet": "-", "tool": "*", "spin": "|/-\\", "blk": "#"},
}


class UI:
    color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
    mono = False
    quiet = False
    silent = False
    glyphs = "unicode"
    layout = "wide"
    theme = "midnight"


def g(key: str) -> str:
    return GLYPHS[UI.glyphs][key]


def c(text, role: str = "accent", bold: bool = False, dim: bool = False) -> str:
    if not UI.color:
        return str(text)
    pre = (BOLD if bold else "") + (DIM if dim else "")
    if not UI.mono:
        pre += f"\033[38;5;{THEMES[UI.theme][role]}m"
    return f"{pre}{text}{RESET}" if pre else str(text)


def out(*a, **k) -> None:
    print(*a, **k, flush=True)


def note(msg: str, role: str = "muted") -> None:
    if not (UI.quiet or UI.silent):
        out(c(msg, role))


def good(msg: str) -> None:
    if not UI.silent:
        out(c(g("ok") + " ", "ok", True) + msg)


def warn(msg: str) -> None:
    if not UI.silent:
        print(c(f"{g('warn')} {msg}", "warn"), file=sys.stderr, flush=True)


def bad(msg: str) -> None:
    print(c(f"{g('x')} {msg}", "err", True), file=sys.stderr, flush=True)


def tool_line(msg: str) -> None:
    if not (UI.quiet or UI.silent):
        out(c(g("tool") + " ", "accent2") + c(msg, "muted"))


def term_width() -> int:
    return shutil.get_terminal_size((100, 24)).columns


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


def human(n: float) -> str:
    n = float(n)
    return f"{n/1000:.1f}k" if n >= 1000 else f"{int(n)}"


def trunc(s: str, n: int) -> str:
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


class Spinner:
    def __init__(self, label: str = "working") -> None:
        self.label = label
        self.t0 = time.time()
        self._stop = threading.Event()
        self._t: Optional[threading.Thread] = None
        self.active = sys.stderr.isatty() and not (UI.quiet or UI.silent)

    def _run(self) -> None:
        frames, i = g("spin"), 0
        while not self._stop.is_set():
            el = time.time() - self.t0
            sys.stderr.write("\r\033[K" + c(frames[i % len(frames)], "accent") + " " + c(self.label, "muted")
                             + " " + c(f"{el:0.1f}s", "muted", dim=True))
            sys.stderr.flush()
            i += 1
            self._stop.wait(0.08)

    def start(self) -> "Spinner":
        if self.active and not self._t:
            self.t0 = time.time()
            self._stop.clear()
            self._t = threading.Thread(target=self._run, daemon=True)
            self._t.start()
        return self

    def stop(self) -> None:
        if self._t:
            self._stop.set()
            self._t.join()
            self._t = None
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


FONT = {
    "P": ["###", "#.#", "###", "#..", "#.."], "R": ["###", "#.#", "##.", "#.#", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"], "C": ["###", "#..", "#..", "#..", "###"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."], "E": ["###", "#..", "##.", "#..", "###"],
    "L": ["#..", "#..", "#..", "#..", "###"], "I": ["###", ".#.", ".#.", ".#.", "###"],
}


def banner_lines(text: str = "PRO CODE CLI") -> list:
    th = THEMES[UI.theme]
    roles = ["accent", "accent", "head", "accent2", "accent2"]
    rows = []
    for r in range(5):
        parts = []
        for ch in text:
            if ch == " ":
                parts.append("  ")
            else:
                parts.append("".join(g("blk") if p == "#" else " " for p in FONT[ch][r]) + " ")
        rows.append(c("".join(parts), roles[r], bold=True))
    del th
    return rows


def print_banner(app: "App") -> None:
    if UI.quiet or UI.silent:
        return
    out()
    for line in banner_lines():
        out("  " + line)
    out()
    out("  " + c(f"v{__version__}", "accent2", True) + c(f"  {g('bullet')}  {app.cfg['model']}  {g('bullet')}  "
        "type ", "muted") + c("/help", "accent", True) + c(" for commands, ", "muted") + c("/exit", "accent", True)
        + c(" to quit", "muted"))
    out()


def md_inline(s: str) -> str:
    s = re.sub(r"`([^`]+)`", lambda m: c(m.group(1), "code"), s)
    if UI.color:
        s = re.sub(r"\*\*([^*]+)\*\*", lambda m: BOLD + m.group(1) + RESET, s)
    return s


class StreamRenderer:
    """Line-buffered markdown/code renderer for streamed tokens."""

    def __init__(self) -> None:
        self.line = ""
        self.in_code = False
        self.parts: list = []

    def feed(self, text: str) -> None:
        self.parts.append(text)
        self.line += text
        while "\n" in self.line:
            ln, self.line = self.line.split("\n", 1)
            self._emit(ln)

    def finish(self) -> None:
        if self.line:
            self._emit(self.line)
            self.line = ""

    def _emit(self, ln: str) -> None:
        if not UI.color:
            out(ln)
            return
        s = ln.strip()
        if s.startswith("```"):
            if not self.in_code:
                lang = s[3:].strip().split(" ")[0] if s[3:].strip() else "code"
                out(c(g("top") + g("h") + " " + lang, "muted"))
            else:
                out(c(g("bot") + g("h"), "muted"))
            self.in_code = not self.in_code
            return
        if self.in_code:
            out(c(g("bar"), "muted") + " " + c(ln, "code"))
            return
        m = re.match(r"^(#{1,6})\s+(.*)", ln)
        if m:
            out(c(m.group(2), "head", bold=True))
        elif re.match(r"^\s*[-*]\s+", ln):
            ind, rest = re.match(r"^(\s*)[-*]\s+(.*)", ln).groups()  # type: ignore
            out(ind + c(g("bullet"), "accent") + " " + md_inline(rest))
        elif ln.startswith(">"):
            out(c(g("bar") + " " + ln.lstrip("> "), "muted", dim=True))
        elif re.match(r"^\s*([-*_])\1{2,}\s*$", ln):
            out(c(g("h") * min(60, term_width()), "muted", dim=True))
        else:
            out(md_inline(ln))


class ThoughtSplitter:
    """Splits <thought>...</thought> segments out of a content stream."""

    def __init__(self) -> None:
        self.buf, self.inside = "", False

    def feed(self, s: str) -> list:
        self.buf += s
        res = []
        while True:
            tag = "</thought>" if self.inside else "<thought>"
            i = self.buf.find(tag)
            if i >= 0:
                if i:
                    res.append(("thought" if self.inside else "text", self.buf[:i]))
                self.buf = self.buf[i + len(tag):]
                self.inside = not self.inside
                continue
            hold = 0
            for k in range(min(len(tag) - 1, len(self.buf)), 0, -1):
                if tag.startswith(self.buf[-k:]):
                    hold = k
                    break
            emit = self.buf[: len(self.buf) - hold]
            if emit:
                res.append(("thought" if self.inside else "text", emit))
            self.buf = self.buf[len(self.buf) - hold:]
            return res

    def flush(self) -> list:
        res = [("thought" if self.inside else "text", self.buf)] if self.buf else []
        self.buf = ""
        return res


# --------------------------------------------------------------------------- #
# Config, logging, utilities
# --------------------------------------------------------------------------- #
def ensure_dirs() -> None:
    for d in (CONFIG_DIR, SESSIONS_DIR, CACHE_DIR, TEMPLATES_DIR, LOGS_DIR, BACKUPS_DIR, REPORTS_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass


def load_config() -> dict:
    ensure_dirs()
    cfg = json.loads(json.dumps(DEFAULTS))
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text("utf-8")))
        except (OSError, ValueError) as e:
            warn(f"Could not read {CONFIG_FILE}: {e}; using defaults")
    else:
        save_config(cfg)
    if os.environ.get("PROCODE_BASE_URL"):
        cfg["base_url"] = os.environ["PROCODE_BASE_URL"]
    if os.environ.get("PROCODE_MODEL"):
        cfg["model"] = os.environ["PROCODE_MODEL"]
    return cfg


def save_config(cfg: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2, sort_keys=True), "utf-8")
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except OSError:
            pass
    except OSError as e:
        warn(f"Could not save config: {e}")


def resolve_key(cfg: dict) -> tuple:
    for env in ("PROCODE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(env):
            return os.environ[env], f"env:{env}"
    if cfg.get("api_key"):
        return cfg["api_key"], "config"
    return "procode-anonymous", "zero-auth default"


def mask(s: str) -> str:
    return "(none)" if not s else (s[:4] + "…" + s[-3:] if len(s) > 10 else "****")


SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{20,}"),
    re.compile(r"(?i)((?:api[_-]?key|secret|token|passwd|password)\s*[=:]\s*['\"]?)[^\s'\"]{8,}"),
]


def sanitize(text: str) -> tuple:
    n = 0
    for pat in SECRET_PATTERNS:
        def rep(m, _pat=pat):
            nonlocal n
            n += 1
            return (m.group(1) if m.lastindex else "") + "[REDACTED]"
        text = pat.sub(rep, text)
    return text, n


def log(msg: str) -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 1_000_000:
            LOG_FILE.replace(LOG_FILE.with_suffix(".log.1"))
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {sanitize(msg)[0]}\n")
    except OSError:
        pass


def ask_yes(q: str, default: bool = False, strict: bool = False) -> bool:
    if FLAGS["yes"] and not strict:
        return True
    if not sys.stdin.isatty():
        return default
    try:
        a = input(c(f"{q} [{'Y/n' if default else 'y/N'}] ", "warn")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return default if not a else a[0] == "y"


def ask_choice(q: str, choices: str, default: str = "n") -> str:
    if not sys.stdin.isatty():
        return default
    try:
        a = input(c(q, "warn")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"
    return a[0] if a and a[0] in choices else default


def split_args(a: str) -> list:
    try:
        return shlex.split(a)
    except ValueError as e:
        raise UsageError(f"Bad quoting: {e}")


def parse_bool(a: str, current: bool) -> bool:
    a = a.strip().lower()
    if a in ("on", "true", "1", "yes", "y"):
        return True
    if a in ("off", "false", "0", "no", "n"):
        return False
    return not current


class UsageError(Exception):
    pass


def clip_copy(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"],
                ["clip.exe"], ["clip"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), check=True, timeout=5)
                return True
            except (OSError, subprocess.SubprocessError):
                continue
    return False


def clip_paste() -> Optional[str]:
    for cmd in (["pbpaste"], ["wl-paste", "-n"], ["xclip", "-selection", "clipboard", "-o"],
                ["xsel", "--clipboard", "--output"], ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"]):
        if shutil.which(cmd[0]):
            try:
                return subprocess.run(cmd, capture_output=True, timeout=5, check=True).stdout.decode("utf-8", "replace")
            except (OSError, subprocess.SubprocessError):
                continue
    return None


def notify(title: str, msg: str) -> None:
    try:
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", title, msg], timeout=5)
        elif shutil.which("osascript"):
            subprocess.run(["osascript", "-e", f'display notification {json.dumps(msg)} with title {json.dumps(title)}'],
                           timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def edit_text(initial: str = "") -> str:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor and sys.stdin.isatty():
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(initial)
            path = f.name
        try:
            subprocess.call(shlex.split(editor) + [path])
            return Path(path).read_text("utf-8").strip()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    note("Multi-line editor: type your prompt; finish with a line containing only '.' (or Ctrl-D).")
    lines = initial.splitlines()
    try:
        while True:
            ln = input(c("… ", "muted"))
            if ln.strip() == ".":
                break
            lines.append(ln)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def safe_path(rel: str) -> Optional[Path]:
    root = Path.cwd().resolve()
    p = (root / rel).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return None
    return p


def read_text_file(path: str, limit: int = 200_000) -> str:
    p = Path(path).expanduser()
    if not p.is_file():
        raise UsageError(f"Not a file: {path}")
    data = p.read_bytes()
    if b"\0" in data[:4096]:
        raise UsageError(f"Binary file skipped: {path}")
    txt = data[:limit].decode("utf-8", "replace")
    if len(data) > limit:
        txt += f"\n… [truncated {len(data) - limit} bytes]"
    return txt


LANG_BY_EXT = {".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx", ".go": "go",
               ".rs": "rust", ".java": "java", ".c": "c", ".h": "c", ".cpp": "cpp", ".cs": "csharp", ".rb": "ruby",
               ".php": "php", ".sh": "bash", ".md": "markdown", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
               ".html": "html", ".css": "css", ".sql": "sql", ".kt": "kotlin", ".swift": "swift", ".toml": "toml"}
TEXT_EXT = set(LANG_BY_EXT) | {".txt", ".cfg", ".ini", ".xml", ".gradle", ".lock", ".env.example", ".vue", ".scss"}
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".mypy_cache",
               ".pytest_cache", "target", ".next", ".gradle", ".tox", "egg-info"}


def fenced(path: str, content: str) -> str:
    return f"\n\n--- {path} ---\n```{LANG_BY_EXT.get(Path(path).suffix, '')}\n{content}\n```"


# --------------------------------------------------------------------------- #
# Local workspace index (hashed bag-of-words embedding + cosine retrieval)
# --------------------------------------------------------------------------- #
def tokenize(text: str) -> list:
    out_ = []
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text):
        out_.append(w.lower())
        out_.extend(p.lower() for p in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", w) if len(p) > 2)
    return out_


def scan_workspace(root: Path, max_files: int = 500, max_bytes: int = 120_000) -> list:
    found = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in IGNORE_DIRS and not d.endswith(".egg-info")]
        for fn in fns:
            p = Path(dp) / fn
            if p.suffix.lower() in TEXT_EXT or fn in ("Makefile", "Dockerfile", "README"):
                try:
                    if p.stat().st_size <= max_bytes:
                        found.append(p)
                except OSError:
                    pass
            if len(found) >= max_files:
                return found
    return found


class WorkspaceIndex:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.docs: dict = {}
        self.idf: dict = {}
        self.build()

    def build(self) -> None:
        df: Counter = Counter()
        for p in scan_workspace(self.root):
            try:
                text = p.read_text("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            tf = Counter(tokenize(text + " " + p.name * 2))
            if tf:
                self.docs[p] = (tf, text)
                df.update(tf.keys())
        n = max(1, len(self.docs))
        self.idf = {t: math.log(1 + n / d) for t, d in df.items()}
        self.vecs = {}
        for p, (tf, _) in self.docs.items():
            v = {t: (1 + math.log(f)) * self.idf[t] for t, f in tf.items()}
            self.vecs[p] = (v, math.sqrt(sum(x * x for x in v.values())) or 1.0)

    def query(self, text: str, k: int = 4) -> list:
        qtf = Counter(t for t in tokenize(text) if t in self.idf)
        qv = {t: (1 + math.log(f)) * self.idf[t] for t, f in qtf.items()}
        qn = math.sqrt(sum(x * x for x in qv.values())) or 1.0
        scored = []
        for p, (v, n) in self.vecs.items():
            dot = sum(w * v.get(t, 0.0) for t, w in qv.items())
            if dot > 0:
                scored.append((dot / (qn * n), p))
        return sorted(scored, reverse=True)[:k]

    def context(self, query: str, budget: int = 12000) -> str:
        rels = sorted(str(p.relative_to(self.root)) for p in self.docs)
        tree = "\n".join(rels[:80]) + (f"\n… (+{len(rels) - 80} more)" if len(rels) > 80 else "")
        parts = [f"Workspace root: {self.root}\nFiles:\n{tree}"]
        used = len(parts[0])
        for score, p in self.query(query):
            body = self.docs[p][1]
            take = min(len(body), max(0, budget - used), 4000)
            if take < 200:
                break
            parts.append(f"\n--- {p.relative_to(self.root)} (relevance {score:.2f}) ---\n{body[:take]}")
            used += take
        return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Code block extraction
# --------------------------------------------------------------------------- #
FENCE_RE = re.compile(r"^```([^\n`]*)\n(.*?)^```[ \t]*$", re.S | re.M)
FILE_COMMENT_RE = re.compile(r"^\s*(?:#|//|--|/\*|<!--|;)\s*(?:file(?:name)?|path)\s*[:=]\s*([^\s*>]+)", re.I)


def extract_blocks(text: str) -> list:
    blocks = []
    for m in FENCE_RE.finditer(text):
        info, code = m.group(1).strip(), m.group(2)
        lang = info.split()[0].split(":")[0] if info else ""
        path = None
        for tok in re.split(r"[\s,]+", info):
            tok = tok.split("=", 1)[-1].split(":", 1)[-1]
            if tok and ("." in tok or "/" in tok) and not tok.startswith("."):
                path = tok
                break
        first = code.split("\n", 1)[0]
        fm = FILE_COMMENT_RE.match(first)
        if fm:
            path = fm.group(1)
        if not path:
            before = [ln for ln in text[: m.start()].splitlines() if ln.strip()][-1:]
            if before:
                pm = re.search(r"`([\w./\\-]+\.\w+)`", before[0])
                if pm:
                    path = pm.group(1)
        blocks.append({"lang": lang, "path": path, "code": code})
    return blocks


# --------------------------------------------------------------------------- #
# API client (OpenAI-compatible, SSE streaming, stdlib only)
# --------------------------------------------------------------------------- #
class APIError(Exception):
    def __init__(self, msg: str, status: Optional[int] = None, retry: bool = False, wait: float = 0.0, partial: str = ""):
        super().__init__(msg)
        self.status, self.retry, self.wait, self.partial = status, retry, wait, partial


THINK_LEVELS = {"off": None, "low": "low", "medium": "medium", "high": "high", "max": "high"}


class Client:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.unsupported: set = set()

    def opener(self):
        handlers = []
        if self.cfg.get("proxy"):
            handlers.append(urllib.request.ProxyHandler({"http": self.cfg["proxy"], "https": self.cfg["proxy"]}))
        return urllib.request.build_opener(*handlers)

    def headers(self, stream: bool) -> dict:
        key, _ = resolve_key(self.cfg)
        h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
             "User-Agent": f"pro-code-cli/{__version__}"}
        if stream:
            h["Accept"] = "text/event-stream"
        return h

    def url(self, path: str) -> str:
        return self.cfg["base_url"].rstrip("/") + "/" + path.lstrip("/")

    def _http_error(self, e: urllib.error.HTTPError) -> APIError:
        try:
            raw = e.read().decode("utf-8", "replace")
        except Exception:
            raw = ""
        detail = raw[:300]
        try:
            j = json.loads(raw)
            j = j[0] if isinstance(j, list) and j else j
            detail = (j.get("error", {}) or {}).get("message", detail) if isinstance(j, dict) else detail
        except (ValueError, AttributeError):
            pass
        s = e.code
        try:
            wait = float(e.headers.get("Retry-After", 0))
        except (TypeError, ValueError):
            wait = 0.0
        _, src = resolve_key(self.cfg)
        if s == 429:
            return APIError("Rate limit reached (429). Slow down or check your quota/billing.", s, True, wait)
        if s in (500, 502, 503, 504):
            names = {500: "server error", 502: "bad gateway", 503: "service unavailable", 504: "gateway timeout"}
            return APIError(f"Upstream {names[s]} ({s}); the API is having trouble. Retrying may help.", s, True, wait)
        if s in (401, 403):
            hint = " Set GEMINI_API_KEY or run /login." if src == "zero-auth default" else " Check your key with /auth."
            return APIError(f"Authentication failed ({s}).{hint} {trunc(detail, 120)}", s)
        if s == 404:
            return APIError(f"Model or endpoint not found (404). Check /config (model={self.cfg['model']}). "
                            f"{trunc(detail, 120)}", s)
        return APIError(f"Request rejected ({s}): {trunc(detail, 240)}", s)

    def _net_error(self, e: Exception) -> APIError:
        if isinstance(e, urllib.error.URLError):
            r = e.reason
            if isinstance(r, (socket.timeout, TimeoutError)):
                return APIError("Network timeout: the API did not respond in time (see /timeout).", None, True)
            if isinstance(r, socket.gaierror):
                return APIError("DNS lookup failed. Check your connection or proxy settings.", None, True)
            return APIError(f"Could not reach the API: {r}", None, True)
        if isinstance(e, (socket.timeout, TimeoutError)):
            return APIError("Network timeout: the API did not respond in time (see /timeout).", None, True)
        return APIError(f"Network error: {e}", None, True)

    def get(self, path: str, timeout: float = 15):
        req = urllib.request.Request(self.url(path), headers=self.headers(False))
        try:
            with self.opener().open(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise self._http_error(e)
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            raise self._net_error(e)

    def chat(self, messages: list, *, stream: bool = True, on_text: Optional[Callable] = None,
             on_thought: Optional[Callable] = None, thinking: Optional[str] = None,
             max_tokens: Optional[int] = None, temperature: Optional[float] = None,
             model: Optional[str] = None) -> dict:
        cfg = self.cfg
        level = thinking or cfg.get("thinking", "medium")
        body: dict = {"model": model or cfg["model"], "messages": messages, "stream": stream,
                      "temperature": cfg["temperature"] if temperature is None else temperature}
        mt = max_tokens if max_tokens is not None else cfg.get("max_tokens", 0)
        if mt:
            body["max_tokens"] = int(mt)
        if stream:
            body["stream_options"] = {"include_usage": True}
        if THINK_LEVELS.get(level):
            body["reasoning_effort"] = THINK_LEVELS[level]
        body["extra_body"] = {"google": {"thinking_config": {"include_thoughts": True}}}
        for k in self.unsupported:
            body.pop(k, None)
        attempts = 0
        while True:
            try:
                return self._once(body, stream, on_text, on_thought)
            except APIError as e:
                if e.status == 400:
                    for key in ("extra_body", "reasoning_effort", "stream_options"):
                        if key in body:
                            body.pop(key)
                            self.unsupported.add(key)
                            log(f"400 from API; dropping unsupported field {key}")
                            break
                    else:
                        raise
                    continue
                if e.retry and attempts < int(cfg.get("retries", 3)) and not e.partial:
                    attempts += 1
                    delay = e.wait or min(2 ** attempts, 20)
                    note(f"{e}  (retry {attempts}/{cfg.get('retries', 3)} in {delay:.0f}s)", "warn")
                    time.sleep(delay)
                    continue
                raise

    def _once(self, body: dict, stream: bool, on_text, on_thought) -> dict:
        if self.cfg.get("debug"):
            print(c("DEBUG request: " + sanitize(json.dumps({k: v for k, v in body.items() if k != "messages"}))[0],
                    "muted"), file=sys.stderr)
        req = urllib.request.Request(self.url("chat/completions"), data=json.dumps(body).encode("utf-8"),
                                     headers=self.headers(stream), method="POST")
        t0 = time.time()
        try:
            resp = self.opener().open(req, timeout=float(self.cfg.get("timeout", 120)))
        except urllib.error.HTTPError as e:
            raise self._http_error(e)
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            raise self._net_error(e)
        split = ThoughtSplitter()
        text_parts: list = []
        thought_parts: list = []
        usage: dict = {}
        ttft: Optional[float] = None

        def emit(items: list) -> None:
            nonlocal ttft
            for kind, s in items:
                if not s:
                    continue
                if ttft is None:
                    ttft = time.time() - t0
                if kind == "thought":
                    thought_parts.append(s)
                    if on_thought:
                        on_thought(s)
                else:
                    text_parts.append(s)
                    if on_text:
                        on_text(s)

        try:
            with resp:
                if not stream:
                    data = json.loads(resp.read().decode("utf-8", "replace"))
                    msg = (data.get("choices") or [{}])[0].get("message", {})
                    if msg.get("reasoning_content"):
                        emit([("thought", msg["reasoning_content"])])
                    emit(split.feed(msg.get("content") or "") + split.flush())
                    usage = data.get("usage") or {}
                else:
                    for raw in resp:
                        line = raw.decode("utf-8", "replace").strip()
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            j = json.loads(payload)
                        except ValueError:
                            continue
                        if isinstance(j, list):
                            j = j[0] if j else {}
                        if j.get("error"):
                            raise APIError(f"API error mid-stream: {trunc(str(j['error']), 200)}", partial="".join(text_parts))
                        if j.get("usage"):
                            usage = j["usage"]
                        ch = (j.get("choices") or [])
                        if not ch:
                            continue
                        delta = ch[0].get("delta") or {}
                        if delta.get("reasoning_content"):
                            emit([("thought", delta["reasoning_content"])])
                        if delta.get("content"):
                            emit(split.feed(delta["content"]))
                    emit(split.flush())
        except (socket.timeout, TimeoutError, ConnectionError, http.client.HTTPException, OSError) as e:
            raise APIError(f"Stream interrupted: {e}", partial="".join(text_parts) or "(partial)")
        total = time.time() - t0
        text, thought = "".join(text_parts), "".join(thought_parts)
        return {"text": text, "thought": thought, "usage": usage, "ttft": ttft if ttft is not None else total,
                "total": total, "model": body["model"]}


# --------------------------------------------------------------------------- #
# Prompts: roles, templates
# --------------------------------------------------------------------------- #
ROLES = {
    "ui-researcher": "You are a senior UI/UX researcher. Evaluate the task for usability, accessibility, layout and "
                     "interaction design. Give concrete, prioritized recommendations.",
    "security-analyst": "You are an application security analyst. Find vulnerabilities, insecure defaults, secrets "
                        "exposure and injection risks. Rank by severity and give fixes.",
    "code-reviewer": "You are a meticulous code reviewer. Find bugs, edge cases, readability and maintainability "
                     "problems. Be specific and show corrected code where useful.",
    "architect": "You are a principal software architect. Assess structure, boundaries, scalability and tradeoffs, "
                 "and propose a clean design.",
    "test-engineer": "You are a test engineer. Design thorough test strategies and write runnable tests covering edge "
                     "cases and failure modes.",
    "docs-writer": "You are a technical writer. Produce clear, accurate documentation with examples.",
    "performance-engineer": "You are a performance engineer. Identify hot spots, algorithmic issues and resource "
                            "waste; propose measurable optimizations.",
    "refactorer": "You are a refactoring specialist. Simplify and restructure code without changing behavior.",
}
ROLE_ALIASES = {"ui": "ui-researcher", "security": "security-analyst", "sec": "security-analyst",
                "review": "code-reviewer", "reviewer": "code-reviewer", "arch": "architect", "tests": "test-engineer",
                "test": "test-engineer", "docs": "docs-writer", "perf": "performance-engineer",
                "refactor": "refactorer"}

BUILTIN_TEMPLATES = {
    "review": "Perform a rigorous code review of the following. List bugs, security issues, performance concerns and "
              "style problems ordered by severity, with concrete fixes.\n\n{{input}}\n\n{{extra}}",
    "explain": "Explain the following clearly for an experienced developer: purpose, control flow, and any "
               "non-obvious details.\n\n{{input}}\n\n{{extra}}",
    "refactor": "Refactor the following for clarity and maintainability without changing behavior. Return the full "
                "result and a short summary of changes.\n\n{{input}}\n\n{{extra}}",
    "tests": "Write a comprehensive unit test suite for the code below. Cover normal paths, edge cases and failure "
             "modes. {{extra}}\n\n{{input}}",
    "docs": "Write documentation (docstrings and a usage overview) for the following code.\n\n{{input}}\n\n{{extra}}",
    "bugfix": "Find and fix the bug(s) in the following. Explain the root cause and show the corrected code.\n\n"
              "{{input}}\n\n{{extra}}",
    "optimize": "Optimize the following for performance. Explain each change and its expected impact.\n\n"
                "{{input}}\n\n{{extra}}",
    "security-audit": "Audit the following for security vulnerabilities (OWASP-style). Provide severity, exploit "
                      "scenario and remediation for each finding.\n\n{{input}}\n\n{{extra}}",
}


def render_template(tpl: str, input_text: str = "", extra: str = "") -> str:
    def file_sub(m):
        try:
            return read_text_file(m.group(1))
        except UsageError as e:
            return f"[{e}]"
    tpl = re.sub(r"\{\{file:([^}]+)\}\}", file_sub, tpl)
    tpl = tpl.replace("{{input}}", input_text).replace("{{extra}}", extra)
    tpl = tpl.replace("{{date}}", datetime.now().strftime("%Y-%m-%d")).replace("{{cwd}}", str(Path.cwd()))
    if "{{clip}}" in tpl:
        tpl = tpl.replace("{{clip}}", clip_paste() or "")
    return tpl.strip()


def load_template(name: str) -> Optional[str]:
    p = TEMPLATES_DIR / f"{re.sub(r'[^A-Za-z0-9_.-]', '', name)}.txt"
    if p.exists():
        return p.read_text("utf-8")
    return BUILTIN_TEMPLATES.get(name)


def to_yaml(obj, ind: int = 0) -> str:
    pad = "  " * ind
    if isinstance(obj, dict):
        if not obj:
            return pad + "{}"
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{k}:\n{to_yaml(v, ind + 1)}")
            else:
                lines.append(f"{pad}{k}: {to_yaml_scalar(v, ind + 1)}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return pad + "[]"
        lines = []
        for v in obj:
            if isinstance(v, (dict, list)) and v:
                sub = to_yaml(v, ind + 1).split("\n")
                lines.append(f"{pad}- {sub[0].lstrip()}")
                lines.extend(sub[1:])
            else:
                lines.append(f"{pad}- {to_yaml_scalar(v, ind + 1)}")
        return "\n".join(lines)
    return pad + to_yaml_scalar(obj, ind)


def to_yaml_scalar(v, ind: int) -> str:
    if isinstance(v, str):
        if "\n" in v:
            pad = "  " * ind
            return "|-\n" + "\n".join(pad + ln for ln in v.split("\n"))
        return json.dumps(v, ensure_ascii=False)
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return str(v)


# --------------------------------------------------------------------------- #
# Session / App
# --------------------------------------------------------------------------- #
def new_name() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


@dataclass
class Session:
    name: str = field(default_factory=new_name)
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    messages: list = field(default_factory=list)
    system: str = ""
    stats: list = field(default_factory=list)
    totals: dict = field(default_factory=lambda: {"requests": 0, "prompt": 0, "completion": 0, "cost": 0.0, "time": 0.0})

    def to_dict(self, model: str) -> dict:
        return {"version": __version__, "name": self.name, "created": self.created, "model": model,
                "system": self.system, "messages": self.messages, "totals": self.totals, "stats": self.stats[-200:]}


@dataclass
class Agent:
    id: int
    role: str
    task: str
    status: str = "queued"
    started: float = 0.0
    ended: float = 0.0
    text: str = ""
    tokens: int = 0


class Send:
    def __init__(self, text: str, **kw) -> None:
        self.text, self.kw = text, kw


def prune_messages(messages: list, limit_tokens: int) -> list:
    """Drop oldest turns to fit the budget and leave a compact digest of what was removed."""
    def total(ms):
        return sum(est_tokens(m["content"]) for m in ms)
    if total(messages) <= limit_tokens:
        return messages
    system = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]
    dropped: list = []
    while len(rest) > 2 and total(system + rest) > limit_tokens:
        dropped.append(rest.pop(0))
    if dropped:
        digest = "; ".join(trunc(m["content"], 100) for m in dropped if m["role"] == "user")[:900]
        system = system + [{"role": "system", "content": f"[Earlier conversation condensed. User topics: {digest}]"}]
    return system + rest


class App:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.client = Client(cfg)
        self.session = Session(system=cfg.get("system_prompt", ""))
        self.pending: list = []
        self.agents: list = []
        self.index: Optional[WorkspaceIndex] = None
        self.index_on = bool(cfg.get("index_workspace"))
        self.extract_mode = bool(cfg.get("auto_write"))
        self.think = cfg.get("thinking", "medium")
        self.last_text = ""
        self.last_thought = ""
        self.last_blocks: list = []
        self.lock = threading.Lock()

    # ----- accounting
    def account(self, r: dict, messages: Optional[list] = None) -> dict:
        u = r.get("usage") or {}
        pt = u.get("prompt_tokens") or (est_tokens(json.dumps(messages)) if messages else 0)
        ct = u.get("completion_tokens") or est_tokens(r.get("text", "") + r.get("thought", ""))
        det = u.get("completion_tokens_details") or {}
        rt = det.get("reasoning_tokens") or est_tokens(r.get("thought", ""))
        cost = (pt * self.cfg["price_in_per_mtok"] + ct * self.cfg["price_out_per_mtok"]) / 1e6
        with self.lock:
            t = self.session.totals
            t["requests"] += 1
            t["prompt"] += pt
            t["completion"] += ct
            t["cost"] += cost
            t["time"] += r.get("total", 0)
            self.session.stats.append({"t": datetime.now().isoformat(timespec="seconds"), "model": r.get("model"),
                                       "prompt": pt, "completion": ct, "reasoning": rt,
                                       "ttft": round(r.get("ttft", 0), 3), "total": round(r.get("total", 0), 3)})
        return {"pt": pt, "ct": ct, "rt": rt, "cost": cost}

    def clean(self, text: str) -> str:
        if self.cfg.get("sanitize"):
            text, n = sanitize(text)
            if n:
                warn(f"Redacted {n} potential secret(s) before sending.")
        return text

    def check_budget(self) -> None:
        b = float(self.cfg.get("budget_usd") or 0)
        if b > 0 and self.session.totals["cost"] >= b:
            raise UsageError(f"Budget of ${b:.2f} reached (spent ${self.session.totals['cost']:.4f}). Raise it with /budget.")

    def run_hook(self, event: str, text: str = "") -> None:
        cmd = (self.cfg.get("hooks") or {}).get(event)
        if not cmd:
            return
        env = dict(os.environ, PROCODE_EVENT=event, PROCODE_MODEL=self.cfg["model"], PROCODE_SESSION=self.session.name)
        try:
            r = subprocess.run(cmd, shell=True, input=text.encode("utf-8"), capture_output=True, timeout=30, env=env)
            if self.cfg.get("verbose") and r.stdout:
                note(f"[hook:{event}] " + r.stdout.decode("utf-8", "replace").strip())
            if r.returncode:
                warn(f"hook '{event}' exited {r.returncode}")
        except (OSError, subprocess.SubprocessError) as e:
            warn(f"hook '{event}' failed: {e}")

    # ----- context assembly
    def system_messages(self, extra: Optional[str] = None) -> list:
        sysmsg = self.session.system or SYSTEM_DEFAULT
        if self.extract_mode:
            sysmsg += "\n" + EXTRACT_HINT
        if extra:
            sysmsg += "\n" + extra
        return [{"role": "system", "content": sysmsg}]

    def build_messages(self, text: str, extra: Optional[str] = None) -> list:
        msgs = self.system_messages(extra)
        if self.index_on:
            if self.index is None:
                with Spinner("indexing workspace"):
                    self.index = WorkspaceIndex(Path.cwd())
            msgs.append({"role": "system", "content": "Local workspace context (auto-retrieved):\n"
                         + self.index.context(text)})
        msgs += self.session.messages
        msgs = prune_messages(msgs, int(self.cfg["max_context_tokens"]))
        return msgs + [{"role": "user", "content": text}]

    def take_attachments(self, text: str) -> str:
        names = [m for m in re.findall(r"(?<!\S)@([\w./\\~-]+)", text) if Path(m).expanduser().is_file()]
        for n in names:
            try:
                self.pending.append((n, read_text_file(n, 60_000)))
            except UsageError as e:
                warn(str(e))
        if self.pending:
            for name, content in self.pending:
                text += fenced(name, content)
            tool_line(f"attached {len(self.pending)} file(s): " + ", ".join(n for n, _ in self.pending))
            self.pending = []
        return text

    # ----- core send (streaming)
    def send(self, text: str, *, thinking: Optional[str] = None, system_extra: Optional[str] = None,
             record: bool = True) -> Optional[str]:
        cfg = self.cfg
        self.check_budget()
        text = self.clean(self.take_attachments(text))
        self.run_hook("pre_send", text)
        msgs = self.build_messages(text, system_extra)
        if cfg.get("verbose"):
            note(f"→ {cfg['model']} · {len(msgs)} msgs · ~{human(sum(est_tokens(m['content']) for m in msgs))} tok · "
                 f"think={thinking or self.think} · stream={cfg['stream']}")
        renderer = StreamRenderer()
        spin = Spinner("thinking").start()
        st = {"first": False, "thought": 0}
        t0 = time.time()

        def thought_line() -> None:
            if st["thought"] and not (UI.quiet or UI.silent):
                out(c(f"> Thought for {time.time() - t0:.1f}s, ~{human(st['thought'])} tokens", "muted", dim=True)
                    + c("  (/thoughts to expand)", "muted", dim=True))

        def on_thought(s: str) -> None:
            st["thought"] += est_tokens(s) or 1
            spin.label = f"thinking · ~{human(st['thought'])} tok"

        def on_text(s: str) -> None:
            if not st["first"]:
                st["first"] = True
                spin.stop()
                thought_line()
            renderer.feed(s)

        try:
            r = self.client.chat(msgs, stream=bool(cfg["stream"]), on_text=on_text, on_thought=on_thought,
                                 thinking=thinking or self.think)
        except KeyboardInterrupt:
            spin.stop()
            renderer.finish()
            warn("Interrupted.")
            return None
        except APIError as e:
            spin.stop()
            renderer.finish()
            if e.partial and e.partial != "(partial)":
                warn("Partial response above was cut off.")
            bad(str(e))
            log(f"APIError status={e.status}: {e}")
            self.run_hook("on_error", str(e))
            return None
        finally:
            spin.stop()
        if not st["first"]:
            thought_line()
        renderer.finish()
        spin.stop()
        text_out = r["text"]
        if not text_out.strip():
            warn("The model returned an empty response.")
        acc = self.account(r, msgs)
        self.last_text, self.last_thought = text_out, r["thought"]
        if record:
            self.session.messages += [{"role": "user", "content": text}, {"role": "assistant", "content": text_out}]
        if not (UI.quiet or UI.silent):
            tps = acc["ct"] / r["total"] if r["total"] > 0 else 0
            cost = f" · ${acc['cost']:.4f}" if acc["cost"] else ""
            out(c(f"{g('ok')} {human(acc['ct'])} tokens · {r['total']:.1f}s · {tps:.0f} tok/s · "
                  f"ttft {r['ttft']:.2f}s{cost}", "muted", dim=True))
        if cfg.get("show_thoughts") and r["thought"]:
            self.show_thought()
        self.run_hook("post_response", text_out)
        if self.extract_mode:
            self.offer_write(text_out)
        else:
            self.last_blocks = extract_blocks(text_out)
        if cfg.get("sound"):
            sys.stdout.write("\a")
            sys.stdout.flush()
        if cfg.get("notify"):
            notify(APP_NAME, "Response complete")
        return text_out

    def show_thought(self) -> None:
        if not self.last_thought:
            note("No reasoning captured for the last response.")
            return
        out(c(g("top") + g("h") + " reasoning", "muted"))
        for ln in self.last_thought.strip().splitlines():
            out(c(g("bar") + " " + ln, "muted", dim=True))
        out(c(g("bot") + g("h"), "muted"))

    # ----- one-shot (non-streaming, not recorded)
    def ask(self, prompt: str, system: Optional[str] = None, thinking: Optional[str] = None,
            label: str = "working", spinner: bool = True) -> str:
        self.check_budget()
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": self.clean(prompt)}]
        key = None
        if self.cfg.get("cache"):
            key = hashlib.sha256(json.dumps([self.cfg["model"], msgs, self.cfg["temperature"]]).encode()).hexdigest()
            f = CACHE_DIR / f"{key}.json"
            if f.exists() and time.time() - f.stat().st_mtime < 86400:
                note("(cache hit)")
                return json.loads(f.read_text("utf-8"))["text"]
        sp = Spinner(label)
        if spinner:
            sp.start()
        try:
            r = self.client.chat(msgs, stream=False, thinking=thinking or self.think)
        finally:
            sp.stop()
        self.account(r, msgs)
        if key:
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                (CACHE_DIR / f"{key}.json").write_text(json.dumps({"text": r["text"]}), "utf-8")
            except OSError:
                pass
        return r["text"]

    # ----- code extraction / writing
    def offer_write(self, text: str, blocks: Optional[list] = None) -> None:
        blocks = blocks if blocks is not None else extract_blocks(text)
        self.last_blocks = blocks
        cands = [b for b in blocks if b["path"]]
        if not cands:
            return
        note(f"Detected {len(cands)} file(s) in the response.")
        auto = False
        for b in cands:
            target = safe_path(b["path"])
            if target is None:
                warn(f"Skipping path outside the working directory: {b['path']}")
                continue
            rel = target.relative_to(Path.cwd().resolve())
            exists = target.exists()
            if not auto:
                while True:
                    ans = ask_choice(f"Write {rel} ({len(b['code'].splitlines())} lines){' [exists]' if exists else ''}? "
                                     "[y]es/[n]o/[a]ll/[d]iff/[q]uit ", "ynadq")
                    if ans == "d" and exists:
                        old = target.read_text("utf-8", "replace").splitlines()
                        out("\n".join(difflib.unified_diff(old, b["code"].splitlines(), "current", "proposed", lineterm="")))
                        continue
                    break
                if ans == "q":
                    return
                if ans == "a":
                    auto = True
                elif ans != "y":
                    continue
            if exists and not (auto or FLAGS["yes"]) and not ask_yes(f"{rel} exists. Overwrite?", strict=False):
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(b["code"], "utf-8")
                good(f"wrote {rel}")
                self.run_hook("post_write", str(rel))
            except OSError as e:
                bad(f"Could not write {rel}: {e}")

    # ----- subagents
    def run_agents(self, roles: list, task: str, context: str = "") -> list:
        agents = [Agent(len(self.agents) + i + 1, r, task) for i, r in enumerate(roles)]
        self.agents.extend(agents)

        def work(a: Agent) -> None:
            a.status, a.started = "running", time.time()
            try:
                msgs = [{"role": "system", "content": ROLES[a.role]}, {"role": "user", "content": task + context}]
                r = self.client.chat(msgs, stream=False, thinking=self.think)
                a.text, a.status = r["text"], "done"
                a.tokens = self.account(r, msgs)["ct"]
            except (APIError, Exception) as e:  # noqa: BLE001
                a.text, a.status = str(e), "failed"
            a.ended = time.time()

        sp = Spinner("agents").start()
        with cf.ThreadPoolExecutor(max_workers=max(1, min(len(agents), int(self.cfg["max_parallel"])))) as ex:
            futs = [ex.submit(work, a) for a in agents]
            try:
                while not all(f.done() for f in futs):
                    done = sum(a.status in ("done", "failed") for a in agents)
                    sp.label = f"agents {done}/{len(agents)} · " + " ".join(
                        f"{a.role}{g('ok') if a.status == 'done' else ('…' if a.status == 'running' else '')}" for a in agents)
                    time.sleep(0.1)
            except KeyboardInterrupt:
                for f in futs:
                    f.cancel()
                sp.stop()
                warn("Interrupted; waiting for in-flight calls to finish.")
        sp.stop()
        return agents

    def decompose(self, goal: str) -> list:
        sysmsg = ("You are a task-decomposition engine. Return ONLY JSON: "
                  '{"tasks":[{"id":"t1","title":"short title","prompt":"self-contained instruction","deps":[]}]}. '
                  "Use 3-8 tasks, deps reference earlier ids, maximize parallelism.")
        raw = self.ask(goal, system=sysmsg, label="decomposing task")
        blob = raw[raw.find("{"): raw.rfind("}") + 1]
        try:
            tasks = json.loads(blob)["tasks"]
        except (ValueError, KeyError, TypeError):
            raise UsageError("Planner did not return valid JSON; try rephrasing the goal.")
        ids = {str(t.get("id")) for t in tasks}
        for t in tasks:
            t["id"] = str(t["id"])
            t["deps"] = [str(d) for d in t.get("deps", []) if str(d) in ids and str(d) != t["id"]]
        return tasks


def task_waves(tasks: list) -> list:
    done: set = set()
    waves = []
    remaining = list(tasks)
    while remaining:
        ready = [t for t in remaining if all(d in done for d in t["deps"])]
        if not ready:
            raise UsageError("Task graph contains a dependency cycle.")
        waves.append(ready)
        done |= {t["id"] for t in ready}
        remaining = [t for t in remaining if t not in ready]
    return waves


# --------------------------------------------------------------------------- #
# Command registry
# --------------------------------------------------------------------------- #
@dataclass
class Command:
    name: str
    fn: Callable
    help: str
    group: str
    usage: str
    aliases: tuple


COMMANDS: dict = {}
CANON: list = []


def command(name: str, *aliases: str, group: str = "core", usage: str = ""):
    def deco(fn):
        cmd = Command(name, fn, ((fn.__doc__ or "").strip().split("\n")[0]), group, usage or f"/{name}", aliases)
        for n in (name,) + aliases:
            COMMANDS[n] = cmd
        CANON.append(cmd)
        return fn
    return deco


def run_proc(argv: list, capture: bool = False, cwd: Optional[str] = None, quiet_tool: bool = False) -> int:
    if not shutil.which(argv[0]):
        raise UsageError(f"'{argv[0]}' is not installed or not on PATH.")
    if not quiet_tool:
        tool_line(" ".join(shlex.quote(a) for a in argv))
    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=capture, text=capture)
    except KeyboardInterrupt:
        warn("Interrupted.")
        return 130
    if capture:
        if r.stdout:
            out(r.stdout.rstrip())
        if r.stderr:
            print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode


def git_out(*args: str) -> str:
    if not shutil.which("git"):
        raise UsageError("git is not installed.")
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode:
        raise UsageError(r.stderr.strip() or f"git {args[0]} failed")
    return r.stdout


def toggle_cfg(app: App, key: str, a: str, label: str) -> None:
    app.cfg[key] = parse_bool(a, bool(app.cfg.get(key)))
    save_config(app.cfg)
    good(f"{label}: {'on' if app.cfg[key] else 'off'}")


# ---- session & core control ------------------------------------------------
@command("session", group="session", usage="/session [new [name]|list|rename NAME]")
def h_session(app, a):
    """Show or manage the current session."""
    args = split_args(a)
    if args and args[0] == "new":
        app.session = Session(system=app.cfg.get("system_prompt", ""))
        if len(args) > 1:
            app.session.name = args[1]
        return good(f"new session {app.session.name}")
    if args and args[0] == "list":
        files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return out("\n".join(f"  {f.stem}" for f in files[:30]) or "(no saved sessions)")
    if args and args[0] == "rename" and len(args) > 1:
        app.session.name = re.sub(r"[^A-Za-z0-9_.-]", "-", args[1])
        return good(f"renamed to {app.session.name}")
    t = app.session.totals
    out(f"{c('session', 'accent', True)} {app.session.name}  created {app.session.created}\n"
        f"messages: {len(app.session.messages)}  requests: {t['requests']}  tokens in/out: {t['prompt']}/{t['completion']}")


@command("clear", group="session")
def h_clear(app, a):
    """Clear the terminal screen (conversation is kept; see /reset)."""
    out("\033[2J\033[H", end="")


@command("reset", group="session")
def h_reset(app, a):
    """Erase the conversation history and start fresh."""
    app.session.messages.clear()
    app.pending.clear()
    good("conversation reset")


@command("exit", "quit", "q", group="session")
def h_exit(app, a):
    """Leave Pro Code CLI."""
    return "exit"


@command("history", group="session", usage="/history [N|search TEXT]")
def h_history(app, a):
    """List messages, show one in full, or search them."""
    ms = app.session.messages
    if a.startswith("search "):
        q = a[7:].lower()
        for i, m in enumerate(ms):
            if q in m["content"].lower():
                out(f"{c(i, 'accent')} {m['role']:9} {trunc(m['content'], 90)}")
        return
    if a.strip().isdigit():
        i = int(a)
        if 0 <= i < len(ms):
            return out(f"{c(ms[i]['role'], 'accent', True)}\n{ms[i]['content']}")
        raise UsageError("No such message index.")
    for i, m in enumerate(ms):
        out(f"{c(i, 'accent')} {m['role']:9} {trunc(m['content'], 90)}")
    if not ms:
        out("(empty)")


@command("export", group="session", usage="/export [json|yaml|md] [path]")
def h_export(app, a):
    """Export the session to JSON, YAML or Markdown."""
    args = split_args(a)
    fmt = (args[0] if args else "md").lower()
    if fmt not in ("json", "yaml", "yml", "md", "markdown"):
        raise UsageError("Format must be json, yaml or md.")
    ext = {"yml": "yaml", "markdown": "md"}.get(fmt, fmt)
    path = Path(args[1]) if len(args) > 1 else Path(f"procode-{app.session.name}.{ext}")
    data = app.session.to_dict(app.cfg["model"])
    if ext == "json":
        body = json.dumps(data, indent=2, ensure_ascii=False)
    elif ext == "yaml":
        body = to_yaml(data)
    else:
        lines = [f"# Pro Code CLI session {app.session.name}", f"_model: {app.cfg['model']} · {app.session.created}_", ""]
        for m in app.session.messages:
            lines += [f"## {m['role'].capitalize()}", "", m["content"], ""]
        body = "\n".join(lines)
    if path.exists() and not ask_yes(f"{path} exists. Overwrite?"):
        return
    path.write_text(body, "utf-8")
    good(f"exported {len(app.session.messages)} messages to {path}")


@command("import", group="session", usage="/import FILE")
def h_import(app, a):
    """Import a JSON session export, or add any text file as context."""
    if not a:
        raise UsageError("Usage: /import FILE")
    p = Path(a.strip().strip("'\""))
    text = read_text_file(str(p), 2_000_000)
    try:
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("messages"), list):
            app.session.messages = [m for m in data["messages"] if m.get("role") in ("user", "assistant")]
            app.session.system = data.get("system", "")
            return good(f"imported {len(app.session.messages)} messages")
    except ValueError:
        pass
    app.pending.append((p.name, text[:60_000]))
    good(f"{p.name} queued as context for the next prompt")


@command("save", group="session", usage="/save [name]")
def h_save(app, a):
    """Save the session to disk."""
    name = re.sub(r"[^A-Za-z0-9_.-]", "-", a.strip()) or app.session.name
    app.session.name = name
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    (SESSIONS_DIR / f"{name}.json").write_text(json.dumps(app.session.to_dict(app.cfg["model"]), indent=2), "utf-8")
    good(f"saved session '{name}'")


@command("load", group="session", usage="/load [name]")
def h_load(app, a):
    """Load a saved session (lists sessions when no name is given)."""
    name = re.sub(r"[^A-Za-z0-9_.-]", "", a.strip())
    if not name:
        return h_session(app, "list")
    p = SESSIONS_DIR / f"{name}.json"
    if not p.exists():
        raise UsageError(f"No saved session '{name}'.")
    d = json.loads(p.read_text("utf-8"))
    app.session = Session(name=d.get("name", name), created=d.get("created", ""), messages=d.get("messages", []),
                          system=d.get("system", ""), stats=d.get("stats", []), totals=d.get("totals", Session().totals))
    good(f"loaded '{name}' ({len(app.session.messages)} messages)")


@command("config", group="session", usage="/config [path|edit|reset]")
def h_config(app, a):
    """Show the configuration, open it in your editor, or reset it."""
    if a == "path":
        return out(str(CONFIG_FILE))
    if a == "edit":
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
        subprocess.call(shlex.split(editor) + [str(CONFIG_FILE)])
        return h_reload(app, "")
    if a == "reset":
        if ask_yes("Reset all settings to defaults (API key is kept)?", strict=True):
            key = app.cfg.get("api_key", "")
            app.cfg.clear()
            app.cfg.update(json.loads(json.dumps(DEFAULTS)))
            app.cfg["api_key"] = key
            save_config(app.cfg)
            good("configuration reset")
        return
    shown = dict(app.cfg, api_key=mask(app.cfg.get("api_key", "")))
    out(json.dumps(shown, indent=2, sort_keys=True))


@command("status", group="session")
def h_status(app, a):
    """Show model, endpoint, auth source, session and flags."""
    _, src = resolve_key(app.cfg)
    t = app.session.totals
    out(f"{c('model', 'accent')}      {app.cfg['model']}\n{c('endpoint', 'accent')}   {app.cfg['base_url']}\n"
        f"{c('auth', 'accent')}       {src}\n{c('thinking', 'accent')}   {app.think}\n"
        f"{c('session', 'accent')}    {app.session.name} · {len(app.session.messages)} msgs · {t['requests']} requests\n"
        f"{c('flags', 'accent')}      stream={app.cfg['stream']} sanitize={app.cfg['sanitize']} index={app.index_on} "
        f"cache={app.cfg['cache']} write={app.extract_mode}")


@command("reload", group="session")
def h_reload(app, a):
    """Reload configuration from disk."""
    new = load_config()
    app.cfg.clear()
    app.cfg.update(new)
    app.client.unsupported.clear()
    apply_ui(app.cfg)
    app.think = app.cfg["thinking"]
    good("configuration reloaded")


def check_line(ok: Optional[bool], msg: str) -> None:
    mark = c(g("ok"), "ok", True) if ok else (c(g("warn"), "warn", True) if ok is None else c(g("x"), "err", True))
    out(f"  {mark} {msg}")


@command("doctor", group="session")
def h_doctor(app, a):
    """Run environment and connectivity diagnostics."""
    out(c("Pro Code CLI doctor", "accent", True))
    check_line(sys.version_info >= (3, 9), f"Python {platform.python_version()} ({platform.system()})")
    check_line(CONFIG_FILE.exists(), f"config file {CONFIG_FILE}")
    _, src = resolve_key(app.cfg)
    check_line(None if src == "zero-auth default" else True, f"auth source: {src}")
    host = re.sub(r"^https?://", "", app.cfg["base_url"]).split("/")[0]
    try:
        socket.create_connection((host.split(":")[0], int(host.split(":")[1]) if ":" in host else 443), 5).close()
        check_line(True, f"TCP reachable: {host}")
    except OSError as e:
        check_line(False, f"cannot reach {host}: {e}")
    try:
        models = app.client.get("models")
        names = [m.get("id", "") for m in models.get("data", [])]
        have = any(app.cfg["model"] in n for n in names)
        check_line(have or None, f"models endpoint OK ({len(names)} models); '{app.cfg['model']}' "
                   f"{'found' if have else 'not listed'}")
    except APIError as e:
        check_line(False, f"models endpoint: {e}")
    check_line(bool(shutil.which("git")), "git available")
    check_line(bool(shutil.which("curl")), "curl available (optional)")
    check_line(None if not (os.environ.get("VISUAL") or os.environ.get("EDITOR")) else True,
               f"editor: {os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'not set (built-in editor used)'}")
    try:
        import cryptography  # noqa: F401
        check_line(True, "cryptography installed (/encrypt, /decrypt)")
    except ImportError:
        check_line(None, "cryptography not installed (pip install pro-code-cli[crypto])")
    check_line(UI.color or None, f"colors {'on' if UI.color else 'off'} · TERM={os.environ.get('TERM', '?')}")


@command("debug", group="session")
def h_debug(app, a):
    """Toggle debug output (request metadata, tracebacks)."""
    toggle_cfg(app, "debug", a, "debug")


@command("logs", group="session", usage="/logs [N|clear|path]")
def h_logs(app, a):
    """Show the tail of the log file."""
    if a == "path":
        return out(str(LOG_FILE))
    if a == "clear":
        LOG_FILE.unlink(missing_ok=True)
        return good("log cleared")
    n = int(a) if a.strip().isdigit() else 25
    out("".join(LOG_FILE.read_text("utf-8", "replace").splitlines(True)[-n:]) if LOG_FILE.exists() else "(no logs)")


@command("version", group="session")
def h_version(app, a):
    """Show version information."""
    out(f"{APP_NAME} {__version__} · Python {platform.python_version()} · {platform.platform()}")


@command("update", "upgrade", group="session")
def h_update(app, a):
    """Upgrade pro-code-cli with pip."""
    if ask_yes("Run pip install --upgrade pro-code-cli?", strict=True):
        run_proc([sys.executable, "-m", "pip", "install", "--upgrade", "pro-code-cli"])


@command("rollback", group="session", usage="/rollback VERSION")
def h_rollback(app, a):
    """Install a specific earlier version with pip."""
    if not re.fullmatch(r"[0-9][0-9A-Za-z.\-+]*", a.strip()):
        raise UsageError("Usage: /rollback VERSION (e.g. /rollback 0.9.0)")
    if ask_yes(f"Install pro-code-cli=={a.strip()}?", strict=True):
        run_proc([sys.executable, "-m", "pip", "install", f"pro-code-cli=={a.strip()}"])


@command("backup", group="session")
def h_backup(app, a):
    """Back up config (without the API key), sessions and templates."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUPS_DIR / f"procode-backup-{new_name()}.tar.gz"
    with tempfile.TemporaryDirectory() as td:
        cfgcopy = Path(td) / "config.json"
        cfgcopy.write_text(json.dumps(dict(app.cfg, api_key=""), indent=2), "utf-8")
        with tarfile.open(dest, "w:gz") as tf:
            tf.add(cfgcopy, arcname="config/config.json")
            for sub in (SESSIONS_DIR, TEMPLATES_DIR):
                if sub.exists():
                    tf.add(sub, arcname=f"data/{sub.name}")
    good(f"backup written to {dest}")


@command("restore", group="session", usage="/restore [file]")
def h_restore(app, a):
    """Restore from a backup archive (lists backups when no file is given)."""
    files = sorted(BACKUPS_DIR.glob("*.tar.gz"))
    if not a:
        return out("\n".join(f"  {f}" for f in files) or "(no backups)")
    src = Path(a.strip().strip("'\""))
    if not src.exists():
        src = BACKUPS_DIR / src.name
    if not src.exists():
        raise UsageError("Backup not found.")
    if not ask_yes(f"Restore from {src.name}? Existing files may be overwritten.", strict=True):
        return
    bases = {"config": CONFIG_DIR, "data": DATA_DIR}
    count = 0
    with tarfile.open(src, "r:gz") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            top, _, rel = m.name.partition("/")
            if top not in bases:
                continue
            target = (bases[top] / rel).resolve()
            if bases[top].resolve() not in target.parents:
                warn(f"Skipped unsafe entry {m.name}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            fobj = tf.extractfile(m)
            if fobj:
                target.write_bytes(fobj.read())
                count += 1
    key = app.cfg.get("api_key", "")
    h_reload(app, "")
    if key and not app.cfg.get("api_key"):
        app.cfg["api_key"] = key
        save_config(app.cfg)
    good(f"restored {count} file(s)")


@command("clean", group="session", usage="/clean [all]")
def h_clean(app, a):
    """Delete cached responses and old logs (all = also reports)."""
    n = 0
    targets = [CACHE_DIR] + ([REPORTS_DIR] if a == "all" else [])
    for d in targets:
        for f in d.glob("*"):
            if f.is_file():
                f.unlink()
                n += 1
    LOG_FILE.unlink(missing_ok=True)
    good(f"removed {n} file(s) and cleared the log")


@command("cache", group="session", usage="/cache [on|off|stats|clear]")
def h_cache(app, a):
    """Control the response cache used by one-shot calls (agents, plan, commit)."""
    if a == "clear":
        n = 0
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()
            n += 1
        return good(f"cleared {n} cached response(s)")
    if a == "stats":
        fs = list(CACHE_DIR.glob("*.json"))
        return out(f"{len(fs)} entries · {sum(f.stat().st_size for f in fs) / 1024:.1f} KiB · enabled={app.cfg['cache']}")
    toggle_cfg(app, "cache", a, "cache")


@command("stats", group="session")
def h_stats(app, a):
    """Show usage statistics for this session."""
    t, s = app.session.totals, app.session.stats
    avg = t["time"] / t["requests"] if t["requests"] else 0
    ttft = sum(x["ttft"] for x in s) / len(s) if s else 0
    out(f"requests {t['requests']} · prompt tokens {human(t['prompt'])} · completion {human(t['completion'])}\n"
        f"avg latency {avg:.2f}s · avg ttft {ttft:.2f}s · cost ${t['cost']:.4f}")


@command("benchmark", group="session", usage="/benchmark [N]")
def h_benchmark(app, a):
    """Time N tiny requests to the model."""
    n = int(a) if a.strip().isdigit() else 3
    times = []
    for i in range(n):
        t0 = time.time()
        app.ask("Reply with the single word: ok", system="Reply tersely.", thinking="off", label=f"benchmark {i + 1}/{n}")
        times.append(time.time() - t0)
        out(f"  run {i + 1}: {times[-1]:.2f}s")
    out(c(f"min {min(times):.2f}s · avg {sum(times) / n:.2f}s · max {max(times):.2f}s", "accent"))


@command("latency", group="session")
def h_latency(app, a):
    """Measure round-trip latency to the models endpoint."""
    ts = []
    for _ in range(3):
        t0 = time.time()
        app.client.get("models")
        ts.append((time.time() - t0) * 1000)
    out(f"{' · '.join(f'{x:.0f}ms' for x in ts)}  (avg {sum(ts) / len(ts):.0f}ms)")


@command("tokens", group="session")
def h_tokens(app, a):
    """Show token usage for this session and the current context size."""
    ctx = sum(est_tokens(m["content"]) for m in app.session.messages)
    t = app.session.totals
    out(f"context ~{human(ctx)} / {human(app.cfg['max_context_tokens'])} · billed in {human(t['prompt'])} · out {human(t['completion'])}")


@command("cost", group="session")
def h_cost(app, a):
    """Show spend; set prices with /set price_in_per_mtok and price_out_per_mtok."""
    t = app.session.totals
    out(f"${t['cost']:.4f} this session (in ${app.cfg['price_in_per_mtok']}/Mtok, out ${app.cfg['price_out_per_mtok']}/Mtok)")
    if not (app.cfg["price_in_per_mtok"] or app.cfg["price_out_per_mtok"]):
        note("Prices are 0: set them with /set price_in_per_mtok 0.3 and /set price_out_per_mtok 2.5")


@command("budget", group="session", usage="/budget [USD|off]")
def h_budget(app, a):
    """Set a spending cap in USD for requests."""
    if a.strip():
        app.cfg["budget_usd"] = 0.0 if a.strip() == "off" else float(a)
        save_config(app.cfg)
    b = app.cfg["budget_usd"]
    good(f"budget: {'off' if not b else f'${b:.2f}'}")


@command("limit", group="session", usage="/limit [max_output_tokens|off]")
def h_limit(app, a):
    """Cap the model's output tokens per response."""
    if a.strip():
        app.cfg["max_tokens"] = 0 if a.strip() == "off" else int(a)
        save_config(app.cfg)
    good(f"output limit: {app.cfg['max_tokens'] or 'model default'}")


@command("timeout", group="session", usage="/timeout [seconds]")
def h_timeout(app, a):
    """Set the network timeout in seconds."""
    if a.strip():
        app.cfg["timeout"] = max(5, int(a))
        save_config(app.cfg)
    good(f"timeout: {app.cfg['timeout']}s")


def apply_ui(cfg: dict) -> None:
    UI.theme = cfg["theme"] if cfg["theme"] in THEMES else "midnight"
    UI.glyphs = cfg["glyphs"] if cfg["glyphs"] in GLYPHS else "unicode"
    UI.layout = cfg["layout"]
    UI.quiet, UI.silent = bool(cfg["quiet"]), bool(cfg["silent"])


@command("verbose", group="ui")
def h_verbose(app, a):
    """Toggle verbose request details."""
    toggle_cfg(app, "verbose", a, "verbose")


@command("quiet", group="ui")
def h_quiet(app, a):
    """Hide banners, spinners and footers."""
    toggle_cfg(app, "quiet", a, "quiet")
    apply_ui(app.cfg)


@command("silent", group="ui")
def h_silent(app, a):
    """Print only responses and errors."""
    toggle_cfg(app, "silent", a, "silent")
    apply_ui(app.cfg)


@command("theme", group="ui", usage="/theme [name]")
def h_theme(app, a):
    """Switch color theme."""
    if a.strip() in THEMES:
        app.cfg["theme"] = a.strip()
        save_config(app.cfg)
        apply_ui(app.cfg)
        return good(f"theme: {a.strip()}")
    out("themes: " + ", ".join(c(t, "accent") if t == UI.theme else t for t in THEMES))


@command("color", group="ui")
def h_color(app, a):
    """Toggle ANSI colors."""
    UI.color = parse_bool(a, UI.color)
    good(f"color: {'on' if UI.color else 'off'}")


@command("monochrome", group="ui")
def h_monochrome(app, a):
    """Toggle monochrome (bold/dim only, no hues)."""
    UI.mono = parse_bool(a, UI.mono)
    good(f"monochrome: {'on' if UI.mono else 'off'}")


@command("font", group="ui", usage="/font [unicode|ascii]")
def h_font(app, a):
    """Choose the glyph set (your terminal emulator controls the actual font)."""
    if a.strip() in GLYPHS:
        app.cfg["glyphs"] = a.strip()
        save_config(app.cfg)
        apply_ui(app.cfg)
    good(f"glyphs: {UI.glyphs}")


@command("layout", group="ui", usage="/layout [wide|compact|plain]")
def h_layout(app, a):
    """Pick the status-bar layout."""
    if a.strip() in ("wide", "compact", "plain"):
        app.cfg["layout"] = a.strip()
        save_config(app.cfg)
        apply_ui(app.cfg)
    good(f"layout: {UI.layout}")


@command("banner", group="ui", usage="/banner [on|off]")
def h_banner(app, a):
    """Show the banner, or toggle it at startup."""
    if a.strip() in ("on", "off"):
        app.cfg["banner"] = a.strip() == "on"
        save_config(app.cfg)
        return good(f"startup banner: {a.strip()}")
    print_banner(app)


@command("sound", group="ui")
def h_sound(app, a):
    """Toggle the terminal bell when a response finishes."""
    toggle_cfg(app, "sound", a, "sound")


@command("bell", group="ui")
def h_bell(app, a):
    """Ring the terminal bell once (or 'on'/'off' to toggle the finish bell)."""
    if a.strip() in ("on", "off"):
        return toggle_cfg(app, "sound", a, "sound")
    sys.stdout.write("\a")
    sys.stdout.flush()


@command("notify", group="ui")
def h_notify(app, a):
    """Toggle desktop notifications when a response finishes."""
    toggle_cfg(app, "notify", a, "notify")


@command("clipboard", group="ui", usage="/clipboard [copy|code|paste]")
def h_clipboard(app, a):
    """Copy the last response (or its last code block) to the clipboard, or show the clipboard."""
    if a == "paste":
        t = clip_paste()
        return out(t if t is not None else "(no clipboard tool found)")
    text = app.last_text
    if a == "code":
        blocks = extract_blocks(text)
        text = blocks[-1]["code"] if blocks else ""
    if not text:
        raise UsageError("Nothing to copy yet.")
    good("copied to clipboard") if clip_copy(text) else bad("No clipboard tool found (pbcopy, wl-copy, xclip, xsel, clip).")


@command("paste", group="ui", usage="/paste [instruction]")
def h_paste(app, a):
    """Send the clipboard contents (with an optional instruction) to the model."""
    t = clip_paste()
    if not t:
        raise UsageError("Clipboard is empty or no clipboard tool was found.")
    return Send((a + "\n\n" if a else "") + f"```\n{t}\n```")


# ---- AI controls -----------------------------------------------------------
@command("model", group="ai", usage="/model [name]")
def h_model(app, a):
    """Show or switch the model."""
    if a.strip():
        app.cfg["model"] = a.strip()
        save_config(app.cfg)
    good(f"model: {app.cfg['model']}")


@command("models", group="ai")
def h_models(app, a):
    """List models available at the endpoint."""
    data = app.client.get("models").get("data", [])
    out("\n".join("  " + m.get("id", "?") for m in data) or "(none)")


@command("thinking", "think", group="ai", usage="/thinking [off|low|medium|high|max]")
def h_thinking(app, a):
    """Set reasoning depth."""
    if a.strip():
        if a.strip() not in THINK_LEVELS:
            raise UsageError("Choose off, low, medium, high or max.")
        app.think = app.cfg["thinking"] = a.strip()
        save_config(app.cfg)
    good(f"thinking: {app.think}")


@command("thoughts", group="ai", usage="/thoughts [on|off|show]")
def h_thoughts(app, a):
    """Expand the last reasoning block, or always show reasoning."""
    if a.strip() in ("on", "off"):
        return toggle_cfg(app, "show_thoughts", a, "show reasoning")
    app.show_thought()


@command("system", group="ai", usage="/system [text|reset]")
def h_system(app, a):
    """Show or set the system prompt for this session."""
    if a == "reset":
        app.session.system = ""
        return good("system prompt reset")
    if a.strip():
        app.session.system = a.strip()
        return good("system prompt set")
    out(app.session.system or SYSTEM_DEFAULT)


@command("temp", group="ai", usage="/temp [0-2]")
def h_temp(app, a):
    """Set sampling temperature."""
    if a.strip():
        app.cfg["temperature"] = min(2.0, max(0.0, float(a)))
        save_config(app.cfg)
    good(f"temperature: {app.cfg['temperature']}")


@command("undo", group="ai")
def h_undo(app, a):
    """Remove the last exchange from the conversation."""
    if len(app.session.messages) >= 2:
        del app.session.messages[-2:]
        return good("removed last exchange")
    raise UsageError("Nothing to undo.")


@command("retry", group="ai")
def h_retry(app, a):
    """Regenerate the last response."""
    ms = app.session.messages
    if len(ms) < 2 or ms[-2]["role"] != "user":
        raise UsageError("Nothing to retry.")
    last = ms[-2]["content"]
    del ms[-2:]
    return Send(last)


@command("compact", group="ai")
def h_compact(app, a):
    """Condense older turns now to free context space."""
    before = len(app.session.messages)
    kept = prune_messages(app.session.messages, max(1000, int(app.cfg["max_context_tokens"]) // 3))
    app.session.messages = [m for m in kept if m["role"] != "system"] if kept else []
    digest = [m for m in kept if m["role"] == "system"]
    if digest:
        app.session.messages.insert(0, {"role": "user", "content": digest[-1]["content"]})
        app.session.messages.insert(1, {"role": "assistant", "content": "Understood."})
    good(f"context compacted ({before} -> {len(app.session.messages)} messages)")


@command("edit", group="ai", usage="/edit")
def h_edit(app, a):
    """Compose a multi-line prompt in $EDITOR (or the built-in editor) before sending."""
    txt = edit_text("")
    if txt:
        return Send(txt)
    note("(empty prompt discarded)")


@command("attach", group="ai", usage="/attach [paths...|clear]")
def h_attach(app, a):
    """Queue files as context for the next prompt (also: @path inside a prompt)."""
    if a == "clear":
        app.pending.clear()
        return good("attachments cleared")
    for p in split_args(a):
        for f in glob.glob(os.path.expanduser(p)) or [p]:
            app.pending.append((f, read_text_file(f, 60_000)))
    out("queued: " + (", ".join(n for n, _ in app.pending) or "(none)"))


@command("index", group="ai", usage="/index [on|off|rebuild|status|query TEXT]")
def h_index(app, a):
    """Workspace indexing: auto-retrieve relevant local files as context."""
    args = split_args(a)
    sub = args[0] if args else "status"
    if sub in ("on", "off"):
        app.index_on = sub == "on"
        return good(f"workspace indexing: {sub}")
    if sub == "rebuild" or (sub in ("query", "status") and app.index is None):
        with Spinner("indexing workspace"):
            app.index = WorkspaceIndex(Path.cwd())
        if sub == "rebuild":
            return good(f"indexed {len(app.index.docs)} file(s)")
    if sub == "query":
        for score, p in app.index.query(" ".join(args[1:]), 8):  # type: ignore
            out(f"  {score:.2f}  {p.relative_to(Path.cwd())}")
        return
    out(f"indexing {'on' if app.index_on else 'off'} · {len(app.index.docs) if app.index else 0} file(s) indexed")


@command("write", "extract", group="ai", usage="/write [on|off|N path]")
def h_write(app, a):
    """Auto-extract code blocks from replies and write them to files."""
    args = split_args(a)
    if args and args[0] in ("on", "off"):
        app.extract_mode = args[0] == "on"
        return good(f"auto-extract: {args[0]}")
    blocks = app.last_blocks or extract_blocks(app.last_text)
    if len(args) == 2 and args[0].isdigit():
        i = int(args[0]) - 1
        if not 0 <= i < len(blocks):
            raise UsageError("No such block.")
        blocks[i]["path"] = args[1]
        return app.offer_write("", [blocks[i]])
    if not blocks:
        raise UsageError("No code blocks in the last response.")
    for i, b in enumerate(blocks, 1):
        out(f"  {c(i, 'accent')} {b['lang'] or 'text':10} {b['path'] or '(no filename; use /write N path)'} "
            f"{len(b['code'].splitlines())} lines")
    app.offer_write(app.last_text, blocks)


@command("agents", group="ai", usage="/agents [list|run ROLE[,ROLE] TASK]")
def h_agents(app, a):
    """Spawn parallel subagents (ui, security, review, arch, tests, docs, perf, refactor)."""
    args = a.split(None, 2)
    if not args or args[0] == "list":
        out(c("roles:", "accent") + " " + ", ".join(ROLES))
        for ag in app.agents[-12:]:
            dur = (ag.ended or time.time()) - ag.started if ag.started else 0
            out(f"  #{ag.id} {ag.role:20} {ag.status:8} {dur:5.1f}s ~{ag.tokens} tok  {trunc(ag.task, 50)}")
        return
    if args[0] == "run" and len(args) >= 3:
        roles = [ROLE_ALIASES.get(r.strip(), r.strip()) for r in args[1].split(",")]
        bad_roles = [r for r in roles if r not in ROLES]
        if bad_roles:
            raise UsageError(f"Unknown role(s): {', '.join(bad_roles)}")
        return run_agent_task(app, roles, args[2])
    raise UsageError("Usage: /agents run ROLE[,ROLE...] TASK")


def run_agent_task(app: App, roles: list, task: str) -> Optional[str]:
    task = app.clean(app.take_attachments(task))
    ctx = ""
    if app.index_on:
        if app.index is None:
            app.index = WorkspaceIndex(Path.cwd())
        ctx = "\n\nWorkspace context:\n" + app.index.context(task)
    agents = app.run_agents(roles, task, ctx)
    for ag in agents:
        badge = c(f" {ag.role} ", "accent", True)
        status = c(ag.status, "ok" if ag.status == "done" else "err")
        out(f"\n{badge} {status} {c(f'{ag.ended - ag.started:.1f}s', 'muted')}")
        r = StreamRenderer()
        r.feed(ag.text + "\n")
    ok = [ag for ag in agents if ag.status == "done"]
    if not ok:
        return None
    if len(ok) == 1:
        app.session.messages += [{"role": "user", "content": task}, {"role": "assistant", "content": ok[0].text}]
        app.last_text = ok[0].text
        return ok[0].text
    reports = "\n\n".join(f"### {ag.role}\n{ag.text}" for ag in ok)
    synth = f"Task: {task}\n\nSpecialist reports:\n{reports}\n\nSynthesize one prioritized, de-duplicated action plan."
    out(c("\n" + g("h") * 3 + " synthesis", "accent", True))
    result = app.send(synth, record=False)
    if result is not None:
        app.session.messages += [{"role": "user", "content": task}, {"role": "assistant", "content": result}]
    return result


@command("plan", "decompose", group="ai", usage="/plan GOAL")
def h_plan(app, a):
    """Decompose a big goal into a task graph and run it with parallel workers."""
    if not a.strip():
        raise UsageError("Usage: /plan GOAL")
    goal = app.clean(app.take_attachments(a))
    tasks = app.decompose(goal)
    waves = task_waves(tasks)
    out(c("Task graph", "accent", True))
    for i, wave in enumerate(waves, 1):
        for t in wave:
            deps = f" ← {','.join(t['deps'])}" if t["deps"] else ""
            out(f"  {c(f'wave {i}', 'muted')} {c(t['id'], 'accent2', True)} {t.get('title', '')}{c(deps, 'muted')}")
    results: dict = {}
    for i, wave in enumerate(waves, 1):
        def run(t):
            ctx = "\n\n".join(f"[{d}] {results[d][:3000]}" for d in t["deps"] if d in results)
            msgs = [{"role": "system", "content": SYSTEM_DEFAULT},
                    {"role": "user", "content": f"Overall goal: {goal}\n\nYour task: {t.get('prompt', t.get('title', ''))}"
                     + (f"\n\nContext from prerequisite tasks:\n{ctx}" if ctx else "")}]
            r = app.client.chat(msgs, stream=False, thinking=app.think)
            app.account(r, msgs)
            return t["id"], r["text"]
        sp = Spinner(f"wave {i}/{len(waves)} · {len(wave)} task(s)").start()
        try:
            with cf.ThreadPoolExecutor(max_workers=max(1, min(len(wave), int(app.cfg["max_parallel"])))) as ex:
                for tid, text in ex.map(run, wave):
                    results[tid] = text
        finally:
            sp.stop()
        good(f"wave {i} complete")
    final = ("Goal: " + goal + "\n\nTask outputs:\n" + "\n\n".join(f"## {t['id']} {t.get('title', '')}\n{results.get(t['id'], '')}"
                                                                for t in tasks)
             + "\n\nCombine these into one coherent final deliverable.")
    return Send(final, record=True)


@command("template", group="ai", usage="/template [list|show N|save N TEXT|rm N|use N [input]]")
def h_template(app, a):
    """Manage and apply prompt templates ({{input}}, {{extra}}, {{file:path}}, {{clip}}, {{date}})."""
    args = a.split(None, 2)
    sub = args[0] if args else "list"
    if sub == "list":
        names = sorted(set(BUILTIN_TEMPLATES) | {p.stem for p in TEMPLATES_DIR.glob("*.txt")})
        return out(", ".join(names))
    if sub == "show" and len(args) > 1:
        return out(load_template(args[1]) or "(not found)")
    if sub == "save" and len(args) > 2:
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        (TEMPLATES_DIR / f"{re.sub(r'[^A-Za-z0-9_.-]', '', args[1])}.txt").write_text(args[2], "utf-8")
        return good(f"saved template {args[1]}")
    if sub == "rm" and len(args) > 1:
        (TEMPLATES_DIR / f"{re.sub(r'[^A-Za-z0-9_.-]', '', args[1])}.txt").unlink(missing_ok=True)
        return good("removed")
    if sub == "use" and len(args) > 1:
        return template_send(app, args[1], args[2] if len(args) > 2 else "")
    raise UsageError(h_template.__doc__ or "")


def template_send(app: App, name: str, arg: str, extra: str = "") -> Send:
    tpl = load_template(name)
    if not tpl:
        raise UsageError(f"Unknown template '{name}'.")
    inp = arg
    if arg and Path(arg).expanduser().is_file():
        inp = fenced(arg, read_text_file(arg)).strip()
    elif not arg:
        inp = fenced("git diff", git_out("diff", "HEAD")[:40000]).strip() if shutil.which("git") else ""
    return Send(render_template(tpl, inp, extra))


@command("hooks", group="ai", usage="/hooks [list|set EVENT CMD|rm EVENT|run EVENT]")
def h_hooks(app, a):
    """Manage shell hooks (on_start, pre_send, post_response, post_write, on_error, on_exit)."""
    args = a.split(None, 2)
    hooks = app.cfg.setdefault("hooks", {})
    if not args or args[0] == "list":
        return out("\n".join(f"  {k}: {v}" for k, v in hooks.items()) or "(no hooks)")
    if args[0] == "set" and len(args) == 3:
        hooks[args[1]] = args[2]
        save_config(app.cfg)
        return good(f"hook {args[1]} set")
    if args[0] == "rm" and len(args) > 1:
        hooks.pop(args[1], None)
        save_config(app.cfg)
        return good("hook removed")
    if args[0] == "run" and len(args) > 1:
        return app.run_hook(args[1], app.last_text)
    raise UsageError("Usage: /hooks [list|set EVENT CMD|rm EVENT|run EVENT]")


@command("sanitize", group="ai")
def h_sanitize(app, a):
    """Toggle automatic secret redaction on outgoing prompts."""
    toggle_cfg(app, "sanitize", a, "sanitize")


@command("profile", group="ai")
def h_profile(app, a):
    """Speed profile of the most recent requests."""
    rows = app.session.stats[-10:]
    if not rows:
        return out("(no requests yet)")
    out(c(f"{'time':8} {'prompt':>7} {'compl':>7} {'think':>7} {'ttft':>7} {'total':>7} {'tok/s':>6}", "muted"))
    for r in rows:
        tps = r["completion"] / r["total"] if r["total"] else 0
        out(f"{r['t'][11:]:8} {r['prompt']:>7} {r['completion']:>7} {r['reasoning']:>7} {r['ttft']:>6.2f}s {r['total']:>6.2f}s {tps:>6.0f}")


@command("review", group="ai", usage="/review [file]")
def h_review(app, a):
    """Code review of a file or your uncommitted git changes."""
    return template_send(app, "review", a.strip())


@command("explain", group="ai", usage="/explain [file]")
def h_explain(app, a):
    """Explain a file or your uncommitted changes."""
    return template_send(app, "explain", a.strip())


@command("refactor", group="ai", usage="/refactor FILE [instructions]")
def h_refactor(app, a):
    """Refactor a file."""
    p = a.split(None, 1)
    return template_send(app, "refactor", p[0] if p else "", p[1] if len(p) > 1 else "")


@command("gentest", "gentests", group="ai", usage="/gentest FILE")
def h_gentest(app, a):
    """Generate a unit-test suite for a script."""
    path = a.strip()
    if not path:
        raise UsageError("Usage: /gentest FILE")
    ext = Path(path).suffix
    fw = {".py": "pytest", ".js": "Jest", ".ts": "Jest", ".go": "the standard testing package", ".rs": "cargo test",
          ".java": "JUnit 5"}.get(ext, "the idiomatic framework")
    stem = Path(path).stem
    hint = f"Use {fw}. Put the code in one fenced block whose first line is a comment `file: tests/test_{stem}{ext}`."
    app.extract_mode = True
    return template_send(app, "tests", path, hint)


# ---- files -----------------------------------------------------------------
@command("cat", group="files", usage="/cat FILE... [-n]")
def h_cat(app, a):
    """Print files (-n for line numbers)."""
    args = split_args(a)
    num = "-n" in args
    for f in [x for x in args if x != "-n"]:
        txt = read_text_file(f)
        out(c(f"── {f}", "muted"))
        out("\n".join(f"{i:4} {c(g('bar'), 'muted')} {ln}" for i, ln in enumerate(txt.splitlines(), 1)) if num else txt)


@command("head", group="files", usage="/head FILE [N]")
def h_head(app, a):
    """Show the first N lines of a file (default 10)."""
    args = split_args(a)
    if not args:
        raise UsageError("Usage: /head FILE [N]")
    out("\n".join(read_text_file(args[0]).splitlines()[: int(args[1]) if len(args) > 1 else 10]))


@command("tail", group="files", usage="/tail FILE [N]")
def h_tail(app, a):
    """Show the last N lines of a file (default 10)."""
    args = split_args(a)
    if not args:
        raise UsageError("Usage: /tail FILE [N]")
    out("\n".join(read_text_file(args[0]).splitlines()[-(int(args[1]) if len(args) > 1 else 10):]))


@command("grep", group="files", usage="/grep PATTERN [PATH] [-i]")
def h_grep(app, a):
    """Search files recursively with a regular expression."""
    args = split_args(a)
    ic = "-i" in args
    args = [x for x in args if x != "-i"]
    if not args:
        raise UsageError("Usage: /grep PATTERN [PATH] [-i]")
    try:
        rx = re.compile(args[0], re.I if ic else 0)
    except re.error as e:
        raise UsageError(f"Bad regex: {e}")
    root = Path(args[1] if len(args) > 1 else ".")
    hits = 0
    files = [root] if root.is_file() else scan_workspace(root, 5000, 1_000_000)
    for p in files:
        try:
            for i, ln in enumerate(p.read_text("utf-8").splitlines(), 1):
                if rx.search(ln):
                    out(f"{c(p, 'accent2')}:{c(i, 'muted')}: {trunc(ln.strip(), 160)}")
                    hits += 1
                    if hits >= 200:
                        return note("(stopped after 200 matches)")
        except (OSError, UnicodeDecodeError):
            continue
    if not hits:
        note("no matches")


@command("find", group="files", usage="/find GLOB [PATH]")
def h_find(app, a):
    """Find files by name pattern."""
    args = split_args(a)
    if not args:
        raise UsageError("Usage: /find GLOB [PATH]")
    n = 0
    for dp, dns, fns in os.walk(args[1] if len(args) > 1 else "."):
        dns[:] = [d for d in dns if d not in IGNORE_DIRS]
        for fn in fns + dns:
            if fnmatch.fnmatch(fn.lower(), args[0].lower()):
                out(os.path.join(dp, fn))
                n += 1
                if n >= 300:
                    return note("(stopped after 300 results)")


@command("diff", group="files", usage="/diff [A B | git-args]")
def h_diff(app, a):
    """Diff two files, or show git diff."""
    args = split_args(a)
    if len(args) == 2 and all(Path(x).is_file() for x in args):
        d = difflib.unified_diff(read_text_file(args[0]).splitlines(), read_text_file(args[1]).splitlines(),
                                 args[0], args[1], lineterm="")
        return out("\n".join(d) or "(identical)")
    run_proc(["git", "diff", "--color=auto" if UI.color else "--no-color", *args])


@command("patch", group="files", usage="/patch FILE INSTRUCTIONS")
def h_patch(app, a):
    """Ask the model for a unified diff that changes FILE; apply it with /apply."""
    p = a.split(None, 1)
    if len(p) < 2:
        raise UsageError("Usage: /patch FILE INSTRUCTIONS")
    src = read_text_file(p[0])
    raw = app.ask(f"File {p[0]}:\n```\n{src}\n```\nChange request: {p[1]}\n\nReturn ONLY a unified diff (git format, "
                  f"paths a/{p[0]} b/{p[0]}) in one ```diff fenced block.",
                  system="You output precise unified diffs and nothing else.", label="writing patch")
    blocks = extract_blocks(raw)
    diff = blocks[0]["code"] if blocks else raw
    dest = Path(".procode"); dest.mkdir(exist_ok=True)
    (dest / "last.patch").write_text(diff.rstrip("\n") + "\n", "utf-8")
    out(diff)
    good("saved to .procode/last.patch; review it, then run /apply")


@command("apply", group="files", usage="/apply [patchfile]")
def h_apply(app, a):
    """Validate and apply a patch with git apply."""
    pf = a.strip() or ".procode/last.patch"
    if not Path(pf).is_file():
        raise UsageError(f"No patch file at {pf}")
    if run_proc(["git", "apply", "--check", pf]) != 0:
        return bad("Patch does not apply cleanly.")
    if ask_yes("Patch checks out. Apply it?"):
        if run_proc(["git", "apply", pf]) == 0:
            good("patch applied")


COMMIT_SYS = ("You write Conventional Commit messages. Output ONLY the message: a `type(scope): subject` line "
              "(imperative, <=72 chars), a blank line, then a short body of bullet points if useful. No code fences.")


@command("commit", group="git", usage="/commit [-a] [--dry]")
def h_commit(app, a):
    """Generate a conventional commit message from staged changes and commit."""
    flags = split_args(a)
    if "-a" in flags or "--all" in flags:
        run_proc(["git", "add", "-A"])
    diff = git_out("diff", "--staged")
    if not diff.strip():
        return warn("Nothing staged. Use /add PATHS or /commit -a.")
    stat = git_out("diff", "--staged", "--stat")
    msg = app.ask(f"Staged changes summary:\n{stat}\n\nDiff:\n{diff[:30000]}", system=COMMIT_SYS, label="writing commit message")
    msg = re.sub(r"^```\w*\n|\n```$", "", msg.strip()).strip().strip("`")
    out(c(g("top") + g("h") * 3, "muted"))
    out("\n".join(c(g("bar"), "muted") + " " + ln for ln in msg.splitlines()))
    out(c(g("bot") + g("h") * 3, "muted"))
    if "--dry" in flags:
        return
    ans = ask_choice("Commit with this message? [y]es/[e]dit/[n]o ", "yen")
    if ans == "e":
        msg = edit_text(msg)
        ans = "y" if msg else "n"
    if ans == "y":
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(msg + "\n")
        try:
            run_proc(["git", "commit", "-F", f.name])
        finally:
            os.unlink(f.name)


def git_passthrough(name: str, base: list, doc: str, default_args: Optional[list] = None):
    @command(name, group="git", usage=f"/{name} [args]")
    def _h(app, a, _base=base, _def=default_args):
        args = split_args(a) or (_def or [])
        return run_proc(["git", *_base, *args]) and None
    _h.__doc__ = doc
    COMMANDS[name].help = doc


git_passthrough("push", ["push"], "git push")
git_passthrough("pull", ["pull"], "git pull")
git_passthrough("remote", ["remote"], "git remote (defaults to -v)", ["-v"])
git_passthrough("branch", ["branch"], "git branch")
git_passthrough("tag", ["tag"], "git tag")
git_passthrough("clone", ["clone"], "git clone")
git_passthrough("init", ["init"], "git init")
git_passthrough("log", ["log"], "git log (defaults to a short graph)", ["--oneline", "--graph", "-n", "15"])
git_passthrough("add", ["add"], "git add")
git_passthrough("rm", ["rm"], "git rm")
git_passthrough("mv", ["mv"], "git mv")


@command("sync", group="git")
def h_sync(app, a):
    """git pull --rebase, then push."""
    if run_proc(["git", "pull", "--rebase"]) == 0:
        run_proc(["git", "push"])


# ---- dev workflow -----------------------------------------------------------
def detect_project(kind: str) -> list:
    cwd = Path.cwd()
    if (cwd / "package.json").exists():
        try:
            scripts = json.loads((cwd / "package.json").read_text("utf-8")).get("scripts", {})
        except ValueError:
            scripts = {}
        if kind in ("test", "build") and kind in scripts:
            return ["npm", "run", kind] if kind == "build" else ["npm", "test"]
        if kind == "package":
            return ["npm", "pack"]
        if kind == "publish":
            return ["npm", "publish"]
    if (cwd / "go.mod").exists():
        return {"test": ["go", "test", "./..."], "build": ["go", "build", "./..."], "compile": ["go", "vet", "./..."]}.get(kind, ["go", "build", "./..."])
    if (cwd / "Cargo.toml").exists():
        return {"test": ["cargo", "test"], "build": ["cargo", "build"], "compile": ["cargo", "check"],
                "package": ["cargo", "package"], "publish": ["cargo", "publish"]}.get(kind, ["cargo", "build"])
    if (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists() or list(cwd.glob("*.py")):
        return {"test": [sys.executable, "-m", "pytest", "-q"], "build": [sys.executable, "-m", "build"],
                "compile": [sys.executable, "-m", "compileall", "-q", "."], "package": [sys.executable, "-m", "build"],
                "publish": [sys.executable, "-m", "twine", "upload", "dist/*"]}.get(kind, [sys.executable, "-m", "build"])
    if (cwd / "Makefile").exists():
        return ["make", kind if kind != "compile" else "all"]
    raise UsageError(f"Could not detect a project type for '{kind}'. Pass a command: /{kind} <command>")


def dev_cmd(kind: str):
    def h(app, a):
        argv = split_args(a) or detect_project(kind)
        if kind == "publish":
            if not ask_yes(f"About to run: {' '.join(argv)}. This publishes publicly. Continue?", strict=True):
                return
            if "dist/*" in argv:
                argv = argv[:-1] + sorted(glob.glob("dist/*"))
        app.run_hook(f"pre_{kind}")
        rc = run_proc(argv)
        (good if rc == 0 else bad)(f"{kind} {'succeeded' if rc == 0 else f'failed (exit {rc})'}")
    return h


for _k, _doc in (("test", "Run the project's tests (auto-detected)."), ("build", "Build the project (auto-detected)."),
                 ("compile", "Compile/syntax-check the project (auto-detected)."),
                 ("package", "Package the project for distribution."),
                 ("publish", "Publish the package (asks for confirmation).")):
    _f = dev_cmd(_k)
    _f.__doc__ = _doc
    command(_k, group="dev", usage=f"/{_k} [command]")(_f)


@command("run", group="dev", usage="/run FILE|COMMAND")
def h_run(app, a):
    """Run a script (by extension) or a command."""
    args = split_args(a)
    if not args:
        raise UsageError("Usage: /run FILE|COMMAND")
    runners = {".py": [sys.executable], ".js": ["node"], ".sh": ["bash"], ".rb": ["ruby"], ".go": ["go", "run"], ".pl": ["perl"]}
    p = Path(args[0])
    if p.is_file() and p.suffix in runners:
        args = runners[p.suffix] + args
    run_proc(args)


@command("deploy", group="dev")
def h_deploy(app, a):
    """Run the 'deploy' hook from your config (asks for confirmation)."""
    cmd = (app.cfg.get("hooks") or {}).get("deploy")
    if not cmd:
        raise UsageError("No deploy command. Define one: /hooks set deploy \"your deploy command\"")
    if ask_yes(f"Run deploy command: {cmd}?", strict=True):
        subprocess.call(cmd, shell=True)


@command("serve", group="dev", usage="/serve [port] [dir]")
def h_serve(app, a):
    """Serve a directory over HTTP on 127.0.0.1."""
    args = split_args(a)
    port = args[0] if args else "8000"
    run_proc([sys.executable, "-m", "http.server", port, "--bind", "127.0.0.1", "--directory", args[1] if len(args) > 1 else "."])


@command("proxy", group="dev", usage="/proxy [URL|off]")
def h_proxy(app, a):
    """Show or set the HTTP(S) proxy used for API calls."""
    if a.strip():
        app.cfg["proxy"] = "" if a.strip() == "off" else a.strip()
        save_config(app.cfg)
    good(f"proxy: {app.cfg['proxy'] or 'none'}")


@command("tunnel", group="dev", usage="/tunnel PORT | /tunnel -L LOCAL:HOST:REMOTE SSHHOST")
def h_tunnel(app, a):
    """Expose a local port (cloudflared) or create an SSH port-forward."""
    args = split_args(a)
    if len(args) == 1 and args[0].isdigit():
        return run_proc(["cloudflared", "tunnel", "--url", f"http://localhost:{args[0]}"])
    if len(args) == 3 and args[0] == "-L":
        return run_proc(["ssh", "-N", "-L", args[1], args[2]])
    raise UsageError(h_tunnel.__doc__ or "")


# ---- network ----------------------------------------------------------------
def http_url(u: str) -> str:
    if not re.match(r"^https?://", u):
        raise UsageError("Only http(s) URLs are supported.")
    return u


def http_get(app: App, url: str, limit: int = 2_000_000) -> bytes:
    req = urllib.request.Request(http_url(url), headers={"User-Agent": f"pro-code-cli/{__version__}"})
    try:
        with app.client.opener().open(req, timeout=float(app.cfg["timeout"])) as r:
            return r.read(limit)
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        raise UsageError(f"Request failed: {e}")


@command("host", group="net", usage="/host [NAME]")
def h_host(app, a):
    """Show this machine's hostname, or resolve NAME."""
    if a.strip():
        return out("\n".join(sorted({x[4][0] for x in socket.getaddrinfo(a.strip(), None)})))
    out(f"{socket.gethostname()} ({platform.node()})")


@command("ip", group="net", usage="/ip [public]")
def h_ip(app, a):
    """Show local IP addresses (or 'public' to ask api.ipify.org)."""
    if a.strip() == "public":
        return out(http_get(app, "https://api.ipify.org", 100).decode().strip())
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        out(s.getsockname()[0])
        s.close()
    except OSError:
        out("127.0.0.1")


@command("dns", group="net", usage="/dns NAME")
def h_dns(app, a):
    """Resolve a hostname."""
    if not a.strip():
        raise UsageError("Usage: /dns NAME")
    try:
        for fam, _, _, _, addr in socket.getaddrinfo(a.strip(), None):
            out(f"{'IPv6' if fam == socket.AF_INET6 else 'IPv4'}  {addr[0]}")
    except socket.gaierror as e:
        raise UsageError(f"Lookup failed: {e}")


@command("ping", group="net", usage="/ping [HOST[:PORT]]")
def h_ping(app, a):
    """TCP connect-time probe (no ICMP privileges needed). Default: the API host."""
    target = a.strip() or re.sub(r"^https?://", "", app.cfg["base_url"]).split("/")[0]
    host, _, port = target.partition(":")
    for i in range(4):
        t0 = time.time()
        try:
            socket.create_connection((host, int(port or 443)), 4).close()
            out(f"{host}: connected in {(time.time() - t0) * 1000:.0f}ms")
        except OSError as e:
            out(c(f"{host}: {e}", "err"))
        time.sleep(0.3)


@command("pong", group="net")
def h_pong(app, a):
    """Reply to a ping."""
    out(c("ping", "accent", True) + " " + g("dot"))


@command("port", group="net", usage="/port HOST PORT")
def h_port(app, a):
    """Check whether a TCP port is open."""
    args = split_args(a)
    if len(args) != 2 or not args[1].isdigit():
        raise UsageError("Usage: /port HOST PORT")
    try:
        socket.create_connection((args[0], int(args[1])), 4).close()
        good(f"{args[0]}:{args[1]} is open")
    except OSError as e:
        bad(f"{args[0]}:{args[1]} closed/unreachable ({e})")


@command("curl", group="net", usage="/curl [curl args | URL]")
def h_curl(app, a):
    """Run curl (or a built-in GET when curl is missing)."""
    args = split_args(a)
    if shutil.which("curl"):
        return run_proc(["curl", *args])
    if len(args) == 1:
        return out(http_get(app, args[0]).decode("utf-8", "replace"))
    raise UsageError("curl is not installed; use /fetch URL.")


def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", re.sub(r"(?s)<[^>]+>", "", html))).strip()


@command("fetch", group="net", usage="/fetch URL [--ctx]")
def h_fetch(app, a):
    """GET a URL; with --ctx the text is queued as context for your next prompt."""
    args = split_args(a)
    ctx = "--ctx" in args
    args = [x for x in args if x != "--ctx"]
    if not args:
        raise UsageError("Usage: /fetch URL [--ctx]")
    body = http_get(app, args[0]).decode("utf-8", "replace")
    text = strip_html(body) if "<html" in body[:2000].lower() else body
    if ctx:
        app.pending.append((args[0], text[:60_000]))
        return good(f"fetched {len(text)} chars; queued as context")
    out(text[:20_000])


@command("download", group="net", usage="/download URL [dest]")
def h_download(app, a):
    """Download a URL to a file."""
    args = split_args(a)
    if not args:
        raise UsageError("Usage: /download URL [dest]")
    dest = Path(args[1] if len(args) > 1 else (Path(args[0].split("?")[0]).name or "download.bin"))
    if dest.exists() and not ask_yes(f"{dest} exists. Overwrite?"):
        return
    data = http_get(app, args[0], 500_000_000)
    dest.write_bytes(data)
    good(f"saved {len(data)} bytes to {dest}")


@command("upload", group="net", usage="/upload FILE URL [--put]")
def h_upload(app, a):
    """POST (or PUT) a file to a URL."""
    args = split_args(a)
    put = "--put" in args
    args = [x for x in args if x != "--put"]
    if len(args) != 2:
        raise UsageError("Usage: /upload FILE URL [--put]")
    if not ask_yes(f"Send {args[0]} to {args[1]}?"):
        return
    req = urllib.request.Request(http_url(args[1]), data=Path(args[0]).read_bytes(),
                                 headers={"Content-Type": "application/octet-stream"}, method="PUT" if put else "POST")
    try:
        with app.client.opener().open(req, timeout=float(app.cfg["timeout"])) as r:
            good(f"server replied {r.status}")
    except (urllib.error.URLError, OSError) as e:
        raise UsageError(f"Upload failed: {e}")


# ---- archives / hashing / crypto -----------------------------------------------
@command("zip", group="archive", usage="/zip OUT.zip PATH...")
def h_zip(app, a):
    """Create a zip archive."""
    args = split_args(a)
    if len(args) < 2:
        raise UsageError("Usage: /zip OUT.zip PATH...")
    outp = Path(args[0]).resolve()
    n = 0
    with zipfile.ZipFile(outp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in map(Path, args[1:]):
            files = [f for f in p.rglob("*") if f.is_file() and not (set(f.parts) & IGNORE_DIRS)] if p.is_dir() else [p]
            for f in files:
                if f.exists() and f.resolve() != outp:
                    z.write(f)
                    n += 1
    good(f"{n} file(s) -> {outp.name}")


@command("unzip", group="archive", usage="/unzip FILE [dest]")
def h_unzip(app, a):
    """Safely extract a zip archive."""
    args = split_args(a)
    if not args:
        raise UsageError("Usage: /unzip FILE [dest]")
    dest = Path(args[1] if len(args) > 1 else ".").resolve()
    with zipfile.ZipFile(args[0]) as z:
        for m in z.infolist():
            t = (dest / m.filename).resolve()
            if t != dest and dest not in t.parents:
                raise UsageError(f"Unsafe path in archive: {m.filename}")
        z.extractall(dest)
        good(f"extracted {len(z.namelist())} entries to {dest}")


@command("tar", group="archive", usage="/tar c|x|t ARCHIVE [PATHS|DEST]")
def h_tar(app, a):
    """Create (c), extract (x) or list (t) tar archives (.tar, .tgz, .tar.bz2, .tar.xz)."""
    args = split_args(a)
    if len(args) < 2 or args[0] not in ("c", "x", "t"):
        raise UsageError("Usage: /tar c|x|t ARCHIVE [PATHS|DEST]")
    mode, arc = args[0], args[1]
    comp = ":gz" if arc.endswith((".gz", ".tgz")) else ":bz2" if arc.endswith(".bz2") else ":xz" if arc.endswith(".xz") else ""
    if mode == "c":
        with tarfile.open(arc, "w" + comp) as tf:
            for p in args[2:]:
                tf.add(p, filter=lambda ti: None if (set(Path(ti.name).parts) & IGNORE_DIRS) else ti)
        return good(f"created {arc}")
    with tarfile.open(arc, "r" + comp) as tf:
        if mode == "t":
            return out("\n".join(tf.getnames()))
        dest = Path(args[2] if len(args) > 2 else ".").resolve()
        for m in tf.getmembers():
            t = (dest / m.name).resolve()
            if m.issym() or m.islnk() or (t != dest and dest not in t.parents):
                raise UsageError(f"Unsafe entry in archive: {m.name}")
        tf.extractall(dest, filter="data") if hasattr(tarfile, "data_filter") else tf.extractall(dest)
        good(f"extracted to {dest}")


@command("gzip", group="archive", usage="/gzip [-d] FILE")
def h_gzip(app, a):
    """Compress a file to .gz (or decompress with -d). The original is kept."""
    args = split_args(a)
    dec = "-d" in args
    args = [x for x in args if x != "-d"]
    if len(args) != 1:
        raise UsageError("Usage: /gzip [-d] FILE")
    src = Path(args[0])
    if dec:
        dst = src.with_suffix("") if src.suffix == ".gz" else src.with_name(src.name + ".out")
        with gzip.open(src, "rb") as fi, open(dst, "wb") as fo:
            shutil.copyfileobj(fi, fo)
    else:
        dst = src.with_name(src.name + ".gz")
        with open(src, "rb") as fi, gzip.open(dst, "wb") as fo:
            shutil.copyfileobj(fi, fo)
    good(f"wrote {dst}")


def data_arg(a: str) -> bytes:
    a = a.strip()
    if not a:
        raise UsageError("Provide text or a file path.")
    p = Path(a.strip("'\""))
    return p.read_bytes() if p.is_file() else a.encode("utf-8")


@command("base64", group="archive", usage="/base64 [-d] TEXT|FILE")
def h_base64(app, a):
    """Base64-encode (or decode with -d) text or a file."""
    dec = a.startswith("-d ")
    data = data_arg(a[3:] if dec else a)
    try:
        out(base64.b64decode(data).decode("utf-8", "replace") if dec else base64.b64encode(data).decode())
    except ValueError as e:
        raise UsageError(f"Invalid base64: {e}")


@command("md5", group="archive", usage="/md5 TEXT|FILE")
def h_md5(app, a):
    """MD5 checksum (not for security use)."""
    out(hashlib.md5(data_arg(a)).hexdigest())


@command("sha256", group="archive", usage="/sha256 TEXT|FILE")
def h_sha256(app, a):
    """SHA-256 checksum."""
    out(hashlib.sha256(data_arg(a)).hexdigest())


def fernet_for(passphrase: str, salt: bytes):
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise UsageError("Encryption needs the 'cryptography' package: pip install cryptography")
    key = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 600_000, 32))
    return Fernet(key)


@command("encrypt", group="archive", usage="/encrypt FILE|TEXT")
def h_encrypt(app, a):
    """Encrypt a file (writes FILE.enc) or text with a passphrase (Fernet + PBKDF2)."""
    data = data_arg(a)
    pw = getpass.getpass("Passphrase: ")
    if pw != getpass.getpass("Repeat: "):
        raise UsageError("Passphrases do not match.")
    salt = os.urandom(16)
    token = base64.b64encode(salt) + b"." + fernet_for(pw, salt).encrypt(data)
    p = Path(a.strip().strip("'\""))
    if p.is_file():
        Path(str(p) + ".enc").write_bytes(token)
        good(f"wrote {p}.enc")
    else:
        out(token.decode())


@command("decrypt", group="archive", usage="/decrypt FILE.enc|TOKEN")
def h_decrypt(app, a):
    """Decrypt output of /encrypt."""
    raw = data_arg(a).strip()
    try:
        salt_b64, token = raw.split(b".", 1)
        plain = fernet_for(getpass.getpass("Passphrase: "), base64.b64decode(salt_b64)).decrypt(token)
    except UsageError:
        raise
    except Exception:
        raise UsageError("Decryption failed (wrong passphrase or corrupted data).")
    p = Path(a.strip().strip("'\""))
    if p.is_file():
        dst = p.with_suffix("") if p.suffix == ".enc" else Path(str(p) + ".dec")
        dst.write_bytes(plain)
        good(f"wrote {dst}")
    else:
        out(plain.decode("utf-8", "replace"))


# ---- auth ----------------------------------------------------------------------
@command("key", group="auth", usage="/key [show|set|rm]")
def h_key(app, a):
    """Show (masked), set or remove the stored API key."""
    if a in ("set", "rm"):
        return h_login(app, "") if a == "set" else h_logout(app, "")
    key, src = resolve_key(app.cfg)
    out(f"{mask(key) if src != 'zero-auth default' else '(zero-auth default token)'}  source: {src}")


@command("token", group="auth", usage="/token TEXT|FILE")
def h_token(app, a):
    """Estimate how many tokens some text or a file would use."""
    out(f"~{est_tokens(data_arg(a).decode('utf-8', 'replace'))} tokens (heuristic)")


@command("auth", group="auth")
def h_auth(app, a):
    """Test authentication against the endpoint."""
    key, src = resolve_key(app.cfg)
    try:
        app.client.get("models")
        good(f"authenticated OK via {src}")
    except APIError as e:
        bad(str(e))


@command("login", group="auth")
def h_login(app, a):
    """Store an API key in your config (input hidden)."""
    k = getpass.getpass("API key (input hidden): ").strip()
    if not k:
        return warn("No key entered.")
    app.cfg["api_key"] = k
    save_config(app.cfg)
    good("API key saved to config (file mode 600)")


@command("logout", group="auth")
def h_logout(app, a):
    """Remove the stored API key."""
    app.cfg["api_key"] = ""
    save_config(app.cfg)
    good("API key removed from config")


@command("whoami", group="auth")
def h_whoami(app, a):
    """Show the local user, host and active endpoint/auth source."""
    _, src = resolve_key(app.cfg)
    out(f"{getpass.getuser()}@{socket.gethostname()} → {app.cfg['base_url']} · {app.cfg['model']} · auth: {src}")


@command("env", group="auth")
def h_env(app, a):
    """Show relevant environment variables (secrets masked)."""
    for k in sorted(os.environ):
        if k.startswith(("PROCODE_", "GEMINI_", "GOOGLE_API", "EDITOR", "VISUAL", "NO_COLOR", "HTTP_PROXY", "HTTPS_PROXY")):
            v = os.environ[k]
            out(f"{k}={mask(v) if re.search('KEY|TOKEN|SECRET', k) else v}")


@command("set", group="auth", usage="/set KEY VALUE")
def h_set(app, a):
    """Set a configuration value (JSON-typed)."""
    p = a.split(None, 1)
    if len(p) != 2 or p[0] not in DEFAULTS or p[0] in ("hooks", "aliases"):
        raise UsageError("Usage: /set KEY VALUE  (keys: " + ", ".join(k for k in DEFAULTS if k not in ("hooks", "aliases")) + ")")
    try:
        val = json.loads(p[1])
    except ValueError:
        val = p[1]
    app.cfg[p[0]] = val
    save_config(app.cfg)
    apply_ui(app.cfg)
    app.think = app.cfg["thinking"]
    good(f"{p[0]} = {mask(str(val)) if p[0] == 'api_key' else val}")


@command("unset", group="auth", usage="/unset KEY")
def h_unset(app, a):
    """Reset a configuration value to its default."""
    k = a.strip()
    if k not in DEFAULTS:
        raise UsageError("Unknown key.")
    app.cfg[k] = json.loads(json.dumps(DEFAULTS[k]))
    save_config(app.cfg)
    good(f"{k} reset")


@command("alias", group="auth", usage="/alias [NAME = TEXT | -d NAME]")
def h_alias(app, a):
    """Define shortcuts: /alias rv = /review src/app.py"""
    al = app.cfg.setdefault("aliases", {})
    if a.startswith("-d "):
        al.pop(a[3:].strip(), None)
        save_config(app.cfg)
        return good("alias removed")
    if "=" in a:
        n, _, v = a.partition("=")
        al[n.strip().lstrip("/")] = v.strip()
        save_config(app.cfg)
        return good(f"alias {n.strip()} defined")
    out("\n".join(f"  {k} = {v}" for k, v in al.items()) or "(no aliases)")


# ---- shells / interpreters -------------------------------------------------------
SAFE_FUNCS = {n: getattr(math, n) for n in ("sqrt", "sin", "cos", "tan", "log", "log2", "log10", "exp", "floor", "ceil",
                                           "factorial", "gcd", "radians", "degrees", "atan", "asin", "acos")}
SAFE_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max, "pow": pow})
SAFE_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}
BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
          ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in BINOPS:
        l, r = safe_eval(node.left), safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(r) > 1000:
            raise UsageError("Exponent too large.")
        return BINOPS[type(node.op)](l, r)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return -safe_eval(node.operand) if isinstance(node.op, ast.USub) else safe_eval(node.operand)
    if isinstance(node, ast.Name) and node.id in SAFE_NAMES:
        return SAFE_NAMES[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCS and not node.keywords:
        return SAFE_FUNCS[node.func.id](*[safe_eval(x) for x in node.args])
    raise UsageError("Unsupported expression (arithmetic and math functions only).")


@command("eval", group="shell", usage="/eval EXPRESSION")
def h_eval(app, a):
    """Safely evaluate an arithmetic expression (e.g. sqrt(2)*10)."""
    try:
        out(safe_eval(ast.parse(a.strip(), mode="eval")))
    except (SyntaxError, ZeroDivisionError, ValueError, OverflowError) as e:
        raise UsageError(f"Cannot evaluate: {e}")


@command("exec", group="shell", usage="/exec COMMAND [args]")
def h_exec(app, a):
    """Run a program directly (no shell interpretation)."""
    args = split_args(a)
    if not args:
        raise UsageError("Usage: /exec COMMAND [args]")
    run_proc(args)


@command("shell", group="shell", usage="/shell [command line]")
def h_shell(app, a):
    """Run a command line through your shell, or open an interactive shell."""
    sh = os.environ.get("SHELL") or os.environ.get("COMSPEC") or "/bin/sh"
    if a.strip():
        tool_line(a.strip())
        return subprocess.call(a.strip(), shell=True) and None
    note("Entering a subshell; type 'exit' to return.")
    subprocess.call([sh])


def interp(name: str, flag: str):
    def h(app, a):
        if a.strip():
            return run_proc([name, flag, a.strip()])
        return run_proc([name])
    h.__doc__ = f"Run code with {name} (or open an interactive {name} session)."
    return h


for _n, _fl in (("bash", "-c"), ("sh", "-c"), ("zsh", "-c"), ("fish", "-c"), ("node", "-e"), ("ruby", "-e"), ("perl", "-e")):
    command(_n, group="shell", usage=f"/{_n} [code]")(interp(_n, _fl))


@command("python", group="shell", usage="/python [code]")
def h_python(app, a):
    """Run Python code with this interpreter (or open a Python REPL)."""
    run_proc([sys.executable, "-c", a.strip()] if a.strip() else [sys.executable])


# ---- help & info -------------------------------------------------------------------
GROUP_TITLES = {"session": "Session & control", "ui": "Interface", "ai": "AI & agents", "files": "Files & text",
                "git": "Git", "dev": "Dev workflow", "net": "Network", "archive": "Archives, hashes & crypto",
                "auth": "Auth & config", "shell": "Shells & interpreters", "info": "Help & info", "misc": "Misc"}


@command("help", "?", group="info", usage="/help [command]")
def h_help(app, a):
    """List commands or show help for one."""
    n = a.strip().lstrip("/")
    if n:
        cmd = COMMANDS.get(n)
        if not cmd:
            raise UsageError(f"Unknown command '{n}'.")
        return out(f"{c(cmd.usage, 'accent', True)}\n  {cmd.help}" + (f"\n  aliases: {', '.join('/' + x for x in cmd.aliases)}" if cmd.aliases else ""))
    seen = set()
    for grp, title in GROUP_TITLES.items():
        cmds = [x for x in CANON if x.group == grp and x.name not in seen]
        if not cmds:
            continue
        out(c(title, "accent", True))
        line = "  " + "  ".join(f"/{x.name}" for x in sorted(cmds, key=lambda z: z.name))
        out(textwrap_wrap(line))
        seen.update(x.name for x in cmds)
    out(c(f"\n{len(COMMANDS)} commands. Tips: @file attaches a file · !cmd runs a shell command · \"\"\" starts a multi-line prompt · "
          "/help NAME for details", "muted"))


def textwrap_wrap(s: str) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(s, width=min(term_width(), 110), subsequent_indent="  "))


@command("man", group="info", usage="/man COMMAND")
def h_man(app, a):
    """Detailed manual entry for a command."""
    h_help(app, a)
    if a.strip():
        cmd = COMMANDS.get(a.strip().lstrip("/"))
        if cmd:
            out(c(f"  group: {cmd.group}", "muted"))


@command("docs", group="info", usage="/docs [open]")
def h_docs(app, a):
    """Show the documentation URL (or open it)."""
    out(HOMEPAGE)
    if a == "open":
        webbrowser.open(HOMEPAGE)


@command("faq", group="info")
def h_faq(app, a):
    """Frequently asked questions."""
    out(c("Do I need an API key?", "accent", True) + "\n  The CLI starts with zero-config defaults; Google's endpoint still needs a "
        "valid key. Set GEMINI_API_KEY or use /login.\n"
        + c("Where is my data stored?", "accent", True) + f"\n  Config: {CONFIG_FILE}\n  Sessions/cache/logs: {DATA_DIR}\n"
        + c("How do I pipe input?", "accent", True) + "\n  cat file.py | procode \"refactor this\"\n"
        + c("How do I write the code the model produces?", "accent", True) + "\n  procode --write ... or /write on")


@command("about", group="info")
def h_about(app, a):
    """About Pro Code CLI."""
    print_banner(app)
    out(f"{APP_NAME} {__version__} · stdlib-only Python CLI for OpenAI-compatible chat endpoints.")


@command("license", group="info")
def h_license(app, a):
    """License information."""
    out("Pro Code CLI is distributed under the MIT License. Replace this notice with the full text in your LICENSE file.")


@command("credits", group="info")
def h_credits(app, a):
    """Credits."""
    out("Built with the Python standard library. Model access via your configured OpenAI-compatible provider.")


@command("feedback", group="info", usage="/feedback TEXT")
def h_feedback(app, a):
    """Save feedback locally (nothing is sent anywhere)."""
    if not a.strip():
        raise UsageError("Usage: /feedback TEXT")
    f = LOGS_DIR / "feedback.log"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now().isoformat(timespec='seconds')} {sanitize(a)[0]}\n")
    good(f"saved to {f}. Share it at {HOMEPAGE}")


@command("report", group="info")
def h_report(app, a):
    """Write a sanitized diagnostics report you can attach to a bug report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"{APP_NAME} {__version__}", f"python {platform.python_version()} on {platform.platform()}",
             f"model {app.cfg['model']} endpoint {app.cfg['base_url']} auth {resolve_key(app.cfg)[1]}",
             "config: " + json.dumps(dict(app.cfg, api_key=mask(app.cfg.get('api_key', ''))), sort_keys=True), "--- log tail ---"]
    if LOG_FILE.exists():
        lines += LOG_FILE.read_text("utf-8", "replace").splitlines()[-100:]
    p = REPORTS_DIR / f"report-{new_name()}.txt"
    p.write_text(sanitize("\n".join(lines))[0], "utf-8")
    good(f"report written to {p}")


@command("issue", group="info")
def h_issue(app, a):
    """Print a bug-report template."""
    out(f"Open an issue at {HOMEPAGE}/issues with:\n  version: {__version__}\n  python: {platform.python_version()}\n"
        "  steps to reproduce:\n  expected / actual:\n  attach: output of /report")


@command("support", group="info")
def h_support(app, a):
    """Where to get help."""
    out(f"Docs and issue tracker: {HOMEPAGE}")


@command("donate", "sponsor", group="info")
def h_donate(app, a):
    """Support the project."""
    out(f"Thanks for considering it! Sponsorship links live at {HOMEPAGE}")


@command("contact", group="info")
def h_contact(app, a):
    """Contact the maintainers."""
    out(f"Reach the maintainers via {HOMEPAGE}")


@command("echo", "print", group="misc", usage="/echo TEXT")
def h_echo(app, a):
    """Print text."""
    out(a)


@command("date", group="misc", usage="/date [strftime-format]")
def h_date(app, a):
    """Print the date."""
    out(datetime.now().strftime(a.strip() or "%A, %Y-%m-%d"))


@command("time", group="misc")
def h_time(app, a):
    """Print the local time."""
    out(datetime.now().astimezone().strftime("%H:%M:%S %Z"))


@command("sleep", "wait", group="misc", usage="/sleep [seconds]")
def h_sleep(app, a):
    """Pause for N seconds (default 1)."""
    try:
        n = float(a.strip() or 1)
    except ValueError:
        raise UsageError("Usage: /sleep SECONDS")
    with Spinner(f"waiting {n:g}s"):
        time.sleep(min(n, 3600))


# --------------------------------------------------------------------------- #
# Dispatcher, REPL, main
# --------------------------------------------------------------------------- #
def run_command(app: App, line: str):
    name, _, rest = line[1:].partition(" ")
    name = name.lower()
    al = app.cfg.get("aliases", {})
    if name in al and name not in COMMANDS:
        return handle_line(app, al[name] + (" " + rest if rest else ""))
    cmd = COMMANDS.get(name)
    if not cmd:
        close = difflib.get_close_matches(name, list(COMMANDS), 3, 0.6)
        raise UsageError(f"Unknown command /{name}." + (f" Did you mean {', '.join('/' + x for x in close)}?" if close else " Try /help."))
    return cmd.fn(app, rest.strip())


def handle_line(app: App, line: str) -> bool:
    line = line.strip()
    if not line:
        return True
    try:
        if line.startswith("!"):
            subprocess.call(line[1:], shell=True)
            return True
        res = run_command(app, line) if line.startswith("/") else Send(line)
        if res == "exit":
            return False
        if isinstance(res, Send):
            app.send(res.text, **res.kw)
    except UsageError as e:
        bad(str(e))
    except APIError as e:
        bad(str(e))
        log(f"APIError: {e}")
    except KeyboardInterrupt:
        warn("Interrupted.")
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile) as e:
        bad(f"{type(e).__name__}: {e}")
        if app.cfg.get("debug"):
            traceback.print_exc()
    return True


def rl_wrap(s: str) -> str:
    return re.sub(r"(\033\[[0-9;]*m)", "\001\\1\002", s) if readline and UI.color else s


def status_line(app: App) -> str:
    if UI.quiet or UI.silent or UI.layout == "plain":
        return ""
    ctx = sum(est_tokens(m["content"]) for m in app.session.messages)
    sep = c(f" {g('bar')} ", "muted")
    parts = [c(f" {app.cfg['model']} ", "accent", True), c(f"{g('dot')} ready", "ok"),
             c(f"{len(app.session.messages)} msgs", "muted"), c(f"~{human(ctx)} ctx", "muted"), c(f"think:{app.think}", "muted")]
    if app.session.totals["cost"]:
        parts.append(c(f"${app.session.totals['cost']:.3f}", "muted"))
    if app.pending:
        parts.append(c(f"{len(app.pending)} attached", "warn"))
    bar = sep.join(parts)
    if UI.layout == "wide":
        return c(g("h") * min(term_width(), 100), "muted", dim=True) + "\n" + bar
    return bar


def setup_readline() -> None:
    if not readline:
        return
    hist = DATA_DIR / "history"
    try:
        readline.read_history_file(hist)
    except (OSError, FileNotFoundError):
        pass
    import atexit
    atexit.register(lambda: (DATA_DIR.mkdir(parents=True, exist_ok=True), readline.write_history_file(hist)))

    def completer(text: str, state: int):
        buf = readline.get_line_buffer()
        if buf.startswith("/") and " " not in buf:
            opts = sorted("/" + n for n in COMMANDS if ("/" + n).startswith(text))
        else:
            opts = [p + ("/" if os.path.isdir(p) else "") for p in glob.glob(os.path.expanduser(text.lstrip("@")) + "*")]
        return opts[state] if state < len(opts) else None
    readline.set_completer(completer)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("bind ^I rl_complete" if "libedit" in (readline.__doc__ or "") else "tab: complete")


def repl(app: App) -> int:
    setup_readline()
    if app.cfg.get("banner"):
        print_banner(app)
    app.run_hook("on_start")
    prompt = rl_wrap(c("procode", "accent", True) + c(f" {g('arrow')} ", "accent2", True))
    while True:
        sl = status_line(app)
        if sl:
            out(sl)
        try:
            line = input(prompt)
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            note("(Ctrl-D or /exit to quit)")
            continue
        if line.strip() == '"""':
            buf = []
            try:
                while True:
                    ln = input(c("… ", "muted"))
                    if ln.strip() == '"""':
                        break
                    buf.append(ln)
            except EOFError:
                pass
            line = "\n".join(buf)
        else:
            while line.endswith("\\"):
                try:
                    line = line[:-1] + "\n" + input(c("… ", "muted"))
                except EOFError:
                    break
        if not handle_line(app, line):
            break
    try:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        if app.session.messages:
            (SESSIONS_DIR / "last.json").write_text(json.dumps(app.session.to_dict(app.cfg["model"]), indent=2), "utf-8")
    except OSError:
        pass
    app.run_hook("on_exit")
    note("Goodbye.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="procode", description="Pro Code CLI: terminal AI coding companion.",
                                epilog="Examples:\n  procode \"hello\"\n  cat app.py | procode \"refactor this\"\n"
                                       "  procode --agents security,review \"audit @app.py\"\n  procode /doctor",
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prompt", nargs="*", help="prompt text or a /slash command")
    p.add_argument("-m", "--model")
    p.add_argument("--base-url")
    p.add_argument("-t", "--thinking", choices=list(THINK_LEVELS))
    p.add_argument("--temperature", type=float)
    p.add_argument("--max-tokens", type=int)
    p.add_argument("--system")
    p.add_argument("--template", help="apply a prompt template (use with a file path or text)")
    p.add_argument("--agents", help="comma-separated subagent roles to run in parallel")
    p.add_argument("--plan", action="store_true", help="decompose the prompt into a task graph and execute it")
    p.add_argument("--gen-tests", metavar="FILE", help="generate a test suite for FILE")
    p.add_argument("--commit", action="store_true", help="generate a conventional commit message from staged changes")
    p.add_argument("--index", action="store_true", help="include relevant local files as context")
    p.add_argument("--write", action="store_true", help="extract code blocks and offer to write them to files")
    p.add_argument("--edit", action="store_true", help="compose the prompt in an editor first")
    p.add_argument("--resume", metavar="NAME", help="resume a saved session (e.g. last)")
    p.add_argument("--cache", action="store_true")
    p.add_argument("--no-stream", action="store_true")
    p.add_argument("--no-sanitize", action="store_true")
    p.add_argument("--theme", choices=list(THEMES))
    p.add_argument("--raw", action="store_true", help="plain output: no colors or chrome")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("-y", "--yes", action="store_true", help="auto-confirm file writes")
    p.add_argument("--doctor", action="store_true")
    p.add_argument("--debug", action="store_true")
    p.add_argument("-V", "--version", action="store_true")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        out(f"{APP_NAME} {__version__}")
        return 0
    cfg = load_config()
    for k, v in (("model", args.model), ("base_url", args.base_url), ("thinking", args.thinking),
                 ("temperature", args.temperature), ("max_tokens", args.max_tokens), ("theme", args.theme)):
        if v is not None:
            cfg[k] = v
    cfg["stream"] = cfg["stream"] and not args.no_stream
    cfg["sanitize"] = cfg["sanitize"] and not args.no_sanitize
    cfg["cache"] = cfg["cache"] or args.cache
    cfg["debug"] = cfg["debug"] or args.debug
    cfg["quiet"] = cfg["quiet"] or args.quiet
    apply_ui(cfg)
    if args.raw:
        UI.color = False
    if not sys.stdout.isatty():
        UI.color, UI.quiet = False, True
    FLAGS["yes"] = args.yes
    app = App(cfg)
    app.think = cfg["thinking"]
    app.index_on = app.index_on or args.index
    app.extract_mode = app.extract_mode or args.write
    if args.system:
        app.session.system = args.system
    if args.resume:
        try:
            h_load(app, args.resume)
        except (UsageError, ValueError) as e:
            bad(str(e))
            return 1
    stdin_text = ""
    if not sys.stdin.isatty():
        try:
            stdin_text = sys.stdin.read()
        except OSError:
            stdin_text = ""
    prompt = " ".join(args.prompt).strip()
    try:
        if args.doctor:
            h_doctor(app, "")
            return 0
        if args.commit:
            h_commit(app, "")
            return 0
        if args.gen_tests:
            res = h_gentest(app, args.gen_tests)
            return 0 if app.send(res.text) is not None else 1
        if args.template:
            inp = (prompt + "\n\n" if prompt else "") + (f"```\n{stdin_text}\n```" if stdin_text else "")
            res = template_send(app, args.template, prompt if Path(prompt).is_file() else "", inp if not Path(prompt).is_file() else "")
            return 0 if app.send(res.text) is not None else 1
        if stdin_text and not stdin_text.endswith("\n"):
            stdin_text += "\n"
        full = prompt
        if stdin_text:
            full = f"{prompt}\n\n```\n{stdin_text.rstrip()}\n```" if prompt else stdin_text.strip()
        if args.edit:
            full = edit_text(full)
        if full:
            if full.startswith("/") and not stdin_text:
                return 0 if handle_line(app, full) is not None else 1
            if args.agents:
                roles = [ROLE_ALIASES.get(r.strip(), r.strip()) for r in args.agents.split(",")]
                unknown = [r for r in roles if r not in ROLES]
                if unknown:
                    bad(f"Unknown agent role(s): {', '.join(unknown)}. Available: {', '.join(ROLES)}")
                    return 1
                return 0 if run_agent_task(app, roles, full) is not None else 1
            if args.plan:
                res = h_plan(app, full)
                return 0 if app.send(res.text) is not None else 1
            app.run_hook("on_start")
            ok = app.send(full) is not None
            app.run_hook("on_exit")
            return 0 if ok else 1
        if not sys.stdin.isatty():
            bad("No prompt provided.")
            return 1
        return repl(app)
    except UsageError as e:
        bad(str(e))
        return 1
    except APIError as e:
        bad(str(e))
        return 1
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == "__main__":
    sys.exit(main())
