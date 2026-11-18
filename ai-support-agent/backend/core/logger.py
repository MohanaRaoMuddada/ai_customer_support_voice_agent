"""
core/logger.py — Centralised Logging Configuration
====================================================

Every module in the application obtains its logger through `get_logger()`.
Centralising the format string, date format, and log level here means a
single edit propagates across the entire codebase instantly.

Design note: a plain function is the right tool here — there is no state to
encapsulate, and no lifecycle to manage. A Logger factory class would add
ceremony with zero benefit.
"""

import logging


_LOGGING_CONFIGURED: bool = False

_LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def _configure_root_logger() -> None:
    """Configure the root logger exactly once for the process lifetime."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    logging.basicConfig(
        level=logging.INFO,
        format=_LOG_FORMAT,
        datefmt=_DATE_FORMAT,
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger, ensuring the root logger is configured first.

    Args:
        name (str): Logger name, typically the module's ``__name__``.
                    Example: ``get_logger(__name__)``

    Returns:
        logging.Logger: A configured, named logger instance.
    """
    _configure_root_logger()
    return logging.getLogger(name)
