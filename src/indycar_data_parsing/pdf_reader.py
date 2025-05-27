import pdfplumber
from typing import Generator


class PDFReader:
    """Simple PDF reader that returns the raw text of each page."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def read_pages(self) -> Generator[str, None, None]:
        """Yields the raw text of each page in the PDF."""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                yield page.extract_text()

    def read_all_text(self) -> str:
        """Returns all text from the PDF as a single string, joined by newlines."""
        return "\n".join(filter(None, self.read_pages()))

    def num_pages(self) -> int:
        """Returns the number of pages in the PDF."""
        with pdfplumber.open(self.pdf_path) as pdf:
            return len(pdf.pages)
