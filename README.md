# run-codeql

A pip-installable CLI tool that runs [CodeQL](https://codeql.github.com/) analysis locally. By default it runs the `security-and-quality` suite profile and can honor repository CodeQL query profile settings.

## Installation

```sh
pip install run-codeql
```

This installs two commands: `run-codeql` and the shorthand `rcql`.

## Requirements

- Python 3.10+
- CodeQL CLI — auto-downloaded on Linux, macOS, and Windows to `~/.codeql-tools/` on first run if not already on `PATH` (SHA-256 verified, with retry/timeout policy)

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
| `--files` | Comma-separated file paths or fnmatch patterns to restrict findings to (e.g. `src/foo.py` or `src/*.py`) |
| `--exclude-files` | Comma-separated file paths or fnmatch patterns to exclude from findings (e.g. `src/generated/**`) |
| `--rule` | Comma-separated rule IDs or fnmatch patterns to restrict findings to (e.g. `py/unused-import` or `py/*`) |
| `--limit N` | Return at most N findings (after `--files`/`--rule` filtering) |
| `--offset N` | Skip the first N findings before applying `--limit` (for pagination) |
| `--mode` | Scan mode: `default` (repo-config-driven) or `standard-findings` (full-repo code-quality parity mode) |
| `--include-third-party` | Include findings from third-party/vendor paths (default output suppresses common dependency noise) |
| `--config` | Repo config filename to load from repo root (default: `.rcql.json`; pass `--config ''` to disable) |
| `--keep-db` | Reuse existing databases instead of recreating them |
| `--keep-reports` | Do not delete prior SARIF reports before running |
| `--no-fail` | Exit 0 even if findings or scan errors exist |

Download behavior can be tuned with environment variables:
`RCQL_DOWNLOAD_TIMEOUT_SECONDS`, `RCQL_DOWNLOAD_RETRY_ATTEMPTS`, and `RCQL_DOWNLOAD_RETRY_SLEEP_SECONDS`.

Report cleanup behavior before scans:
- with `--lang`, only the matching `<lang>-*.sarif` reports are replaced
- without `--lang`, all prior SARIF reports are cleared first
- with `--keep-reports`, no reports are deleted

### Language auto-detection

When `--lang` is not specified, the tool scans the repo for source files and detects which CodeQL languages to run. Common dependency directories are skipped (`node_modules`, `vendor`, `target`, `.venv`, etc.).

Supported languages: `python`, `rust`, `javascript-typescript`, `go`, `java`, `csharp`, `cpp`, `ruby`, `swift`, `actions`

GitHub Actions workflows (`.github/workflows/*.yml` and `.github/workflows/*.yaml`) are detected automatically and trigger the `actions` scanner.

### Outputs

- Databases: `.codeql/db-<lang>/`
- SARIF reports: `.codeql/reports/<lang>-<profile>.sarif`

A `.codeql/.gitignore` with `*` is created automatically on first run so these artifacts are not committed.

By default, `rcql` exits non-zero if any findings are present or any language scan fails. Use `--no-fail` to force a zero exit code for informational/reporting workflows.

### Suite selection

- default profile: `security-and-quality`
- repo override: when `.github/codeql/codeql-config.yml` contains top-level `queries: - uses: ...`, rcql uses that selector for analysis
- currently supported query selectors: `security-and-quality`, `code-quality`

## Common workflows

### Full scan

```sh
cd ~/projects/my-repo
rcql
```

### GitHub standard findings parity scan

```sh
rcql --mode standard-findings
```

### Quick re-summary after a previous scan

```sh
rcql --report-only
rcql --report-only --verbose
rcql --report-only --lang rust
```

### Agent-friendly output

Produces clean, structured output suitable for an AI agent — no log noise, findings include rule ID, file location, and message:

```sh
rcql -q -v --report-only
```

Example output:

```
[python] SARIF: /path/to/.codeql/reports/python-security-and-quality.sarif
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

### Filtering findings for large codebases

When a scan returns hundreds or thousands of findings, use `--files`, `--rule`, `--limit`, and `--offset` to slice the results. These flags work with both `--report-only` and live scans.

By default, summary output suppresses common third-party/build noise paths such as:
`node_modules`, `vendor`, `dist`, `build`, `out`, `coverage`, `.next`, and `.codeql` mirror artifacts.
Use `--include-third-party` to opt in to those findings.

### Repository config (`.rcql.json`)

You can define default filters and language selection per repository:

```json
{
  "langs": ["javascript-typescript", "python"],
  "files": ["src/**"],
  "exclude_files": ["frontend/dist/**", "**/generated/**"],
  "rules": ["js/*", "py/*"],
  "include_third_party": false
}
```

Precedence is:
1. Built-in defaults
2. `.rcql.json`
3. CLI flags (highest)

**Filter to a specific file:**

```sh
rcql -q -v --report-only --files src/models/user.py
```

**Filter using a glob pattern:**

```sh
rcql -q -v --report-only --files 'src/api/*.py'
```

**Filter to a specific rule:**

```sh
rcql -q -v --report-only --rule py/unused-import
```

**Filter to an entire rule category:**

```sh
rcql -q -v --report-only --rule 'py/*'
```

**Combine file and rule filters:**

```sh
rcql -q -v --report-only --files src/models/user.py --rule py/unused-import
```

**Paginate through a large result set:**

```sh
# First 20 findings
rcql -q -v --report-only --limit 20

# Next 20
rcql -q -v --report-only --limit 20 --offset 20
```

When any filter or pagination flag is active, the summary line changes from `Total: N` to `Shown: X  (matched: Y)` so you can see both how many were returned and how many matched in total.

Language blocks with zero matching findings are automatically suppressed when `--files` or `--rule` is active, so only relevant output is shown.

### Single-language scan

```sh
rcql --lang actions --no-fail
```

## Parallel execution

When scanning multiple languages, all scans run in parallel with CPU threads divided evenly across languages. Log timestamps make this visible.

## Upgrading CodeQL

The CodeQL version is pinned in the package. The checksum for each release is fetched live from GitHub at download time, so no manual SHA updates are needed. To use a newer CodeQL version, update `CODEQL_VERSION` in `run_codeql/settings.py` and delete `~/.codeql-tools/` to trigger a fresh download on next run.

## Development

```sh
git clone https://github.com/YOUR_USERNAME/run-codeql
cd run-codeql
pip install -e ".[dev]"
```

### Make targets

| Target | Description |
|--------|-------------|
| `make test` | Run the test suite |
| `make cov` | Run tests with coverage report |
| `make lint` | Run ruff (check only) |
| `make fmt` | Auto-format with black and ruff --fix |
| `make fmt-check` | Check formatting without modifying files |
| `make check` | fmt-check + lint (CI-safe, no modifications) |
| `make fix` | lint + fmt combined (auto-fix everything) |
| `make install` | Install in editable mode with dev deps |

### Running tests

```sh
make test       # run all 100+ tests
make cov        # with per-line coverage report
```

Tests cover SARIF filtering, language detection, download integrity, extraction safety, and CLI behavior using fixture SARIF files. No CodeQL installation is required to run the tests.

### Package layout

| File | Purpose |
|------|---------|
| `run_codeql/cli.py` | Argument parsing and orchestration |
| `run_codeql/download.py` | CodeQL download, retry, checksum, extraction |
| `run_codeql/scanner.py` | Language detection and per-language scan execution |
| `run_codeql/sarif.py` | SARIF parsing, filtering, and summary rendering |
| `run_codeql/settings.py` | Constants and environment-tunable defaults |

## Contributing

Contributions are welcome. Please:

1. Fork the repo and create a feature branch
2. Run `make check` and `make test` before submitting
3. Open a pull request with a clear description of the change

## License

MIT


> Note: This README was modified as part of the Kanbus/Tactus orchestration smoke test.