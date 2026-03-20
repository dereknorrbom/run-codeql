.PHONY: help test lint fmt fmt-check typecheck check fix install

POETRY := poetry run
SRC    := run_codeql tests

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  test        Run the test suite"
	@echo "  cov         Run tests with coverage report"
	@echo "  lint        Run ruff (check only)"
	@echo "  fmt         Auto-format with black and ruff --fix"
	@echo "  fmt-check   Check formatting without modifying files"
	@echo "  fix         lint + fmt combined (auto-fix everything)"
	@echo "  check       fmt-check + lint (CI-safe, no modifications)"
	@echo "  install     Install package and dev deps via Poetry"

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

check: fmt-check lint

install:
	poetry install --with dev
