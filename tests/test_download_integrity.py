from pathlib import Path

import pytest

from run_codeql.download import codeql_bundle_platform, compute_sha256, parse_sha256_checksum
from run_codeql.settings import codeql_bin_path


def test_parse_sha256_checksum_finds_expected_file():
    checksum_text = (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  other.tar.gz\n"
        "bc082757b2e6d4fd35f82c8588dbbb05c8c348c6e4456d53ae7cd6b10438d599  codeql-bundle-linux64.tar.gz\n"  # noqa: E501
    )
    result = parse_sha256_checksum(checksum_text, "codeql-bundle-linux64.tar.gz")
    assert result == "bc082757b2e6d4fd35f82c8588dbbb05c8c348c6e4456d53ae7cd6b10438d599"


def test_parse_sha256_checksum_raises_when_missing():
    with pytest.raises(ValueError):
        parse_sha256_checksum(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  other.tar.gz",
            "missing.tar.gz",
        )


def test_compute_sha256(tmp_path: Path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"abc")
    assert (
        compute_sha256(target) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


@pytest.mark.parametrize(
    ("system", "platform_token"),
    [
        ("Linux", "linux64"),
        ("Darwin", "osx64"),
        ("Windows", "win64"),
    ],
)
def test_codeql_bundle_platform(system: str, platform_token: str):
    assert codeql_bundle_platform(system) == platform_token


def test_codeql_bin_path_uses_windows_executable(tmp_path: Path):
    assert (
        codeql_bin_path(system="Windows", tools_dir=tmp_path) == tmp_path / "codeql" / "codeql.exe"
    )


def test_codeql_bin_path_uses_unix_executable(tmp_path: Path):
    assert codeql_bin_path(system="Linux", tools_dir=tmp_path) == tmp_path / "codeql" / "codeql"
