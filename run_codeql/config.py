"""Repository-level rcql configuration loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from run_codeql.logging_utils import err

CONFIG_FILE_NAME = ".rcql.json"


@dataclass(frozen=True)
class RepoConfig:
    """Normalized rcql repo configuration."""

    files: list[str] | None = None
    exclude_files: list[str] | None = None
    rules: list[str] | None = None
    langs: list[str] | None = None
    include_third_party: bool = False


def _normalize_str_list(value: object, field_name: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"'{field_name}' must be a list of strings")
    normalized = [item.strip() for item in value if item.strip()]
    return normalized or None


def _parse_config(path: Path) -> RepoConfig:
    """Parse and validate a config file at *path*."""
    if not path.exists():
        return RepoConfig()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        err(f"Invalid {CONFIG_FILE_NAME}: {exc}")
        raise SystemExit(2) from exc

    if not isinstance(raw, dict):
        err(f"Invalid {CONFIG_FILE_NAME}: top-level value must be an object")
        raise SystemExit(2)

    try:
        files = _normalize_str_list(raw.get("files"), "files")
        exclude_files = _normalize_str_list(raw.get("exclude_files"), "exclude_files")
        rules = _normalize_str_list(raw.get("rules"), "rules")
        langs = _normalize_str_list(raw.get("langs"), "langs")
    except ValueError as exc:
        err(f"Invalid {CONFIG_FILE_NAME}: {exc}")
        raise SystemExit(2) from exc

    include_third_party = raw.get("include_third_party", False)
    if not isinstance(include_third_party, bool):
        err(f"Invalid {CONFIG_FILE_NAME}: 'include_third_party' must be a boolean")
        raise SystemExit(2)

    return RepoConfig(
        files=files,
        exclude_files=exclude_files,
        rules=rules,
        langs=langs,
        include_third_party=include_third_party,
    )


def load_repo_config(repo_root: Path, filename: str = CONFIG_FILE_NAME) -> RepoConfig:
    """Load and validate config file from *repo_root* when present."""
    if not filename:
        return RepoConfig()
    return _parse_config(repo_root / filename)
