from __future__ import annotations

import logging
from datetime import date

from src.config import (
    EXEC_DATA_QUALITY_REVIEW,
    EXEC_NOT_APPLICABLE,
    EXEC_READY,
    RISK_EXPIRY_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    STATUS_AUTO_DISCOUNT,
    STATUS_BLOCK_BRAK,
    STATUS_BLOCK_CATEGORY,
    STATUS_BLOCK_EXPIRY,
    STATUS_MARGIN_ALERT,
)
from src.models import Decision, ParsedItem, QualityIssue
from src.pricing import min_margin_price, promotional_price, violates_margin_guardrail
from src.rules import (
    brak_block_reason,
    discount_start_datetime,
    expires_at_or_before_discount_start,
    expiry_datetime,
    expiry_same_calendar_day_after_start,
    is_allowed_category,
    is_forbidden_category,
    is_unknown_category,
)
from src.validation import barcode_unsafe_issues, critical_data_issues

LOGGER = logging.getLogger(__name__)


def _join_issues(issues: list[QualityIssue]) -> str:
    return "; ".join(issue.message for issue in issues)


def _all_issue_messages(item: ParsedItem) -> list[str]:
    return [issue.message for issue in item.issues]


def decide_item(item: ParsedItem, business_date: date) -> Decision:
    try:
        return _decide_item(item, business_date)
    except Exception as exc:
        LOGGER.exception("Сбой правила на строке %s (%s)", item.raw.source_row, item.name)
        return Decision(
            item=item,
            business_status=None,
            execution_status=EXEC_DATA_QUALITY_REVIEW,
            reason=f"Внутренняя ошибка обработки строки: {exc}",
            execution_reason="Автоматическое исполнение невозможно из-за внутренней ошибки",
            recommended_action="Передать строку аналитику; автоуценку не выполнять",
            risk_level=RISK_HIGH,
            extra_notes=_all_issue_messages(item),
        )


def _decide_item(item: ParsedItem, business_date: date) -> Decision:
    critical = critical_data_issues(item)
    if critical:
        return Decision(
            item=item,
            business_status=None,
            execution_status=EXEC_DATA_QUALITY_REVIEW,
            reason="Нельзя безопасно определить бизнес-решение: " + _join_issues(critical),
            execution_reason="Критичные данные строки требуют исправления",
            recommended_action="Исправить карточку в 1С и повторно сформировать выгрузку",
            risk_level=RISK_HIGH,
            extra_notes=_all_issue_messages(item),
        )

    if is_unknown_category(item.category):
        return Decision(
            item=item,
            business_status=None,
            execution_status=EXEC_DATA_QUALITY_REVIEW,
            reason=f"Категория {item.category!r} отсутствует в разрешённом и запрещённом списках регламента",
            execution_reason="Нельзя определить действие без классификации товара",
            recommended_action="Уточнить классификатор 1С; до разбора не уценивать",
            risk_level=RISK_HIGH,
            extra_notes=_all_issue_messages(item),
        )

    if is_forbidden_category(item.category):
        return Decision(
            item=item,
            business_status=STATUS_BLOCK_CATEGORY,
            execution_status=EXEC_NOT_APPLICABLE,
            reason=f"Категория «{item.category}» запрещена к вечерней уценке 20:00",
            execution_reason="Автоисполнение не требуется: товар заблокирован бизнес-правилом",
            recommended_action="Не клеить жёлтый стикер",
            risk_level=RISK_LOW,
            extra_notes=_all_issue_messages(item),
        )

    expiry = expiry_datetime(item, business_date)
    if expiry is None:
        return Decision(
            item=item,
            business_status=None,
            execution_status=EXEC_DATA_QUALITY_REVIEW,
            reason="Нельзя однозначно вычислить окончание срока годности",
            execution_reason="Нет достаточных данных о времени изготовления / сроке годности",
            recommended_action="Уточнить данные в 1С; до расчёта СГ не уценивать",
            risk_level=RISK_HIGH,
            extra_notes=_all_issue_messages(item),
        )

    if expires_at_or_before_discount_start(expiry, business_date):
        return Decision(
            item=item,
            business_status=STATUS_BLOCK_EXPIRY,
            execution_status=EXEC_NOT_APPLICABLE,
            reason="Срок годности заканчивается не позднее начала вечерней уценки",
            execution_reason="Автоисполнение не требуется: товар нельзя продавать после окончания СГ",
            recommended_action="Не включать в план 20:00. Не продавать после окончания срока годности",
            risk_level=RISK_HIGH,
            expiry_at=expiry,
            extra_notes=_all_issue_messages(item),
        )

    brak_reason = brak_block_reason(item)
    if brak_reason:
        return Decision(
            item=item,
            business_status=STATUS_BLOCK_BRAK,
            execution_status=EXEC_NOT_APPLICABLE,
            reason=brak_reason,
            execution_reason="Автоисполнение не требуется: позиция уходит на бракераж",
            recommended_action="Стикер не клеить. Передать на списание/утилизацию по акту бракеража",
            risk_level=RISK_MEDIUM,
            expiry_at=expiry,
            extra_notes=_all_issue_messages(item),
        )

    if item.retail_price is None or item.cost is None:
        return Decision(
            item=item,
            business_status=None,
            execution_status=EXEC_DATA_QUALITY_REVIEW,
            reason="Недостаточно данных для расчёта цены и маржи",
            execution_reason="Нельзя рассчитать безопасную цену",
            recommended_action="Проверить цену и себестоимость в 1С",
            risk_level=RISK_HIGH,
            expiry_at=expiry,
            extra_notes=_all_issue_messages(item),
        )

    promo = promotional_price(item.retail_price)
    floor_price = min_margin_price(item.cost)
    if violates_margin_guardrail(item.retail_price, item.cost):
        return Decision(
            item=item,
            business_status=STATUS_MARGIN_ALERT,
            execution_status=EXEC_NOT_APPLICABLE,
            reason=(
                f"Цена после −30% ({promo} ₸) ниже минимально допустимой "
                f"себестоимость × 1.05 ({floor_price} ₸)"
            ),
            execution_reason="Автоматическая скидка не разрешена до решения директора",
            recommended_action="Ручное решение директора. Не выдавать иную скидку под видом −30%",
            risk_level=RISK_HIGH,
            expiry_at=expiry,
            discount_price=None,
            min_margin_price=floor_price,
            raw_discount_price=promo,
            extra_notes=_all_issue_messages(item),
        )

    if not is_allowed_category(item.category):
        return Decision(
            item=item,
            business_status=None,
            execution_status=EXEC_DATA_QUALITY_REVIEW,
            reason="Категория не подтверждена как разрешённая к стандартной уценке 30%",
            execution_reason="Нельзя подготовить кассовое исполнение",
            recommended_action="Не уценивать до проверки классификатора",
            risk_level=RISK_HIGH,
            expiry_at=expiry,
            extra_notes=_all_issue_messages(item),
        )

    risk_flag = ""
    risk_level = RISK_LOW
    extra = _all_issue_messages(item)
    if expiry_same_calendar_day_after_start(expiry, business_date):
        risk_flag = RISK_EXPIRY_CRITICAL
        risk_level = RISK_MEDIUM
        extra.append("Короткое окно продажи после 20:00; бизнес-статус AUTO_DISCOUNT сохранён")

    barcode_issues = barcode_unsafe_issues(item)
    if barcode_issues:
        execution_status = EXEC_DATA_QUALITY_REVIEW
        execution_reason = _join_issues(barcode_issues)
        action = "Исправить штрихкод в 1С; до исправления стикер не клеить"
        risk_level = RISK_HIGH
    else:
        execution_status = EXEC_READY
        execution_reason = "Штрихкод однозначен для исполнения; позиция готова к стикеру"
        action = "Наклеить жёлтый стикер −30% с 19:40; касса применяет скидку с 20:00"

    start = discount_start_datetime(business_date)
    return Decision(
        item=item,
        business_status=STATUS_AUTO_DISCOUNT,
        execution_status=execution_status,
        reason=(
            f"Разрешённая категория «{item.category}», срок годности до {expiry:%H:%M %d.%m.%Y} "
            f"(после начала уценки {start:%H:%M}), остаток достаточен, −30% не нарушает порог маржи"
        ),
        execution_reason=execution_reason,
        recommended_action=action,
        risk_level=risk_level,
        risk_flag=risk_flag,
        expiry_at=expiry,
        discount_price=promo,
        min_margin_price=floor_price,
        raw_discount_price=promo,
        extra_notes=extra,
    )


def decide_all(items: list[ParsedItem], business_date: date) -> list[Decision]:
    return [decide_item(item, business_date) for item in items]
