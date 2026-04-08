# tests/unit/test_sanitize.py
# Unit tests for utils/sanitize.py — input sanitization utilities.

import pytest
from utils.sanitize import sanitize_filename, sanitize_for_log, safe_content_disposition


class TestSanitizeFilename:
    """Tests for sanitize_filename()."""

    def test_normal_filename(self):
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_empty_string_returns_download(self):
        assert sanitize_filename("") == "download"

    def test_none_returns_download(self):
        assert sanitize_filename(None) == "download"

    def test_strips_path_traversal_forward_slash(self):
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result
        assert "etc" in result  # Filename part kept

    def test_strips_path_traversal_backslash(self):
        result = sanitize_filename("..\\..\\windows\\system32\\config")
        assert "\\" not in result

    def test_strips_null_bytes(self):
        result = sanitize_filename("file\x00.pdf")
        assert "\x00" not in result
        assert result == "file.pdf"

    def test_strips_control_characters(self):
        result = sanitize_filename("file\x01\x02\x03.txt")
        assert result == "file.txt"

    def test_strips_cr_lf_injection(self):
        """Prevent HTTP header injection via CRLF in filename."""
        result = sanitize_filename("file\r\nContent-Type: text/html\r\n.pdf")
        assert "\r" not in result
        assert "\n" not in result

    def test_strips_quotes(self):
        result = sanitize_filename('file"name.txt')
        assert '"' not in result

    def test_strips_leading_dots(self):
        result = sanitize_filename("...hidden.txt")
        assert not result.startswith(".")

    def test_strips_trailing_dots_and_spaces(self):
        result = sanitize_filename("file.txt . . ")
        assert not result.endswith(".")
        assert not result.endswith(" ")

    def test_max_length_truncation(self):
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name, max_length=50)
        assert len(result) <= 50
        assert result.endswith(".pdf")

    def test_unicode_normalized(self):
        # Test that Unicode is NFC-normalized
        import unicodedata
        filename = "caf\u0065\u0301.txt"  # e + combining acute
        result = sanitize_filename(filename)
        assert unicodedata.is_normalized("NFC", result)

    def test_only_dots_returns_download(self):
        assert sanitize_filename("...") == "download"

    def test_only_spaces_returns_download(self):
        assert sanitize_filename("   ") == "download"


class TestSanitizeForLog:
    """Tests for sanitize_for_log()."""

    def test_normal_string(self):
        assert sanitize_for_log("hello world") == "hello world"

    def test_empty_string(self):
        assert sanitize_for_log("") == ""

    def test_none_returns_empty(self):
        assert sanitize_for_log(None) == ""

    def test_strips_newlines(self):
        """Prevent log injection by stripping newlines."""
        result = sanitize_for_log("line1\nINFO: fake log entry\nline3")
        assert "\n" not in result

    def test_strips_control_characters(self):
        result = sanitize_for_log("test\x00\x01\x02string")
        assert "\x00" not in result

    def test_truncates_long_strings(self):
        long_string = "x" * 500
        result = sanitize_for_log(long_string, max_length=200)
        assert len(result) < 220  # 200 + ...[truncated]
        assert result.endswith("...[truncated]")

    def test_custom_max_length(self):
        result = sanitize_for_log("x" * 100, max_length=50)
        assert len(result) < 70
        assert result.endswith("...[truncated]")

    def test_no_truncation_for_short_strings(self):
        result = sanitize_for_log("short", max_length=200)
        assert result == "short"
        assert "[truncated]" not in result


class TestSafeContentDisposition:
    """Tests for safe_content_disposition()."""

    def test_ascii_filename(self):
        result = safe_content_disposition("report.pdf")
        assert result == 'attachment; filename="report.pdf"'

    def test_inline_disposition(self):
        result = safe_content_disposition("image.png", disposition="inline")
        assert result.startswith("inline;")

    def test_non_ascii_filename_uses_rfc5987(self):
        result = safe_content_disposition("rapport_résumé.pdf")
        assert "filename*=UTF-8''" in result
        assert "r%C3%A9sum%C3%A9" in result  # URL-encoded

    def test_sanitizes_before_building_header(self):
        """Ensure the filename is sanitized (no path traversal, etc.)."""
        result = safe_content_disposition("../../etc/passwd")
        assert "/../" not in result
        assert "..\\.." not in result

    def test_empty_filename_uses_download(self):
        result = safe_content_disposition("")
        assert 'filename="download"' in result

    def test_crlf_injection_prevented(self):
        result = safe_content_disposition("file\r\nInjected-Header: value")
        assert "\r" not in result
        assert "\n" not in result
