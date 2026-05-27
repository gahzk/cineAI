# -*- coding: utf-8 -*-
"""
Utility functions extracted from the CineAI legacy notebook.
Handles string normalization, type coercion, and other helpers.
"""
import unicodedata
from typing import Any, Optional


def normalize(s: Optional[str]) -> str:
    """Normalize a string: lowercase, strip accents, strip whitespace."""
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(s)).lower()
        if not unicodedata.combining(c)
    ).strip()


def get_year(date_str: Optional[str]) -> Optional[int]:
    """Parse a TMDB date string (YYYY-MM-DD) and return the year."""
    if not date_str:
        return None
    try:
        year = int(date_str.split("-")[0])
        return year if 1888 <= year <= 2030 else None
    except (ValueError, IndexError):
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure or NaN."""
    try:
        result = float(value)
        return default if result != result else result  # NaN check
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def is_empty(s: str) -> bool:
    """Return True if the string represents an empty/null preference."""
    return not s or normalize(s) in ("nenhum", "nenhuma", "nada", "n/a", "")
