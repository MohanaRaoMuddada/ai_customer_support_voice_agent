"""
models/database_models.py — Internal Database Record Types
===========================================================

These typed structures represent rows returned from the SQLite database.
They are NOT Pydantic models — they live only inside the application's
internal layers (repository → service) and are never serialised directly
to API responses.

Using TypedDict provides static type checking and IDE auto-complete without
the overhead of Pydantic validation, which is unnecessary for data that
has already been validated by SQLite constraints.
"""

from typing import TypedDict


class OrderRecord(TypedDict):
    """
    Represents a single row from the ``orders`` table.

    Attributes:
        id                (int): Unique order identifier (primary key).
        customer_name     (str): Full name of the customer who placed the order.
        status            (str): Current order status (e.g., "Processing", "Shipped").
        expected_delivery (str): Expected delivery date string (e.g., "2025-07-10").
    """

    id: int
    customer_name: str
    status: str
    expected_delivery: str
