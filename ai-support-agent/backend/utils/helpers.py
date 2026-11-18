"""
utils/helpers.py — General-purpose Helpers
============================================

Miscellaneous stateless utility functions that are shared across multiple
layers of the application but don't belong to a more specific utility module.
"""

from typing import Any, Dict


def format_order_result(order: Dict[str, Any]) -> str:
    """
    Format an order dictionary into a human-readable, pipe-delimited string.

    The AI agent receives this formatted string as its "tool result" and uses
    it to compose a natural-language response. Pipe separators are unambiguous
    to both humans and the LLM.

    Args:
        order (Dict[str, Any]): An order record with keys: id, customer_name,
                                 status, expected_delivery.

    Returns:
        str: Formatted string such as:
             ``"Order #1002 | Customer: Bob Smith | Status: Shipped | Expected Delivery: 2025-07-05"``
    """
    return (
        f"Order #{order.get('id')} | "
        f"Customer: {order.get('customer_name', 'Unknown')} | "
        f"Status: {order.get('status', 'Unknown')} | "
        f"Expected Delivery: {order.get('expected_delivery', 'Unknown')}"
    )


# ---------------------------------------------------------------------------
# Tool registry — preserved for reference and future native function-calling
# ---------------------------------------------------------------------------
# When upgrading to Groq's native function-calling API, register tool
# schemas here. The agent dispatcher can then call tools dynamically without
# an if/elif chain.

TOOL_SCHEMAS: list = [
    {
        "type": "function",
        "function": {
            "name": "get_order_tool",
            "description": (
                "Look up a customer's order by its unique order ID. "
                "Use this tool whenever a customer asks about their order status, "
                "delivery date, or any order-specific information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": (
                            "The unique integer ID of the order to look up. "
                            "Must be a positive integer (e.g., 1001, 1002, 1003)."
                        ),
                    }
                },
                "required": ["order_id"],
            },
        },
    }
]
