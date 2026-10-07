from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.config import DEFAULT_INPUT_XLSX, DEFAULT_OUTPUT_XLSX, DEFAULT_PRINT_XLSX
from src.decision_engine import decide_all
from src.excel_report import build_workbook
from src.kpi import KpiReport, build_kpi
from src.loader import load_items
from src.models import Decision
from src.print_sheet import build_print_workbook
from src.validation import apply_quality_checks

LOGGER = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    decisions: list[Decision]
    kpi: KpiReport
    output_path: Path
    print_path: Path
    input_path: Path
    input_rows: int


def run_pipeline(
    input_path: Path | None = None,
    output_path: Path | None = None,
    print_path: Path | None = None,
    business_date: date | None = None,
) -> PipelineResult:
    source = input_path or DEFAULT_INPUT_XLSX
    target = output_path or DEFAULT_OUTPUT_XLSX
    print_target = print_path or target.with_name(DEFAULT_PRINT_XLSX.name)
    as_of = business_date or date.today()

    if not source.exists():
        raise FileNotFoundError(f"Не найден файл выгрузки: {source}")

    LOGGER.info("Загрузка %s", source)
    items = load_items(source)
    LOGGER.info("Загружено строк: %s", len(items))
    apply_quality_checks(items)
    decisions = decide_all(items, as_of)
    if len(decisions) != len(items):
        raise RuntimeError(
            f"Потеря строк: вход {len(items)}, решений {len(decisions)}"
        )
    kpi = build_kpi(decisions)
    LOGGER.info("Запись Excel %s", target)
    build_workbook(decisions, kpi, target)
    LOGGER.info("Запись листа для печати %s", print_target)
    build_print_workbook(decisions, print_target)
    return PipelineResult(
        decisions=decisions,
        kpi=kpi,
        output_path=target,
        print_path=print_target,
        input_path=source,
        input_rows=len(items),
    )
