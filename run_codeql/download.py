"""CodeQL download, integrity verification, and safe extraction."""

import hashlib
import os
import platform
import re
import shutil
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, TypeVar

from run_codeql.logging_utils import LOGGER, err, log
from run_codeql.settings import (
    CODEQL_VERSION,
    DOWNLOAD_RETRY_ATTEMPTS,
    DOWNLOAD_RETRY_SLEEP_SECONDS,
    DOWNLOAD_TIMEOUT_SECONDS,
    TOOLS_DIR,
    codeql_bin_path,
)

T = TypeVar("T")


def codeql_bundle_platform(system: str | None = None) -> str:
    """Return the CodeQL bundle platform token for the current operating system."""
    resolved_system = system or platform.system()
    if resolved_system == "Linux":
        return "linux64"
    if resolved_system == "Darwin":
        return "osx64"
    if resolved_system == "Windows":
        return "win64"
    raise ValueError(f"Unsupported platform for CodeQL auto-download: {resolved_system}")


def _is_usable_codeql(path: Path, system: str) -> bool:
    """Return whether a downloaded CodeQL binary can be used on the target OS."""
    if system == "Windows":
        return path.is_file()
    return path.is_file() and os.access(path, os.X_OK)


def fetch_codeql() -> Path:
    """Resolve an executable CodeQL binary, downloading and verifying if needed."""
    which = shutil.which("codeql")
    if which:
        log(f"Using system CodeQL: {which}")
        return Path(which)

    system = platform.system()
    downloaded_codeql = codeql_bin_path(system=system, tools_dir=TOOLS_DIR)
    if _is_usable_codeql(downloaded_codeql, system):
        log(f"Using downloaded CodeQL: {downloaded_codeql}")
        return downloaded_codeql

    try:
        plat = codeql_bundle_platform(system)
    except ValueError as exc:
        err(str(exc))
        sys.exit(1)

    log(f"Downloading CodeQL CLI {CODEQL_VERSION} to {TOOLS_DIR}")
    archive_name = f"codeql-bundle-{plat}.tar.gz"
    url = (
        f"https://github.com/github/codeql-action/releases/download/"
        f"codeql-bundle-v{CODEQL_VERSION}/{archive_name}"
    )
    checksum_url = f"{url}.checksum.txt"
    tmp = TOOLS_DIR / f"{archive_name}.part"
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        download_file_with_retry(url, tmp)
        checksum_text = download_text_with_retry(checksum_url)
        expected_checksum = parse_sha256_checksum(checksum_text, archive_name)
        actual_checksum = compute_sha256(tmp)
        if actual_checksum != expected_checksum:
            raise ValueError(
                f"Checksum mismatch for {archive_name}: expected {expected_checksum}, got {actual_checksum}"  # noqa: E501
            )
        with tarfile.open(tmp, "r:gz") as tar:
            safe_extract_tar(tar, TOOLS_DIR)
    except Exception as exc:
        err(f"Failed to download/install CodeQL: {exc}")
        sys.exit(1)
    finally:
        tmp.unlink(missing_ok=True)

    if not _is_usable_codeql(downloaded_codeql, system):
        err(f"Downloaded CodeQL bundle missing binary at {downloaded_codeql}")
        sys.exit(1)

    if system != "Windows":
        downloaded_codeql.chmod(downloaded_codeql.stat().st_mode | 0o111)
    log(f"Downloaded CodeQL to {downloaded_codeql}")
    return downloaded_codeql


def _with_retries(action: str, operation: Callable[[], T]) -> T:
    """Run an operation with bounded retries and fixed backoff."""
    for attempt in range(1, DOWNLOAD_RETRY_ATTEMPTS + 1):
        try:
            return operation()
        except (OSError, TimeoutError, urllib.error.URLError, ValueError) as exc:
            if attempt == DOWNLOAD_RETRY_ATTEMPTS:
                raise
            LOGGER.warning(
                "%s failed (%s), retrying in %ss (%s/%s)",
                action,
                exc,
                DOWNLOAD_RETRY_SLEEP_SECONDS,
                attempt,
                DOWNLOAD_RETRY_ATTEMPTS,
            )
            time.sleep(DOWNLOAD_RETRY_SLEEP_SECONDS)
    raise RuntimeError(f"{action} failed")


def download_file_with_retry(url: str, destination: Path) -> None:
    """Download a URL to disk with retries and timeout."""

    def _download() -> None:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            with destination.open("wb") as out:
                shutil.copyfileobj(response, out)

    _with_retries(f"Download failed for {url}", _download)


def download_text_with_retry(url: str) -> str:
    """Download UTF-8 text from a URL with retries and timeout."""

    def _download() -> str:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")

    return _with_retries(f"Download failed for {url}", _download)


def parse_sha256_checksum(checksum_text: str, filename: str) -> str:
    """Extract the expected SHA-256 digest for a file from checksum text."""
    for line in checksum_text.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        digest, name = parts[0], parts[1].lstrip("*")
        if name == filename and re.fullmatch(r"[A-Fa-f0-9]{64}", digest):
            return digest.lower()
    raise ValueError(f"Checksum for {filename} not found")


def compute_sha256(path: Path) -> str:
    """Compute the SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract_tar(tar: tarfile.TarFile, destination: Path) -> None:
    """Extract a tar archive while blocking path traversal and link entries."""
    dest = destination.resolve()
    for member in tar.getmembers():
        if member.issym() or member.islnk():
            raise ValueError(f"Refusing to extract link from archive: {member.name}")
        member_path = (dest / member.name).resolve()
        if member_path != dest and dest not in member_path.parents:
            raise ValueError(f"Refusing to extract path outside destination: {member.name}")
    try:
        tar.extractall(dest, filter="data")
    except TypeError:
        tar.extractall(dest)
