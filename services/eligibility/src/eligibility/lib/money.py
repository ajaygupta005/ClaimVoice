"""Money helpers — all monetary values are stored as integer cents (BIGINT)."""

from __future__ import annotations


def cents_to_usd(cents: int | None) -> str:
    """Format integer cents as a USD string.

    150000 -> "$1,500"   3000 -> "$30"   12345 -> "$123.45"   None -> ""
    """
    if cents is None:
        return ""
    dollars = cents / 100
    if cents % 100 == 0:
        return f"${dollars:,.0f}"
    return f"${dollars:,.2f}"
