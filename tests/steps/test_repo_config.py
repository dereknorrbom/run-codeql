from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import make_report_dir, run_rcql, write_repo_config, write_sarif_with_paths

scenarios("../features/repo_config.feature")


# ── given ─────────────────────────────────────────────────────────────────────


@given("a Python SARIF report with findings exists")
def python_sarif_with_findings(cli_ctx):
    make_report_dir(cli_ctx["tmp_path"], "python-code-quality.sarif")


@given(parsers.parse('a SARIF report exists with findings in "{path_a}" and "{path_b}"'))
def sarif_with_two_paths(cli_ctx, path_a, path_b):
    write_sarif_with_paths(cli_ctx["tmp_path"], [path_a, path_b])


@given(parsers.parse('the repo config sets files to "{pattern}"'))
def repo_config_files(cli_ctx, pattern):
    write_repo_config(cli_ctx["tmp_path"], {"files": [pattern]})


@given(parsers.parse('the repo config sets exclude_files to "{pattern}"'))
def repo_config_exclude_files(cli_ctx, pattern):
    write_repo_config(cli_ctx["tmp_path"], {"exclude_files": [pattern]})


@given("the repo config sets include_third_party to true")
def repo_config_include_third_party(cli_ctx):
    write_repo_config(cli_ctx["tmp_path"], {"include_third_party": True})


@given("no repo config file exists")
def no_repo_config(cli_ctx):
    pass  # tmp_path starts without .rcql.json


# ── when ──────────────────────────────────────────────────────────────────────


@when(parsers.parse('I run rcql with "{args}"'))
def run_rcql_with_args(cli_ctx, args):
    cli_ctx["result"] = run_rcql(args.split(), cli_ctx["tmp_path"])


# ── then ──────────────────────────────────────────────────────────────────────


@then("the exit code is zero")
def exit_code_zero(cli_ctx):
    assert cli_ctx["result"].returncode == 0


@then(parsers.parse('stdout contains "{text}"'))
def stdout_contains(cli_ctx, text):
    assert text in cli_ctx["result"].stdout


@then(parsers.parse('stdout does not contain "{text}"'))
def stdout_not_contains(cli_ctx, text):
    assert text not in cli_ctx["result"].stdout
