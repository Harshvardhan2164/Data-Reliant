"""File and source validation for Data Ingestion."""

from __future__ import annotations

import hashlib
from pathlib import Path

import chardet

from datareliant.common.config import get_settings
from datareliant.common.exceptions import (
    FileTooLargeError,
    IngestionError,
    UnsupportedFormatError,
)

SUPPORTED_EXTENSIONS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".parquet": "parquet",
    ".pq": "parquet",
}


def validate_file_path(file_path: Path | str) -> Path:
    """Validate that the file exists and is readable."""
    path = Path(file_path)
    if not path.exists():
        raise IngestionError(
            f"File does not exist: {path}",
            details={"file_path": str(path)},
        )
    if not path.is_file():
        raise IngestionError(
            f"Specified path is not a file: {path}",
            details={"file_path": str(path)},
        )
    return path


def validate_file_size(path: Path, max_bytes: int | None = None) -> int:
    """Ensure file size is within permitted threshold."""
    if max_bytes is None:
        settings = get_settings()
        max_bytes = settings.max_upload_bytes

    size = path.stat().st_size
    if size > max_bytes:
        raise FileTooLargeError(
            f"File size {size} bytes exceeds maximum allowed {max_bytes} bytes",
            details={
                "file_size_bytes": size,
                "max_allowed_bytes": max_bytes,
                "file_path": str(path),
            },
        )
    return size


def validate_file_format(path: Path) -> str:
    """Validate format suffix and return standard format identifier."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported file format '{suffix}'. Supported formats: {list(SUPPORTED_EXTENSIONS.keys())}",
            details={
                "extension": suffix,
                "supported": list(SUPPORTED_EXTENSIONS.keys()),
                "file_path": str(path),
            },
        )
    return SUPPORTED_EXTENSIONS[suffix]


def detect_file_encoding(path: Path, sample_size: int = 65536) -> str:
    """Detect encoding of text files using chardet. Defaults to utf-8."""
    try:
        with open(path, "rb") as f:
            raw = f.read(sample_size)
        if not raw:
            return "utf-8"
        detected = chardet.detect(raw)
        encoding = detected.get("encoding")
        return encoding or "utf-8"
    except Exception:
        return "utf-8"


def compute_file_hash(path: Path) -> str:
    """Compute sha256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1048576):  # 1MB chunks
            hasher.update(chunk)
    return hasher.hexdigest()
