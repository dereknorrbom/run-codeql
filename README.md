# run-codeql

A pip-installable CLI tool that runs [CodeQL](https://codeql.github.com/) code-quality analysis locally, mirroring the GitHub "Code Quality" check. Install once, run from any repository.

## Installation

```sh
pip install -e ~/Projects/run-codeql
```

Or from wherever you cloned it:

```sh
pip install -e /path/to/run-codeql
```

This installs two commands: `run-codeql` and the shorthand `rcql`.

## Requirements

- Python 3.10+
- CodeQL CLI — auto-downloaded to `~/.codeql-tools/` on first run if not already on `PATH`

## Usage

Run from the root of any repository:

```sh
rcql                        # auto-detect languages, run full scan
rcql --lang python          # scan only Python
rcql --lang python,actions  # scan multiple specific languages
```

### Options

| Flag | Description |
|------|-------------|
| `--lang` | Comma-separated languages to scan (default: auto-detected) |
| `--report-only` | Skip scanning; summarize existing SARIF reports from the last run |
| `--verbose`, `-v` | Print each finding with rule ID, location, and message |
| `--quiet`, `-q` | Suppress log output; print only final summaries (for agent/scripted use) |
| `--keep-db` | Reuse existing databases instead of recreating them |
| `--keep-reports` | Do not delete prior SARIF reports before running |
| `--no-fail` | Exit 0 even if findings exist |

### Language auto-detection

When `--lang` is not specified, the tool scans the repo for source files and detects which CodeQL languages to run. Common dependency directories are skipped (`node_modules`, `vendor`, `target`, `.venv`, etc.).

Supported languages: `python`, `rust`, `javascript-typescript`, `go`, `java`, `csharp`, `cpp`, `ruby`, `swift`, `actions`

GitHub Actions workflows (`.github/workflows/*.yml`) are detected automatically and trigger the `actions` scanner.

### Outputs

- Databases: `.codeql/db-<lang>/`
- SARIF reports: `.codeql/reports/<lang>-code-quality.sarif`

A `.codeql/.gitignore` with `*` is created automatically on first run so these artifacts are not committed.

## Common workflows

### Full scan

```sh
cd ~/Projects/my-repo
rcql
```

### Quick re-summary after a previous scan

```sh
rcql --report-only
rcql --report-only --verbose
rcql --report-only --lang rust
```

### Agent-friendly output (quiet + verbose)

Produces clean, structured output suitable for pasting into an AI agent for remediation — no log noise, findings include rule ID, file location, and message:

```sh
rcql -q -v --report-only
```

Example output:

```
[python] SARIF: /path/to/.codeql/reports/python-code-quality.sarif
  error: 1
  warning: 2
  Total: 3

  [error] py/sql-injection
    SQL injection
    src/db.py:42
    This query depends on user-provided value.

  [warning] py/unused-import
    Unused import
    src/utils.py:3
    Import of 'os' is not used.
```

### Single-language scan

```sh
rcql --lang actions --no-fail
```

## Parallel execution

When scanning multiple languages, all scans run in parallel with CPU threads divided evenly across languages. Log timestamps make this visible.

## Development

```sh
cd ~/Projects/run-codeql
pip install -e ".[dev]"
pytest
```

Tests cover `summarize_sarif`, `detect_langs`, and CLI smoke tests (run against fixture SARIF files without invoking CodeQL).
