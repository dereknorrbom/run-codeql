"""Run CodeQL code-quality analysis locally (mirrors GitHub "Code Quality" check)."""

import argparse
import concurrent.futures
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

CODEQL_VERSION = "2.24.2"
TOOLS_DIR = Path.home() / ".codeql-tools"
CODEQL_BIN = TOOLS_DIR / "codeql" / "codeql"
PACKAGES_DIR = Path.home() / ".codeql" / "packages"

# Directories to skip when scanning for source files
IGNORE_DIRS = {
    ".git", ".codeql", ".venv", "venv", "env", ".env",
    "node_modules", "vendor", "target", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
}

# Maps file extensions to CodeQL language names
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
        "suite": "codeql/javascript-queries:codeql-suites/javascript-code-quality.qls",
    },
    "rust": {
        "suite": "codeql/rust-queries:codeql-suites/rust-security-and-quality.qls",
        "build_command": "cd rust && cargo build --workspace --all-targets --locked",
    },
    "actions": {
        "suite": "codeql/actions-queries:codeql-suites/actions-security-and-quality.qls",
    },
}


_quiet = False


def log(msg: str) -> None:
    if not _quiet:
        ts = time.strftime("%H:%M:%S")
        print(f"[codeql-local {ts}] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[codeql-local][error] {msg}", file=sys.stderr, flush=True)


def detect_langs(repo_root: Path) -> list[str]:
    """Scan the repo for source files and return the CodeQL languages to run."""
    found: set[str] = set()
    for _, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fname in filenames:
            lang = EXT_TO_LANG.get(Path(fname).suffix)
            if lang:
                found.add(lang)

    # Always include actions if there are workflow files
    workflows = repo_root / ".github" / "workflows"
    if workflows.is_dir() and any(workflows.glob("*.yml")):
        found.add("actions")

    langs = sorted(found)
    log(f"Auto-detected languages: {', '.join(langs) if langs else '(none)'}")
    return langs


def fetch_codeql() -> Path:
    which = shutil.which("codeql")
    if which:
        log(f"Using system CodeQL: {which}")
        return Path(which)

    if CODEQL_BIN.is_file() and os.access(CODEQL_BIN, os.X_OK):
        log(f"Using downloaded CodeQL: {CODEQL_BIN}")
        return CODEQL_BIN

    system = platform.system()
    if system == "Linux":
        plat = "linux64"
    elif system == "Darwin":
        plat = "osx64"
    else:
        err(f"Unsupported platform for CodeQL auto-download: {system}")
        sys.exit(1)

    log(f"Downloading CodeQL CLI {CODEQL_VERSION} to {TOOLS_DIR}")
    archive_name = f"codeql-bundle-{plat}.tar.gz"
    url = (
        f"https://github.com/github/codeql-action/releases/download/"
        f"codeql-bundle-v{CODEQL_VERSION}/{archive_name}"
    )
    tmp = TOOLS_DIR / archive_name
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, tmp)
    with tarfile.open(tmp, "r:gz") as tar:
        tar.extractall(TOOLS_DIR)
    tmp.unlink()

    if not (CODEQL_BIN.is_file() and os.access(CODEQL_BIN, os.X_OK)):
        err(f"Downloaded CodeQL bundle missing binary at {CODEQL_BIN}")
        sys.exit(1)

    CODEQL_BIN.chmod(CODEQL_BIN.stat().st_mode | 0o111)
    log(f"Downloaded CodeQL to {CODEQL_BIN}")
    return CODEQL_BIN


def ensure_pack(pack_name: str, codeql: Path) -> None:
    """Download a CodeQL query pack if it is not already in the local cache."""
    pack_dir = PACKAGES_DIR / pack_name
    if pack_dir.exists():
        return
    log(f"Downloading missing pack: {pack_name}")
    subprocess.run(
        [str(codeql), "pack", "download", pack_name],
        check=True,
        stdout=subprocess.DEVNULL if _quiet else None,
        stderr=subprocess.DEVNULL if _quiet else None,
    )


def cleanup_reports(report_dir: Path, keep: bool) -> None:
    if keep:
        return
    if report_dir.exists():
        shutil.rmtree(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)


def cleanup_db(work_dir: Path, lang: str, keep: bool) -> None:
    if keep:
        return
    db_dir = work_dir / f"db-{lang}"
    if db_dir.exists():
        shutil.rmtree(db_dir)


def run_lang(lang: str, codeql: Path, keep_db: bool, repo_root: Path, work_dir: Path, report_dir: Path, config_file: Path, threads: int = 0) -> Path:
    cfg = LANG_CONFIG.get(lang, {})
    lang_arg = cfg.get("lang_arg", lang)
    suite = cfg.get("suite", f"codeql/{lang}-queries:codeql-suites/{lang}-code-quality.qls")
    build_command = cfg.get("build_command")

    db_dir = work_dir / f"db-{lang}"
    sarif = report_dir / f"{lang}-code-quality.sarif"

    cleanup_db(work_dir, lang, keep_db)

    log(f"Creating DB for {lang}")
    create_cmd = [
        str(codeql), "database", "create", str(db_dir),
        f"--language={lang_arg}",
        f"--source-root={repo_root}",
        "--overwrite",
        f"--threads={threads}",
        "--no-run-unnecessary-builds",
    ]
    if config_file.is_file():
        create_cmd += ["--codescanning-config", str(config_file)]
    if build_command:
        create_cmd += ["--command", build_command]

    subprocess.run(
        create_cmd, check=True,
        stdout=subprocess.DEVNULL if _quiet else None,
        stderr=subprocess.DEVNULL if _quiet else None,
    )

    pack_name = suite.split(":")[0]
    ensure_pack(pack_name, codeql)

    log(f"Analyzing {lang}")
    analyze_cmd = [
        str(codeql), "database", "analyze", str(db_dir), suite,
        "--format=sarif-latest",
        f"--output={sarif}",
        f"--threads={threads}",
        "--ram=6144",
        f"--search-path={TOOLS_DIR / 'codeql'}",
    ]
    subprocess.run(
        analyze_cmd, check=True,
        stdout=subprocess.DEVNULL if _quiet else None,
        stderr=subprocess.DEVNULL if _quiet else None,
    )

    return sarif


def summarize_sarif(sarif: Path, lang: str, verbose: bool = False) -> str:
    try:
        data = json.loads(sarif.read_text())
    except Exception as exc:
        return f"  (could not read SARIF: {exc})"

    counts: dict[str, int] = {}
    finding_lines: list[str] = []

    for run in data.get("runs", []):
        rules = {
            r["id"]: r
            for r in run.get("tool", {}).get("driver", {}).get("rules", [])
        }
        for result in run.get("results", []):
            level = result.get("level", "warning")
            counts[level] = counts.get(level, 0) + 1

            if verbose:
                rule_id = result.get("ruleId", "unknown")
                rule = rules.get(rule_id, {})
                short_desc = rule.get("shortDescription", {}).get("text", "")
                message = result.get("message", {}).get("text", "")
                # Strip SARIF markdown link syntax from messages: [text](N) -> text
                message = re.sub(r"\[([^\]]+)\]\(\d+\)", r"\1", message)
                loc = result.get("locations", [{}])[0]
                phys = loc.get("physicalLocation", {})
                uri = phys.get("artifactLocation", {}).get("uri", "")
                line = phys.get("region", {}).get("startLine", "")
                location = f"{uri}:{line}" if line else uri
                finding_lines.append(
                    f"  [{level}] {rule_id}\n"
                    f"    {short_desc}\n"
                    f"    {location}\n"
                    f"    {message}"
                )

    total = sum(counts.values())
    count_lines = [f"  {level}: {counts[level]}" for level in sorted(counts)]
    count_lines.append(f"  Total: {total}")

    if verbose and finding_lines:
        return "\n".join(count_lines) + "\n\n" + "\n\n".join(finding_lines)
    return "\n".join(count_lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run CodeQL code-quality analysis locally (mirrors GitHub 'Code Quality' check)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Outputs:\n"
            "  Databases:  .codeql/db-<lang>/\n"
            "  SARIF:      .codeql/reports/<lang>-code-quality.sarif\n\n"
            "CodeQL CLI is auto-downloaded to ~/.codeql-tools/ if not on PATH.\n"
            "Run from the root of any repository."
        ),
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Comma-separated languages to scan (default: auto-detected from repo contents)",
    )
    parser.add_argument("--keep-db", action="store_true", help="Reuse existing databases instead of recreating")
    parser.add_argument("--keep-reports", action="store_true", help="Do not delete prior SARIF reports before running")
    parser.add_argument("--no-fail", action="store_true", help="Exit 0 even if findings exist")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each finding with rule, location, and message")
    parser.add_argument("--report-only", action="store_true", help="Skip scanning; summarize existing SARIF reports from the last run")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress log output; print only the final summaries (useful for agent/scripted use)")
    args = parser.parse_args()

    global _quiet
    _quiet = args.quiet
    if _quiet:
        print("[codeql-local] running in quiet mode", file=sys.stderr, flush=True)

    repo_root = Path.cwd()
    work_dir = repo_root / ".codeql"
    report_dir = work_dir / "reports"

    if args.report_only:
        filter_langs = {l.strip() for l in args.lang.split(",")} if args.lang else None
        sarif_files = sorted(report_dir.glob("*.sarif"))
        if filter_langs:
            sarif_files = [f for f in sarif_files if f.stem.removesuffix("-code-quality") in filter_langs]
        if not sarif_files:
            err(f"No SARIF files found in {report_dir}. Run without --report-only first.")
            sys.exit(1)
        log("===== Summaries (from previous scan) =====")
        for sarif in sarif_files:
            lang = sarif.stem.removesuffix("-code-quality")
            summary = summarize_sarif(sarif, lang, verbose=args.verbose)
            print(f"[{lang}] SARIF: {sarif}\n{summary}")
        sys.exit(0)

    config_file = repo_root / ".github" / "codeql" / "codeql-config.yml"

    if args.lang:
        langs = [l.strip() for l in args.lang.split(",") if l.strip()]
    else:
        langs = detect_langs(repo_root)

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    gitignore = work_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n")

    codeql = fetch_codeql()
    cleanup_reports(report_dir, args.keep_reports)

    overall_status = 0
    threads_per_lang = max(1, (os.cpu_count() or 1) // len(langs)) if len(langs) > 1 else 0
    log(f"Running {len(langs)} language(s) in parallel with {threads_per_lang} thread(s) each")
    # Order results by original lang list regardless of completion order
    summaries: dict[str, str] = {}

    def scan(lang: str) -> None:
        try:
            sarif = run_lang(lang, codeql, args.keep_db, repo_root, work_dir, report_dir, config_file, threads=threads_per_lang)
            summary = summarize_sarif(sarif, lang, verbose=args.verbose)
            summaries[lang] = f"[{lang}] SARIF: {sarif}\n{summary}"
        except subprocess.CalledProcessError as exc:
            err(f"{lang} failed (exit {exc.returncode})")
            summaries[lang] = f"[{lang}] FAILED (exit {exc.returncode})"

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(scan, lang): lang for lang in langs}
        for future in concurrent.futures.as_completed(futures):
            if future.exception():
                overall_status = 1

    log("===== Summaries =====")
    for lang in langs:
        if lang in summaries:
            print(summaries[lang])

    sys.exit(0 if args.no_fail else overall_status)


if __name__ == "__main__":
    main()
