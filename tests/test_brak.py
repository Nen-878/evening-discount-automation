from __future__ import annotations

from datetime import time
from decimal import Decimal

from src.config import STATUS_BLOCK_BRAK
from src.decision_engine import decide_item
from tests.factories import BUSINESS_DATE, make_item


def test_weight_below_half_kg_is_brak() -> None:
    item = make_item(
        name="Салат Столичный с курицей",
        produced_time=time(8, 30),
        qty=Decimal("0.35"),
        unit="кг",
        shelf_hours=Decimal("12"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.status == STATUS_BLOCK_BRAK
    assert "0.35" in decision.reason


def test_piece_below_one_is_brak() -> None:
    item = make_item(
        name="Утка запеченная с яблоками",
        category="Кулинария: Горячие блюда",
        produced_time=time(11, 0),
        shelf_hours=Decimal("24"),
        qty=Decimal("0.25"),
        unit="шт",
        retail_price=Decimal("4800"),
        cost=Decimal("4200"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.status == STATUS_BLOCK_BRAK
    assert "0.25" in decision.reason
