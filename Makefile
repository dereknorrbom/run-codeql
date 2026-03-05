.PHONY: help test lint fmt fmt-check typecheck check fix install

PYTHON := python
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
	@echo "  install     Install package in editable mode with dev deps"

test:
	$(PYTHON) -m pytest tests/

cov:
	$(PYTHON) -m pytest tests/ --cov=run_codeql --cov-report=term-missing

lint:
	ruff check $(SRC)

fmt:
	black $(SRC)
	ruff check --fix $(SRC)

fmt-check:
	black --check $(SRC)
	ruff check $(SRC)

fix: fmt lint

check: fmt-check lint

install:
	pip install -e ".[dev]"
