"""
database/sqlite_manager.py — Schema Initialisation and Lifecycle Management
===========================================================================

DatabaseManager owns the one-time setup of the SQLite schema. It is called
during application startup and is never invoked again during normal operation.

Why a class here:
    DatabaseManager holds ``db_path`` as instance state and is responsible for
    a well-defined lifecycle phase (initialise once). Encapsulating this in a
    class makes it mockable in tests and swappable if the storage engine changes
    (e.g., migrate to PostgreSQL by creating a ``PostgresManager`` that shares
    the same interface).
"""

import sqlite3

from core.logger import get_logger
from database.connection import get_connection

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages the SQLite database lifecycle: schema creation and seed data.

    Intended to be instantiated once at application startup via the
    ``initialize()`` method.

    Attributes:
        db_path (str): Absolute path to the SQLite ``.db`` file.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        """
        Create the ``orders`` table and seed sample data if not already present.

        This method is idempotent — safe to call on every application restart:
        ``CREATE TABLE IF NOT EXISTS`` and ``INSERT OR IGNORE`` ensure that
        existing data is never overwritten or duplicated.

        Raises:
            sqlite3.Error: If the database file is unwritable or SQL fails.
        """
        logger.info("Initialising database at: %s", self.db_path)
        connection = get_connection(self.db_path)

        try:
            cursor = connection.cursor()
            self._create_orders_table(cursor)
            self._seed_sample_orders(cursor)
            connection.commit()
            logger.info("Database initialisation complete.")
        except sqlite3.Error as exc:
            logger.error("Database initialisation failed: %s", exc)
            connection.rollback()
            raise
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_orders_table(self, cursor: sqlite3.Cursor) -> None:
        """Create the orders table if it does not already exist."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id                INTEGER PRIMARY KEY,
                customer_name     TEXT    NOT NULL,
                status            TEXT    NOT NULL,
                expected_delivery TEXT    NOT NULL
            )
        """)
        logger.info("Table `orders` verified/created successfully.")

    def _seed_sample_orders(self, cursor: sqlite3.Cursor) -> None:
        """Insert sample orders; skips rows whose primary key already exists."""
        sample_orders = [
            (1001, "Alice Johnson",  "Processing", "2025-07-10"),
            (1002, "Bob Smith",      "Shipped",    "2025-07-05"),
            (1003, "Carol Williams", "Delivered",  "2025-06-30"),
        ]
        cursor.executemany(
            "INSERT OR IGNORE INTO orders "
            "(id, customer_name, status, expected_delivery) VALUES (?, ?, ?, ?)",
            sample_orders,
        )
        logger.info("Seeded %d new sample order(s).", cursor.rowcount)
