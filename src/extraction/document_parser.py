import hashlib
import base64
import io
import logging
from typing import List, Tuple, Dict, Any, Optional
from src.config.settings import settings
from src.exceptions.errors import DocumentValidationError

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
except ImportError:
    pytesseract = None
    Image = None
    cv2 = None
    np = None

class ParsedDocument:
    def __init__(
        self,
        raw_bytes: bytes,
        sha256_hash: str,
        text_content: str,
        page_images_b64: List[str],
        is_scanned: bool,
        page_count: int,
    ):
        self.raw_bytes = raw_bytes
        self.sha256_hash = sha256_hash
        self.text_content = text_content
        self.page_images_b64 = page_images_b64
        self.is_scanned = is_scanned
        self.page_count = page_count

class DocumentParser:
    """
    Intelligent document parser for digital and scanned PDFs.
    Uses PyMuPDF for fast digital text extraction and Tesseract OCR with OpenCV
    preprocessing for scanned/image-only PDFs (<50 characters per page).
    """
    def __init__(self, char_threshold_per_page: int = 50):
        self.char_threshold = char_threshold_per_page

    def parse(self, file_bytes: bytes, filename: str = "document.pdf") -> ParsedDocument:
        if not file_bytes:
            raise DocumentValidationError("Uploaded document is empty.")
        if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise DocumentValidationError("Uploaded document exceeds the 20 MB size limit.")
        if not file_bytes.startswith(b"%PDF-"):
            raise DocumentValidationError("Uploaded file is not a valid PDF document.")
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        if not fitz:
            raise DocumentValidationError("PDF parsing support is not installed.")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            raise DocumentValidationError("Uploaded PDF could not be opened.") from exc
        page_count = len(doc)
        if page_count < 1 or page_count > settings.MAX_DOCUMENT_PAGES:
            doc.close()
            raise DocumentValidationError(
                f"PDF must contain between 1 and {settings.MAX_DOCUMENT_PAGES} pages."
            )
        extracted_text_spans = []
        page_images_b64 = []
        total_chars = 0

        for page_idx in range(page_count):
            page = doc[page_idx]
            page_text = page.get_text("text") or ""
            extracted_text_spans.append(page_text)
            total_chars += len(page_text.strip())

            # Render 300 DPI image for vision LLM and OCR
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            b64_str = base64.b64encode(img_bytes).decode("utf-8")
            page_images_b64.append(b64_str)

        avg_chars_per_page = total_chars / max(1, page_count)
        is_scanned = avg_chars_per_page < self.char_threshold

        final_text = "\n--- PAGE BREAK ---\n".join(extracted_text_spans)

        # If scanned and pytesseract available, apply OCR pipeline
        if is_scanned and pytesseract and Image:
            ocr_text_spans = []
            for b64_img in page_images_b64:
                raw_img = Image.open(io.BytesIO(base64.b64decode(b64_img)))
                
                # Image preprocessing if cv2 available
                if cv2 and np:
                    cv_img = cv2.cvtColor(np.array(raw_img), cv2.COLOR_RGB2BGR)
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    # Contrast enhancement & Otsu thresholding
                    contrast = cv2.equalizeHist(gray)
                    processed_pil = Image.fromarray(contrast)
                else:
                    processed_pil = raw_img.convert("L")

                try:
                    ocr_text = pytesseract.image_to_string(processed_pil)
                    ocr_text_spans.append(ocr_text)
                except Exception:
                    logger.exception("OCR failed for page %s", len(ocr_text_spans) + 1)
                    ocr_text_spans.append("")
            
            ocr_combined = "\n--- PAGE BREAK ---\n".join(ocr_text_spans)
            if len(ocr_combined.strip()) > len(final_text.strip()):
                final_text = ocr_combined

        doc.close()

        return ParsedDocument(
            raw_bytes=file_bytes,
            sha256_hash=sha256_hash,
            text_content=final_text,
            page_images_b64=page_images_b64,
            is_scanned=is_scanned,
            page_count=page_count,
        )

