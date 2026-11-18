"""
database/connection.py — SQLite Connection Factory
====================================================

Provides a single, consistent way to open SQLite connections throughout
the application. All repository methods call ``get_connection()`` rather
than calling ``sqlite3.connect()`` directly, which keeps connection
configuration (row_factory, thread safety) in one place.

Design note: this is intentionally a pure function, not a class. Opening
a database connection is a stateless operation — it takes a path, returns
a connection object. There is no state to encapsulate here.
"""

import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Open and return a new SQLite connection to the given database file.

    SQLite will create the file if it does not already exist.

    Args:
        db_path (str): Absolute or relative path to the ``.db`` file.

    Returns:
        sqlite3.Connection: An active connection configured with:
            - ``check_same_thread=False`` — allows connection sharing across
              threads, required for FastAPI's thread-pool-based sync routes.
            - ``row_factory=sqlite3.Row`` — makes result rows accessible by
              column name (``row["customer_name"]``) rather than by index.

    Note:
        The caller is responsible for closing the connection, preferably
        inside a ``try/finally`` block to guarantee cleanup on error.
    """
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection
