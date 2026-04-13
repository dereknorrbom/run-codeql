import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import run_codeql.scanner as scanner

scenarios("../features/scan_modes.feature")


# ── shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture()
def scan_ctx(tmp_path, monkeypatch):
    """Shared mutable context passed between steps."""
    repo_root = tmp_path / "repo"
    work_dir = tmp_path / "work"
    report_dir = tmp_path / "reports"
    repo_root.mkdir()
    work_dir.mkdir()
    report_dir.mkdir()

    codeql = tmp_path / "codeql"
    codeql.write_text("", encoding="utf-8")

    create_commands: list[list[str]] = []
    analyze_commands: list[list[str]] = []

    def fake_run(cmd, check, stdout=None, stderr=None):  # noqa: ANN001
        if len(cmd) > 2 and cmd[2] == "create":
            create_commands.append(cmd)
        if len(cmd) > 2 and cmd[2] == "analyze":
            analyze_commands.append(cmd)
        return None

    monkeypatch.setattr(scanner.subprocess, "run", fake_run)
    monkeypatch.setattr(scanner, "ensure_pack", lambda pack_name, codeql, quiet: None)

    return {
        "tmp_path": tmp_path,
        "repo_root": repo_root,
        "work_dir": work_dir,
        "report_dir": report_dir,
        "codeql": codeql,
        "config_file": tmp_path / "missing.yml",
        "mode": "default",
        "create_commands": create_commands,
        "analyze_commands": analyze_commands,
        "sarif_path": None,
    }


# ── given ─────────────────────────────────────────────────────────────────────


@given('a repo config that selects the "code-quality" query suite')
def repo_config_code_quality(scan_ctx):
    config_file = scan_ctx["tmp_path"] / "codeql-config.yml"
    config_file.write_text("queries:\n  - uses: code-quality\n", encoding="utf-8")
    scan_ctx["config_file"] = config_file


@given('a repo config that selects the "security-and-quality" query suite')
def repo_config_security_and_quality(scan_ctx):
    config_file = scan_ctx["tmp_path"] / "codeql-config.yml"
    config_file.write_text("queries:\n  - uses: security-and-quality\n", encoding="utf-8")
    scan_ctx["config_file"] = config_file


@given("no repo config file exists")
def no_repo_config(scan_ctx):
    scan_ctx["config_file"] = scan_ctx["tmp_path"] / "missing.yml"


# ── when ──────────────────────────────────────────────────────────────────────


@when("I run a Python scan in default mode")
def run_python_default(scan_ctx):
    scan_ctx["sarif_path"] = scanner.run_lang(
        lang="python",
        codeql=scan_ctx["codeql"],
        keep_db=True,
        repo_root=scan_ctx["repo_root"],
        work_dir=scan_ctx["work_dir"],
        report_dir=scan_ctx["report_dir"],
        config_file=scan_ctx["config_file"],
    )


@when("I run a Python scan in standard-findings mode")
def run_python_standard_findings(scan_ctx):
    scan_ctx["sarif_path"] = scanner.run_lang(
        lang="python",
        codeql=scan_ctx["codeql"],
        keep_db=True,
        repo_root=scan_ctx["repo_root"],
        work_dir=scan_ctx["work_dir"],
        report_dir=scan_ctx["report_dir"],
        config_file=scan_ctx["config_file"],
        mode="standard-findings",
    )


# ── then ──────────────────────────────────────────────────────────────────────


@then('the SARIF report is named "python-code-quality.sarif"')
def sarif_named_code_quality(scan_ctx):
    assert scan_ctx["sarif_path"].name == "python-code-quality.sarif"


@then('the database create command does not include "--codescanning-config"')
def create_excludes_codescanning_config(scan_ctx):
    assert scan_ctx["create_commands"], "No database create command was recorded"
    assert "--codescanning-config" not in scan_ctx["create_commands"][0]


@then(parsers.parse('the analyze command uses suite "{suite}"'))
def analyze_uses_suite(scan_ctx, suite):
    assert scan_ctx["analyze_commands"], "No analyze command was recorded"
    assert suite in scan_ctx["analyze_commands"][0]
