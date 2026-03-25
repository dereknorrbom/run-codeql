# AGENTS.md

## Project management with Kanbus

Use Kanbus for task management.
Why: Kanbus task management is MANDATORY here; every task must live in Kanbus.
When: Create/update the Kanbus task before coding; close it only after the change lands.
How: See CONTRIBUTING_AGENT.md for the Kanbus workflow, hierarchy, status rules, priorities, command examples, and the sins to avoid. Never inspect project/ or issue JSON directly (including with cat or jq); use Kanbus commands only.
Performance: Prefer kbs (Rust) when available; kanbus (Python) is equivalent but slower.
Warning: Editing project/ directly is a sin against The Way. Do not read or write anything in project/; work only through Kanbus.

This file provides guidance to AI coding agents when working with code in this repository.

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
