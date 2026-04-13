from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import make_report_dir, run_rcql, write_sarif_with_paths

scenarios("../features/findings_filtering.feature")


# ── given ─────────────────────────────────────────────────────────────────────


@given("a Python SARIF report with findings exists")
def python_sarif_with_findings(cli_ctx):
    make_report_dir(cli_ctx["tmp_path"], "python-code-quality.sarif")


@given(parsers.parse('a SARIF report exists with findings in "{path_a}" and "{path_b}"'))
def sarif_with_two_paths(cli_ctx, path_a, path_b):
    write_sarif_with_paths(cli_ctx["tmp_path"], [path_a, path_b])


# ── when ──────────────────────────────────────────────────────────────────────


@when(parsers.parse('I run rcql with "{args}"'))
def run_rcql_with_args(cli_ctx, args):
    cli_ctx["result"] = run_rcql(args.split(), cli_ctx["tmp_path"])


# ── then ──────────────────────────────────────────────────────────────────────


@then(parsers.parse('stdout contains "{text}"'))
def stdout_contains(cli_ctx, text):
    assert text in cli_ctx["result"].stdout


@then(parsers.parse('stdout does not contain "{text}"'))
def stdout_not_contains(cli_ctx, text):
    assert text not in cli_ctx["result"].stdout
