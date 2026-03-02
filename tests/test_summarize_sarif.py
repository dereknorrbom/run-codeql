from pathlib import Path

from run_codeql import summarize_sarif

FIXTURES = Path(__file__).parent / "fixtures"


def test_counts_by_level():
    result = summarize_sarif(FIXTURES / "python-code-quality.sarif", "python")
    assert "error: 1" in result
    assert "warning: 2" in result
    assert "Total: 3" in result


def test_empty_sarif():
    result = summarize_sarif(FIXTURES / "empty-code-quality.sarif", "python")
    assert "Total: 0" in result


def test_missing_file():
    result = summarize_sarif(FIXTURES / "nonexistent.sarif", "python")
    assert "could not read SARIF" in result


def test_verbose_includes_rule_id():
    result = summarize_sarif(FIXTURES / "python-code-quality.sarif", "python", verbose=True)
    assert "py/sql-injection" in result
    assert "py/unused-import" in result


def test_verbose_includes_location():
    result = summarize_sarif(FIXTURES / "python-code-quality.sarif", "python", verbose=True)
    assert "src/db.py:42" in result
    assert "src/utils.py:3" in result


def test_verbose_includes_short_description():
    result = summarize_sarif(FIXTURES / "python-code-quality.sarif", "python", verbose=True)
    assert "SQL injection" in result
    assert "Unused import" in result


def test_verbose_strips_sarif_markdown_links():
    result = summarize_sarif(FIXTURES / "python-code-quality.sarif", "python", verbose=True)
    # The raw message is "This query depends on [user-provided value](1)."
    # After stripping it should be "This query depends on user-provided value."
    assert "[user-provided value](1)" not in result
    assert "user-provided value" in result


def test_verbose_counts_still_present():
    result = summarize_sarif(FIXTURES / "python-code-quality.sarif", "python", verbose=True)
    assert "Total: 3" in result


def test_non_verbose_has_no_rule_ids():
    result = summarize_sarif(FIXTURES / "python-code-quality.sarif", "python", verbose=False)
    assert "py/sql-injection" not in result
    assert "src/db.py" not in result
