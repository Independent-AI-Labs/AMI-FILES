"""Document extractors for various file formats."""

from files.backend.extractors.base import DocumentExtractor, ExtractionResult
from files.backend.extractors.docx_extractor import DOCXExtractor
from files.backend.extractors.image_extractor import ImageExtractor
from files.backend.extractors.pdf_extractor import PDFExtractor
from files.backend.extractors.spreadsheet_extractor import SpreadsheetExtractor

__all__ = [
    "DOCXExtractor",
    "DocumentExtractor",
    "ExtractionResult",
    "ImageExtractor",
    "PDFExtractor",
    "SpreadsheetExtractor",
]
