from __future__ import annotations

from datetime import time
from decimal import Decimal

from src.config import STATUS_AUTO_DISCOUNT, STATUS_MARGIN_ALERT
from src.decision_engine import decide_item
from src.pricing import min_margin_price, promotional_price
from tests.factories import BUSINESS_DATE, make_item


def test_margin_guardrail_blocks_unsafe_30_percent() -> None:
    item = make_item(
        name="Стейк из семги с овощами-гриль",
        category="Кулинария: Горячие блюда",
        produced_time=time(11, 0),
        shelf_hours=Decimal("24"),
        qty=Decimal("6"),
        unit="порц",
        retail_price=Decimal("3500"),
        cost=Decimal("2800"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.status == STATUS_MARGIN_ALERT
    assert decision.discount_price is None
    assert promotional_price(Decimal("3500")) < min_margin_price(Decimal("2800"))


def test_safe_margin_is_auto_discount() -> None:
    item = make_item(
        name="Плов Ташкентский с говядиной",
        category="Кулинария: Горячие блюда",
        produced_time=time(10, 0),
        shelf_hours=Decimal("24"),
        qty=Decimal("14.2"),
        unit="кг",
        retail_price=Decimal("2800"),
        cost=Decimal("1600"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.status == STATUS_AUTO_DISCOUNT
    assert decision.discount_price == promotional_price(Decimal("2800"))
