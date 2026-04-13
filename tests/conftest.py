"""Shared pytest fixtures and helpers for both unit and BDD tests."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def run_rcql(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "run_codeql"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def make_report_dir(tmp_path: Path, *sarif_names: str) -> Path:
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    for name in sarif_names:
        shutil.copy(FIXTURES / name, report_dir / name)
    return report_dir


def write_sarif_with_paths(tmp_path: Path, paths: list[str], lang: str = "python") -> None:
    report_dir = tmp_path / ".codeql" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    sarif = {
        "runs": [
            {
                "tool": {
                    "driver": {
                        "rules": [
                            {
                                "id": "py/unused-import",
                                "shortDescription": {"text": "Unused import"},
                            }
                        ]
                    }
                },
                "results": [
                    {
                        "ruleId": "py/unused-import",
                        "level": "warning",
                        "message": {"text": f"finding-{idx}"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": uri},
                                    "region": {"startLine": idx + 1},
                                }
                            }
                        ],
                    }
                    for idx, uri in enumerate(paths)
                ],
            }
        ]
    }
    (report_dir / f"{lang}-code-quality.sarif").write_text(json.dumps(sarif), encoding="utf-8")


def write_repo_config(tmp_path: Path, payload: dict) -> None:
    (tmp_path / ".rcql.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def cli_ctx(tmp_path):
    """Shared mutable context used by BDD CLI step definitions."""
    return {
        "tmp_path": tmp_path,
        "result": None,
    }
