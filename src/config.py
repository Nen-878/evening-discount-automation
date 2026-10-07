"""Explicit business and technical parameters. No hidden magic numbers."""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_INPUT_XLSX = INPUT_DIR / "input_1c.xlsx"
DEFAULT_OUTPUT_XLSX = OUTPUT_DIR / "Итоги_Вечерней_Уценки_20_00.xlsx"
DEFAULT_PRINT_XLSX = OUTPUT_DIR / "Лист_для_стикеров_20_00.xlsx"
EXPECTED_SHEET_NAME = "Остатки_Кулинария_19_30"

SNAPSHOT_TIME = time(19, 30)
DISCOUNT_START_TIME = time(20, 0)

DISCOUNT_FACTOR = Decimal("0.70")
MARGIN_FACTOR = Decimal("1.05")
PRICE_STEP_TENGE = Decimal("5")

WEIGHT_MIN_QTY = Decimal("0.5")
PIECE_MIN_QTY = Decimal("1")

WEIGHT_UNITS = frozenset({"кг"})
PIECE_UNITS = frozenset({"шт", "порц"})

ALLOWED_CATEGORIES = frozenset(
    {
        "Кулинария: Салаты заправленные",
        "Кулинария: Салаты незаправленные",
        "Кулинария: Горячие блюда",
        "Кулинария: Выпечка и сдоба",
    }
)

FORBIDDEN_CATEGORIES = frozenset(
    {
        "Полуфабрикаты замороженные",
        "Сырье и ингредиенты цеха СП",
        "Упаковка и расходные материалы",
    }
)

STATUS_AUTO_DISCOUNT = "AUTO_DISCOUNT"
STATUS_BLOCK_CATEGORY = "BLOCK_CATEGORY"
STATUS_BLOCK_EXPIRY = "BLOCK_EXPIRY"
STATUS_BLOCK_BRAK = "BLOCK_BRAK"
STATUS_MARGIN_ALERT = "MARGIN_ALERT"

EXEC_READY = "READY"
EXEC_DATA_QUALITY_REVIEW = "DATA_QUALITY_REVIEW"
EXEC_NOT_APPLICABLE = "NOT_APPLICABLE"

BLOCKED_STATUSES = frozenset(
    {STATUS_BLOCK_CATEGORY, STATUS_BLOCK_EXPIRY, STATUS_BLOCK_BRAK}
)

RISK_EXPIRY_CRITICAL = "EXPIRY_CRITICAL"

RISK_LOW = "низкий"
RISK_MEDIUM = "средний"
RISK_HIGH = "высокий"
