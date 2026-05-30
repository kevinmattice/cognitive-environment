from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO


class PdfTextExtractionError(RuntimeError):
    """Raised when declared PDF text extraction fails."""


@dataclass(frozen=True)
class PdfTextExtractionResult:
    text: str
    page_count: int
    had_any_text: bool


def extract_pdf_text(pdf_bytes: bytes, *, max_output_bytes: int) -> PdfTextExtractionResult:
    if not isinstance(pdf_bytes, (bytes, bytearray)):
        raise PdfTextExtractionError("invalid pdf_bytes (expected bytes)")
    if not isinstance(max_output_bytes, int) or max_output_bytes <= 0:
        raise PdfTextExtractionError("invalid max_output_bytes (expected positive int)")

    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - exercised only when dependency missing
        raise PdfTextExtractionError("pypdf is not installed; cannot read declared PDF sources") from exc

    try:
        reader = PdfReader(BytesIO(bytes(pdf_bytes)))
    except Exception as exc:
        raise PdfTextExtractionError(f"PDF unreadable: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        try:
            ok = reader.decrypt("")  # type: ignore[attr-defined]
        except Exception as exc:
            raise PdfTextExtractionError("PDF is encrypted; cannot extract text (no decryption support)") from exc
        if not ok:
            raise PdfTextExtractionError("PDF is encrypted; cannot extract text (no decryption support)")

    parts: list[str] = []
    used_bytes = 0
    had_any_text = False

    pages = getattr(reader, "pages", None)
    if pages is None:
        raise PdfTextExtractionError("PDF unreadable: missing pages")

    for idx, page in enumerate(pages, start=1):
        marker = f"--- page {idx} ---\n"
        marker_b = marker.encode("utf-8")
        if used_bytes + len(marker_b) > max_output_bytes:
            raise PdfTextExtractionError(f"extracted text exceeds max_read_bytes ({max_output_bytes} bytes)")
        parts.append(marker)
        used_bytes += len(marker_b)

        try:
            page_text = page.extract_text()  # type: ignore[no-untyped-call]
        except Exception as exc:
            raise PdfTextExtractionError(f"PDF unreadable: page {idx} extraction failed: {exc}") from exc

        if not page_text:
            parts.append("\n")
            used_bytes += 1
            continue

        if page_text.strip():
            had_any_text = True

        chunk = page_text.rstrip() + "\n\n"
        chunk_b = chunk.encode("utf-8")
        if used_bytes + len(chunk_b) > max_output_bytes:
            raise PdfTextExtractionError(f"extracted text exceeds max_read_bytes ({max_output_bytes} bytes)")
        parts.append(chunk)
        used_bytes += len(chunk_b)

    page_count = len(pages)
    return PdfTextExtractionResult(text="".join(parts).strip() + "\n", page_count=page_count, had_any_text=had_any_text)
