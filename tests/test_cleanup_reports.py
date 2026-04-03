from pathlib import Path

from run_codeql.scanner import cleanup_reports


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")


def test_cleanup_reports_keep_true_keeps_existing(tmp_path):
    report_dir = tmp_path / ".codeql" / "reports"
    target = report_dir / "python-code-quality.sarif"
    touch(target)
    cleanup_reports(report_dir, keep=True, langs=["python"])
    assert target.exists()


def test_cleanup_reports_without_langs_clears_all(tmp_path):
    report_dir = tmp_path / ".codeql" / "reports"
    touch(report_dir / "python-code-quality.sarif")
    touch(report_dir / "rust-code-quality.sarif")
    cleanup_reports(report_dir, keep=False, langs=None)
    assert report_dir.exists()
    assert list(report_dir.glob("*.sarif")) == []


def test_cleanup_reports_with_langs_clears_only_targeted(tmp_path):
    report_dir = tmp_path / ".codeql" / "reports"
    py = report_dir / "python-code-quality.sarif"
    py_security = report_dir / "python-security-and-quality.sarif"
    rs = report_dir / "rust-code-quality.sarif"
    act = report_dir / "actions-code-quality.sarif"
    touch(py)
    touch(py_security)
    touch(rs)
    touch(act)
    cleanup_reports(report_dir, keep=False, langs=["actions"])
    assert not act.exists()
    assert py.exists()
    assert py_security.exists()
    assert rs.exists()


def test_cleanup_reports_with_langs_clears_profile_variants(tmp_path):
    report_dir = tmp_path / ".codeql" / "reports"
    py_quality = report_dir / "python-code-quality.sarif"
    py_security = report_dir / "python-security-and-quality.sarif"
    rs_security = report_dir / "rust-security-and-quality.sarif"
    touch(py_quality)
    touch(py_security)
    touch(rs_security)
    cleanup_reports(report_dir, keep=False, langs=["python"])
    assert not py_quality.exists()
    assert not py_security.exists()
    assert rs_security.exists()
