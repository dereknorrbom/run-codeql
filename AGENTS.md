# AGENTS.md

## Project management with Kanbus

Use Kanbus for task management.
Why: Kanbus task management is MANDATORY here; every task must live in Kanbus.
When: Create/update the Kanbus task before coding; close it only after the change lands.
How: See CONTRIBUTING_AGENT.md for the Kanbus workflow, hierarchy, status rules, priorities, command examples, and the sins to avoid. Never inspect project/ or issue JSON directly (including with cat or jq); use Kanbus commands only.
Performance: Prefer kbs (Rust) when available; kanbus (Python) is equivalent but slower.
Warning: Editing project/ directly is a sin against The Way. Do not read or write anything in project/; work only through Kanbus.

This file provides guidance to AI coding agents when working with code in this repository.

## Git workflow

### Branching (Git Flow)

- `main` — production-ready releases only; never commit directly
- `develop` — integration branch; merge feature/fix branches here first
- Feature branches: `feature/<short-description>`
- Bug fix branches: `fix/<short-description>`
- Hotfix branches (off `main`): `hotfix/<short-description>`

All pull requests target `develop` unless it is a hotfix, which targets `main` directly. PRs from `develop` → `main` represent a release.

### Commit messages (Semantic Release)

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) spec so that `semantic-release` can determine version bumps and generate changelogs automatically.

| Prefix | When to use | Version bump |
|--------|-------------|--------------|
| `feat:` | New user-facing feature | minor |
| `fix:` | Bug fix | patch |
| `chore:` | Build, tooling, CI, or housekeeping (no production code change) | none |
| `docs:` | Documentation only | none |
| `refactor:` | Code restructure with no behaviour change | none |
| `test:` | Adding or fixing tests | none |
| `style:` | Formatting, whitespace (no logic change) | none |
| `perf:` | Performance improvement | patch |
| `BREAKING CHANGE:` | Footer or `!` suffix — breaking API change | major |

Examples:
```
feat: add --mode standard-findings scan mode
fix: resolve javascript suite packs correctly
chore: apply black formatting to test_scanner_config
refactor(tests): update imports to use scanner module directly
feat!: remove legacy --output flag
```

Do not include a body or footer beyond what is necessary. Never add a `Co-authored-by` trailer or any attribution to AI tools.

### Pull requests

- Title must follow the same Conventional Commits format as the commit messages above.
- Do not add `Co-authored-by` lines or any AI attribution in the PR body.
- Keep the description concise: what changed and why. Include a brief test evidence section (e.g. "All N tests pass").
- Assign the PR to the appropriate project/milestone if one exists in Kanbus.

### Pre-push checklist

Before pushing a branch or marking a PR ready for review, run the following locally and fix any failures:

```sh
make fix        # auto-format (black + ruff --fix)
make check      # verify fmt + lint are clean (CI-equivalent)
make test       # all tests must pass (unit + BDD)
```

CI runs the same checks. A PR with a failing lint or test step will not be merged.

## Behavior-Driven Development (BDD)

This project uses [pytest-bdd](https://pytest-bdd.readthedocs.io/) to make behavior specifications executable. BDD is mandatory for all new user-facing behavior, following the outside-in process prescribed in `CONTRIBUTING_AGENT.md`.

### Directory layout

```
tests/
  features/       # Gherkin .feature files — one file per feature area
  steps/          # Step definition files — test_<feature>.py per feature file
```

### The process (per CONTRIBUTING_AGENT.md)

1. Write the Gherkin scenario in a `.feature` file before any production code
2. Run `make test` — confirm the scenario is collected and **fails**
3. Write the minimum step definitions and production code to make it pass
4. Refactor while all scenarios stay green

### Writing scenarios

- Feature files live in `tests/features/<area>.feature`
- Step definitions live in `tests/steps/test_<area>.py`
- Each step file must call `scenarios("../features/<area>.feature")` to register all scenarios
- Use `parsers.parse(...)` for steps with quoted parameters, e.g.:

```python
@then(parsers.parse('the report is named "{name}"'))
def report_named(ctx, name): ...
```

- Steps are shared across scenarios via a `ctx` fixture (a plain dict) rather than module-level state
- BDD scenarios test observable behavior (CLI output, file names, command arguments); they do not test internal implementation details

### Running BDD tests

```sh
make test                              # runs everything including BDD
poetry run pytest tests/steps/ -v     # BDD only
```

All scenarios must be green before a PR is opened.

## Commands

```sh
# Install
poetry install --with dev

# Test
make test           # run all tests
make cov            # run tests with coverage report
poetry run pytest tests/test_sarif.py  # run a single test file

# Lint / Format
make check          # fmt-check + lint (CI-safe, no modifications)
make fix            # auto-fix everything (fmt + lint)
make lint           # ruff check only
make fmt            # black + ruff --fix
```

## Architecture

This is a zero-dependency CLI tool (`run-codeql` / `rcql`) that wraps the CodeQL CLI to run GitHub "Code Quality" checks locally.

**Module responsibilities:**

- `run_codeql/cli.py` — Argument parsing and top-level orchestration. Runs language scans in parallel via `ThreadPoolExecutor`, collects `SarifSummary` results, and controls exit codes.
- `run_codeql/scanner.py` — Language auto-detection (walks repo, maps file extensions via `EXT_TO_LANG`) and per-language scan execution (`codeql database create` + `codeql database analyze`).
- `run_codeql/download.py` — CodeQL CLI auto-download to `~/.codeql-tools/` with SHA-256 verification, retry/timeout policy, and safe tar extraction.
- `run_codeql/sarif.py` — SARIF JSON parsing, `--files`/`--rule` fnmatch filtering, `--limit`/`--offset` pagination, and summary text rendering into `SarifSummary` dataclass.
- `run_codeql/settings.py` — All constants: `CODEQL_VERSION`, paths, `EXT_TO_LANG` extension map, `LANG_CONFIG` per-language overrides, `IGNORE_DIRS`, and env-tunable download settings.

**Key data flow:**

1. `cli.py` calls `detect_langs()` (or uses `--lang`) → calls `fetch_codeql()` → calls `run_lang()` per language in parallel threads
2. `run_lang()` invokes `codeql database create` then `codeql database analyze`, writing SARIF to `.codeql/reports/<lang>-code-quality.sarif`
3. `build_sarif_summary()` parses each SARIF file, applies filters/pagination, returns a `SarifSummary` for display and exit-code logic

**Outputs written to the scanned repo (not this repo):**
- `.codeql/db-<lang>/` — CodeQL databases
- `.codeql/reports/<lang>-code-quality.sarif` — scan results

**To update the pinned CodeQL version:** change `CODEQL_VERSION` in `run_codeql/settings.py` and delete `~/.codeql-tools/` to trigger a re-download.

**Tests** use fixture SARIF files in `tests/fixtures/` and do not require a CodeQL installation.
