from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.config import (
    EXEC_DATA_QUALITY_REVIEW,
    EXEC_READY,
    STATUS_AUTO_DISCOUNT,
    STATUS_BLOCK_BRAK,
    STATUS_BLOCK_CATEGORY,
    STATUS_BLOCK_EXPIRY,
    STATUS_MARGIN_ALERT,
)
from src.models import Decision

ZERO = Decimal("0")


def line_retail_value(decision: Decision) -> Optional[Decimal]:
    item = decision.item
    if item.qty is None or item.retail_price is None:
        return None
    return item.qty * item.retail_price


def line_cost_value(decision: Decision) -> Optional[Decimal]:
    item = decision.item
    if item.qty is None or item.cost is None:
        return None
    return item.qty * item.cost


def line_discount_revenue(decision: Decision) -> Optional[Decimal]:
    if decision.business_status != STATUS_AUTO_DISCOUNT:
        return None
    if decision.discount_price is None or decision.item.qty is None:
        return None
    return decision.item.qty * decision.discount_price


@dataclass
class KpiReport:
    input_rows: int
    processed_rows: int
    auto_discount: int
    block_category: int
    block_expiry: int
    block_brak: int
    margin_alert: int
    execution_ready: int
    data_quality_review: int
    stock_retail_value_all: Decimal
    auto_stock_retail_value: Decimal
    potential_revenue_after_discount: Decimal
    auto_cost_value: Decimal
    remainder_over_cost: Decimal
    ready_stock_retail_value: Decimal
    ready_revenue: Decimal
    ready_cost_value: Decimal
    ready_remainder_over_cost: Decimal
    master_data_revenue_at_risk: Decimal
    salvageable_revenue: Decimal
    formulas: dict[str, str]


def build_kpi(decisions: list[Decision]) -> KpiReport:
    counts = {
        STATUS_AUTO_DISCOUNT: 0,
        STATUS_BLOCK_CATEGORY: 0,
        STATUS_BLOCK_EXPIRY: 0,
        STATUS_BLOCK_BRAK: 0,
        STATUS_MARGIN_ALERT: 0,
    }
    stock_all = ZERO
    auto_retail = ZERO
    auto_revenue = ZERO
    auto_cost = ZERO
    ready_retail = ZERO
    ready_revenue = ZERO
    ready_cost = ZERO
    ready_count = 0
    dq_count = 0

    for decision in decisions:
        if decision.business_status in counts:
            counts[decision.business_status] += 1
        retail = line_retail_value(decision)
        if retail is not None:
            stock_all += retail

        if decision.business_status == STATUS_AUTO_DISCOUNT:
            if retail is not None:
                auto_retail += retail
            revenue = line_discount_revenue(decision)
            if revenue is not None:
                auto_revenue += revenue
            cost = line_cost_value(decision)
            if cost is not None:
                auto_cost += cost

            if decision.execution_status == EXEC_READY:
                ready_count += 1
                if retail is not None:
                    ready_retail += retail
                if revenue is not None:
                    ready_revenue += revenue
                if cost is not None:
                    ready_cost += cost
            elif decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
                dq_count += 1

    remainder = auto_revenue - auto_cost
    ready_remainder = ready_revenue - ready_cost
    at_risk = auto_revenue - ready_revenue

    formulas = {
        "stock_retail_value_all": "Σ (остаток × розничная цена) по всем строкам",
        "auto_stock_retail_value": "Σ (остаток × розничная цена) по BUSINESS_STATUS=AUTO_DISCOUNT",
        "potential_revenue_after_discount": "Σ (остаток × округлённая цена −30%) по всем бизнес-кандидатам AUTO_DISCOUNT",
        "ready_revenue": "Σ (остаток × округлённая цена −30%) только AUTO_DISCOUNT + EXECUTION_STATUS=READY",
        "master_data_revenue_at_risk": "Бизнес-потенциал AUTO_DISCOUNT − исполнимая сегодня выручка READY",
        "auto_cost_value": "Σ (остаток × себестоимость) по AUTO_DISCOUNT",
        "ready_cost_value": "Σ (остаток × себестоимость) по AUTO_DISCOUNT + READY",
        "remainder_over_cost": "Потенциальная выручка AUTO_DISCOUNT − себестоимость AUTO_DISCOUNT",
        "ready_remainder_over_cost": "Исполнимая сегодня выручка − себестоимость READY",
    }

    return KpiReport(
        input_rows=len(decisions),
        processed_rows=len(decisions),
        auto_discount=counts[STATUS_AUTO_DISCOUNT],
        block_category=counts[STATUS_BLOCK_CATEGORY],
        block_expiry=counts[STATUS_BLOCK_EXPIRY],
        block_brak=counts[STATUS_BLOCK_BRAK],
        margin_alert=counts[STATUS_MARGIN_ALERT],
        execution_ready=ready_count,
        data_quality_review=dq_count,
        stock_retail_value_all=stock_all,
        auto_stock_retail_value=auto_retail,
        potential_revenue_after_discount=auto_revenue,
        auto_cost_value=auto_cost,
        remainder_over_cost=remainder,
        ready_stock_retail_value=ready_retail,
        ready_revenue=ready_revenue,
        ready_cost_value=ready_cost,
        ready_remainder_over_cost=ready_remainder,
        master_data_revenue_at_risk=at_risk,
        salvageable_revenue=ready_revenue,
        formulas=formulas,
    )
