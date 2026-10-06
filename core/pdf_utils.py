"""PDF text extraction and hashing."""
from __future__ import annotations

import hashlib
import io
import re

from pypdf import PdfReader


class PdfError(Exception):
    """Raised when a PDF cannot be read or contains no extractable text."""


def file_hash(data: bytes) -> str:
    """Return the SHA-256 hex digest of the file bytes."""
    return hashlib.sha256(data).hexdigest()


def clean_text(text: str) -> str:
    """Normalise whitespace while keeping paragraph breaks."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(data: bytes) -> str:
    """Extract text from PDF bytes. Raises PdfError if unreadable or image-only."""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:
        raise PdfError("That file could not be read as a PDF.") from exc
    text = clean_text("\n\n".join(pages))
    if len(text) < 20:
        raise PdfError("No selectable text found. Scanned/image-only PDFs are not supported yet.")
    return text
