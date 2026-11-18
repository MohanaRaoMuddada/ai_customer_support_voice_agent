"""
utils/text_utils.py — Text Processing Utilities
================================================

Pure, stateless functions for text analysis and transformation.
These helpers are intentionally kept simple and dependency-free so they
can be unit-tested in isolation without mocking anything.
"""

from typing import Optional

from core.constants import ORDER_NUMBER_PATTERN


def extract_order_id(message: str) -> Optional[int]:
    """
    Extract a 4-digit order number from a customer message using regex.

    Uses a pre-compiled pattern (``ORDER_NUMBER_PATTERN``) for performance.
    Word boundaries prevent false positives from longer digit sequences.

    Args:
        message (str): The raw customer message string.

    Returns:
        Optional[int]: The first detected 4-digit order ID as an integer,
                       or ``None`` if no 4-digit number was found.

    Examples:
        >>> extract_order_id("Where is my order 1002?")
        1002
        >>> extract_order_id("I need help with my return.")
        None
        >>> extract_order_id("Order #1001 is delayed!")
        1001
    """
    match = ORDER_NUMBER_PATTERN.search(message)
    if match:
        return int(match.group(1))
    return None


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to ``max_length`` characters, appending a suffix if cut.

    Useful for safe log line construction without risking enormous log entries.

    Args:
        text       (str): Input string to potentially truncate.
        max_length (int): Maximum allowed character count before truncating.
        suffix     (str): String appended when truncation occurs.

    Returns:
        str: Original string if within limit, otherwise truncated + suffix.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix
