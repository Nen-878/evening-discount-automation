from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_pipeline  # noqa: E402


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def print_summary(result) -> None:
    kpi = result.kpi
    lines = [
        "",
        "==== Вечерняя уценка 20:00 — итог ====",
        f"Исходных строк:                    {kpi.input_rows}",
        "",
        "Бизнес-решения:",
        f"  AUTO_DISCOUNT:                   {kpi.auto_discount}",
        f"  BLOCK_CATEGORY:                  {kpi.block_category}",
        f"  BLOCK_EXPIRY:                    {kpi.block_expiry}",
        f"  BLOCK_BRAK:                      {kpi.block_brak}",
        f"  MARGIN_ALERT:                    {kpi.margin_alert}",
        "",
        "Готовность исполнения AUTO_DISCOUNT:",
        f"  READY:                           {kpi.execution_ready}",
        f"  DATA_QUALITY_REVIEW:             {kpi.data_quality_review}",
        "",
        f"Бизнес-потенциал промо-выручки:   {kpi.potential_revenue_after_discount} ₸",
        f"Исполнимая сегодня промо-выручка: {kpi.ready_revenue} ₸",
        f"Под риском из-за мастер-данных:    {kpi.master_data_revenue_at_risk} ₸",
        f"Итоговый Excel:                    {result.output_path}",
        f"Лист для печати:                   {result.print_path}",
        "",
    ]
    print("\n".join(lines))


def main() -> int:
    configure_logging()
    try:
        result = run_pipeline()
    except Exception as exc:
        logging.getLogger(__name__).exception("Конвейер остановлен")
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
