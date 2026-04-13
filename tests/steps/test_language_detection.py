from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from run_codeql.scanner import detect_langs

scenarios("../features/language_detection.feature")


def _touch(tmp_path: Path, rel_path: str) -> None:
    full = tmp_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.touch()


# ── given ─────────────────────────────────────────────────────────────────────


@given(parsers.parse('the repo contains "{rel_path}"'))
def repo_contains_file(cli_ctx, rel_path):
    _touch(cli_ctx["tmp_path"], rel_path)


@given("the repo is empty")
def repo_is_empty(cli_ctx):
    pass  # tmp_path starts empty


# ── when ──────────────────────────────────────────────────────────────────────


@when("I run language detection")
def run_language_detection(cli_ctx):
    cli_ctx["detected_langs"] = detect_langs(cli_ctx["tmp_path"])


# ── then ──────────────────────────────────────────────────────────────────────


@then(parsers.parse('the detected languages include "{lang}"'))
def detected_includes(cli_ctx, lang):
    assert lang in cli_ctx["detected_langs"]


@then(parsers.parse('the detected languages do not include "{lang}"'))
def detected_excludes(cli_ctx, lang):
    assert lang not in cli_ctx["detected_langs"]


@then("no languages are detected")
def no_languages_detected(cli_ctx):
    assert cli_ctx["detected_langs"] == []


@then("the detected languages are sorted alphabetically")
def langs_are_sorted(cli_ctx):
    langs = cli_ctx["detected_langs"]
    assert langs == sorted(langs)
