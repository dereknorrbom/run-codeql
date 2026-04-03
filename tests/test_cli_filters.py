"""CLI integration tests for --files, --rule, --limit, and --offset flags."""

import json
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


def make_report_dir(tmp_path: Path, *sarif_names: str) -> Path:
    """Copy one or more fixture SARIFs into a .codeql/reports/ structure."""
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True)
    for name in sarif_names:
        shutil.copy(FIXTURES / name, report_dir / name)
    return report_dir


def write_sarif_with_paths(tmp_path: Path, paths: list[str]) -> None:
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    sarif = {
        "runs": [
            {
                "tool": {
                    "driver": {
                        "rules": [
                            {
                                "id": "py/unused-import",
                                "shortDescription": {"text": "Unused import"},
                            }
                        ]
                    }
                },
                "results": [
                    {
                        "ruleId": "py/unused-import",
                        "level": "warning",
                        "message": {"text": f"finding-{idx}"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": uri},
                                    "region": {"startLine": idx + 1},
                                }
                            }
                        ],
                    }
                    for idx, uri in enumerate(paths)
                ],
            }
        ]
    }
    (report_dir / "python-code-quality.sarif").write_text(json.dumps(sarif), encoding="utf-8")


# ---------------------------------------------------------------------------
# --files
# ---------------------------------------------------------------------------


def test_files_filters_to_matching_file(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--files", "src/db.py"], cwd=tmp_path)
    assert result.returncode == 0
    assert "Shown: 1" in result.stdout
    assert "matched: 1" in result.stdout


def test_files_no_match_suppresses_lang_block(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--files", "nonexistent.py"], cwd=tmp_path)
    # No matching findings — the [python] block should be suppressed entirely
    assert "[python]" not in result.stdout


def test_files_no_match_exits_zero_with_no_fail(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--files", "nonexistent.py"], cwd=tmp_path)
    assert result.returncode == 0


def test_files_suppresses_other_langs_when_no_match(tmp_path):
    """When two lang SARIFs exist and --files only matches one, only that lang prints."""
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True)
    shutil.copy(
        FIXTURES / "python-code-quality.sarif",
        report_dir / "python-code-quality.sarif",
    )
    shutil.copy(
        FIXTURES / "empty-code-quality.sarif",
        report_dir / "rust-code-quality.sarif",
    )
    result = run_rcql(["--report-only", "--no-fail", "--files", "src/db.py"], cwd=tmp_path)
    assert "[python]" in result.stdout
    assert "[rust]" not in result.stdout


def test_files_glob_pattern(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--files", "src/*.py"], cwd=tmp_path)
    assert "Shown: 3" in result.stdout
    assert "matched: 3" in result.stdout


def test_files_verbose_shows_only_matching_locations(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(
        ["--report-only", "--no-fail", "--verbose", "--files", "src/utils.py"],
        cwd=tmp_path,
    )
    assert "src/utils.py" in result.stdout
    assert "src/db.py" not in result.stdout


def test_default_excludes_hide_node_modules(tmp_path):
    write_sarif_with_paths(
        tmp_path,
        ["src/app.py", "tactus-desktop/node_modules/pkg/index.py"],
    )
    result = run_rcql(["--report-only", "--no-fail"], cwd=tmp_path)
    assert result.returncode == 0
    assert "Total: 1" in result.stdout
    assert "node_modules" not in result.stdout


def test_include_third_party_restores_node_modules(tmp_path):
    write_sarif_with_paths(
        tmp_path,
        ["src/app.py", "tactus-desktop/node_modules/pkg/index.py"],
    )
    result = run_rcql(["--report-only", "--no-fail", "--include-third-party"], cwd=tmp_path)
    assert result.returncode == 0
    assert "Total: 2" in result.stdout


def test_exclude_files_flag_hides_matching_paths(tmp_path):
    write_sarif_with_paths(tmp_path, ["src/app.py", "src/generated/foo.py"])
    result = run_rcql(
        ["--report-only", "--no-fail", "--exclude-files", "src/generated/**"],
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert "Total: 1" in result.stdout


# ---------------------------------------------------------------------------
# --rule
# ---------------------------------------------------------------------------


def test_rule_filters_to_matching_rule(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--rule", "py/unused-import"], cwd=tmp_path)
    assert "Shown: 2" in result.stdout
    assert "matched: 2" in result.stdout


def test_rule_no_match_suppresses_lang_block(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--rule", "js/something"], cwd=tmp_path)
    assert "[python]" not in result.stdout


def test_rule_glob(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--rule", "py/*"], cwd=tmp_path)
    assert "Shown: 3" in result.stdout


def test_rule_verbose_shows_only_matching_rule_id(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(
        ["--report-only", "--no-fail", "--verbose", "--rule", "py/sql-injection"],
        cwd=tmp_path,
    )
    assert "py/sql-injection" in result.stdout
    assert "py/unused-import" not in result.stdout


def test_rule_multiple_comma_separated(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(
        [
            "--report-only",
            "--no-fail",
            "--rule",
            "py/sql-injection,py/unused-import",
        ],
        cwd=tmp_path,
    )
    assert "Shown: 3" in result.stdout


# ---------------------------------------------------------------------------
# --files + --rule combined
# ---------------------------------------------------------------------------


def test_files_and_rule_combined(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(
        [
            "--report-only",
            "--no-fail",
            "--files",
            "src/utils.py",
            "--rule",
            "py/unused-import",
        ],
        cwd=tmp_path,
    )
    assert "Shown: 2" in result.stdout


def test_files_and_rule_combined_no_match_suppresses_block(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(
        [
            "--report-only",
            "--no-fail",
            "--files",
            "src/utils.py",
            "--rule",
            "py/sql-injection",
        ],
        cwd=tmp_path,
    )
    assert "[python]" not in result.stdout


# ---------------------------------------------------------------------------
# --limit
# ---------------------------------------------------------------------------


def test_limit_caps_findings(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--limit", "1"], cwd=tmp_path)
    assert "Shown: 1" in result.stdout
    assert "matched: 3" in result.stdout


def test_limit_zero_still_shows_lang_block_with_matched_count(tmp_path):
    # --limit 0 shows 0 findings but there are still matched results, so the
    # lang block is printed so the caller can see the matched count.
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--limit", "0"], cwd=tmp_path)
    assert "[python]" in result.stdout
    assert "Shown: 0" in result.stdout
    assert "matched: 3" in result.stdout


def test_limit_larger_than_results_returns_all(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--limit", "100"], cwd=tmp_path)
    assert "Shown: 3" in result.stdout


# ---------------------------------------------------------------------------
# --offset
# ---------------------------------------------------------------------------


def test_offset_skips_findings(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--offset", "2"], cwd=tmp_path)
    assert "Shown: 1" in result.stdout
    assert "matched: 3" in result.stdout


def test_offset_beyond_all_still_shows_lang_block_with_matched_count(tmp_path):
    # --offset past the end still shows the block so callers know the total matched.
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--offset", "100"], cwd=tmp_path)
    assert "[python]" in result.stdout
    assert "Shown: 0" in result.stdout
    assert "matched: 3" in result.stdout


# ---------------------------------------------------------------------------
# --limit + --offset pagination
# ---------------------------------------------------------------------------


def test_pagination_page_one(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--limit", "2", "--offset", "0"], cwd=tmp_path)
    assert "Shown: 2" in result.stdout
    assert "matched: 3" in result.stdout


def test_pagination_page_two(tmp_path):
    make_report_dir(tmp_path, "python-code-quality.sarif")
    result = run_rcql(["--report-only", "--no-fail", "--limit", "2", "--offset", "2"], cwd=tmp_path)
    assert "Shown: 1" in result.stdout
    assert "matched: 3" in result.stdout


# ---------------------------------------------------------------------------
# --help mentions new flags
# ---------------------------------------------------------------------------


def test_help_mentions_files(tmp_path):
    result = run_rcql(["--help"], cwd=tmp_path)
    assert "--files" in result.stdout


def test_help_mentions_rule(tmp_path):
    result = run_rcql(["--help"], cwd=tmp_path)
    assert "--rule" in result.stdout


def test_help_mentions_limit(tmp_path):
    result = run_rcql(["--help"], cwd=tmp_path)
    assert "--limit" in result.stdout


def test_help_mentions_offset(tmp_path):
    result = run_rcql(["--help"], cwd=tmp_path)
    assert "--offset" in result.stdout


def test_help_mentions_exclude_files(tmp_path):
    result = run_rcql(["--help"], cwd=tmp_path)
    assert "--exclude-files" in result.stdout


def test_help_mentions_include_third_party(tmp_path):
    result = run_rcql(["--help"], cwd=tmp_path)
    assert "--include-third-party" in result.stdout
