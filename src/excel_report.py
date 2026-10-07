from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from src.config import (
    EXEC_DATA_QUALITY_REVIEW,
    EXEC_READY,
    STATUS_AUTO_DISCOUNT,
    STATUS_BLOCK_BRAK,
    STATUS_BLOCK_CATEGORY,
    STATUS_BLOCK_EXPIRY,
    STATUS_MARGIN_ALERT,
)
from src.kpi import KpiReport
from src.models import Decision
from src.validation import data_quality_summary

MONEY_FORMAT = '#,##0.0'
QTY_FORMAT = "#,##0.000"
HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True, name="Calibri", size=11)
TITLE_FONT = Font(bold=True, name="Calibri", size=16, color="1F4E79")
SECTION_FONT = Font(bold=True, name="Calibri", size=12, color="1F4E79")
LABEL_FONT = Font(bold=True, name="Calibri", size=11)
THIN = Border(
    left=Side(style="thin", color="D0D7DE"),
    right=Side(style="thin", color="D0D7DE"),
    top=Side(style="thin", color="D0D7DE"),
    bottom=Side(style="thin", color="D0D7DE"),
)

GREEN_FILL = PatternFill("solid", fgColor="E2F0D9")
YELLOW_FILL = PatternFill("solid", fgColor="FFF2CC")
RED_FILL = PatternFill("solid", fgColor="FCE4D6")
GRAY_FILL = PatternFill("solid", fgColor="E7E6E6")
BLUE_FILL = PatternFill("solid", fgColor="DDEBF7")
ORANGE_FILL = PatternFill("solid", fgColor="FCE4D6")

HUMAN_STATUS_FILL = {
    "ГОТОВО К УЦЕНКЕ": GREEN_FILL,
    "НУЖНО РЕШЕНИЕ ДИРЕКТОРА": YELLOW_FILL,
    "НУЖНО ИСПРАВИТЬ ДАННЫЕ": BLUE_FILL,
    "СРОК ГОДНОСТИ — НЕ УЦЕНЯТЬ": RED_FILL,
    "НЕ УЧАСТВУЕТ В АКЦИИ": GRAY_FILL,
    "БРАКЕРАЖ / СПИСАНИЕ": ORANGE_FILL,
    "НУЖНА ПРОВЕРКА": RED_FILL,
}

ISSUE_LABELS = {
    "BARCODE_MISSING": "Нет штрихкода",
    "BARCODE_WHITESPACE": "Лишние пробелы в штрихкоде — исправлено автоматически",
    "BARCODE_MULTI": "В одном поле указано несколько штрихкодов",
    "BARCODE_SCIENTIFIC": "Штрихкод записан в научной нотации — исходные цифры нельзя восстановить безопасно",
    "BARCODE_DUPLICATE": "Один штрихкод используется у нескольких товаров",
    "QTY_NEGATIVE": "Отрицательный остаток",
    "QTY_ZERO": "Нулевой остаток",
    "RETAIL_NEGATIVE": "Отрицательная розничная цена",
    "RETAIL_ZERO": "Нулевая розничная цена",
    "RETAIL_UNPARSEABLE": "Не удалось прочитать розничную цену",
    "COST_NEGATIVE": "Отрицательная себестоимость",
    "COST_ZERO": "Нулевая себестоимость",
    "COST_UNPARSEABLE": "Не удалось прочитать себестоимость",
    "PRODUCTION_UNPARSEABLE": "Не удалось прочитать время изготовления",
}


def _header_row(ws: Worksheet, headers: list[str], row: int = 1) -> None:
    for col, title in enumerate(headers, start=1):
        cell = ws.cell(row, col, title)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = THIN
    ws.auto_filter.ref = f"A{row}:{get_column_letter(len(headers))}{row}"
    ws.row_dimensions[row].height = 34


def _autosize(ws: Worksheet, widths: dict[int, int]) -> None:
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width


def _barcode_cell(cell, barcode: str | None) -> None:
    cell.number_format = "@"
    cell.value = "" if barcode is None else str(barcode)
    cell.alignment = Alignment(horizontal="left")


def _money_cell(cell, value: Decimal | None) -> None:
    cell.number_format = MONEY_FORMAT
    cell.value = float(value) if value is not None else None


def _qty_cell(cell, value: Decimal | None) -> None:
    cell.number_format = QTY_FORMAT
    cell.value = float(value) if value is not None else None


def _human_status(decision: Decision) -> str:
    if decision.business_status == STATUS_MARGIN_ALERT:
        return "НУЖНО РЕШЕНИЕ ДИРЕКТОРА"
    if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
        return "НУЖНО ИСПРАВИТЬ ДАННЫЕ"
    if decision.business_status == STATUS_BLOCK_EXPIRY:
        return "СРОК ГОДНОСТИ — НЕ УЦЕНЯТЬ"
    if decision.business_status == STATUS_BLOCK_BRAK:
        return "БРАКЕРАЖ / СПИСАНИЕ"
    if decision.business_status == STATUS_BLOCK_CATEGORY:
        return "НЕ УЧАСТВУЕТ В АКЦИИ"
    if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_READY:
        return "ГОТОВО К УЦЕНКЕ"
    return "НУЖНА ПРОВЕРКА"


def _human_reason(decision: Decision) -> str:
    if decision.business_status == STATUS_MARGIN_ALERT:
        promo = f"{decision.raw_discount_price} ₸" if decision.raw_discount_price is not None else "не рассчитана"
        minimum = f"{decision.min_margin_price} ₸" if decision.min_margin_price is not None else "не рассчитан"
        return f"Цена со скидкой −30% будет {promo}, а минимально допустимая цена по марже — {minimum}."
    if decision.business_status == STATUS_BLOCK_EXPIRY:
        if decision.expiry_at:
            return f"Срок годности заканчивается {decision.expiry_at:%d.%m.%Y в %H:%M}. Уценка начинается в 20:00."
        return "Срок годности заканчивается не позднее начала вечерней уценки."
    if decision.business_status == STATUS_BLOCK_BRAK:
        return decision.reason
    if decision.business_status == STATUS_BLOCK_CATEGORY:
        return f"Категория «{decision.item.category}» по регламенту не участвует в вечерней уценке."
    if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
        return decision.execution_reason or "Данные товара не позволяют безопасно выполнить уценку автоматически."
    return decision.reason


def _who_decides(decision: Decision) -> str:
    if decision.business_status == STATUS_MARGIN_ALERT:
        return "Директор магазина"
    if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
        return "Ответственный за 1С / мастер-данные"
    if decision.business_status == STATUS_BLOCK_BRAK:
        return "Зав. производством"
    if decision.business_status in {STATUS_BLOCK_EXPIRY, STATUS_BLOCK_CATEGORY}:
        return "Регламент — решение не требуется"
    return "Ответственный сотрудник"


def _sticker_answer(decision: Decision) -> str:
    if decision.business_status == STATUS_MARGIN_ALERT:
        return "НЕТ — до решения директора"
    if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
        return "НЕТ — до исправления данных"
    if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_READY:
        return "ДА"
    return "НЕТ"


def _human_action(decision: Decision) -> str:
    if decision.business_status == STATUS_MARGIN_ALERT:
        return "Передать директору. До согласования стикер не клеить."
    if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
        return "Исправить штрихкод в 1С и повторить расчёт. До исправления стикер не клеить."
    if decision.business_status == STATUS_BLOCK_EXPIRY:
        return "Не включать в план уценки. Не продавать после окончания срока годности."
    if decision.business_status == STATUS_BLOCK_BRAK:
        return "Стикер не клеить. Передать на списание/утилизацию по акту бракеража."
    if decision.business_status == STATUS_BLOCK_CATEGORY:
        return "Не уценять. Жёлтый стикер не клеить."
    return decision.recommended_action


def _exception_sort_key(decision: Decision) -> tuple[int, int]:
    if decision.business_status == STATUS_MARGIN_ALERT:
        p = 0
    elif decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
        p = 1
    elif decision.business_status == STATUS_BLOCK_EXPIRY:
        p = 2
    elif decision.business_status == STATUS_BLOCK_BRAK:
        p = 3
    elif decision.business_status == STATUS_BLOCK_CATEGORY:
        p = 4
    else:
        p = 5
    return p, decision.item.raw.source_row


def _risk_text(decision: Decision) -> str:
    mapping = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}
    return mapping.get((decision.risk_level or "").lower(), decision.risk_level or "")


def _issue_human_text(decision: Decision) -> str:
    labels = [ISSUE_LABELS.get(issue.code, issue.message) for issue in decision.item.issues]
    return "; ".join(dict.fromkeys(labels))


def _write_action_row(ws: Worksheet, row: int, label: str, value, action: str, fill: PatternFill) -> None:
    ws.cell(row, 1, label).font = LABEL_FONT
    ws.cell(row, 2, value).font = Font(bold=True, size=13, name="Calibri")
    ws.cell(row, 3, action)
    for c in range(1, 4):
        ws.cell(row, c).border = THIN
        ws.cell(row, c).alignment = Alignment(wrap_text=True, vertical="center")
        ws.cell(row, c).fill = fill
    ws.row_dimensions[row].height = 34


def _write_money_row(ws: Worksheet, row: int, label: str, value: Decimal, meaning: str, fill: PatternFill | None = None) -> None:
    ws.cell(row, 1, label).font = LABEL_FONT
    cell = ws.cell(row, 2, float(value))
    cell.number_format = MONEY_FORMAT
    ws.cell(row, 3, meaning)
    for c in range(1, 4):
        ws.cell(row, c).border = THIN
        ws.cell(row, c).alignment = Alignment(wrap_text=True, vertical="center")
        if fill:
            ws.cell(row, c).fill = fill
    ws.row_dimensions[row].height = 32


def write_director_sheet(ws: Worksheet, kpi: KpiReport, generated_at: datetime) -> None:
    ws["A1"] = "Вечерняя уценка — что делать сегодня"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:C1")
    ws["A2"] = f"Сформировано: {generated_at.strftime('%d.%m.%Y %H:%M')}"
    ws["A3"] = "Срез остатков 19:30 → подготовка стикеров 19:40–20:00 → скидка на кассе с 20:00"
    ws.merge_cells("A3:C3")

    r = 5
    ws.cell(r, 1, "Главное на сегодня").font = SECTION_FONT
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    r += 1
    _header_row(ws, ["Ситуация", "Позиций", "Что делать"], row=r)

    rows = [
        ("Готовы к уценке", kpi.execution_ready, "Клеить жёлтые стикеры −30%", GREEN_FILL),
        ("Нужно решение директора", kpi.margin_alert, "Не уценять до решения директора", YELLOW_FILL),
        ("Нужно исправить данные", kpi.data_quality_review, "Проверить штрихкод в 1С; до исправления стикер не клеить", BLUE_FILL),
        ("Срок годности заканчивается к 20:00", kpi.block_expiry, "Не включать в уценку; не продавать после срока", RED_FILL),
        ("Категория не участвует в акции", kpi.block_category, "Не уценять", GRAY_FILL),
        ("Бракераж / списание", kpi.block_brak, "Не уценять; оформить бракераж", ORANGE_FILL),
    ]
    for label, value, action, fill in rows:
        r += 1
        _write_action_row(ws, r, label, value, action, fill)

    r += 2
    ws.cell(r, 1, "Деньги").font = SECTION_FONT
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    r += 1
    _header_row(ws, ["Показатель", "Сумма, ₸", "Что это значит"], row=r)
    money_rows = [
        ("Можно получить сегодня по готовым позициям", kpi.ready_revenue, "43 позиции уже готовы к стикерам и кассовому исполнению", GREEN_FILL),
        ("Под риском из-за проблем в данных", kpi.master_data_revenue_at_risk, "Потенциальная промо-выручка 7 товаров, пока их штрихкоды не исправлены", YELLOW_FILL),
        ("Потенциал после исправления данных", kpi.potential_revenue_after_discount, "Промо-выручка по всем 50 товарам, которые подходят по бизнес-правилам", BLUE_FILL),
        ("Стоимость всех остатков по рознице", kpi.stock_retail_value_all, "Справочно: текущая розничная стоимость всего среза 1С", None),
    ]
    for label, value, meaning, fill in money_rows:
        r += 1
        _write_money_row(ws, r, label, value, meaning, fill)

    r += 2
    ws.cell(r, 1, "Как пользоваться отчётом").font = SECTION_FONT
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    guidance = [
        "02_План_уценки — готовый список: эти товары можно брать в работу и клеить стикеры.",
        "03_Исключения — всё, что нельзя уценивать автоматически. В колонке «Кто решает» сразу видно, нужен ли директор.",
        "04_Контроль_данных — служебный лист для ответственного за 1С/аналитика; обычному сотруднику он не нужен для ежедневной работы.",
        "В приложении кнопка «Открыть лист для печати» формирует карточки только по готовым к уценке позициям.",
    ]
    for text in guidance:
        r += 1
        ws.cell(r, 1, "• " + text)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        ws.cell(r, 1).alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[r].height = 28

    _autosize(ws, {1: 48, 2: 20, 3: 78})
    ws.sheet_view.showGridLines = False


def write_plan_sheet(ws: Worksheet, decisions: list[Decision]) -> None:
    headers = [
        "Товар", "Штрихкод", "Что делать", "Остаток", "Ед. изм.",
        "Старая цена, ₸", "Новая цена, ₸", "Продать до", "Важно", "Категория", "Код 1С",
    ]
    _header_row(ws, headers)
    ws.freeze_panes = "A2"
    row = 2
    for decision in decisions:
        if not (
            decision.business_status == STATUS_AUTO_DISCOUNT
            and decision.execution_status == EXEC_READY
        ):
            continue
        item = decision.item
        ws.cell(row, 1, item.name)
        _barcode_cell(ws.cell(row, 2), item.barcode)
        action = ws.cell(row, 3, "Клеить жёлтый стикер −30%")
        action.fill = GREEN_FILL
        action.font = Font(bold=True)
        _qty_cell(ws.cell(row, 4), item.qty)
        ws.cell(row, 5, item.unit)
        _money_cell(ws.cell(row, 6), item.retail_price)
        _money_cell(ws.cell(row, 7), decision.discount_price)
        ws.cell(row, 8, decision.expiry_at.strftime("%d.%m.%Y %H:%M") if decision.expiry_at else "")
        important = ""
        if decision.risk_flag and decision.expiry_at:
            important = f"Короткое окно продажи: срок до {decision.expiry_at:%H:%M}"
        flag_cell = ws.cell(row, 9, important)
        if important:
            flag_cell.fill = YELLOW_FILL
            flag_cell.font = Font(bold=True)
        ws.cell(row, 10, item.category)
        ws.cell(row, 11, item.code_1c).number_format = "@"
        for c in range(1, 12):
            ws.cell(row, c).border = THIN
            ws.cell(row, c).alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[row].height = 34
        row += 1
    last = max(row - 1, 1)
    ws.auto_filter.ref = f"A1:K{last}"
    _autosize(ws, {1: 46, 2: 21, 3: 29, 4: 11, 5: 10, 6: 16, 7: 16, 8: 19, 9: 30, 10: 34, 11: 12})


def write_exceptions_sheet(ws: Worksheet, decisions: list[Decision]) -> None:
    headers = [
        "Товар", "Статус", "Что произошло", "Что делать", "Кто решает", "Стикер?",
        "Остаток", "Ед. изм.", "Цена, ₸", "Цена −30%, ₸", "Минимум по марже, ₸",
        "Штрихкод", "Годен до", "Категория", "Код 1С",
    ]
    _header_row(ws, headers)
    ws.freeze_panes = "A2"
    row = 2
    exceptions = [
        d for d in decisions
        if not (d.business_status == STATUS_AUTO_DISCOUNT and d.execution_status == EXEC_READY)
    ]
    exceptions.sort(key=_exception_sort_key)

    for decision in exceptions:
        item = decision.item
        status = _human_status(decision)
        ws.cell(row, 1, item.name)
        status_cell = ws.cell(row, 2, status)
        status_cell.fill = HUMAN_STATUS_FILL.get(status, RED_FILL)
        status_cell.font = Font(bold=True)
        status_cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.cell(row, 3, _human_reason(decision))
        ws.cell(row, 4, _human_action(decision))
        who = ws.cell(row, 5, _who_decides(decision))
        if decision.business_status == STATUS_MARGIN_ALERT:
            who.fill = YELLOW_FILL
            who.font = Font(bold=True)
        sticker = ws.cell(row, 6, _sticker_answer(decision))
        if sticker.value == "ДА":
            sticker.fill = GREEN_FILL
        else:
            sticker.fill = RED_FILL if decision.business_status != STATUS_MARGIN_ALERT else YELLOW_FILL
        sticker.font = Font(bold=True)
        _qty_cell(ws.cell(row, 7), item.qty)
        ws.cell(row, 8, item.unit)
        _money_cell(ws.cell(row, 9), item.retail_price)
        if decision.business_status == STATUS_MARGIN_ALERT:
            _money_cell(ws.cell(row, 10), decision.raw_discount_price)
            _money_cell(ws.cell(row, 11), decision.min_margin_price)
        else:
            ws.cell(row, 10, "")
            ws.cell(row, 11, "")
        _barcode_cell(ws.cell(row, 12), item.barcode)
        ws.cell(row, 13, decision.expiry_at.strftime("%d.%m.%Y %H:%M") if decision.expiry_at else "")
        ws.cell(row, 14, item.category)
        ws.cell(row, 15, item.code_1c).number_format = "@"
        for c in range(1, 16):
            ws.cell(row, c).border = THIN
            ws.cell(row, c).alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[row].height = 50
        row += 1
    last = max(row - 1, 1)
    ws.auto_filter.ref = f"A1:O{last}"
    _autosize(ws, {1: 38, 2: 30, 3: 48, 4: 44, 5: 28, 6: 24, 7: 11, 8: 10, 9: 13, 10: 15, 11: 20, 12: 22, 13: 18, 14: 33, 15: 12})


def write_data_control_sheet(ws: Worksheet, decisions: list[Decision]) -> None:
    items = [d.item for d in decisions]
    summary = data_quality_summary(items)
    ws["A1"] = "Контроль данных 1С — служебный лист"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = "Для ответственного за 1С / аналитика. Для ежедневной работы цеха достаточно листов 01–03."
    ws.merge_cells("A2:D2")

    diag = [
        ("Всего строк", summary.get("rows", 0), "Все строки выгрузки"),
        ("Нет штрихкода", summary.get("BARCODE_MISSING", 0), "Нужно заполнить в 1С"),
        ("Лишние пробелы в штрихкоде", summary.get("BARCODE_WHITESPACE", 0), "Пробелы убираются автоматически; исходное значение сохраняется"),
        ("Несколько штрихкодов в одном поле", summary.get("BARCODE_MULTI", 0), "Нужно разделить/уточнить в 1С"),
        ("Штрихкод в научной нотации", summary.get("BARCODE_SCIENTIFIC", 0), "Нельзя безопасно восстановить исходные цифры"),
        ("Один штрихкод у нескольких товаров", summary.get("BARCODE_DUPLICATE", 0), "Нужно проверить мастер-данные"),
        ("Проблемы с остатком", summary.get("QTY_NEGATIVE", 0) + summary.get("QTY_ZERO", 0), "Проверить значение в 1С"),
        ("Проблемы с розничной ценой", summary.get("RETAIL_NEGATIVE", 0) + summary.get("RETAIL_ZERO", 0) + summary.get("RETAIL_UNPARSEABLE", 0), "Проверить значение в 1С"),
        ("Проблемы с себестоимостью", summary.get("COST_NEGATIVE", 0) + summary.get("COST_ZERO", 0) + summary.get("COST_UNPARSEABLE", 0), "Проверить значение в 1С"),
        ("Не читается время изготовления", summary.get("PRODUCTION_UNPARSEABLE", 0), "Проверить формат времени"),
    ]
    _header_row(ws, ["Что проверяем", "Количество", "Что это значит"], row=4)
    for i, (label, value, comment) in enumerate(diag, start=5):
        ws.cell(i, 1, label)
        ws.cell(i, 2, value)
        ws.cell(i, 3, comment)
        for c in range(1, 4):
            ws.cell(i, c).border = THIN
            ws.cell(i, c).alignment = Alignment(wrap_text=True, vertical="center")

    start = 5 + len(diag) + 2
    ws.cell(start, 1, "Строки, в которых найдены замечания")
    ws.cell(start, 1).font = LABEL_FONT
    detail_headers = [
        "Строка Excel", "Код 1С", "Товар", "Штрихкод как в 1С", "После безопасной обработки",
        "Что не так", "Влияет на сегодняшнюю уценку?", "Что делать", "Технический код",
    ]
    header_row = start + 1
    _header_row(ws, detail_headers, row=header_row)
    r = header_row + 1
    for decision in decisions:
        item = decision.item
        if not item.issues:
            continue
        issue_text = _issue_human_text(decision)
        if decision.business_status == STATUS_AUTO_DISCOUNT and decision.execution_status == EXEC_DATA_QUALITY_REVIEW:
            impact = "ДА — товар нельзя включать в план, пока данные не исправлены"
            action = "Исправить данные в 1С и повторить расчёт"
        elif all(issue.code == "BARCODE_WHITESPACE" for issue in item.issues):
            impact = "НЕТ — пробелы уже убраны автоматически"
            action = "Информационно; желательно очистить мастер-данные в 1С"
        elif decision.business_status in {STATUS_BLOCK_CATEGORY, STATUS_BLOCK_EXPIRY, STATUS_BLOCK_BRAK, STATUS_MARGIN_ALERT}:
            impact = "НЕ МЕНЯЕТ РЕШЕНИЕ — товар уже обработан по бизнес-правилу"
            action = "Исправить мастер-данные отдельно; решение по уценке смотрите в листе 03"
        else:
            impact = "ТРЕБУЕТ ПРОВЕРКИ"
            action = decision.recommended_action

        ws.cell(r, 1, item.raw.source_row)
        ws.cell(r, 2, item.code_1c).number_format = "@"
        ws.cell(r, 3, item.name)
        _barcode_cell(ws.cell(r, 4), item.barcode_raw_display)
        _barcode_cell(ws.cell(r, 5), item.barcode)
        ws.cell(r, 6, issue_text)
        impact_cell = ws.cell(r, 7, impact)
        if impact.startswith("ДА") or impact.startswith("ТРЕБУЕТ"):
            impact_cell.fill = YELLOW_FILL
            impact_cell.font = Font(bold=True)
        elif impact.startswith("НЕТ"):
            impact_cell.fill = GREEN_FILL
        else:
            impact_cell.fill = GRAY_FILL
        ws.cell(r, 8, action)
        ws.cell(r, 9, ", ".join(issue.code for issue in item.issues))
        for c in range(1, 10):
            ws.cell(r, c).border = THIN
            ws.cell(r, c).alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[r].height = 46
        r += 1
    last = max(r - 1, header_row)
    ws.auto_filter.ref = f"A{header_row}:I{last}"
    _autosize(ws, {1: 13, 2: 13, 3: 46, 4: 25, 5: 25, 6: 56, 7: 42, 8: 52, 9: 34})
    # Технический код оставляем для поддержки, но прячем от обычного пользователя.
    ws.column_dimensions["I"].hidden = True
    ws.sheet_view.showGridLines = False


def build_workbook(decisions: list[Decision], kpi: KpiReport, output_path: Path) -> Path:
    wb = Workbook()
    director = wb.active
    director.title = "01_Директор"
    write_director_sheet(director, kpi, datetime.now())
    plan = wb.create_sheet("02_План_уценки")
    write_plan_sheet(plan, decisions)
    exceptions = wb.create_sheet("03_Исключения")
    write_exceptions_sheet(exceptions, decisions)
    control = wb.create_sheet("04_Контроль_данных")
    write_data_control_sheet(control, decisions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
