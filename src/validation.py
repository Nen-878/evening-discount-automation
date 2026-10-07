from __future__ import annotations

from collections import defaultdict

from src.models import ParsedItem, QualityIssue

SCIENTIFIC_MARKERS = ("E+", "e+", "E-", "e-")


def inspect_barcode(barcode: str | None, raw_barcode: object | None = None) -> list[QualityIssue]:
    """Validate a normalized barcode while preserving raw-value diagnostics."""
    issues: list[QualityIssue] = []
    raw_text = None if raw_barcode is None else str(raw_barcode)

    if barcode is None or barcode == "":
        issues.append(QualityIssue("BARCODE_MISSING", "Штрихкод отсутствует или пустой"))
        return issues

    if raw_text is not None and raw_text != raw_text.strip():
        issues.append(
            QualityIssue(
                "BARCODE_WHITESPACE",
                "По краям штрихкода были пробелы; применён безопасный trim, исходное значение сохранено",
            )
        )
    if ";" in barcode:
        issues.append(
            QualityIssue(
                "BARCODE_MULTI",
                "В ячейке несколько штрихкодов через ';'; автоматически не выбирается ни один",
            )
        )
    if any(marker in barcode for marker in SCIENTIFIC_MARKERS):
        issues.append(
            QualityIssue(
                "BARCODE_SCIENTIFIC",
                "Штрихкод в научной нотации; исходный полный код восстановить однозначно нельзя",
            )
        )
    return issues


def inspect_numeric_sanity(item: ParsedItem) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    if item.qty is not None and item.qty < 0:
        issues.append(QualityIssue("QTY_NEGATIVE", "Отрицательный остаток"))
    if item.qty is not None and item.qty == 0:
        issues.append(QualityIssue("QTY_ZERO", "Нулевой остаток"))
    if item.retail_price is not None and item.retail_price < 0:
        issues.append(QualityIssue("RETAIL_NEGATIVE", "Отрицательная розничная цена"))
    if item.retail_price is not None and item.retail_price == 0:
        issues.append(QualityIssue("RETAIL_ZERO", "Нулевая розничная цена"))
    if item.cost is not None and item.cost < 0:
        issues.append(QualityIssue("COST_NEGATIVE", "Отрицательная себестоимость"))
    if item.cost is not None and item.cost == 0:
        issues.append(QualityIssue("COST_ZERO", "Нулевая себестоимость"))
    if item.shelf_hours is not None and item.shelf_hours <= 0:
        issues.append(QualityIssue("SHELF_HOURS_NON_POSITIVE", "Срок годности в часах неположительный"))
    return issues


def mark_duplicate_barcodes(items: list[ParsedItem]) -> None:
    groups: dict[str, list[ParsedItem]] = defaultdict(list)
    for item in items:
        if not item.barcode:
            continue
        groups[item.barcode].append(item)
    for barcode, grouped in groups.items():
        if len(grouped) < 2:
            continue
        names = {row.name for row in grouped}
        codes = {row.code_1c for row in grouped}
        if len(names) == 1 and len(codes) == 1:
            continue
        for row in grouped:
            row.issues.append(
                QualityIssue(
                    "BARCODE_DUPLICATE",
                    f"Один и тот же нормализованный штрихкод {barcode!r} указан у разных позиций",
                )
            )


def apply_quality_checks(items: list[ParsedItem]) -> list[ParsedItem]:
    for item in items:
        item.issues.extend(inspect_barcode(item.barcode, item.raw.barcode_raw))
        item.issues.extend(inspect_numeric_sanity(item))
    mark_duplicate_barcodes(items)
    return items


def has_issue(item: ParsedItem, *codes: str) -> bool:
    found = {issue.code for issue in item.issues}
    return any(code in found for code in codes)


CRITICAL_PARSE_CODES = frozenset(
    {
        "ROW_PARSE_FAILURE",
        "EMPTY_CATEGORY",
        "EMPTY_UNIT",
        "QTY_UNPARSEABLE",
        "RETAIL_UNPARSEABLE",
        "COST_UNPARSEABLE",
        "SHELF_HOURS_UNPARSEABLE",
        "PRODUCTION_UNPARSEABLE",
        "QTY_NEGATIVE",
        "RETAIL_NEGATIVE",
        "RETAIL_ZERO",
        "COST_NEGATIVE",
        "COST_ZERO",
        "SHELF_HOURS_NON_POSITIVE",
        "EMPTY_NAME",
    }
)

BARCODE_UNSAFE_CODES = frozenset(
    {
        "BARCODE_MISSING",
        "BARCODE_MULTI",
        "BARCODE_SCIENTIFIC",
        "BARCODE_DUPLICATE",
        "BARCODE_NUMERIC_FLOAT",
    }
)


def critical_data_issues(item: ParsedItem) -> list[QualityIssue]:
    return [issue for issue in item.issues if issue.code in CRITICAL_PARSE_CODES]


def barcode_unsafe_issues(item: ParsedItem) -> list[QualityIssue]:
    return [issue for issue in item.issues if issue.code in BARCODE_UNSAFE_CODES]


def data_quality_summary(items: list[ParsedItem]) -> dict[str, int]:
    summary: dict[str, int] = defaultdict(int)
    summary["rows"] = len(items)
    for item in items:
        for issue in item.issues:
            summary[issue.code] += 1
    return dict(summary)
