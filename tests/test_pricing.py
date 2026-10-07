from __future__ import annotations

from decimal import Decimal

from src.pricing import promotional_price, round_down_to_step


def test_round_down_to_five_tenge() -> None:
    assert round_down_to_step(Decimal("1540")) == Decimal("1540")
    assert round_down_to_step(Decimal("1541")) == Decimal("1540")
    assert round_down_to_step(Decimal("1544.99")) == Decimal("1540")
    assert round_down_to_step(Decimal("2450")) == Decimal("2450")


def test_promotional_price_is_70_percent_then_floor_5() -> None:
    # 2200 * 0.70 = 1540, already multiple of 5
    assert promotional_price(Decimal("2200")) == Decimal("1540")
    # 3500 * 0.70 = 2450
    assert promotional_price(Decimal("3500")) == Decimal("2450")
    # 1950 * 0.70 = 1365 → floor to 1365 (already *5)
    assert promotional_price(Decimal("1950")) == Decimal("1365")
    # 160 * 0.70 = 112 → floor to 110
    assert promotional_price(Decimal("160")) == Decimal("110")
