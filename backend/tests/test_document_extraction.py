"""
Document/file intake tests — Agent 6 scope.

Covers both layers:
  1. Unit tests for app/services/document_extraction.py (TXT/PDF extraction,
     whitespace normalization, controlled errors).
  2. Integration tests for POST /api/deviations/analyze-file, run with
     FastAPI's TestClient against the deterministic stub AI service (no
     live Groq/network access needed — AI_SERVICE_ENABLED defaults to
     false, see app/services/ai_service_stub.py).

No live PDF/TXT fixtures are checked in: a minimal single-page PDF is
built by hand at test time (raw PDF object syntax) so these tests don't
need an extra dependency like reportlab just to produce a text-bearing
PDF fixture.
"""
import io

import pytest


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _build_minimal_pdf_bytes(text: str) -> bytes:
    """A hand-rolled, minimal single-page PDF containing `text`, extractable
    by pypdf. Good enough as a fixture without pulling in reportlab."""
    content_stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        (
            f"5 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1")
            + content_stream
            + b"\nendstream\nendobj\n"
        ),
    ]

    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode("latin-1")
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    ).encode("latin-1")
    return pdf


def _build_blank_pdf_bytes() -> bytes:
    """A minimal, validly-structured single-page PDF with no /Contents at
    all — stands in for a scanned/image-only PDF with no extractable text."""
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode("latin-1")
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"
    ).encode("latin-1")
    return pdf


# ---------------------------------------------------------------------------
# 1. Unit tests — app/services/document_extraction.py
# ---------------------------------------------------------------------------

def test_txt_extraction_normalizes_text():
    """Test 1: a valid TXT file produces normalized text."""
    from app.services.document_extraction import extract_text_from_upload

    raw = b"Line one.\r\n\r\n\r\n\r\nLine two   with   extra   spaces.   \r\nTrailing.   "
    out = extract_text_from_upload("deviation.txt", raw, "text/plain")

    assert out == "Line one.\n\nLine two with extra spaces.\nTrailing."
    assert "\n\n\n" not in out  # blank-line runs collapsed
    assert "   " not in out  # repeated spaces collapsed


def test_filename_extension_controls_extraction_when_mime_is_misleading():
    """A misleading browser MIME type must not route a PDF through TXT parsing."""
    from app.core.errors import ExtractionFailedError
    from app.services.document_extraction import extract_text_from_upload

    with pytest.raises(ExtractionFailedError):
        extract_text_from_upload("deviation.pdf", b"plain text pretending to be a PDF", "text/plain")


def test_txt_extraction_handles_non_utf8_gracefully():
    """Non-UTF-8 TXT (e.g. legacy Windows export) still extracts instead of raising."""
    from app.services.document_extraction import extract_text_from_upload

    raw = "Café déviation".encode("latin-1")
    out = extract_text_from_upload("legacy.txt", raw, "text/plain")

    assert "d" in out and len(out) > 0


def test_pdf_extraction_returns_readable_text():
    """Test 2: a simple text-based PDF produces readable extracted text."""
    from app.services.document_extraction import extract_text_from_upload

    pdf_bytes = _build_minimal_pdf_bytes("Deviation report content for extraction test.")
    out = extract_text_from_upload("deviation.pdf", pdf_bytes, "application/pdf")

    assert "Deviation report content for extraction test." in out


def test_empty_txt_extracts_to_blank_string():
    """Test 3: an empty/whitespace-only TXT extracts to blank text, which the
    endpoint layer (see test_analyze_file_rejects_empty_txt below) rejects."""
    from app.services.document_extraction import extract_text_from_upload

    out = extract_text_from_upload("empty.txt", b"   \n\n  \t ", "text/plain")
    assert out.strip() == ""


def test_pdf_with_no_extractable_text_raises_controlled_error():
    """Test 4: an image-only/blank PDF raises a controlled extraction error,
    not a raw library exception."""
    from app.core.errors import ExtractionFailedError
    from app.services.document_extraction import extract_text_from_upload

    with pytest.raises(ExtractionFailedError) as exc_info:
        extract_text_from_upload("scanned.pdf", _build_blank_pdf_bytes(), "application/pdf")

    assert "No readable text could be extracted from this PDF." in str(exc_info.value)


def test_corrupted_pdf_raises_controlled_error_without_leaking_internals():
    """A file with a .pdf name that isn't actually a parseable PDF should
    fail safely, and the message must not contain raw library/stack detail."""
    from app.core.errors import ExtractionFailedError
    from app.services.document_extraction import extract_text_from_upload

    with pytest.raises(ExtractionFailedError) as exc_info:
        extract_text_from_upload("not-really.pdf", b"this is not a pdf file", "application/pdf")

    message = str(exc_info.value)
    assert "Traceback" not in message
    assert "pypdf" not in message.lower()


def test_unsupported_extension_raises_controlled_error():
    """Test 5: unsupported extensions/types are rejected."""
    from app.core.errors import UnsupportedFileTypeError
    from app.services.document_extraction import extract_text_from_upload

    with pytest.raises(UnsupportedFileTypeError):
        extract_text_from_upload("deviation.docx", b"some bytes", "application/msword")


# ---------------------------------------------------------------------------
# 2. Endpoint integration tests — POST /api/deviations/analyze-file
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch, tmp_path):
    """TestClient wired to a throwaway SQLite DB (Postgres isn't required
    for these tests — see tests/test_database.py for the DB layer itself)
    and the deterministic stub AI service (AI_SERVICE_ENABLED=false)."""
    db_path = tmp_path / "test_intake.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("AI_SERVICE_ENABLED", "false")

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import app

    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def test_analyze_file_valid_txt_reaches_ai_service(client):
    """Test 7: a valid uploaded file reaches the existing AI service with
    extracted text, and the response matches the canonical AiOutputSchema."""
    files = {"file": ("deviation.txt", b"Batch API-2026-014 temperature excursion.", "text/plain")}
    resp = client.post("/api/deviations/analyze-file", files=files)

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "extraction" in body["data"]
    assert "impact_assessment" in body["data"]
    assert "severity" in body["data"]
    assert "missing_information" in body["data"]


def test_analyze_file_valid_pdf_reaches_ai_service(client):
    pdf_bytes = _build_minimal_pdf_bytes("Batch API-2026-014 temperature excursion.")
    files = {"file": ("deviation.pdf", pdf_bytes, "application/pdf")}
    resp = client.post("/api/deviations/analyze-file", files=files)

    assert resp.status_code == 200
    assert "extraction" in resp.json()["data"]


def test_analyze_file_rejects_empty_txt(client):
    """Test 3 (endpoint level): empty TXT upload is rejected, AI is never called."""
    files = {"file": ("empty.txt", b"", "text/plain")}
    resp = client.post("/api/deviations/analyze-file", files=files)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_FILE"


def test_analyze_file_rejects_whitespace_only_txt(client):
    files = {"file": ("blank.txt", b"   \n\n   ", "text/plain")}
    resp = client.post("/api/deviations/analyze-file", files=files)

    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "EMPTY_SOURCE"


def test_analyze_file_rejects_unreadable_pdf(client):
    """Test 4 (endpoint level): a blank/scanned PDF returns a controlled error."""
    files = {"file": ("scanned.pdf", _build_blank_pdf_bytes(), "application/pdf")}
    resp = client.post("/api/deviations/analyze-file", files=files)

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "EXTRACTION_FAILED"


def test_analyze_file_rejects_unsupported_extension(client):
    """Test 5 (endpoint level): unsupported file type is rejected."""
    files = {"file": ("deviation.docx", b"fake docx bytes", "application/msword")}
    resp = client.post("/api/deviations/analyze-file", files=files)

    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_analyze_file_rejects_oversized_file(client, monkeypatch):
    """Test 6: files exceeding the configured MAX_UPLOAD_SIZE_MB are rejected."""
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")
    from app.core.config import get_settings

    get_settings.cache_clear()

    oversized_content = b"A" * (2 * 1024 * 1024)  # 2MB, over the 1MB limit above
    files = {"file": ("big.txt", oversized_content, "text/plain")}
    resp = client.post("/api/deviations/analyze-file", files=files)

    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"

    get_settings.cache_clear()


def test_analyze_file_no_file_provided_returns_controlled_error(client):
    resp = client.post("/api/deviations/analyze-file")
    # FastAPI/Pydantic's own required-field validation fires before our
    # handler body runs; still surfaced through the same error envelope.
    assert resp.status_code == 422
