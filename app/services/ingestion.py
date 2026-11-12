"""Bounded in-memory expense file ingestion."""

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pandas as pd

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_XLSX_EXPANDED_BYTES = 100 * 1024 * 1024


class IngestionError(ValueError):
    """A user-actionable upload error."""


def read_upload(content: bytes, filename: str) -> pd.DataFrame:
    """Read CSV/XLSX without changing source values; reject oversized workbooks."""
    if not content:
        raise IngestionError("The uploaded file is empty.")
    if len(content) > MAX_BYTES:
        raise IngestionError("File exceeds the 10 MB upload limit.")
    extension = Path(filename).suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise IngestionError("Only CSV and XLSX files are supported.")
    try:
        if extension == ".xlsx":
            with ZipFile(BytesIO(content)) as archive:
                if sum(i.file_size for i in archive.infolist()) > MAX_XLSX_EXPANDED_BYTES:
                    raise IngestionError("Workbook decompressed size exceeds the safe limit.")
            frame = pd.read_excel(
                BytesIO(content), dtype=str, keep_default_na=False, nrows=MAX_ROWS + 1
            )
        else:
            frame = pd.read_csv(
                BytesIO(content),
                dtype=str,
                keep_default_na=False,
                nrows=MAX_ROWS + 1,
                on_bad_lines="error",
            )
    except IngestionError:
        raise
    except (ValueError, UnicodeError, BadZipFile, KeyError, OSError) as exc:
        raise IngestionError(
            "Cannot parse the file. Check its format, encoding and headers."
        ) from exc
    if frame.empty:
        raise IngestionError("The file contains no transactions.")
    if len(frame) > MAX_ROWS:
        raise IngestionError("Files are limited to 100,000 transaction rows.")
    return frame
