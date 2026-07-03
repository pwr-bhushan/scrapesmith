"""Upload extraction + caps (zip-bomb / traversal / size guards)."""
import gzip
import io
import zipfile

import pytest

from app import upload
from app.upload import UploadError, extract_html_files, safe_filename


def _zip(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_bare_html():
    out = extract_html_files("page.html", b"<html></html>")
    assert out == [("page.html", b"<html></html>")]


def test_gzip_single():
    raw = b"<html><body>hi</body></html>"
    out = extract_html_files("page.html.gz", gzip.compress(raw))
    assert out == [("page.html", raw)]


def test_zip_multiple_html_only():
    data = _zip({"a.html": "<a>", "b.htm": "<b>", "notes.txt": "skip", "sub/c.html": "<c>"})
    names = sorted(n for n, _ in extract_html_files("batch.zip", data))
    assert names == ["a.html", "b.htm", "c.html"]  # txt skipped, path flattened


def test_zip_no_html_rejected():
    with pytest.raises(UploadError):
        extract_html_files("batch.zip", _zip({"notes.txt": "x"}))


def test_per_file_cap(monkeypatch):
    monkeypatch.setattr(upload, "MAX_FILE_BYTES", 10)
    with pytest.raises(UploadError):
        extract_html_files("big.html", b"x" * 11)


def test_total_uncompressed_cap(monkeypatch):
    monkeypatch.setattr(upload, "MAX_TOTAL_UNCOMPRESSED", 20)
    data = _zip({"a.html": "x" * 15, "b.html": "y" * 15})
    with pytest.raises(UploadError):
        extract_html_files("batch.zip", data)


def test_bad_gzip_rejected():
    with pytest.raises(UploadError):
        extract_html_files("x.gz", b"not gzip")


def test_safe_filename_strips_traversal():
    assert safe_filename("../../etc/passwd") == "etc_passwd" or "/" not in safe_filename(
        "../../etc/passwd"
    )
    assert "/" not in safe_filename("a/b/c.html")
