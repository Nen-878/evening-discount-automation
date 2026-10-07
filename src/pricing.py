from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal

from src.config import DISCOUNT_FACTOR, MARGIN_FACTOR, PRICE_STEP_TENGE


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def discount_price_raw(retail_price: Decimal) -> Decimal:
    return money(retail_price * DISCOUNT_FACTOR)


def min_margin_price(cost: Decimal) -> Decimal:
    return money(cost * MARGIN_FACTOR)


def round_down_to_step(price: Decimal, step: Decimal = PRICE_STEP_TENGE) -> Decimal:
    """Floor to the nearest step (default 5 ₸) so the buyer never pays more than raw -30%."""
    if step <= 0:
        raise ValueError("шаг округления должен быть положительным")
    units = (price / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def promotional_price(retail_price: Decimal) -> Decimal:
    raw = discount_price_raw(retail_price)
    return round_down_to_step(raw)


def violates_margin_guardrail(retail_price: Decimal, cost: Decimal) -> bool:
    return promotional_price(retail_price) < min_margin_price(cost)
