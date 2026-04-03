"""Shared configuration and defaults for run_codeql."""

import os
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    """Read a positive integer from environment with safe fallback."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


CODEQL_VERSION = "2.24.2"
TOOLS_DIR = Path.home() / ".codeql-tools"
CODEQL_BIN = TOOLS_DIR / "codeql" / "codeql"
PACKAGES_DIR = Path.home() / ".codeql" / "packages"
DOWNLOAD_TIMEOUT_SECONDS = _int_env("RCQL_DOWNLOAD_TIMEOUT_SECONDS", 60)
DOWNLOAD_RETRY_ATTEMPTS = _int_env("RCQL_DOWNLOAD_RETRY_ATTEMPTS", 3)
DOWNLOAD_RETRY_SLEEP_SECONDS = _int_env("RCQL_DOWNLOAD_RETRY_SLEEP_SECONDS", 2)

# Directories to skip when scanning for source files.
IGNORE_DIRS = {
    ".git",
    ".codeql",
    ".venv",
    "venv",
    "env",
    ".env",
    "node_modules",
    "vendor",
    "target",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
}

# Maps file extensions to CodeQL language names.
EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".rs": "rust",
    ".js": "javascript-typescript",
    ".jsx": "javascript-typescript",
    ".ts": "javascript-typescript",
    ".tsx": "javascript-typescript",
    ".go": "go",
    ".java": "java",
    ".kt": "java",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "cpp",
    ".rb": "ruby",
    ".swift": "swift",
}

LANG_CONFIG = {
    "javascript-typescript": {
        "lang_arg": "javascript",
    },
    "rust": {
        "build_command": "cd rust && cargo build --workspace --all-targets --locked",
    },
    "actions": {},
}

DEFAULT_SUITE_PROFILE = "security-and-quality"

# Default SARIF artifact URI excludes for summary output. These reduce triage
# noise from third-party and generated paths while preserving an opt-in path
# to include them via CLI flags.
DEFAULT_SARIF_EXCLUDE_PATTERNS: list[str] = [
    "**/node_modules/**",
    "**/vendor/**",
    "**/dist/**",
    "**/build/**",
    "**/out/**",
    "**/coverage/**",
    "**/.next/**",
    "**/.nuxt/**",
    "**/.svelte-kit/**",
    ".codeql/**",
    "**/.codeql/**",
]
