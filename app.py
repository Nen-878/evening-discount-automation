from __future__ import annotations

import logging
import os
import platform
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DEFAULT_INPUT_XLSX, DEFAULT_OUTPUT_XLSX  # noqa: E402
from src.pipeline import PipelineResult, run_pipeline  # noqa: E402

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "app.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)

BG = "#F4F7FB"
SURFACE = "#FFFFFF"
TEXT = "#172033"
MUTED = "#6B7280"
PRIMARY = "#1D4ED8"
PRIMARY_DARK = "#1E40AF"
GREEN = "#15803D"
AMBER = "#B45309"
RED = "#B91C1C"
SLATE = "#334155"
BORDER = "#DDE3EA"
HEADER_BG = "#0F172A"


def money(value) -> str:
    """Human-friendly tenge formatting without relying on OS currency locale."""
    formatted = f"{value:,.1f}".replace(",", " ").replace(".", ",")
    return f"{formatted} ₸"


def count(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def open_path(path: Path) -> None:
    system = platform.system()
    if system == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class DiscountApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Вечерняя уценка кулинарии — 20:00")
        self.root.geometry("1040x800")
        self.root.minsize(920, 720)
        self.root.configure(bg=BG)
        self._maximize_window()

        self.input_var = tk.StringVar(value=str(DEFAULT_INPUT_XLSX))
        self.status_var = tk.StringVar(value="Выберите выгрузку 1С и запустите расчет")
        self.output_path: Path | None = None
        self.print_path: Path | None = None
        self._running = False
        self._result_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_styles()
        self._build_ui()
        self.root.after(80, self._maximize_window)

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Surface.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 13))
        style.configure(
            "Primary.TButton",
            font=("Segoe UI Semibold", 11),
            padding=(18, 10),
            foreground="white",
            background=PRIMARY,
            borderwidth=0,
        )
        style.map("Primary.TButton", background=[("active", PRIMARY_DARK), ("disabled", "#9CA3AF")])
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30, background=SURFACE, fieldbackground=SURFACE)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10), background="#E9EEF5", foreground=TEXT)
        style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", TEXT)])
        style.configure("Blue.Horizontal.TProgressbar", troughcolor="#E5E7EB", background=PRIMARY)

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg=HEADER_BG, height=96)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Вечерняя уценка кулинарии",
            bg=HEADER_BG,
            fg="white",
            font=("Segoe UI Semibold", 22),
        ).pack(anchor="w", padx=34, pady=(16, 2))
        tk.Label(
            header,
            text="Срез 19:30 → стикеры 19:40–20:00 → кассовая скидка с 20:00",
            bg=HEADER_BG,
            fg="#CBD5E1",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=35)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=30, pady=16)

        self._build_source_panel(container)
        self._build_summary(container)
        self._build_details(container)
        self._build_footer(container)

    def _build_source_panel(self, parent: tk.Widget) -> None:
        panel = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="x", pady=(0, 18))

        tk.Label(panel, text="Выгрузка 1С", bg=SURFACE, fg=TEXT, font=("Segoe UI Semibold", 11)).grid(
            row=0, column=0, sticky="w", padx=18, pady=(15, 6)
        )
        tk.Label(
            panel,
            text="Можно выбрать любой .xlsx — переименовывать файл не нужно",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).grid(row=0, column=1, columnspan=2, sticky="w", pady=(15, 6))

        self.file_entry = ttk.Entry(panel, textvariable=self.input_var, font=("Segoe UI", 10))
        self.file_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(18, 10), pady=(0, 15), ipady=5)
        ttk.Button(panel, text="Выбрать файл", style="Secondary.TButton", command=self._choose_file).grid(
            row=1, column=2, padx=(0, 18), pady=(0, 15)
        )

        action_row = tk.Frame(panel, bg=SURFACE)
        action_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=18, pady=(0, 16))
        self.run_button = ttk.Button(action_row, text="Рассчитать уценку", style="Primary.TButton", command=self._run)
        self.run_button.pack(side="left")
        self.progress = ttk.Progressbar(action_row, mode="indeterminate", length=180, style="Blue.Horizontal.TProgressbar")
        self.progress.pack(side="left", padx=(16, 12), fill="x", expand=False)
        tk.Label(action_row, textvariable=self.status_var, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(
            side="left", padx=(4, 0), fill="x", expand=True
        )

        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)

    def _build_summary(self, parent: tk.Widget) -> None:
        tk.Label(parent, text="Итог смены", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 13)).pack(anchor="w", pady=(0, 8))

        cards = tk.Frame(parent, bg=BG)
        cards.pack(fill="x", pady=(0, 16))
        self.card_values: dict[str, tk.Label] = {}
        specs = [
            ("ready", "Готовы к уценке", GREEN),
            ("dq", "Проверка данных", AMBER),
            ("expiry", "Истекают к 20:00", RED),
            ("category", "Запрещенные", SLATE),
            ("margin", "Решение директора", PRIMARY),
        ]
        for i, (key, label, color) in enumerate(specs):
            card = tk.Frame(cards, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 5, 0 if i == len(specs) - 1 else 5))
            value = tk.Label(card, text="—", bg=SURFACE, fg=color, font=("Segoe UI Semibold", 20))
            value.pack(anchor="w", padx=14, pady=(12, 0))
            tk.Label(card, text=label, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9), wraplength=150, justify="left").pack(
                anchor="w", padx=14, pady=(2, 12)
            )
            self.card_values[key] = value
            cards.grid_columnconfigure(i, weight=1, uniform="summary")

        money_row = tk.Frame(parent, bg=BG)
        money_row.pack(fill="x", pady=(0, 18))
        self.money_values: dict[str, tk.Label] = {}
        money_specs = [
            ("potential", "Бизнес-потенциал промо", PRIMARY),
            ("ready", "Исполнимая сегодня выручка", GREEN),
            ("risk", "Под риском из-за мастер-данных", AMBER),
        ]
        for i, (key, label, color) in enumerate(money_specs):
            card = tk.Frame(money_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == len(money_specs) - 1 else 6))
            tk.Label(card, text=label, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=15, pady=(11, 2))
            value = tk.Label(card, text="—", bg=SURFACE, fg=color, font=("Segoe UI Semibold", 16))
            value.pack(anchor="w", padx=15, pady=(0, 11))
            self.money_values[key] = value
            money_row.grid_columnconfigure(i, weight=1, uniform="money")

    def _build_details(self, parent: tk.Widget) -> None:
        title_row = tk.Frame(parent, bg=BG)
        title_row.pack(fill="x", pady=(0, 7))
        tk.Label(title_row, text="Контрольные показатели", bg=BG, fg=TEXT, font=("Segoe UI Semibold", 13)).pack(side="left")
        tk.Label(title_row, text="Подробный Excel формируется автоматически", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(
            side="right"
        )

        table_box = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        table_box.pack(fill="both", expand=True)

        columns = ("metric", "value", "meaning")
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings", height=4)
        self.tree.heading("metric", text="Показатель")
        self.tree.heading("value", text="Значение")
        self.tree.heading("meaning", text="Что это означает")
        self.tree.column("metric", width=230, anchor="w")
        self.tree.column("value", width=130, anchor="center")
        self.tree.column("meaning", width=520, anchor="w")
        scrollbar = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        scrollbar.pack(side="right", fill="y", pady=1)

        self._set_placeholder_rows()

    def _build_footer(self, parent: tk.Widget) -> None:
        footer = tk.Frame(parent, bg=BG)
        footer.pack(fill="x", pady=(14, 0))
        self.open_excel_button = ttk.Button(
            footer, text="Открыть итоговый Excel", style="Secondary.TButton", command=self._open_excel, state="disabled"
        )
        self.open_excel_button.pack(side="left")
        self.open_print_button = ttk.Button(
            footer, text="Открыть лист для печати", style="Secondary.TButton", command=self._open_print_sheet, state="disabled"
        )
        self.open_print_button.pack(side="left", padx=(8, 0))
        self.open_folder_button = ttk.Button(
            footer, text="Открыть папку", style="Secondary.TButton", command=self._open_folder, state="disabled"
        )
        self.open_folder_button.pack(side="left", padx=(8, 0))
        tk.Label(
            footer,
            text="Расчет выполняется локально по регламенту. AI/API при работе программы не используется.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(side="right")

    def _maximize_window(self) -> None:
        """Open maximized while keeping the normal Windows title bar/taskbar."""
        try:
            if platform.system() == "Windows":
                self.root.state("zoomed")
            else:
                self.root.attributes("-zoomed", True)
        except tk.TclError:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+0+0")

    def _set_placeholder_rows(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = [
            ("Всего позиций", "—", "Все строки выбранной выгрузки"),
            ("Подходят по бизнес-правилам", "—", "Кандидаты на стандартную скидку −30%"),
            ("Срок годности заканчивается к 20:00", "—", "В вечернюю уценку не включаются"),
            ("Категория не участвует в акции", "—", "Запрещено регламентом"),
            ("Бракераж / списание", "—", "Остаток ниже технологического порога"),
            ("Нужно решение директора", "—", "Скидка −30% нарушает минимальную маржу"),
        ]
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Выберите выгрузку 1С",
            initialdir=str(Path(self.input_var.get()).parent if self.input_var.get() else ROOT),
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if selected:
            self.input_var.set(selected)
            self.status_var.set("Файл выбран. Можно запускать расчет")

    def _run(self) -> None:
        if self._running:
            return
        source = Path(self.input_var.get().strip())
        if not source.exists():
            messagebox.showerror("Файл не найден", "Выбранный файл не найден. Укажите актуальную выгрузку 1С.")
            return
        if source.suffix.lower() != ".xlsx":
            messagebox.showerror("Неверный формат", "Нужен Excel-файл формата .xlsx")
            return

        self._running = True
        self.run_button.configure(state="disabled")
        self.open_excel_button.configure(state="disabled")
        self.open_print_button.configure(state="disabled")
        self.open_folder_button.configure(state="disabled")
        self.status_var.set("Обрабатываю выгрузку и формирую отчет…")
        self.progress.start(10)

        thread = threading.Thread(target=self._worker, args=(source,), daemon=True)
        thread.start()
        self.root.after(60, self._poll_worker)

    def _worker(self, source: Path) -> None:
        try:
            result = run_pipeline(input_path=source, output_path=DEFAULT_OUTPUT_XLSX)
        except Exception as exc:
            LOGGER.exception("GUI pipeline failed")
            self._result_queue.put(("error", exc))
            return
        self._result_queue.put(("success", result))

    def _poll_worker(self) -> None:
        try:
            kind, payload = self._result_queue.get_nowait()
        except queue.Empty:
            if self._running:
                self.root.after(60, self._poll_worker)
            return

        if kind == "success":
            self._finish_success(payload)  # type: ignore[arg-type]
        else:
            self._finish_error(payload)  # type: ignore[arg-type]

    def _finish_success(self, result: PipelineResult) -> None:
        self._running = False
        self.progress.stop()
        self.run_button.configure(state="normal")
        self.output_path = result.output_path
        self.print_path = result.print_path
        self.open_excel_button.configure(state="normal")
        self.open_print_button.configure(state="normal")
        self.open_folder_button.configure(state="normal")

        kpi = result.kpi
        self.card_values["ready"].configure(text=count(kpi.execution_ready))
        self.card_values["dq"].configure(text=count(kpi.data_quality_review))
        self.card_values["expiry"].configure(text=count(kpi.block_expiry))
        self.card_values["category"].configure(text=count(kpi.block_category))
        self.card_values["margin"].configure(text=count(kpi.margin_alert))

        self.money_values["potential"].configure(text=money(kpi.potential_revenue_after_discount))
        self.money_values["ready"].configure(text=money(kpi.ready_revenue))
        self.money_values["risk"].configure(text=money(kpi.master_data_revenue_at_risk))

        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = [
            ("Всего позиций", count(kpi.input_rows), "Все строки выбранной выгрузки"),
            ("Подходят по бизнес-правилам", count(kpi.auto_discount), "Кандидаты на стандартную скидку −30%"),
            ("Готовы к уценке", count(kpi.execution_ready), "Можно брать в работу и клеить стикеры"),
            ("Нужно исправить данные", count(kpi.data_quality_review), "Проблемы штрихкодов мешают безопасному исполнению"),
            ("Срок годности заканчивается к 20:00", count(kpi.block_expiry), "В вечернюю уценку не включаются"),
            ("Категория не участвует в акции", count(kpi.block_category), "Запрещено регламентом"),
            ("Бракераж / списание", count(kpi.block_brak), "Остаток ниже технологического порога"),
            ("Нужно решение директора", count(kpi.margin_alert), "Скидка −30% нарушает минимальную маржу"),
        ]
        for row in rows:
            self.tree.insert("", "end", values=row)

        self.status_var.set(f"Готово. Обработано {kpi.input_rows} позиций; план уценки — {kpi.execution_ready}")

    def _finish_error(self, exc: Exception) -> None:
        self._running = False
        self.progress.stop()
        self.run_button.configure(state="normal")
        self.status_var.set("Расчет не завершен — проверьте сообщение")

        if isinstance(exc, PermissionError):
            title = "Не удалось сохранить Excel"
            message = (
                "Один из выходных Excel-файлов сейчас открыт или заблокирован другой программой.\n\n"
                "Закройте итоговый отчет и лист для печати, затем нажмите «Рассчитать уценку» еще раз."
            )
        elif isinstance(exc, FileNotFoundError):
            title = "Файл не найден"
            message = "Не удалось найти выбранную выгрузку. Выберите актуальный файл 1С и повторите расчет."
        elif isinstance(exc, ValueError):
            title = "Проверьте структуру выгрузки"
            message = f"Входной Excel не соответствует ожидаемой структуре.\n\n{exc}"
        else:
            title = "Не удалось выполнить расчет"
            message = (
                "Произошла техническая ошибка. Подробности записаны в app.log.\n\n"
                f"Кратко: {exc}"
            )
        messagebox.showerror(title, message)

    def _open_excel(self) -> None:
        if self.output_path and self.output_path.exists():
            try:
                open_path(self.output_path)
            except Exception as exc:
                LOGGER.exception("Cannot open Excel")
                messagebox.showerror("Не удалось открыть файл", str(exc))

    def _open_print_sheet(self) -> None:
        if self.print_path and self.print_path.exists():
            try:
                open_path(self.print_path)
            except Exception as exc:
                LOGGER.exception("Cannot open print sheet")
                messagebox.showerror("Не удалось открыть лист для печати", str(exc))

    def _open_folder(self) -> None:
        path = self.output_path.parent if self.output_path else ROOT
        try:
            open_path(path)
        except Exception as exc:
            LOGGER.exception("Cannot open output folder")
            messagebox.showerror("Не удалось открыть папку", str(exc))


def main() -> None:
    root = tk.Tk()
    DiscountApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
