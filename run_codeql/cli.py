"""CLI entrypoint and orchestration for run_codeql."""

import argparse
import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

from run_codeql.download import fetch_codeql
from run_codeql.logging_utils import configure_logging, err, log
from run_codeql.sarif import build_sarif_summary
from run_codeql.scanner import cleanup_reports, detect_langs, run_lang
from run_codeql.settings import TOOLS_DIR


def main() -> None:
    """CLI main function."""
    parser = argparse.ArgumentParser(
        description="Run CodeQL code-quality analysis locally (mirrors GitHub 'Code Quality' check)",  # noqa: E501
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
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Reuse existing databases instead of recreating",
    )
    parser.add_argument(
        "--keep-reports",
        action="store_true",
        help="Do not delete prior SARIF reports before running",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Exit 0 even if findings or scan errors exist",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print each finding with rule, location, and message",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip scanning; summarize existing SARIF reports from the last run",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress log output; print only the final summaries (useful for agent/scripted use)",
    )
    parser.add_argument(
        "--files",
        default=None,
        help=(
            "Comma-separated file paths (or fnmatch patterns) to restrict findings to. "
            "Paths are matched against the end of the SARIF artifact URI "
            "(e.g. 'src/foo.py' or 'src/*.py')"
        ),
    )
    parser.add_argument(
        "--rule",
        default=None,
        help=(
            "Comma-separated rule IDs (or fnmatch patterns) to restrict findings to "
            "(e.g. 'py/unused-import' or 'py/*')"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Return at most N findings across all files (after --files filtering)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        metavar="N",
        help="Skip the first N findings before applying --limit (for pagination)",
    )
    args = parser.parse_args()

    configure_logging(args.quiet)
    if args.quiet:
        print("[codeql-local] running in quiet mode", file=sys.stderr, flush=True)

    file_patterns = [p.strip() for p in args.files.split(",") if p.strip()] if args.files else None
    rule_patterns = [p.strip() for p in args.rule.split(",") if p.strip()] if args.rule else None

    repo_root = Path.cwd()
    work_dir = repo_root / ".codeql"
    report_dir = work_dir / "reports"

    if args.report_only:
        filter_langs = (
            {lang_name.strip() for lang_name in args.lang.split(",")} if args.lang else None
        )
        sarif_files = sorted(report_dir.glob("*.sarif"))
        if filter_langs:
            sarif_files = [
                f for f in sarif_files if f.stem.removesuffix("-code-quality") in filter_langs
            ]
        if not sarif_files:
            err(f"No SARIF files found in {report_dir}. Run without --report-only first.")
            sys.exit(1)
        log("===== Summaries (from previous scan) =====")
        report_failed = False
        findings_found = False
        for sarif in sarif_files:
            lang = sarif.stem.removesuffix("-code-quality")
            summary = build_sarif_summary(
                sarif,
                verbose=args.verbose,
                files=file_patterns,
                rules=rule_patterns,
                limit=args.limit,
                offset=args.offset,
            )
            findings_found = findings_found or summary.total_findings > 0
            report_failed = report_failed or summary.read_error
            if (file_patterns is None and rule_patterns is None) or summary.matched_findings > 0:
                print(f"[{lang}] SARIF: {sarif}\n{summary.text}")
        should_fail = report_failed or findings_found
        sys.exit(0 if args.no_fail else int(should_fail))

    config_file = repo_root / ".github" / "codeql" / "codeql-config.yml"

    if args.lang:
        langs = [lang_name.strip() for lang_name in args.lang.split(",") if lang_name.strip()]
    else:
        langs = detect_langs(repo_root)
    if not langs:
        err("No languages detected. Use --lang to specify one or add supported source files.")
        sys.exit(1)

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    gitignore = work_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n")

    codeql = fetch_codeql()
    cleanup_reports(report_dir, args.keep_reports, langs=langs if args.lang else None)

    scan_failed = False
    findings_found = False
    threads_per_lang = max(1, (os.cpu_count() or 1) // len(langs)) if len(langs) > 1 else 0
    log(f"Running {len(langs)} language(s) in parallel with {threads_per_lang} thread(s) each")
    summaries: dict[str, tuple[str, int]] = {}  # lang -> (text, matched_findings)

    def scan(lang: str) -> tuple[str, str, int, int, bool]:
        try:
            sarif = run_lang(
                lang,
                codeql,
                args.keep_db,
                repo_root,
                work_dir,
                report_dir,
                config_file,
                threads=threads_per_lang,
                quiet=args.quiet,
            )
            summary = build_sarif_summary(
                sarif,
                verbose=args.verbose,
                files=file_patterns,
                rules=rule_patterns,
                limit=args.limit,
                offset=args.offset,
            )
            return (
                lang,
                f"[{lang}] SARIF: {sarif}\n{summary.text}",
                summary.total_findings,
                summary.matched_findings,
                False,
            )
        except subprocess.CalledProcessError as exc:
            err(f"{lang} failed (exit {exc.returncode})")
            return (lang, f"[{lang}] FAILED (exit {exc.returncode})", 0, 0, True)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(scan, lang): lang for lang in langs}
        for future in concurrent.futures.as_completed(futures):
            if future.exception():
                scan_failed = True
                lang = futures[future]
                err(f"{lang} crashed unexpectedly: {future.exception()}")
                summaries[lang] = (f"[{lang}] FAILED (unexpected exception)", 0)
                continue
            lang, text, finding_count, matched_count, failed = future.result()
            summaries[lang] = (text, matched_count)
            findings_found = findings_found or finding_count > 0
            scan_failed = scan_failed or failed

    log("===== Summaries =====")
    for lang in langs:
        if lang in summaries:
            text, matched_count = summaries[lang]
            if (file_patterns is None and rule_patterns is None) or matched_count > 0:
                print(text)

    should_fail = scan_failed or findings_found
    sys.exit(0 if args.no_fail else int(should_fail))
