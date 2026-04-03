"""Language detection and CodeQL scan orchestration helpers."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from run_codeql.logging_utils import log
from run_codeql.settings import (
    DEFAULT_SUITE_PROFILE,
    EXT_TO_LANG,
    IGNORE_DIRS,
    LANG_CONFIG,
    PACKAGES_DIR,
    SUPPORTED_SUITE_PROFILES,
    TOOLS_DIR,
)


def detect_langs(repo_root: Path) -> list[str]:
    """Scan the repo for source files and return the CodeQL languages to run."""
    found: set[str] = set()
    for _, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            lang = EXT_TO_LANG.get(Path(fname).suffix)
            if lang:
                found.add(lang)

    workflows = repo_root / ".github" / "workflows"
    if workflows.is_dir() and (any(workflows.glob("*.yml")) or any(workflows.glob("*.yaml"))):
        found.add("actions")

    langs = sorted(found)
    log(f"Auto-detected languages: {', '.join(langs) if langs else '(none)'}")
    return langs


def ensure_pack(pack_name: str, codeql: Path, quiet: bool) -> None:
    """Download a CodeQL query pack if it is not already in the local cache."""
    pack_dir = PACKAGES_DIR / pack_name
    if pack_dir.exists():
        return
    log(f"Downloading missing pack: {pack_name}")
    subprocess.run(
        [str(codeql), "pack", "download", pack_name],
        check=True,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )


def _sanitize_codescanning_config_for_database_create(
    config_file: Path,
    work_dir: Path,
    lang: str,
) -> Path:
    """Return a config path safe for `codeql database create`.

    GitHub-style code scanning configs commonly include top-level query selectors
    (`queries`, `packs`, `query-filters`). Those selectors are useful for code
    scanning workflows but can break local database creation in some environments.
    For database creation we only need extraction scope controls, so this helper
    strips query selection sections and preserves the remaining config.
    """
    raw = config_file.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    stripped_keys = {"queries", "packs", "query-filters"}
    output_lines: list[str] = []
    changed = False
    skip_mode = False

    top_level_key_pattern = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*#.*)?$")
    for line in lines:
        top_level_match = top_level_key_pattern.match(line.rstrip("\n"))
        if top_level_match and (len(line) - len(line.lstrip(" "))) == 0:
            key = top_level_match.group(1)
            if key in stripped_keys:
                skip_mode = True
                changed = True
                continue
            skip_mode = False
        if skip_mode:
            changed = True
            continue
        output_lines.append(line)

    if not changed:
        return config_file
    sanitized_path = work_dir / f"codescanning-config-dbcreate-{lang}.yml"
    sanitized_path.write_text("".join(output_lines), encoding="utf-8")
    return sanitized_path


class ScanConfigurationError(ValueError):
    """Raised when repository scan configuration is invalid for local rcql use."""


def _extract_query_uses_selectors(config_file: Path) -> list[str]:
    """Extract top-level `queries: - uses: ...` selectors from a config file."""
    selectors: list[str] = []
    in_queries_section = False
    uses_pattern = re.compile(r"^\s*-\s*uses:\s*(.*?)\s*(?:#.*)?$")

    for raw_line in config_file.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if indent == 0:
            if stripped.startswith("queries:"):
                in_queries_section = True
                continue
            in_queries_section = False
        if not in_queries_section:
            continue
        match = uses_pattern.match(raw_line)
        if match:
            selector = match.group(1).strip().strip("'\"")
            if selector:
                selectors.append(selector)
    return selectors


def _resolve_suite_for_lang(suite_lang: str, config_file: Path) -> str:
    """Resolve CodeQL suite for a language from repo config or defaults."""
    profile = DEFAULT_SUITE_PROFILE
    if config_file.is_file():
        selectors = _extract_query_uses_selectors(config_file)
        unique_selectors = sorted(set(selectors))
        if len(unique_selectors) > 1:
            raise ScanConfigurationError(
                "Unsupported codeql-config: multiple 'queries uses' selectors are not supported "
                f"for local rcql runs: {', '.join(unique_selectors)}"
            )
        if unique_selectors:
            profile = unique_selectors[0]
    if profile in SUPPORTED_SUITE_PROFILES:
        return f"codeql/{suite_lang}-queries:codeql-suites/{suite_lang}-{profile}.qls"
    raise ScanConfigurationError(
        "Unsupported codeql-config query selector for local rcql: "
        f"'{profile}'. Supported selectors: {', '.join(SUPPORTED_SUITE_PROFILES)}."
    )


def _resolve_suite_for_mode(
    suite_lang: str,
    mode: str,
    config_file: Path,
) -> str:
    """Resolve CodeQL suite by scan mode."""
    if mode == "standard-findings":
        profile = "code-quality"
        return f"codeql/{suite_lang}-queries:codeql-suites/{suite_lang}-{profile}.qls"
    return _resolve_suite_for_lang(suite_lang=suite_lang, config_file=config_file)


def cleanup_reports(report_dir: Path, keep: bool, langs: list[str] | None = None) -> None:
    """Clean reports before scanning based on target language scope."""
    if keep:
        return
    report_dir.mkdir(parents=True, exist_ok=True)
    if langs is None:
        if report_dir.exists():
            shutil.rmtree(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        return
    for lang in set(langs):
        for target in report_dir.glob(f"{lang}-*.sarif"):
            target.unlink(missing_ok=True)


def _profile_from_suite(suite: str) -> str:
    """Extract the profile suffix from a resolved suite string."""
    for profile in SUPPORTED_SUITE_PROFILES:
        if suite.endswith(f"-{profile}.qls"):
            return profile
    raise ScanConfigurationError(
        "Could not infer suite profile from resolved suite "
        f"'{suite}'. Expected one of: {', '.join(SUPPORTED_SUITE_PROFILES)}."
    )


def cleanup_db(work_dir: Path, lang: str, keep: bool) -> None:
    """Remove an existing language DB unless reusing previous DBs."""
    if keep:
        return
    db_dir = work_dir / f"db-{lang}"
    if db_dir.exists():
        shutil.rmtree(db_dir)


def run_lang(
    lang: str,
    codeql: Path,
    keep_db: bool,
    repo_root: Path,
    work_dir: Path,
    report_dir: Path,
    config_file: Path,
    mode: str = "default",
    threads: int = 0,
    quiet: bool = False,
) -> Path:
    """Run DB creation and analysis for one language and return SARIF path."""
    cfg = LANG_CONFIG.get(lang, {})
    lang_arg = cfg.get("lang_arg", lang)
    suite = _resolve_suite_for_mode(suite_lang=lang_arg, mode=mode, config_file=config_file)
    profile = _profile_from_suite(suite)
    build_command = cfg.get("build_command")

    db_dir = work_dir / f"db-{lang}"
    sarif = report_dir / f"{lang}-{profile}.sarif"

    cleanup_db(work_dir, lang, keep_db)

    log(f"Creating DB for {lang}")
    create_cmd = [
        str(codeql),
        "database",
        "create",
        str(db_dir),
        f"--language={lang_arg}",
        f"--source-root={repo_root}",
        "--overwrite",
        f"--threads={threads}",
        "--no-run-unnecessary-builds",
    ]
    if mode != "standard-findings" and config_file.is_file():
        create_config = _sanitize_codescanning_config_for_database_create(
            config_file=config_file,
            work_dir=work_dir,
            lang=lang,
        )
        create_cmd += ["--codescanning-config", str(create_config)]
    if build_command:
        create_cmd += ["--command", build_command]

    subprocess.run(
        create_cmd,
        check=True,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )

    pack_name = suite.split(":")[0]
    ensure_pack(pack_name, codeql, quiet=quiet)

    log(f"Analyzing {lang}")
    analyze_cmd = [
        str(codeql),
        "database",
        "analyze",
        str(db_dir),
        suite,
        "--format=sarif-latest",
        f"--output={sarif}",
        f"--threads={threads}",
        "--ram=6144",
        f"--search-path={TOOLS_DIR / 'codeql'}",
    ]
    subprocess.run(
        analyze_cmd,
        check=True,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )

    return sarif
