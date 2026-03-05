from pathlib import Path

from run_codeql.scanner import detect_langs
from run_codeql.settings import IGNORE_DIRS


def make_files(tmp_path: Path, paths: list[str]) -> None:
    for p in paths:
        full = tmp_path / p
        full.parent.mkdir(parents=True, exist_ok=True)
        full.touch()


def test_detects_python(tmp_path):
    make_files(tmp_path, ["src/main.py"])
    assert detect_langs(tmp_path) == ["python"]


def test_detects_rust(tmp_path):
    make_files(tmp_path, ["src/main.rs"])
    assert detect_langs(tmp_path) == ["rust"]


def test_detects_typescript(tmp_path):
    make_files(tmp_path, ["src/index.ts", "src/App.tsx"])
    assert detect_langs(tmp_path) == ["javascript-typescript"]


def test_detects_multiple_languages(tmp_path):
    make_files(tmp_path, ["app.py", "main.rs"])
    assert detect_langs(tmp_path) == ["python", "rust"]


def test_detects_actions_from_workflow(tmp_path):
    make_files(tmp_path, [".github/workflows/ci.yml"])
    assert "actions" in detect_langs(tmp_path)


def test_detects_actions_from_yaml_workflow(tmp_path):
    make_files(tmp_path, [".github/workflows/ci.yaml"])
    assert "actions" in detect_langs(tmp_path)


def test_no_actions_without_workflow_dir(tmp_path):
    make_files(tmp_path, ["app.py"])
    assert "actions" not in detect_langs(tmp_path)


def test_no_actions_with_empty_workflow_dir(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    make_files(tmp_path, ["app.py"])
    assert "actions" not in detect_langs(tmp_path)


def test_ignores_node_modules(tmp_path):
    make_files(tmp_path, ["node_modules/lib/index.js", "src/app.py"])
    assert detect_langs(tmp_path) == ["python"]


def test_ignores_all_ignore_dirs(tmp_path):
    for d in IGNORE_DIRS:
        make_files(tmp_path, [f"{d}/file.rs"])
    make_files(tmp_path, ["src/main.py"])
    assert detect_langs(tmp_path) == ["python"]


def test_empty_repo(tmp_path):
    assert detect_langs(tmp_path) == []


def test_unknown_extensions_ignored(tmp_path):
    make_files(tmp_path, ["README.md", "Makefile", "data.csv"])
    assert detect_langs(tmp_path) == []


def test_result_is_sorted(tmp_path):
    make_files(tmp_path, ["a.rs", "b.py", "c.go"])
    langs = detect_langs(tmp_path)
    assert langs == sorted(langs)
