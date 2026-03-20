.PHONY: help test cov lint fmt fmt-check check fix install lock lock-check update audit

POETRY := poetry run
SRC    := run_codeql tests

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  install     Install package and dev deps via Poetry"
	@echo "  lock        Regenerate poetry.lock from pyproject.toml"
	@echo "  lock-check  Verify poetry.lock is up to date (non-destructive)"
	@echo "  update      Update all dev dependencies to latest allowed versions"
	@echo "  audit       Scan dependencies for known vulnerabilities (requires osv-scanner)"
	@echo ""
	@echo "  test        Run the test suite"
	@echo "  cov         Run tests with coverage report"
	@echo "  lint        Run ruff (check only)"
	@echo "  fmt         Auto-format with black and ruff --fix"
	@echo "  fmt-check   Check formatting without modifying files"
	@echo "  fix         lint + fmt combined (auto-fix everything)"
	@echo "  check       fmt-check + lint (CI-safe, no modifications)"

install:
	poetry install --with dev

lock:
	poetry lock

lock-check:
	poetry check --lock

update:
	poetry update --with dev

audit:
	osv-scanner --lockfile poetry.lock

test:
	$(POETRY) pytest tests/

cov:
	$(POETRY) pytest tests/ --cov=run_codeql --cov-report=term-missing

lint:
	$(POETRY) ruff check $(SRC)

fmt:
	$(POETRY) black $(SRC)
	$(POETRY) ruff check --fix $(SRC)

fmt-check:
	$(POETRY) black --check $(SRC)
	$(POETRY) ruff check $(SRC)

fix: fmt lint

check: lock-check fmt-check lint
