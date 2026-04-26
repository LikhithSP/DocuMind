"""Text extraction for PDF, DOCX, and TXT files.
TICKET-102: Extracts clean text with page number preservation, table formatting,
and robust failure handling for unextractable/corrupted files.
"""
from typing import List, Dict, Any, Tuple
from pathlib import Path
import pypdf
from docx import Document as DocxDocument

class ExtractedPage:
    def __init__(self, page_number: int, text: str):
        self.page_number = page_number
        self.text = text

class DocumentExtractor:
    @staticmethod
    def extract_from_file(file_path: str, filename: str) -> Tuple[List[ExtractedPage], int]:
        """Extracts text from PDF, DOCX, or TXT file.
        Returns a tuple of (pages_list, total_page_count).
        Raises ValueError if file cannot be parsed or contains no extractable text.
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            return DocumentExtractor._extract_pdf(file_path)
        elif ext == ".docx":
            return DocumentExtractor._extract_docx(file_path)
        elif ext in [".txt", ".md"]:
            return DocumentExtractor._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Only PDF, DOCX, TXT are supported.")

    @staticmethod
    def _extract_pdf(file_path: str) -> Tuple[List[ExtractedPage], int]:
        pages: List[ExtractedPage] = []
        try:
            reader = pypdf.PdfReader(file_path)
            num_pages = len(reader.pages)
            if num_pages == 0:
                raise ValueError("PDF file has 0 pages.")
            
            for idx, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                # Strip null bytes and normalize whitespace
                clean_text = page_text.replace("\x00", " ").strip()
                if clean_text:
                    pages.append(ExtractedPage(page_number=idx, text=clean_text))
            
            total_extracted_length = sum(len(p.text) for p in pages)
            if total_extracted_length < 10:
                raise ValueError("Document has no extractable text (likely scanned image or empty PDF). OCR is not supported in v1.")
            
            return pages, num_pages
        except Exception as e:
            if "no extractable text" in str(e):
                raise
            raise ValueError(f"Failed to extract PDF: {str(e)}")

    @staticmethod
    def _extract_docx(file_path: str) -> Tuple[List[ExtractedPage], int]:
        try:
            doc = DocxDocument(file_path)
            full_text_blocks: List[str] = []
            
            # Extract paragraphs
            for para in doc.paragraphs:
                p_text = para.text.strip()
                if p_text:
                    full_text_blocks.append(p_text)
            
            # Extract tables preserving structured layout
            for table in doc.tables:
                table_lines = []
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells]
                    table_lines.append(" | ".join(row_cells))
                if table_lines:
                    full_text_blocks.append("\n[TABLE]\n" + "\n".join(table_lines) + "\n[/TABLE]")
            
            combined_text = "\n\n".join(full_text_blocks).strip()
            if not combined_text:
                raise ValueError("DOCX document contains no extractable text or tables.")
            
            # Estimate pages (~3000 chars per page for DOCX)
            chars_per_page = 3000
            estimated_pages = max(1, (len(combined_text) + chars_per_page - 1) // chars_per_page)
            pages: List[ExtractedPage] = []
            
            for p_idx in range(estimated_pages):
                start = p_idx * chars_per_page
                end = min(len(combined_text), (p_idx + 1) * chars_per_page)
                pages.append(ExtractedPage(page_number=p_idx + 1, text=combined_text[start:end]))
            
            return pages, estimated_pages
        except Exception as e:
            if "no extractable text" in str(e):
                raise
            raise ValueError(f"Failed to extract DOCX: {str(e)}")

    @staticmethod
    def _extract_txt(file_path: str) -> Tuple[List[ExtractedPage], int]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            if not content:
                raise ValueError("Text file is empty.")
            return [ExtractedPage(page_number=1, text=content)], 1
        except Exception as e:
            raise ValueError(f"Failed to extract TXT: {str(e)}")
