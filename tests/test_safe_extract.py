import io
import tarfile
from pathlib import Path

import pytest

from run_codeql.download import safe_extract_tar


def make_tar(path: Path, member_name: str) -> None:
    data = b"payload"
    tar_info = tarfile.TarInfo(name=member_name)
    tar_info.size = len(data)
    with tarfile.open(path, "w:gz") as tar:
        tar.addfile(tar_info, io.BytesIO(data))


def test_safe_extract_allows_in_tree_file(tmp_path):
    archive = tmp_path / "safe.tar.gz"
    make_tar(archive, "codeql/readme.txt")
    destination = tmp_path / "out"
    destination.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        safe_extract_tar(tar, destination)
    assert (destination / "codeql" / "readme.txt").is_file()


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.tar.gz"
    make_tar(archive, "../escape.txt")
    destination = tmp_path / "out"
    destination.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        with pytest.raises(ValueError):
            safe_extract_tar(tar, destination)
