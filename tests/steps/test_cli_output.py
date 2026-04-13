import shutil

from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import make_report_dir, run_rcql

scenarios("../features/cli_output.feature")

FIXTURES = __import__("pathlib").Path(__file__).parent.parent / "fixtures"


# ── given ─────────────────────────────────────────────────────────────────────


@given("a Python SARIF report with findings exists")
def python_sarif_with_findings(cli_ctx):
    make_report_dir(cli_ctx["tmp_path"], "python-code-quality.sarif")


@given("an empty Python SARIF report exists")
def empty_python_sarif(cli_ctx):
    make_report_dir(cli_ctx["tmp_path"], "empty-code-quality.sarif")


@given("no SARIF reports exist")
def no_sarif_reports(cli_ctx):
    pass  # tmp_path starts empty


@given("an empty Rust SARIF report exists")
def empty_rust_sarif(cli_ctx):
    report_dir = cli_ctx["tmp_path"] / ".codeql" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "empty-code-quality.sarif", report_dir / "rust-code-quality.sarif")


# ── when ──────────────────────────────────────────────────────────────────────


@when(parsers.parse('I run rcql with "{args}"'))
def run_rcql_with_args(cli_ctx, args):
    cli_ctx["result"] = run_rcql(args.split(), cli_ctx["tmp_path"])


# ── then ──────────────────────────────────────────────────────────────────────


@then("the exit code is zero")
def exit_code_zero(cli_ctx):
    assert cli_ctx["result"].returncode == 0


@then("the exit code is non-zero")
def exit_code_nonzero(cli_ctx):
    assert cli_ctx["result"].returncode != 0


@then(parsers.parse('stdout contains "{text}"'))
def stdout_contains(cli_ctx, text):
    assert text in cli_ctx["result"].stdout


@then(parsers.parse('stdout does not contain "{text}"'))
def stdout_not_contains(cli_ctx, text):
    assert text not in cli_ctx["result"].stdout


@then(parsers.parse('stderr contains "{text}"'))
def stderr_contains(cli_ctx, text):
    assert text in cli_ctx["result"].stderr
