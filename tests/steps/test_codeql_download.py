import hashlib
import io
import tarfile

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import run_codeql.download as download

scenarios("../features/codeql_download.feature")


@pytest.fixture()
def download_ctx(tmp_path, monkeypatch):
    tools_dir = tmp_path / ".codeql-tools"
    downloaded_urls: list[str] = []

    def fake_download_file(url, destination):
        downloaded_urls.append(url)
        data = b"@echo off\r\n"
        tar_info = tarfile.TarInfo("codeql/codeql.exe")
        tar_info.size = len(data)
        with tarfile.open(destination, "w:gz") as tar:
            tar.addfile(tar_info, io.BytesIO(data))

    def fake_download_text(_url):
        archive = tools_dir / "codeql-bundle-win64.tar.gz.part"
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        return f"{digest}  codeql-bundle-win64.tar.gz\n"

    monkeypatch.setattr(download, "TOOLS_DIR", tools_dir)
    monkeypatch.setattr(download.shutil, "which", lambda _name: None)
    monkeypatch.setattr(download, "download_file_with_retry", fake_download_file)
    monkeypatch.setattr(download, "download_text_with_retry", fake_download_text)

    return {
        "downloaded_urls": downloaded_urls,
        "result": None,
    }


@given("no CodeQL executable is already installed")
def no_codeql_executable(download_ctx):
    assert download_ctx["result"] is None


@given(parsers.parse('the operating system is "{system}"'))
def operating_system(download_ctx, monkeypatch, system):
    monkeypatch.setattr(download.platform, "system", lambda: system)


@when("CodeQL is resolved for rcql")
def resolve_codeql(download_ctx):
    download_ctx["result"] = download.fetch_codeql()


@then("the Windows CodeQL bundle is downloaded")
def windows_bundle_downloaded(download_ctx):
    assert download_ctx["downloaded_urls"]
    assert download_ctx["downloaded_urls"][0].endswith("/codeql-bundle-win64.tar.gz")


@then(parsers.parse('the resolved CodeQL executable is "{name}"'))
def resolved_executable_name(download_ctx, name):
    assert download_ctx["result"].name == name
