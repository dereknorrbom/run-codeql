"""CLI smoke tests — run rcql against fixture SARIF without invoking CodeQL."""

import shutil
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def run_rcql(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "run_codeql"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def make_report_dir(tmp_path: Path, sarif_name: str) -> Path:
    """Copy a fixture SARIF into a .codeql/reports/ structure under tmp_path."""
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / sarif_name, report_dir / sarif_name)
    return report_dir


def test_report_only_exits_zero(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail"], cwd=tmp_path)
    assert result.returncode == 0


def test_report_only_output_contains_lang(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail"], cwd=tmp_path)
    assert "[python]" in result.stdout


def test_report_only_output_contains_totals(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail"], cwd=tmp_path)
    assert "Total: 3" in result.stdout


def test_report_only_verbose_contains_rule_id(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--verbose", "--no-fail"], cwd=tmp_path)
    assert "py/sql-injection" in result.stdout


def test_report_only_lang_filter(tmp_path):
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "python-code-quality.sarif", report_dir / "python-code-quality.sarif")
    shutil.copy(FIXTURES / "empty-code-quality.sarif", report_dir / "rust-code-quality.sarif")
    result = run_rcql(["--report-only", "--lang=python", "--no-fail"], cwd=tmp_path)
    assert "[python]" in result.stdout
    assert "[rust]" not in result.stdout


def test_report_only_lang_filter_matches_security_profile_report_name(tmp_path):
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True)
    shutil.copy(
        FIXTURES / "python-code-quality.sarif",
        report_dir / "python-security-and-quality.sarif",
    )
    shutil.copy(FIXTURES / "empty-code-quality.sarif", report_dir / "rust-code-quality.sarif")
    result = run_rcql(["--report-only", "--lang=python", "--no-fail"], cwd=tmp_path)
    assert "[python]" in result.stdout
    assert "[rust]" not in result.stdout


def test_report_only_missing_sarif_exits_nonzero(tmp_path):
    result = run_rcql(["--report-only"], cwd=tmp_path)
    assert result.returncode != 0
    assert "No SARIF files found" in result.stderr


def test_report_only_fails_on_findings_without_no_fail(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only"], cwd=tmp_path)
    assert result.returncode != 0


def test_report_only_succeeds_when_no_findings(tmp_path):
    make_report_dir(tmp_path, "empty-code-quality.sarif")
    result = run_rcql(["--report-only"], cwd=tmp_path)
    assert result.returncode == 0


def test_quiet_suppresses_log_lines(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--quiet", "--no-fail"], cwd=tmp_path)
    # stderr gets the "running in quiet mode" message, stdout should have no [codeql-local] lines
    assert "[codeql-local]" not in result.stdout


def test_quiet_mode_message_on_stderr(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--quiet", "--no-fail"], cwd=tmp_path)
    assert "quiet mode" in result.stderr


def test_help_exits_zero(tmp_path):
    result = run_rcql(["--help"], cwd=tmp_path)
    assert result.returncode == 0
    assert "--report-only" in result.stdout
    assert "--verbose" in result.stdout
    assert "--quiet" in result.stdout


def test_no_detected_languages_exits_nonzero(tmp_path):
    result = run_rcql([], cwd=tmp_path)
    assert result.returncode != 0
    assert "No languages detected" in result.stderr
