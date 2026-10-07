from __future__ import annotations

from datetime import time
from decimal import Decimal

from src.config import (
    EXEC_DATA_QUALITY_REVIEW,
    EXEC_NOT_APPLICABLE,
    EXEC_READY,
    STATUS_AUTO_DISCOUNT,
    STATUS_BLOCK_BRAK,
    STATUS_BLOCK_CATEGORY,
    STATUS_BLOCK_EXPIRY,
    STATUS_MARGIN_ALERT,
)
from src.decision_engine import decide_item
from tests.factories import BUSINESS_DATE, make_item


def test_allowed_category_normal_shelf_auto_discount_ready() -> None:
    item = make_item(
        name="Салат Греческий с сыром Фета",
        category="Кулинария: Салаты незаправленные",
        produced_time=time(9, 0), shelf_hours=Decimal("18"), qty=Decimal("5.5"),
        retail_price=Decimal("3400"), cost=Decimal("2000"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.business_status == STATUS_AUTO_DISCOUNT
    assert decision.execution_status == EXEC_READY


def test_forbidden_frozen_category() -> None:
    item = make_item(
        name="Пельмени Сибирские п/ф заморозка 1кг",
        category="Полуфабрикаты замороженные",
        barcode="4870001040018", qty=Decimal("45"), unit="пач",
        retail_price=Decimal("2100"), cost=Decimal("1350"),
        produced_time=None, shelf_hours=Decimal("2160"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.business_status == STATUS_BLOCK_CATEGORY
    assert decision.execution_status == EXEC_NOT_APPLICABLE


def test_forbidden_beats_missing_barcode() -> None:
    item = make_item(
        name="Сыр Российский голова", category="Сырье и ингредиенты цеха СП",
        barcode=None, qty=Decimal("9"), unit="шт", retail_price=Decimal("24000"),
        cost=Decimal("19500"), produced_time=None, shelf_hours=Decimal("2160"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.business_status == STATUS_BLOCK_CATEGORY


def test_expiry_beats_bad_barcode_and_brak() -> None:
    item = make_item(
        name="Салат Столичный с курицей", barcode="4.60701E+12",
        produced_time=time(8, 0), shelf_hours=Decimal("12"), qty=Decimal("0.35"), unit="кг",
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.business_status == STATUS_BLOCK_EXPIRY
    assert decision.execution_status == EXEC_NOT_APPLICABLE
    assert any(issue.code == "BARCODE_SCIENTIFIC" for issue in item.issues)


def test_brak_beats_margin_alert() -> None:
    item = make_item(
        name="Утка запеченная", category="Кулинария: Горячие блюда",
        produced_time=time(11, 0), shelf_hours=Decimal("24"), qty=Decimal("0.25"),
        unit="шт", retail_price=Decimal("4800"), cost=Decimal("4200"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.business_status == STATUS_BLOCK_BRAK


def test_margin_violation_not_hidden_by_whitespace_barcode() -> None:
    item = make_item(
        name="Стейк из семги", barcode=" 4870001009999 ", category="Кулинария: Горячие блюда",
        produced_time=time(11, 0), shelf_hours=Decimal("24"), qty=Decimal("2"), unit="порц",
        retail_price=Decimal("3500"), cost=Decimal("2800"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.business_status == STATUS_MARGIN_ALERT
    assert item.barcode == "4870001009999"


def test_missing_barcode_on_allowed_item_is_auto_business_review_execution() -> None:
    item = make_item(
        name="Макароны с сыром запеченные", category="Кулинария: Горячие блюда", barcode=None,
        produced_time=time(10, 0), shelf_hours=Decimal("24"), qty=Decimal("6"), unit="кг",
        retail_price=Decimal("1300"), cost=Decimal("600"),
    )
    decision = decide_item(item, BUSINESS_DATE)
    assert decision.business_status == STATUS_AUTO_DISCOUNT
    assert decision.execution_status == EXEC_DATA_QUALITY_REVIEW
