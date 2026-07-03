"""Upload ingestion: caps + extraction of .html / .gz / .zip into (filename, bytes) pairs.

Security (§14): caps enforced BEFORE extraction (zip-bomb guard); filenames sanitized to a basename
(no path traversal); only html files kept.
"""
from __future__ import annotations

import gzip
import io
import re
import zipfile

MAX_FILES = 500
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB per html
MAX_ARCHIVE_BYTES = 50 * 1024 * 1024  # 50 MB compressed archive
MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024  # 200 MB total extracted

_HTML_EXT = (".html", ".htm")
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class UploadError(ValueError):
    """Raised on a cap/validation breach; mapped to HTTP 400 by the route."""


def safe_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1].strip() or "file.html"
    base = _SAFE.sub("_", base)
    return base.lstrip(".") or "file.html"


def _is_html(name: str) -> bool:
    return name.lower().endswith(_HTML_EXT)


def extract_html_files(filename: str, data: bytes) -> list:
    """Return [(safe_filename, html_bytes)]. Raises UploadError on any cap/validation breach."""
    lower = filename.lower()

    if lower.endswith(".zip"):
        if len(data) > MAX_ARCHIVE_BYTES:
            raise UploadError(f"archive exceeds {MAX_ARCHIVE_BYTES} bytes")
        return _extract_zip(data)

    if lower.endswith(".gz"):
        try:
            raw = gzip.decompress(data)
        except OSError as e:
            raise UploadError(f"invalid gzip: {e}") from e
        if len(raw) > MAX_FILE_BYTES:
            raise UploadError(f"file exceeds {MAX_FILE_BYTES} bytes")
        return [(safe_filename(filename[:-3]), raw)]

    # bare html (or unknown ext treated as single html)
    if len(data) > MAX_FILE_BYTES:
        raise UploadError(f"file exceeds {MAX_FILE_BYTES} bytes")
    return [(safe_filename(filename), data)]


def _extract_zip(data: bytes) -> list:
    out = []
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir() and _is_html(i.filename)]
        if not infos:
            raise UploadError("zip contains no .html files")
        if len(infos) > MAX_FILES:
            raise UploadError(f"archive has more than {MAX_FILES} html files")
        for info in infos:
            # zip-bomb guard: trust declared uncompressed size for the pre-check
            if info.file_size > MAX_FILE_BYTES:
                raise UploadError(f"{info.filename} exceeds {MAX_FILE_BYTES} bytes")
            total += info.file_size
            if total > MAX_TOTAL_UNCOMPRESSED:
                raise UploadError(f"archive exceeds {MAX_TOTAL_UNCOMPRESSED} bytes uncompressed")
            out.append((safe_filename(info.filename), zf.read(info)))
    return out
