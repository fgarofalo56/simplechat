# test_functions_content.py
# Unit tests for functions_content.py — text extraction, chunking, and metadata functions.

import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch


class TestExtractTextFile:
    """Tests for extract_text_file()."""

    def test_reads_utf8_file(self, tmp_path):
        from functions_content import extract_text_file

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!", encoding="utf-8")
        result = extract_text_file(str(test_file))
        assert result == "Hello, world!"

    def test_reads_unicode_content(self, tmp_path):
        from functions_content import extract_text_file

        test_file = tmp_path / "unicode.txt"
        test_file.write_text("Héllo wörld — café ñ", encoding="utf-8")
        result = extract_text_file(str(test_file))
        assert "café" in result

    def test_reads_empty_file(self, tmp_path):
        from functions_content import extract_text_file

        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")
        result = extract_text_file(str(test_file))
        assert result == ""


class TestExtractMarkdownFile:
    """Tests for extract_markdown_file()."""

    def test_reads_markdown(self, tmp_path):
        from functions_content import extract_markdown_file

        test_file = tmp_path / "test.md"
        test_file.write_text("# Heading\n\nParagraph text", encoding="utf-8")
        result = extract_markdown_file(str(test_file))
        assert "# Heading" in result
        assert "Paragraph text" in result


class TestExtractTableFile:
    """Tests for extract_table_file() with lazy pandas import."""

    @patch("pandas.read_csv")
    def test_csv_extraction(self, mock_read_csv):
        from functions_content import extract_table_file

        mock_df = MagicMock()
        mock_df.to_csv.return_value = "col1,col2\nval1,val2\n"
        mock_read_csv.return_value = mock_df

        result = extract_table_file("/tmp/test.csv", ".csv")
        assert "col1,col2" in result
        mock_read_csv.assert_called_once_with("/tmp/test.csv")

    @patch("pandas.read_excel")
    def test_xlsx_extraction(self, mock_read_excel):
        from functions_content import extract_table_file

        mock_df = MagicMock()
        mock_df.to_csv.return_value = "a,b\n1,2\n"
        mock_read_excel.return_value = mock_df

        result = extract_table_file("/tmp/test.xlsx", ".xlsx")
        assert "a,b" in result
        mock_read_excel.assert_called_once_with("/tmp/test.xlsx")

    def test_unsupported_extension_raises(self):
        from functions_content import extract_table_file

        with pytest.raises(ValueError, match="Unsupported file extension"):
            extract_table_file("/tmp/test.json", ".json")


class TestExtractPdfMetadata:
    """Tests for extract_pdf_metadata() with lazy fitz import."""

    @patch("fitz.open")
    def test_extracts_all_fields(self, mock_fitz_open):
        from functions_content import extract_pdf_metadata

        mock_doc = MagicMock()
        mock_doc.metadata = {
            "title": "Test PDF",
            "author": "John Doe",
            "subject": "Testing",
            "keywords": "test, pdf, unit",
        }
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        mock_fitz_open.return_value = mock_doc

        title, author, subject, keywords = extract_pdf_metadata("/tmp/test.pdf")
        assert title == "Test PDF"
        assert author == "John Doe"
        assert subject == "Testing"
        assert keywords == "test, pdf, unit"

    @patch("fitz.open")
    def test_missing_metadata_returns_empty(self, mock_fitz_open):
        from functions_content import extract_pdf_metadata

        mock_doc = MagicMock()
        mock_doc.metadata = {}
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        mock_fitz_open.return_value = mock_doc

        title, author, subject, keywords = extract_pdf_metadata("/tmp/test.pdf")
        assert title == ""
        assert author == ""
        assert subject == ""
        assert keywords == ""

    @patch("fitz.open", side_effect=Exception("Cannot open file"))
    def test_error_returns_empty_tuple(self, mock_fitz_open):
        from functions_content import extract_pdf_metadata

        title, author, subject, keywords = extract_pdf_metadata("/tmp/bad.pdf")
        assert title == ""
        assert author == ""


class TestExtractDocxMetadata:
    """Tests for extract_docx_metadata() with lazy docx import."""

    @patch("docx.Document")
    def test_extracts_title_and_author(self, mock_document):
        from functions_content import extract_docx_metadata

        mock_doc = MagicMock()
        mock_doc.core_properties.title = "My Document"
        mock_doc.core_properties.author = "Jane Smith"
        mock_document.return_value = mock_doc

        title, author = extract_docx_metadata("/tmp/test.docx")
        assert title == "My Document"
        assert author == "Jane Smith"

    @patch("docx.Document")
    def test_none_properties_return_empty(self, mock_document):
        from functions_content import extract_docx_metadata

        mock_doc = MagicMock()
        mock_doc.core_properties.title = None
        mock_doc.core_properties.author = None
        mock_document.return_value = mock_doc

        title, author = extract_docx_metadata("/tmp/test.docx")
        assert title == ""
        assert author == ""

    @patch("docx.Document", side_effect=Exception("Cannot open file"))
    def test_error_returns_empty_tuple(self, mock_document):
        from functions_content import extract_docx_metadata

        title, author = extract_docx_metadata("/tmp/bad.docx")
        assert title == ""
        assert author == ""


class TestParseAuthors:
    """Tests for parse_authors()."""

    def test_none_returns_empty(self):
        from functions_content import parse_authors
        assert parse_authors(None) == []

    def test_empty_string_returns_empty(self):
        from functions_content import parse_authors
        assert parse_authors("") == []

    def test_list_input(self):
        from functions_content import parse_authors
        result = parse_authors(["Alice", "Bob"])
        assert result == ["Alice", "Bob"]

    def test_list_with_whitespace(self):
        from functions_content import parse_authors
        result = parse_authors(["  Alice  ", "  Bob  "])
        assert result == ["Alice", "Bob"]

    def test_list_skips_empty_strings(self):
        from functions_content import parse_authors
        result = parse_authors(["Alice", "", "  ", "Bob"])
        assert result == ["Alice", "Bob"]

    def test_comma_separated_string(self):
        from functions_content import parse_authors
        result = parse_authors("John Doe, Jane Smith")
        assert result == ["John Doe", "Jane Smith"]

    def test_semicolon_separated_string(self):
        from functions_content import parse_authors
        result = parse_authors("John Doe; Jane Smith")
        assert result == ["John Doe", "Jane Smith"]

    def test_mixed_delimiters(self):
        from functions_content import parse_authors
        result = parse_authors("John Doe, Jane Smith; Bob Brown")
        assert len(result) == 3

    def test_unsupported_type_returns_empty(self):
        from functions_content import parse_authors
        assert parse_authors(12345) == []


class TestChunkText:
    """Tests for chunk_text()."""

    def test_short_text_single_chunk(self):
        from functions_content import chunk_text
        text = "hello world this is a test"
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        from functions_content import chunk_text
        words = [f"word{i}" for i in range(100)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=30, overlap=5)
        assert len(chunks) > 1

    def test_overlap_creates_repeated_words(self):
        from functions_content import chunk_text
        words = [f"w{i}" for i in range(50)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        # Second chunk should start with words from near end of first
        if len(chunks) >= 2:
            first_words = set(chunks[0].split())
            second_words = set(chunks[1].split())
            overlap_words = first_words & second_words
            assert len(overlap_words) > 0

    def test_empty_text(self):
        from functions_content import chunk_text
        chunks = chunk_text("", chunk_size=100, overlap=10)
        # Empty text splits to no words, so no chunks produced
        assert len(chunks) == 0


class TestChunkWordFileIntoPages:
    """Tests for chunk_word_file_into_pages()."""

    @patch("functions_content.WORD_CHUNK_SIZE", 10)
    def test_splits_by_word_count(self):
        from functions_content import chunk_word_file_into_pages

        di_pages = [
            {"page_number": 1, "content": " ".join([f"word{i}" for i in range(25)])}
        ]
        result = chunk_word_file_into_pages(di_pages)
        assert len(result) == 3  # 10 + 10 + 5
        assert result[0]["page_number"] == 1
        assert result[1]["page_number"] == 2
        assert result[2]["page_number"] == 3

    @patch("functions_content.WORD_CHUNK_SIZE", 100)
    def test_small_input_single_chunk(self):
        from functions_content import chunk_word_file_into_pages

        di_pages = [
            {"page_number": 1, "content": "Hello world"}
        ]
        result = chunk_word_file_into_pages(di_pages)
        assert len(result) == 1
        assert result[0]["content"] == "Hello world"

    @patch("functions_content.WORD_CHUNK_SIZE", 100)
    def test_empty_pages_returns_empty(self):
        from functions_content import chunk_word_file_into_pages

        result = chunk_word_file_into_pages([])
        assert result == []

    @patch("functions_content.WORD_CHUNK_SIZE", 100)
    def test_pages_with_no_content(self):
        from functions_content import chunk_word_file_into_pages

        di_pages = [
            {"page_number": 1, "content": ""},
            {"page_number": 2, "content": ""},
        ]
        result = chunk_word_file_into_pages(di_pages)
        assert result == []

    @patch("functions_content.WORD_CHUNK_SIZE", 5)
    def test_multiple_pages_merged(self):
        from functions_content import chunk_word_file_into_pages

        di_pages = [
            {"page_number": 1, "content": "one two three"},
            {"page_number": 2, "content": "four five six seven eight"},
        ]
        result = chunk_word_file_into_pages(di_pages)
        # 8 words total with chunk size 5 => 2 chunks
        assert len(result) == 2
