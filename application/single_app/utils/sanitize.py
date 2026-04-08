# utils/sanitize.py
# Input sanitization utilities for security-critical operations.

import os
import re
import unicodedata


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize a filename for safe use in Content-Disposition headers and filesystem operations.

    Prevents path traversal, null byte injection, and header injection attacks.

    Args:
        filename: The raw filename to sanitize.
        max_length: Maximum allowed filename length (default 255).

    Returns:
        A safe filename string. Returns 'download' if the input is empty or fully stripped.
    """
    if not filename:
        return "download"

    # Normalize Unicode to NFC form to prevent homoglyph attacks
    filename = unicodedata.normalize("NFC", filename)

    # Strip null bytes and control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)

    # Remove path separators to prevent directory traversal
    filename = filename.replace('/', '').replace('\\', '')

    # Remove characters that are problematic in HTTP headers (CR, LF, quotes)
    filename = re.sub(r'[\r\n"]', '', filename)

    # Strip leading/trailing dots and spaces (Windows filesystem issues)
    filename = filename.strip('. ')

    # Remove any remaining path components (belt-and-suspenders)
    filename = os.path.basename(filename)

    # Truncate to max_length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        # Keep the extension, truncate the name
        filename = name[:max_length - len(ext)] + ext

    # Final fallback
    if not filename:
        return "download"

    return filename


def sanitize_for_log(value: str, max_length: int = 200) -> str:
    """Sanitize a string for safe inclusion in log messages.

    Prevents log injection by stripping newlines and control characters,
    and truncates long values.

    Args:
        value: The string to sanitize.
        max_length: Maximum length of the output string.

    Returns:
        A sanitized string safe for log output.
    """
    if not value:
        return ""

    # Strip control characters including newlines (prevents log injection)
    cleaned = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))

    # Truncate
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "...[truncated]"

    return cleaned


def safe_content_disposition(filename: str, disposition: str = "attachment") -> str:
    """Build a safe Content-Disposition header value.

    Uses RFC 5987 encoding for non-ASCII filenames.

    Args:
        filename: The raw filename (will be sanitized).
        disposition: Either 'attachment' or 'inline'.

    Returns:
        A properly formatted Content-Disposition header value.
    """
    safe_name = sanitize_filename(filename)

    # For ASCII-only filenames, use simple format
    try:
        safe_name.encode('ascii')
        return f'{disposition}; filename="{safe_name}"'
    except UnicodeEncodeError:
        # Use RFC 5987 encoding for non-ASCII filenames
        from urllib.parse import quote
        encoded_name = quote(safe_name, safe='')
        # Include both filename (ASCII fallback) and filename* (UTF-8)
        ascii_fallback = re.sub(r'[^\x20-\x7e]', '_', safe_name)
        return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_name}"
