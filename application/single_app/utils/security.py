# utils/security.py
# Security utility functions — CSP header building, nonce generation, etc.
# This module is kept free of heavy dependencies so it can be imported
# and tested independently of the Azure SDK and database modules.

import secrets


def generate_csp_nonce() -> str:
    """Generate a cryptographically random CSP nonce.

    Returns:
        A URL-safe base64-encoded nonce string (22 chars from 16 random bytes).
    """
    return secrets.token_urlsafe(16)


def build_csp_header(nonce: str = None) -> str:
    """Build the Content-Security-Policy header value.

    When a nonce is provided, uses 'nonce-{value}' for script-src instead of
    'unsafe-inline'/'unsafe-eval', providing strong XSS protection.
    Falls back to 'unsafe-inline' if no nonce is available (e.g. error pages).

    Args:
        nonce: The per-request CSP nonce string (base64url-encoded).

    Returns:
        str: The complete CSP header value.
    """
    if nonce:
        script_src = f"'self' 'nonce-{nonce}'"
    else:
        script_src = "'self' 'unsafe-inline'"

    return (
        f"default-src 'self'; "
        f"script-src {script_src}; "
        f"style-src 'self' 'unsafe-inline'; "
        f"img-src 'self' data: https: blob:; "
        f"font-src 'self'; "
        f"connect-src 'self' https: wss: ws:; "
        f"media-src 'self' blob:; "
        f"object-src 'none'; "
        f"frame-ancestors 'self'; "
        f"base-uri 'self';"
    )
