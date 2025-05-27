from unittest.mock import patch, MagicMock
from indycar_data_parsing.pdf_reader import PDFReader


@patch("pdfplumber.open")
def test_read_pages_yields_text_per_page(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page2 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 text"
    mock_page2.extract_text.return_value = "Page 2 text"
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    reader = PDFReader("dummy.pdf")
    pages = list(reader.read_pages())
    assert pages == ["Page 1 text", "Page 2 text"]


@patch("pdfplumber.open")
def test_read_pages_empty_pdf(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_pdf.pages = []
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    reader = PDFReader("dummy.pdf")
    pages = list(reader.read_pages())
    assert pages == []


@patch("pdfplumber.open")
def test_read_pages_handles_none_text(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page2 = MagicMock()
    mock_page1.extract_text.return_value = None
    mock_page2.extract_text.return_value = "Page 2 text"
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    reader = PDFReader("dummy.pdf")
    pages = list(reader.read_pages())
    assert pages == [None, "Page 2 text"]


@patch("pdfplumber.open")
def test_read_all_text(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page2 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 text"
    mock_page2.extract_text.return_value = "Page 2 text"
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    reader = PDFReader("dummy.pdf")
    all_text = reader.read_all_text()
    assert all_text == "Page 1 text\nPage 2 text"


@patch("pdfplumber.open")
def test_num_pages(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock(), MagicMock(), MagicMock()]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    reader = PDFReader("dummy.pdf")
    assert reader.num_pages() == 3
