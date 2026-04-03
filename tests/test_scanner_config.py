from pathlib import Path

import pytest

from run_codeql.scanner import (
    ScanConfigurationError,
    _resolve_suite_for_lang,
    _sanitize_codescanning_config_for_database_create,
)


def write_config(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_sanitize_config_removes_query_sections_and_keeps_paths(tmp_path):
    config_file = tmp_path / "codeql-config.yml"
    write_config(
        config_file,
        (
            'name: "Example"\n'
            "queries:\n"
            "  - uses: security-and-quality\n"
            "packs:\n"
            "  - codeql/python-queries\n"
            "query-filters:\n"
            "  - include:\n"
            "      severity:\n"
            "        - error\n"
            "paths:\n"
            "  - src\n"
            "paths-ignore:\n"
            "  - tests\n"
        ),
    )

    sanitized = _sanitize_codescanning_config_for_database_create(
        config_file=config_file,
        work_dir=tmp_path,
        lang="python",
    )

    assert sanitized != config_file
    text = sanitized.read_text(encoding="utf-8")
    assert "queries:" not in text
    assert "packs:" not in text
    assert "query-filters:" not in text
    assert "paths:" in text
    assert "paths-ignore:" in text


def test_sanitize_config_returns_original_when_no_query_sections(tmp_path):
    config_file = tmp_path / "codeql-config.yml"
    write_config(
        config_file,
        ('name: "Example"\n' "paths:\n" "  - src\n" "paths-ignore:\n" "  - tests\n"),
    )

    sanitized = _sanitize_codescanning_config_for_database_create(
        config_file=config_file,
        work_dir=tmp_path,
        lang="python",
    )

    assert sanitized == config_file


def test_resolve_suite_defaults_to_security_and_quality_when_no_config(tmp_path):
    suite = _resolve_suite_for_lang(lang="python", config_file=tmp_path / "missing.yml")
    assert suite == "codeql/python-queries:codeql-suites/python-security-and-quality.qls"


def test_resolve_suite_uses_code_quality_from_repo_config(tmp_path):
    config_file = tmp_path / "codeql-config.yml"
    write_config(
        config_file,
        ("queries:\n" "  - uses: code-quality\n" "paths:\n" "  - src\n"),
    )
    suite = _resolve_suite_for_lang(lang="python", config_file=config_file)
    assert suite == "codeql/python-queries:codeql-suites/python-code-quality.qls"


def test_resolve_suite_rejects_unsupported_query_selector(tmp_path):
    config_file = tmp_path / "codeql-config.yml"
    write_config(
        config_file,
        ("queries:\n" "  - uses: security-extended\n"),
    )
    with pytest.raises(ScanConfigurationError):
        _resolve_suite_for_lang(lang="python", config_file=config_file)
