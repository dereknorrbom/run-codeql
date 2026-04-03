"""Tests for build_sarif_summary filtering: --files, --rule, --limit, --offset."""

import json
from pathlib import Path

from run_codeql.sarif import _uri_matches, build_sarif_summary

FIXTURES = Path(__file__).parent / "fixtures"
SARIF = FIXTURES / "python-code-quality.sarif"

# Fixture has 3 results:
#   py/sql-injection  error    src/db.py:42
#   py/unused-import  warning  src/utils.py:3
#   py/unused-import  warning  src/utils.py:4


# ---------------------------------------------------------------------------
# _uri_matches
# ---------------------------------------------------------------------------


def test_uri_matches_exact():
    assert _uri_matches("src/db.py", ["src/db.py"])


def test_uri_matches_basename_only():
    # Passing just the filename should match a URI that has a path prefix.
    assert _uri_matches("src/db.py", ["db.py"])


def test_uri_matches_glob_pattern():
    assert _uri_matches("src/db.py", ["src/*.py"])


def test_uri_matches_basename_glob():
    assert _uri_matches("src/db.py", ["*.py"])


def test_uri_no_match():
    assert not _uri_matches("src/db.py", ["src/other.py"])


def test_uri_matches_first_of_multiple_patterns():
    assert _uri_matches("src/db.py", ["nope.py", "src/db.py"])


# ---------------------------------------------------------------------------
# --files filter
# ---------------------------------------------------------------------------


def test_files_exact_match_reduces_count():
    summary = build_sarif_summary(SARIF, files=["src/db.py"])
    assert summary.matched_findings == 1
    assert summary.total_findings == 1


def test_files_no_match_returns_zero():
    summary = build_sarif_summary(SARIF, files=["nonexistent.py"])
    assert summary.matched_findings == 0
    assert summary.total_findings == 0


def test_files_glob_matches_multiple():
    # src/*.py should match src/db.py and src/utils.py (2 results from utils)
    summary = build_sarif_summary(SARIF, files=["src/*.py"])
    assert summary.matched_findings == 3


def test_files_basename_match():
    summary = build_sarif_summary(SARIF, files=["db.py"])
    assert summary.matched_findings == 1


def test_files_shows_shown_matched_label():
    summary = build_sarif_summary(SARIF, files=["src/db.py"])
    assert "Shown:" in summary.text
    assert "matched:" in summary.text


def test_no_filter_shows_total_label():
    summary = build_sarif_summary(SARIF)
    assert "Total:" in summary.text
    assert "Shown:" not in summary.text


def test_files_multiple_patterns():
    summary = build_sarif_summary(SARIF, files=["src/db.py", "src/utils.py"])
    assert summary.matched_findings == 3


# ---------------------------------------------------------------------------
# --rule filter
# ---------------------------------------------------------------------------


def test_rule_exact_match():
    summary = build_sarif_summary(SARIF, rules=["py/unused-import"])
    assert summary.matched_findings == 2


def test_rule_exact_match_error():
    summary = build_sarif_summary(SARIF, rules=["py/sql-injection"])
    assert summary.matched_findings == 1


def test_rule_glob_matches_all_python():
    summary = build_sarif_summary(SARIF, rules=["py/*"])
    assert summary.matched_findings == 3


def test_rule_no_match():
    summary = build_sarif_summary(SARIF, rules=["js/something"])
    assert summary.matched_findings == 0


def test_rule_shows_shown_matched_label():
    summary = build_sarif_summary(SARIF, rules=["py/unused-import"])
    assert "Shown:" in summary.text
    assert "matched:" in summary.text


def test_rule_multiple_rules():
    summary = build_sarif_summary(SARIF, rules=["py/sql-injection", "py/unused-import"])
    assert summary.matched_findings == 3


# ---------------------------------------------------------------------------
# --files + --rule combined
# ---------------------------------------------------------------------------


def test_files_and_rule_combined():
    # src/utils.py has 2 unused-import warnings; db.py has 0
    summary = build_sarif_summary(SARIF, files=["src/utils.py"], rules=["py/unused-import"])
    assert summary.matched_findings == 2


def test_files_and_rule_combined_no_match():
    # src/utils.py has no sql-injection findings
    summary = build_sarif_summary(SARIF, files=["src/utils.py"], rules=["py/sql-injection"])
    assert summary.matched_findings == 0


# ---------------------------------------------------------------------------
# --limit
# ---------------------------------------------------------------------------


def test_limit_reduces_shown():
    summary = build_sarif_summary(SARIF, limit=2)
    assert summary.total_findings == 2


def test_limit_matched_is_full_count():
    summary = build_sarif_summary(SARIF, limit=2)
    assert summary.matched_findings == 3


def test_limit_zero_returns_nothing():
    summary = build_sarif_summary(SARIF, limit=0)
    assert summary.total_findings == 0
    assert summary.matched_findings == 3


def test_limit_larger_than_results_returns_all():
    summary = build_sarif_summary(SARIF, limit=100)
    assert summary.total_findings == 3


def test_limit_shows_shown_matched_label():
    summary = build_sarif_summary(SARIF, limit=1)
    assert "Shown:" in summary.text


# ---------------------------------------------------------------------------
# --offset
# ---------------------------------------------------------------------------


def test_offset_skips_findings():
    summary = build_sarif_summary(SARIF, offset=2)
    assert summary.total_findings == 1


def test_offset_beyond_results_returns_empty_but_preserves_matched():
    summary = build_sarif_summary(SARIF, offset=100)
    assert summary.total_findings == 0
    assert summary.matched_findings == 3  # matched is pre-pagination


def test_offset_shows_shown_matched_label():
    summary = build_sarif_summary(SARIF, offset=1)
    assert "Shown:" in summary.text


# ---------------------------------------------------------------------------
# --limit + --offset together (pagination)
# ---------------------------------------------------------------------------


def test_limit_and_offset_page_one():
    page1 = build_sarif_summary(SARIF, limit=2, offset=0)
    assert page1.total_findings == 2


def test_limit_and_offset_page_two():
    page2 = build_sarif_summary(SARIF, limit=2, offset=2)
    assert page2.total_findings == 1


def test_paginated_matched_is_always_full_count():
    page1 = build_sarif_summary(SARIF, limit=1, offset=0)
    page2 = build_sarif_summary(SARIF, limit=1, offset=1)
    assert page1.matched_findings == page2.matched_findings == 3


# ---------------------------------------------------------------------------
# verbose output with filters
# ---------------------------------------------------------------------------


def test_files_filter_verbose_only_shows_matching_locations():
    summary = build_sarif_summary(SARIF, verbose=True, files=["src/db.py"])
    assert "src/db.py" in summary.text
    assert "src/utils.py" not in summary.text


def test_rule_filter_verbose_only_shows_matching_rule():
    summary = build_sarif_summary(SARIF, verbose=True, rules=["py/unused-import"])
    assert "py/unused-import" in summary.text
    assert "py/sql-injection" not in summary.text


def test_limit_verbose_only_shows_n_findings():
    summary = build_sarif_summary(SARIF, verbose=True, limit=1)
    # Only first finding (sql-injection) should be in verbose output
    assert "py/sql-injection" in summary.text
    # Second and third findings should not appear
    assert summary.total_findings == 1


# ---------------------------------------------------------------------------
# matched_findings field on SarifSummary
# ---------------------------------------------------------------------------


def test_matched_findings_equals_total_when_no_filter():
    summary = build_sarif_summary(SARIF)
    assert summary.matched_findings == summary.total_findings == 3


def test_read_error_has_zero_matched():
    summary = build_sarif_summary(FIXTURES / "nonexistent.sarif")
    assert summary.matched_findings == 0
    assert summary.read_error is True


def test_dedupes_codeql_db_mirror_and_source_paths(tmp_path):
    repo_abs = str((Path.cwd() / "src" / "demo.py").resolve()).replace("\\", "/")
    mirror_uri = f".codeql/db-python/src/{repo_abs}"

    sarif = {
        "runs": [
            {
                "tool": {"driver": {"rules": [{"id": "py/unused-import"}]}},
                "results": [
                    {
                        "ruleId": "py/unused-import",
                        "level": "warning",
                        "message": {"text": "Duplicate finding"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/demo.py"},
                                    "region": {"startLine": 7},
                                }
                            }
                        ],
                    },
                    {
                        "ruleId": "py/unused-import",
                        "level": "warning",
                        "message": {"text": "Duplicate finding"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": mirror_uri},
                                    "region": {"startLine": 7},
                                }
                            }
                        ],
                    },
                ],
            }
        ]
    }
    sarif_path = tmp_path / "mirror.sarif"
    sarif_path.write_text(json.dumps(sarif), encoding="utf-8")

    summary = build_sarif_summary(sarif_path, verbose=True)
    assert summary.total_findings == 1
    assert summary.matched_findings == 1
    assert "src/demo.py:7" in summary.text
    assert ".codeql/db-python/src/" not in summary.text


def test_files_filter_matches_normalized_db_mirror_uri(tmp_path):
    repo_abs = str((Path.cwd() / "src" / "demo.py").resolve()).replace("\\", "/")
    mirror_uri = f".codeql/db-python/src/{repo_abs}"

    sarif = {
        "runs": [
            {
                "tool": {"driver": {"rules": [{"id": "py/unused-import"}]}},
                "results": [
                    {
                        "ruleId": "py/unused-import",
                        "level": "warning",
                        "message": {"text": "Mirror only"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": mirror_uri},
                                    "region": {"startLine": 3},
                                }
                            }
                        ],
                    }
                ],
            }
        ]
    }
    sarif_path = tmp_path / "mirror_only.sarif"
    sarif_path.write_text(json.dumps(sarif), encoding="utf-8")

    summary = build_sarif_summary(sarif_path, files=["src/demo.py"])
    assert summary.total_findings == 1
    assert summary.matched_findings == 1


def test_normalizes_mirror_uri_without_leading_slash_in_src_segment(tmp_path):
    repo_abs = str((Path.cwd() / "src" / "demo.py").resolve()).replace("\\", "/")
    mirror_uri = f".codeql/db-python/src/{repo_abs.lstrip('/')}"

    sarif = {
        "runs": [
            {
                "tool": {"driver": {"rules": [{"id": "py/unused-import"}]}},
                "results": [
                    {
                        "ruleId": "py/unused-import",
                        "level": "warning",
                        "message": {"text": "Mirror no leading slash"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": mirror_uri},
                                    "region": {"startLine": 9},
                                }
                            }
                        ],
                    }
                ],
            }
        ]
    }
    sarif_path = tmp_path / "mirror_no_leading.sarif"
    sarif_path.write_text(json.dumps(sarif), encoding="utf-8")

    summary = build_sarif_summary(sarif_path, verbose=True)
    assert summary.total_findings == 1
    assert "src/demo.py:9" in summary.text
