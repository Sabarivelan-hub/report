"""Document loader and text extractor supporting PDF (PyMuPDF) and DOCX (python-docx)."""

import os
import re
import logging
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

# PyMuPDF
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# python-docx
try:
    import docx
except ImportError:
    docx = None

logger = logging.getLogger(__name__)


class DocumentLoaderError(Exception):
    """Raised when document loading or parsing fails."""
    pass


class DocumentLoader:
    """Extracts raw and structured text from various document formats."""

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """Clean and normalize extracted text while preserving semantic paragraphs."""
        if not raw_text:
            return ""

        # Normalize unicode spaces and quotes
        text = raw_text.replace("\xa0", " ").replace("\u200b", "")
        text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")

        # Replace multiple carriage returns with standard newlines
        text = re.sub(r"\r\n|\r", "\n", text)

        # Replace excessive whitespace in lines (preserve single newlines)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

        # Group lines, collapsing more than two consecutive empty lines
        cleaned_lines = []
        consecutive_empty = 0
        for line in lines:
            if not line:
                consecutive_empty += 1
                if consecutive_empty <= 1:
                    cleaned_lines.append("")
            else:
                consecutive_empty = 0
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    @classmethod
    def load_pdf(cls, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from PDF using PyMuPDF (fitz)."""
        if fitz is None:
            raise DocumentLoaderError("PyMuPDF (fitz) is not installed.")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        extracted_text_blocks = []
        page_count = 0
        doc_meta = {}

        try:
            with fitz.open(file_path) as doc:
                page_count = len(doc)
                doc_meta = {
                    "pdf_title": doc.metadata.get("title", ""),
                    "pdf_author": doc.metadata.get("author", ""),
                    "pdf_subject": doc.metadata.get("subject", ""),
                    "page_count": page_count,
                }

                for page_num in range(page_count):
                    page = doc.load_page(page_num)
                    text = page.get_text("text")
                    if text:
                        cleaned = cls.clean_text(text)
                        if cleaned:
                            extracted_text_blocks.append(f"--- [Page {page_num + 1}] ---\n{cleaned}")

            full_text = "\n\n".join(extracted_text_blocks)
            return full_text, doc_meta

        except Exception as e:
            logger.error(f"Error parsing PDF with PyMuPDF: {e}")
            raise DocumentLoaderError(f"Failed to parse PDF {file_path}: {e}")

    @classmethod
    def load_docx(cls, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text, headings, and tables from DOCX using python-docx."""
        if docx is None:
            raise DocumentLoaderError("python-docx is not installed.")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")

        try:
            doc = docx.Document(file_path)
            content_blocks = []

            # Extract paragraphs and headings
            for para in doc.paragraphs:
                p_text = para.text.strip()
                if not p_text:
                    continue

                if para.style and para.style.name.startswith("Heading"):
                    content_blocks.append(f"\n## {p_text}")
                else:
                    content_blocks.append(p_text)

            # Extract tables
            for table in doc.tables:
                table_lines = []
                for row in table.rows:
                    row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    table_lines.append(" | ".join(row_cells))
                if table_lines:
                    content_blocks.append("\n" + "\n".join(table_lines))

            full_text = cls.clean_text("\n\n".join(content_blocks))
            doc_meta = {
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(doc.tables),
            }
            return full_text, doc_meta

        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            raise DocumentLoaderError(f"Failed to parse DOCX {file_path}: {e}")

    @classmethod
    def load_text(cls, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract plain text or Markdown files."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        cleaned = cls.clean_text(raw_text)
        return cleaned, {"char_count": len(cleaned)}

    @classmethod
    def load_document(cls, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Universal document loader dispatching by extension."""
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return cls.load_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return cls.load_docx(file_path)
        elif ext in [".txt", ".md", ".json"]:
            return cls.load_text(file_path)
        else:
            # Fallback to plain text attempt
            return cls.load_text(file_path)
