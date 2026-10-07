from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Optional

from src.models import ParsedItem, QualityIssue, RawItem
from src.validation import inspect_barcode, inspect_numeric_sanity, mark_duplicate_barcodes

BUSINESS_DATE = date(2026, 10, 7)


def make_item(
    *,
    source_row: int = 2,
    code_1c: str = "10101",
    barcode: Optional[str] = "4870001001015",
    name: str = "Салат Оливье с колбасой заправленный",
    category: str = "Кулинария: Салаты заправленные",
    qty: Decimal = Decimal("12.5"),
    unit: str = "кг",
    retail_price: Decimal = Decimal("2200"),
    cost: Decimal = Decimal("1200"),
    produced_time: Optional[time] = time(8, 30),
    shelf_hours: Decimal = Decimal("12"),
    extra_issues: Optional[list[QualityIssue]] = None,
    apply_barcode_checks: bool = True,
) -> ParsedItem:
    raw = RawItem(
        source_row=source_row,
        code_1c_raw=code_1c,
        barcode_raw=barcode,
        name_raw=name,
        category_raw=category,
        qty_raw=qty,
        unit_raw=unit,
        retail_raw=retail_price,
        cost_raw=cost,
        produced_raw=produced_time.strftime("%H:%M:%S") if produced_time else None,
        shelf_hours_raw=shelf_hours,
    )
    normalized_barcode = barcode.strip() if isinstance(barcode, str) else barcode
    item = ParsedItem(
        raw=raw,
        code_1c=code_1c,
        barcode=normalized_barcode,
        name=name,
        category=category,
        qty=qty,
        unit=unit,
        retail_price=retail_price,
        cost=cost,
        produced_time=produced_time,
        produced_date=None,
        produced_datetime=None,
        shelf_hours=shelf_hours,
        issues=list(extra_issues or []),
    )
    if apply_barcode_checks:
        item.issues.extend(inspect_barcode(item.barcode, barcode))
        item.issues.extend(inspect_numeric_sanity(item))
    return item


def with_duplicate_barcodes(items: list[ParsedItem]) -> list[ParsedItem]:
    mark_duplicate_barcodes(items)
    return items
