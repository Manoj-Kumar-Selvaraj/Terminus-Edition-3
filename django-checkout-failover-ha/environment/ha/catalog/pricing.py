from __future__ import annotations

from datetime import datetime, timezone

from catalog.models import PriceBook, Product


def current_unit_cents(product: Product, currency: str, at: datetime | None = None) -> int:
    when = (at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    rows = list(
        PriceBook.objects.filter(product=product, currency=currency, effective_from__lte=when)
        .order_by("-effective_from")[:1]
    )
    if not rows:
        raise ValueError(f"no price for sku={product.sku} currency={currency}")
    return int(rows[0].unit_cents)


def category_risk_multiplier(category: str) -> float:
    table = {
        "grocery": 1.0,
        "home": 1.02,
        "electronics": 1.08,
        "apparel": 1.04,
        "beauty": 1.03,
        "outdoor": 1.05,
        "toys": 1.01,
        "auto": 1.06,
    }
    return table.get(category, 1.05)
