from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from src.config import (
    ALLOWED_CATEGORIES,
    DISCOUNT_START_TIME,
    FORBIDDEN_CATEGORIES,
    PIECE_MIN_QTY,
    PIECE_UNITS,
    WEIGHT_MIN_QTY,
    WEIGHT_UNITS,
)
from src.models import ParsedItem


def is_forbidden_category(category: Optional[str]) -> bool:
    return category in FORBIDDEN_CATEGORIES


def is_allowed_category(category: Optional[str]) -> bool:
    return category in ALLOWED_CATEGORIES


def is_unknown_category(category: Optional[str]) -> bool:
    if category is None:
        return True
    return not is_allowed_category(category) and not is_forbidden_category(category)


def production_datetime(item: ParsedItem, business_date: date) -> Optional[datetime]:
    if item.produced_datetime is not None:
        return item.produced_datetime
    if item.produced_time is not None:
        return datetime.combine(business_date, item.produced_time)
    return None


def expiry_datetime(item: ParsedItem, business_date: date) -> Optional[datetime]:
    produced = production_datetime(item, business_date)
    if produced is None or item.shelf_hours is None:
        return None
    hours = item.shelf_hours
    whole_hours = int(hours)
    minutes = int((hours - Decimal(whole_hours)) * Decimal(60))
    return produced + timedelta(hours=whole_hours, minutes=minutes)


def discount_start_datetime(business_date: date) -> datetime:
    return datetime.combine(business_date, DISCOUNT_START_TIME)


def expires_at_or_before_discount_start(expiry: datetime, business_date: date) -> bool:
    return expiry <= discount_start_datetime(business_date)


def expiry_same_calendar_day_after_start(expiry: datetime, business_date: date) -> bool:
    start = discount_start_datetime(business_date)
    return expiry > start and expiry.date() == business_date


def is_weight_unit(unit: Optional[str]) -> bool:
    return unit in WEIGHT_UNITS


def is_piece_unit(unit: Optional[str]) -> bool:
    return unit in PIECE_UNITS


def brak_block_reason(item: ParsedItem) -> Optional[str]:
    if item.qty is None or item.unit is None:
        return None
    if is_weight_unit(item.unit):
        if item.qty < WEIGHT_MIN_QTY:
            return (
                f"Весовой остаток {item.qty} {item.unit} меньше {WEIGHT_MIN_QTY} кг: "
                "стикер не клеится, позиция на бракераж"
            )
        return None
    if is_piece_unit(item.unit):
        if item.qty < PIECE_MIN_QTY:
            return (
                f"Поштучный остаток {item.qty} {item.unit} меньше {PIECE_MIN_QTY} шт: "
                "стикер не клеится, позиция на бракераж"
            )
        return None
    if item.qty < PIECE_MIN_QTY:
        return (
            f"Остаток {item.qty} {item.unit} меньше 1; для единицы '{item.unit}' в регламенте "
            "нет отдельного порога, применён консервативный поштучный порог"
        )
    return None
