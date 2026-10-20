import re
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

class DocumentPassage(BaseModel):
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    timestamp: Optional[str] = None

class DocumentExtractor:
    @staticmethod
    def extract_from_path(file_path: Path) -> list[DocumentPassage]:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return DocumentExtractor._extract_pdf(file_path)
        elif ext == ".docx":
            return DocumentExtractor._extract_docx(file_path)
        elif ext in {".vtt", ".srt"}:
            return DocumentExtractor._extract_subtitles(file_path)
        elif ext == ".txt":
            return DocumentExtractor._extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format for text extraction: {ext}")

    @staticmethod
    def _extract_pdf(file_path: Path) -> list[DocumentPassage]:
        from pypdf import PdfReader
        passages: list[DocumentPassage] = []
        try:
            reader = PdfReader(str(file_path))
            for page_idx, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                cleaned = text.strip()
                if cleaned:
                    passages.append(DocumentPassage(text=cleaned, page=page_idx, section=f"Page {page_idx}"))
            if not passages:
                raise RuntimeError(
                    f"No readable text could be extracted from PDF '{file_path.name}'. "
                    f"The document may be scanned image-only, empty, or password-protected."
                )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to extract PDF contents from '{file_path.name}': {e}")
        return passages

    @staticmethod
    def _extract_docx(file_path: Path) -> list[DocumentPassage]:
        import docx
        passages: list[DocumentPassage] = []
        try:
            doc = docx.Document(str(file_path))
            current_section = "General"
            current_buffer: list[str] = []

            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                # Heading detection
                if paragraph.style and paragraph.style.name and "Heading" in paragraph.style.name:
                    if current_buffer:
                        passages.append(DocumentPassage(text="\n".join(current_buffer), section=current_section))
                        current_buffer = []
                    current_section = text
                else:
                    current_buffer.append(text)

            if current_buffer:
                passages.append(DocumentPassage(text="\n".join(current_buffer), section=current_section))

            # Also extract tables
            for table_idx, table in enumerate(doc.tables, start=1):
                rows_text = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_data:
                        rows_text.append(" | ".join(row_data))
                if rows_text:
                    passages.append(DocumentPassage(
                        text="\n".join(rows_text),
                        section=f"Table {table_idx}"
                    ))
            if not passages:
                raise RuntimeError(f"No readable text could be extracted from DOCX '{file_path.name}'.")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to extract DOCX contents from '{file_path.name}': {e}")
        return passages

    @staticmethod
    def _extract_subtitles(file_path: Path) -> list[DocumentPassage]:
        passages: list[DocumentPassage] = []
        content = ""
        for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                content = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        # Regex for VTT/SRT timestamp lines: e.g., 00:01:20.000 --> 00:01:25.000 or 00:01:20,000 --> 00:01:25,000
        timestamp_pattern = re.compile(r"(\d{2}:\d{2}(?::\d{2})?(?:[.,]\d{3})?)\s*-->\s*(\d{2}:\d{2}(?::\d{2})?(?:[.,]\d{3})?)")
        lines = content.splitlines()
        current_time = "00:00:00"
        current_text: list[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("WEBVTT") or line_str.isdigit():
                continue
            match = timestamp_pattern.search(line_str)
            if match:
                if current_text:
                    passages.append(DocumentPassage(
                        text=" ".join(current_text),
                        timestamp=current_time,
                        section=f"Time {current_time}"
                    ))
                    current_text = []
                current_time = match.group(1)
            else:
                current_text.append(line_str)

        if current_text:
            passages.append(DocumentPassage(
                text=" ".join(current_text),
                timestamp=current_time,
                section=f"Time {current_time}"
            ))

        if not passages:
            raise RuntimeError(f"No subtitle cues or dialogue could be extracted from '{file_path.name}'.")

        return passages

    @staticmethod
    def _extract_txt(file_path: Path) -> list[DocumentPassage]:
        content = ""
        for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                content = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        if not paragraphs:
            # Fallback to lines if no blank line breaks exist
            paragraphs = [line.strip() for line in content.splitlines() if line.strip()]

        if not paragraphs:
            raise RuntimeError(f"No readable text could be extracted from text document '{file_path.name}'.")

        passages: list[DocumentPassage] = []
        for idx, para in enumerate(paragraphs, start=1):
            passages.append(DocumentPassage(
                text=para,
                section=f"Paragraph {idx}"
            ))
        return passages
