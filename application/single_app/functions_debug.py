# functions_debug.py
#
# NOTE: This module must NOT import functions_settings or app_settings_cache
# at module scope using `from ... import name` syntax.
#
# Why: app_settings_cache imports debug_print from this module, and
# functions_settings also imports debug_print from this module. Any
# `from app_settings_cache import X` or `from functions_settings import X`
# here would create a circular import that crashes the worker on boot
# (observed CrashLoopBackOff in production).
#
# The safe pattern is:
#   - Import the module reference (`import app_settings_cache`).
#   - Look up symbols lazily inside functions (`app_settings_cache.get_settings_cache`).
#   - Defer any functions_settings access to call-time via local import.
import app_settings_cache


def _read_debug_flag():
    """Return enable_debug_logging from cache, or False if cache not ready."""
    get_cache = app_settings_cache.get_settings_cache
    if not get_cache:
        return False
    try:
        cache = get_cache()
    except Exception:
        return False
    return bool(cache and cache.get('enable_debug_logging', False))


def debug_print(message, category="INFO", **kwargs):
    """
    Print debug message only if debug logging is enabled in settings.

    Args:
        message (str): The debug message to print
        category (str): Optional category for the debug message
        **kwargs: Additional key-value pairs to include in debug output
    """
    try:
        if not _read_debug_flag():
            return
        debug_msg = f"[DEBUG] [{category}]: {message}"
        if kwargs:
            kwargs_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            debug_msg += f" ({kwargs_str})"
        print(debug_msg)
    except Exception:
        # Never let debug logging break the caller.
        pass


def is_debug_enabled():
    """
    Check if debug logging is enabled.

    Returns:
        bool: True if debug logging is enabled, False otherwise
    """
    return _read_debug_flag()
