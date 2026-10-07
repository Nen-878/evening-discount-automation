from __future__ import annotations

from datetime import time
from decimal import Decimal

from src.config import RISK_EXPIRY_CRITICAL, STATUS_AUTO_DISCOUNT, STATUS_BLOCK_EXPIRY
from src.decision_engine import decide_item
from tests.factories import BUSINESS_DATE, make_item


def test_expiry_at_20_00_is_blocked() -> None:
    item = make_item(produced_time=time(8, 0), shelf_hours=Decimal("12"))
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.status == STATUS_BLOCK_EXPIRY
    assert "не позднее начала вечерней уценки" in decision.reason
    assert decision.expiry_at.hour == 20
    assert decision.expiry_at.minute == 0


def test_expiry_after_20_00_allows_discount() -> None:
    item = make_item(
        produced_time=time(8, 30),
        shelf_hours=Decimal("12"),
        qty=Decimal("6.8"),
        retail_price=Decimal("3200"),
        cost=Decimal("1800"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.status == STATUS_AUTO_DISCOUNT
    assert decision.expiry_at.hour == 20
    assert decision.expiry_at.minute == 30
    assert decision.risk_flag == RISK_EXPIRY_CRITICAL


def test_24h_hot_dish_expires_next_day() -> None:
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
    assert decision.risk_flag == ""
