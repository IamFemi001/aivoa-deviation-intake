"""
Extracts raw text from an uploaded deviation document so it can be handed
to the AI service the same way pasted text is. Kept separate from
ai_service.py so the "how do we read a PDF" concern never leaks into the
AI abstraction.

Callers (see app/api/deviations.py) are responsible for filename/extension
and file-size validation before calling extract_text_from_upload(); this
module owns only "given bytes we've already decided to treat as a PDF or
TXT, turn them into clean, normalized text (or raise a controlled error)".
"""
import io
import logging
import re

from app.core.errors import ExtractionFailedError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)

# Collapse runs of horizontal whitespace (spaces/tabs) to a single space,
# and cap blank-line runs at one blank line, so extracted text is readable
# and consistent regardless of a source PDF/TXT's original formatting.
_HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
_BLANK_LINE_RUN_RE = re.compile(r"\n[ \t]*\n[ \t\n]*\n+")
_TRAILING_LINE_WHITESPACE_RE = re.compile(r"[ \t]+\n")


def extract_text_from_upload(filename: str, content: bytes, content_type: str | None) -> str:
    """
    Returns normalized plain text extracted from an uploaded file.
    Supports .txt (and anything text/plain) and .pdf for the MVP, matching
    the frontend's allowed-file check in deviationApi.analyzeFile().

    Raises UnsupportedFileTypeError or ExtractionFailedError (see
    app/core/errors.py) on failure; never returns partially-garbled text
    silently and never leaks library/stack-trace details to the caller.
    """
    lower_name = filename.lower()

    # The filename extension is authoritative. The API route validates the
    # extension before calling this function, and using the extension here
    # prevents a misleading browser MIME type from routing a PDF through the
    # TXT extractor (or vice versa).
    if lower_name.endswith(".txt"):
        return _normalize_whitespace(_extract_txt(content))

    if lower_name.endswith(".pdf"):
        return _normalize_whitespace(_extract_pdf(content))

    raise UnsupportedFileTypeError("Only PDF and TXT files are supported.")


def _normalize_whitespace(text: str) -> str:
    """
    Tidy up extraction artifacts while preserving paragraph structure:
      - normalize Windows/Mac line endings to \n
      - strip trailing spaces/tabs at the end of each line
      - collapse repeated spaces/tabs within a line to one space
      - collapse 2+ blank lines in a row down to a single blank line
      - trim leading/trailing whitespace on the document as a whole
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Drop stray NUL bytes some PDF/text extractors can emit.
    normalized = normalized.replace("\x00", "")
    normalized = _HORIZONTAL_WHITESPACE_RE.sub(" ", normalized)
    normalized = _TRAILING_LINE_WHITESPACE_RE.sub("\n", normalized)
    normalized = _BLANK_LINE_RUN_RE.sub("\n\n", normalized)
    return normalized.strip()


def _extract_txt(content: bytes) -> str:
    try:
        # UTF-8 (the common case for pasted/exported deviation text) first;
        # fall back to latin-1, which never raises, so unusual-but-legitimate
        # exports (e.g. from older Windows tools) don't get rejected outright.
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            logger.info("Uploaded TXT was not valid UTF-8; falling back to latin-1 decoding.")
            return content.decode("latin-1")
    except Exception as exc:  # noqa: BLE001
        logger.exception("TXT decoding failed for upload")
        raise ExtractionFailedError("Could not read this text file.") from exc


def _extract_pdf(content: bytes) -> str:
    try:
        # pypdf is a small, pure-Python dependency — fine for an MVP.
        # Swap for a more robust extractor (e.g. unstructured, pdfplumber)
        # if scanned/complex PDFs need OCR later.
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(io.BytesIO(content))
        except PdfReadError as exc:
            logger.warning("Uploaded file is not a valid/parseable PDF: %s", exc)
            raise ExtractionFailedError(
                "The uploaded file could not be read as a PDF. It may be corrupted "
                "or not a real PDF file."
            ) from exc

        if getattr(reader, "is_encrypted", False):
            raise ExtractionFailedError(
                "This PDF is password-protected. Please upload an unprotected PDF."
            )

        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages_text).strip()

        if not text:
            raise ExtractionFailedError("No readable text could be extracted from this PDF.")
        return text
    except ExtractionFailedError:
        raise
    except Exception as exc:  # noqa: BLE001
        # Never surface the raw library exception (may include internal
        # details) to the API response — log it, return a safe message.
        logger.exception("PDF extraction failed for upload")
        raise ExtractionFailedError("Could not read this PDF file.") from exc
