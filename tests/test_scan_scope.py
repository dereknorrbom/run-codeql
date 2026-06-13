from run_codeql.scanner import build_scoped_source_root, resolve_scan_scope_files


def test_resolve_scan_scope_files_supports_literal_and_glob(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "src" / "b.py").write_text("print('b')\n", encoding="utf-8")
    (tmp_path / "src" / "c.ts").write_text("console.log('c')\n", encoding="utf-8")

    files = resolve_scan_scope_files(tmp_path, ["src/a.py", "src/*.py"])
    assert [str(path.relative_to(tmp_path)) for path in files] == ["src/a.py", "src/b.py"]


def test_resolve_scan_scope_files_ignores_outside_paths(tmp_path):
    outside = tmp_path.parent / "outside.py"
    outside.write_text("print('x')\n", encoding="utf-8")

    files = resolve_scan_scope_files(tmp_path, [str(outside)])
    assert files == []


def test_build_scoped_source_root_preserves_relative_paths(tmp_path):
    repo_root = tmp_path / "repo"
    destination = tmp_path / "scope"
    nested = repo_root / "src" / "pkg"
    nested.mkdir(parents=True)
    source = nested / "module.py"
    source.write_text("print('hello')\n", encoding="utf-8")

    build_scoped_source_root(repo_root=repo_root, files=[source], destination=destination)

    copied = destination / "src" / "pkg" / "module.py"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == "print('hello')\n"
