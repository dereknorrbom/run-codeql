import json
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import run_codeql.cli as cli
from run_codeql.sarif import SarifSummary

scenarios("../features/scan_scope.feature")


@pytest.fixture()
def scope_ctx(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    codeql_bin = tmp_path / "codeql"
    codeql_bin.write_text("", encoding="utf-8")
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    captured: dict[str, object] = {"files_in_source_root": [], "result": None}

    def fake_fetch_codeql():
        return codeql_bin

    def fake_cleanup_reports(*args, **kwargs):  # noqa: ANN001, ARG001
        return None

    def fake_run_lang(  # noqa: PLR0913
        lang,  # noqa: ANN001
        codeql,  # noqa: ANN001, ARG001
        keep_db,  # noqa: ANN001, ARG001
        repo_root,  # noqa: ANN001, ARG001
        work_dir,  # noqa: ANN001, ARG001
        report_dir,  # noqa: ANN001
        config_file,  # noqa: ANN001, ARG001
        mode="default",  # noqa: ANN001, ARG001
        threads=0,  # noqa: ANN001, ARG001
        quiet=False,  # noqa: ANN001, ARG001
        source_root=None,  # noqa: ANN001
        use_codescanning_config=True,  # noqa: ANN001, ARG001
    ):
        source = source_root or repo_root
        captured["files_in_source_root"] = sorted(
            str(path.relative_to(source))
            for path in Path(source).rglob("*")
            if path.is_file()
        )
        sarif_path = Path(report_dir) / f"{lang}-code-quality.sarif"
        sarif_path.write_text(json.dumps({"runs": [{"results": []}]}), encoding="utf-8")
        return sarif_path

    def fake_build_sarif_summary(*args, **kwargs):  # noqa: ANN001, ARG001
        return SarifSummary(
            text="  Total: 0",
            total_findings=0,
            read_error=False,
            matched_findings=0,
        )

    monkeypatch.setattr(cli, "fetch_codeql", fake_fetch_codeql)
    monkeypatch.setattr(cli, "cleanup_reports", fake_cleanup_reports)
    monkeypatch.setattr(cli, "run_lang", fake_run_lang)
    monkeypatch.setattr(cli, "build_sarif_summary", fake_build_sarif_summary)

    return {"tmp_path": tmp_path, "result": None, "captured": captured}


@given(parsers.parse('a repository with Python files in "{path_a}" and "{path_b}"'))
def repo_with_python_files(scope_ctx, path_a, path_b):
    for rel_path in (path_a, path_b):
        target = scope_ctx["tmp_path"] / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("print('hello')\n", encoding="utf-8")


@given("an empty repository")
def empty_repo(scope_ctx):
    del scope_ctx


@when(parsers.parse('I run rcql with "{args}"'))
def run_cli(scope_ctx, args, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["rcql", *args.split()])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    scope_ctx["result"] = exc.value


@then(parsers.parse('the analyzer source root includes only "{path}"'))
def source_root_contains_file(scope_ctx, path):
    files = scope_ctx["captured"]["files_in_source_root"]
    assert path in files


@then(parsers.parse('the analyzer source root excludes "{path}"'))
def source_root_excludes_file(scope_ctx, path):
    files = scope_ctx["captured"]["files_in_source_root"]
    assert path not in files


@then("the exit code is non-zero")
def non_zero_exit(scope_ctx):
    assert scope_ctx["result"].code != 0


@then(parsers.parse('stderr contains "{text}"'))
def stderr_contains(scope_ctx, text, capsys):
    del scope_ctx
    captured = capsys.readouterr()
    assert text in captured.err
