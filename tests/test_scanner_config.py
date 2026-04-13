from pathlib import Path

import pytest

import run_codeql.scanner as scanner


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

    sanitized = scanner._sanitize_codescanning_config_for_database_create(
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

    sanitized = scanner._sanitize_codescanning_config_for_database_create(
        config_file=config_file,
        work_dir=tmp_path,
        lang="python",
    )

    assert sanitized == config_file


def test_resolve_suite_defaults_to_security_and_quality_when_no_config(tmp_path):
    suite = scanner._resolve_suite_for_lang(
        suite_lang="python", config_file=tmp_path / "missing.yml"
    )
    assert suite == "codeql/python-queries:codeql-suites/python-security-and-quality.qls"


def test_resolve_suite_uses_code_quality_from_repo_config(tmp_path):
    config_file = tmp_path / "codeql-config.yml"
    write_config(
        config_file,
        ("queries:\n" "  - uses: code-quality\n" "paths:\n" "  - src\n"),
    )
    suite = scanner._resolve_suite_for_lang(suite_lang="python", config_file=config_file)
    assert suite == "codeql/python-queries:codeql-suites/python-code-quality.qls"


def test_resolve_suite_rejects_unsupported_query_selector(tmp_path):
    config_file = tmp_path / "codeql-config.yml"
    write_config(
        config_file,
        ("queries:\n" "  - uses: security-extended\n"),
    )
    with pytest.raises(scanner.ScanConfigurationError):
        scanner._resolve_suite_for_lang(suite_lang="python", config_file=config_file)


def test_resolve_suite_uses_javascript_pack_for_typescript_language(tmp_path):
    suite = scanner._resolve_suite_for_lang(
        suite_lang="javascript", config_file=tmp_path / "missing.yml"
    )
    assert suite == "codeql/javascript-queries:codeql-suites/javascript-security-and-quality.qls"


def test_run_lang_uses_javascript_queries_suite_for_javascript_typescript(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    work_dir = tmp_path / "work"
    report_dir = tmp_path / "reports"
    repo_root.mkdir()
    work_dir.mkdir()
    report_dir.mkdir()
    codeql = tmp_path / "codeql"
    codeql.write_text("", encoding="utf-8")
    analyze_commands: list[list[str]] = []

    def fake_run(cmd, check, stdout=None, stderr=None):  # noqa: ANN001
        if cmd[2] == "analyze":
            analyze_commands.append(cmd)
        return None

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    monkeypatch.setattr(scanner, "ensure_pack", lambda pack_name, codeql, quiet: None)

    sarif_path = scanner.run_lang(
        lang="javascript-typescript",
        codeql=codeql,
        keep_db=True,
        repo_root=repo_root,
        work_dir=work_dir,
        report_dir=report_dir,
        config_file=tmp_path / "missing.yml",
    )

    assert analyze_commands
    assert (
        "codeql/javascript-queries:codeql-suites/javascript-security-and-quality.qls"
        in analyze_commands[0]
    )
    assert sarif_path.name == "javascript-typescript-security-and-quality.sarif"


def test_run_lang_uses_code_quality_report_name_when_config_selects_code_quality(
    tmp_path, monkeypatch
):
    repo_root = tmp_path / "repo"
    work_dir = tmp_path / "work"
    report_dir = tmp_path / "reports"
    repo_root.mkdir()
    work_dir.mkdir()
    report_dir.mkdir()
    codeql = tmp_path / "codeql"
    codeql.write_text("", encoding="utf-8")
    config_file = tmp_path / "codeql-config.yml"
    write_config(config_file, "queries:\n  - uses: code-quality\n")

    def fake_run(cmd, check, stdout=None, stderr=None):  # noqa: ANN001
        return None

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    monkeypatch.setattr(scanner, "ensure_pack", lambda pack_name, codeql, quiet: None)

    sarif_path = scanner.run_lang(
        lang="python",
        codeql=codeql,
        keep_db=True,
        repo_root=repo_root,
        work_dir=work_dir,
        report_dir=report_dir,
        config_file=config_file,
    )

    assert sarif_path.name == "python-code-quality.sarif"


def test_run_lang_standard_findings_ignores_config_and_forces_code_quality(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    work_dir = tmp_path / "work"
    report_dir = tmp_path / "reports"
    repo_root.mkdir()
    work_dir.mkdir()
    report_dir.mkdir()
    codeql = tmp_path / "codeql"
    codeql.write_text("", encoding="utf-8")
    config_file = tmp_path / "codeql-config.yml"
    write_config(config_file, "queries:\n  - uses: security-and-quality\n")
    create_commands: list[list[str]] = []
    analyze_commands: list[list[str]] = []

    def fake_run(cmd, check, stdout=None, stderr=None):  # noqa: ANN001
        if cmd[2] == "create":
            create_commands.append(cmd)
        if cmd[2] == "analyze":
            analyze_commands.append(cmd)
        return None

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    monkeypatch.setattr(scanner, "ensure_pack", lambda pack_name, codeql, quiet: None)

    sarif_path = scanner.run_lang(
        lang="python",
        codeql=codeql,
        keep_db=True,
        repo_root=repo_root,
        work_dir=work_dir,
        report_dir=report_dir,
        config_file=config_file,
        mode="standard-findings",
    )

    assert sarif_path.name == "python-code-quality.sarif"
    assert create_commands
    assert "--codescanning-config" not in create_commands[0]
    assert analyze_commands
    assert "codeql/python-queries:codeql-suites/python-code-quality.qls" in analyze_commands[0]
