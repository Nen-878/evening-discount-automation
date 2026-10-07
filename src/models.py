from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional


@dataclass
class RawItem:
    """One Excel row with original cell values preserved."""

    source_row: int
    code_1c_raw: object
    barcode_raw: object
    name_raw: object
    category_raw: object
    qty_raw: object
    unit_raw: object
    retail_raw: object
    cost_raw: object
    produced_raw: object
    shelf_hours_raw: object


@dataclass
class QualityIssue:
    code: str
    message: str


@dataclass
class ParsedItem:
    raw: RawItem
    code_1c: str
    barcode: Optional[str]
    name: str
    category: Optional[str]
    qty: Optional[Decimal]
    unit: Optional[str]
    retail_price: Optional[Decimal]
    cost: Optional[Decimal]
    produced_time: Optional[time]
    produced_date: Optional[date]
    produced_datetime: Optional[datetime]
    shelf_hours: Optional[Decimal]
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def barcode_display(self) -> str:
        return self.barcode or ""

    @property
    def barcode_raw_display(self) -> str:
        if self.raw.barcode_raw is None:
            return ""
        return str(self.raw.barcode_raw)


@dataclass
class Decision:
    item: ParsedItem
    business_status: Optional[str]
    execution_status: str
    reason: str
    recommended_action: str
    risk_level: str
    execution_reason: str = ""
    risk_flag: str = ""
    expiry_at: Optional[datetime] = None
    discount_price: Optional[Decimal] = None
    min_margin_price: Optional[Decimal] = None
    raw_discount_price: Optional[Decimal] = None
    extra_notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        """Backward-compatible alias for the primary business decision."""
        return self.business_status or "UNDETERMINED"
