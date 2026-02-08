"""
PDFConverter — Converts PDF pages to images for Gemini Vision processing.
Uses PyMuPDF (fitz) for high-quality page rendering.
"""

import io
import logging
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger("mtea.pdf")


class PDFConverter:
    """Converts PDF files to images for AI vision processing."""

    def __init__(self, dpi: int = 200):
        self.dpi = dpi
        self.zoom = dpi / 72  # PDF default is 72 DPI

    def pdf_to_images(self, pdf_bytes: bytes, max_pages: int = 10) -> list[bytes]:
        """
        Convert PDF pages to PNG images.

        Args:
            pdf_bytes: Raw PDF file bytes
            max_pages: Maximum pages to convert (default 10)

        Returns:
            List of PNG image bytes, one per page
        """
        images = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = min(len(doc), max_pages)
            logger.info(f"📄 PDF has {len(doc)} pages, converting {page_count}")

            mat = fitz.Matrix(self.zoom, self.zoom)

            for i in range(page_count):
                page = doc[i]
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_bytes = pix.tobytes("png")
                images.append(img_bytes)
                logger.debug(f"  Page {i + 1}: {pix.width}x{pix.height}px")

            doc.close()
        except Exception as e:
            logger.error(f"PDF conversion error: {e}")
            raise ValueError(f"Could not convert PDF: {e}")

        return images

    def get_page_count(self, pdf_bytes: bytes) -> int:
        """Return the number of pages in a PDF."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            count = len(doc)
            doc.close()
            return count
        except Exception:
            return 0

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract raw text from PDF (fallback if vision fails)."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text.strip()
        except Exception as e:
            logger.error(f"PDF text extraction error: {e}")
            return ""
