import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core.pdf_utils import PdfError, clean_text, extract_text, file_hash


def make_pdf(text: str) -> bytes:
    """Build a minimal one-page PDF containing ``text``."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def test_hash_is_deterministic_and_sensitive():
    assert file_hash(b"abc") == file_hash(b"abc")
    assert file_hash(b"abc") != file_hash(b"abd")
    assert len(file_hash(b"abc")) == 64


def test_extract_text_from_pdf():
    text = extract_text(make_pdf("Senior Data Analyst with five years of SQL experience"))
    assert "Data Analyst" in text and "SQL" in text


def test_invalid_pdf_raises_friendly_error():
    with pytest.raises(PdfError):
        extract_text(b"this is not a pdf")


def test_clean_text_collapses_whitespace():
    assert clean_text("a   b\n\n\n\nc \x00") == "a b\n\nc"
