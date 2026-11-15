"""统计分析页：收支概览、月度趋势及分类和商家排行。"""

from __future__ import annotations

from .icons import icon

import math
from calendar import monthrange
from datetime import date
from PySide6.QtWidgets import QGridLayout, QScrollArea, QProgressBar, QSizePolicy
from ..ledger import expense_totals
from .widgets import FittedColumns
from collections import Counter
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton, QComboBox,
)

from ..models import Transaction
from .theme import (
    COLOR_CARD, COLOR_TEXT, COLOR_ACCENT, COLOR_RED, COLOR_GREEN,
)

from .charts import Chart


class StatTile(QFrame):
    """可点击的统计数字卡：点击后跳转。"""

    clicked = Signal()

    def __init__(self, label: str, value: str, accent: str = COLOR_TEXT, key: str = ""):
        super().__init__()
        self.setObjectName("statTile")
        self.setCursor(Qt.PointingHandCursor)
        self.key = key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        self.value_label.setStyleSheet(f"color:{accent};")
        self.name_label = QLabel(label)
        self.name_label.setObjectName("statLabel")
        lay.addWidget(self.name_label)
        lay.addWidget(self.value_label)
        self.setMinimumWidth(96)

    def set_value(self, v: str) -> None:
        self.value_label.setText(v)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main = None
        self._txns = []
        self.breakdown_period = None
        self._trend_info = self._trend_annot = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(18)
        header = QHBoxLayout()
        title = QLabel("统计分析")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(16)
        self.overview = QGridLayout()
        layout.addLayout(self.overview)
        self.tiles = []
        for name, direction in [("支出总额", "支出"), ("支出笔数", "支出"), ("收入总额", "收入"), ("收入笔数", "收入"), ("未分类支出", "未分类")]:
            tone, accent = {"支出": ("expense", COLOR_RED), "收入": ("income", COLOR_GREEN),
                            "未分类": ("pending", "#654587")}[direction]
            tile = StatTile(name, "0", accent)
            tile.setProperty("tone", tone)
            if direction == "未分类":
                tile.clicked.connect(lambda: self._goto_table("支出", "未分类"))
            else:
                tile.clicked.connect(lambda d=direction: self._goto_table(d))
            self.tiles.append(tile)
        chart_card = QFrame()
        chart_card.setObjectName("card")
        chart = QVBoxLayout(chart_card)
        chart.setContentsMargins(16, 14, 16, 8)
        heading = QLabel("月度支出趋势")
        heading.setObjectName("sectionTitle")
        chart.addWidget(heading)
        layout.addWidget(chart_card)
        pie_card = QFrame()
        pie_card.setObjectName("card")
        pie_card.setMinimumWidth(200)
        pie_card.setMinimumHeight(260)
        pie_layout = QVBoxLayout(pie_card)
        pie_layout.setContentsMargins(10, 14, 10, 8)
        pie_title = QLabel("支出占比")
        pie_title.setObjectName("sectionTitle")
        pie_layout.addWidget(pie_title)
        self.pie_canvas = Chart(ring=True)
        self.pie_canvas.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.pie_canvas.selected.connect(lambda name: self._goto_table("支出", name, self.breakdown_period) if name != "其余分类" else None)
        pie_layout.addWidget(self.pie_canvas)

        self.trend_canvas = Chart()
        self.trend_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.trend_canvas.setMinimumHeight(255)
        chart.addWidget(self.trend_canvas)
        self.trend_canvas.selected.connect(lambda month: self._goto_table("支出", month=month))
        month_bar = QHBoxLayout()
        month_bar.addStretch()
        self.breakdown_button = QPushButton(icon("calendar"), "全部时间")
        self.breakdown_button.clicked.connect(self._choose_breakdown_period)
        month_bar.addWidget(self.breakdown_button)
        layout.addLayout(month_bar)
        self.tables = QGridLayout()
        layout.addLayout(self.tables)
        self.panels = [pie_card]
        for title, columns in [("分类支出", ["分类", "占比", "金额（元）"]), ("商家消费排行", ["商家", "笔数", "金额（元）"])]:
            panel = QFrame()
            panel.setObjectName("card")
            column = QVBoxLayout(panel)
            heading = QLabel(title)
            heading.setObjectName("sectionTitle")
            column.addWidget(heading)
            table = QTableWidget(0, len(columns))
            table.setShowGrid(False)
            table.setHorizontalHeaderLabels(columns)
            table.verticalHeader().hide()
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setColumnWidth(0, 220)
            FittedColumns(table)
            table.setMinimumHeight(235)
            self.panels.append(panel)
            if title == "分类支出":
                column.addWidget(table)
                self.categories = table
                table.cellClicked.connect(self._category_clicked)
            else:
                column.addWidget(table)
                self.merchant_table = table
        self._columns = None
        self._arrange()
        layout.addStretch()

    def set_main(self, main):
        self.main = main

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange()

    def _arrange(self):
        cols = 5 if self.width() >= 800 else (3 if self.width() >= 540 else 2)
        if cols == self._columns:
            return
        self._columns = cols
        for i, tile in enumerate(self.tiles):
            self.overview.addWidget(tile, i // cols, i % cols)
        for i, panel in enumerate(self.panels):
            self.tables.addWidget(panel, 0 if cols == 5 else i, i if cols == 5 else 0)

    def _goto_table(self, direction, category=None, month=None):
        table = self.main.table_page
        table.clear_filters()
        table.set_period(None, "全部时间")
        if month:
            if isinstance(month, tuple):
                first, last = month
            else:
                year, number = map(int, month.split("-"))
                first, last = date(year, number, 1), date(year, number, monthrange(year, number)[1])
            table.set_period((first, last), f"{first} 至 {last}")
        table.set_external_direction(direction)
        if category:
            table.set_external_category(category)
        self.main.nav.setCurrentRow(1)

    def _category_clicked(self, row, column):
        self._goto_table("支出", self.categories.item(row, 0).text(), self.breakdown_period)

    def refresh(self, txns):
        self._txns = list(txns)
        expenses = [t for t in txns if t.is_expense]
        incomes = [t for t in txns if t.is_income]
        total = sum(t.net_amount for t in expenses)
        values = [f"¥{total:.2f}", str(len(expenses)), f"¥{sum(t.net_amount for t in incomes):.2f}", str(len(incomes)), str(sum(not t.category for t in expenses))]
        for tile, value in zip(self.tiles, values):
            tile.set_value(value)
        self._draw_trend([t for t in expenses if t.time])
        self._refresh_breakdown()

    def _choose_breakdown_period(self):
        from .date_range import DateRangeDialog
        from PySide6.QtWidgets import QDialog
        anchor = max((t.time.date() for t in self._txns if t.time), default=date.today())
        dialog = DateRangeDialog(self.breakdown_period, anchor, self)
        if dialog.exec() == QDialog.Accepted:
            self.breakdown_period = dialog.period
            label = "全部时间" if not dialog.period else f"{dialog.period[0]} 至 {dialog.period[1]}"
            self.breakdown_button.setText(label)
            self._refresh_breakdown()

    def _refresh_breakdown(self):
        month = self.breakdown_period
        expenses = [t for t in self._txns if t.is_expense and (not month or (t.time and month[0] <= t.time.date() <= month[1]))]
        total = sum(t.net_amount for t in expenses)
        groups = expense_totals(expenses, lambda t: t.category_display)
        self.categories.setRowCount(len(groups))
        for i, (name, amount) in enumerate(groups.most_common()):
            item = QTableWidgetItem(name)
            item.setToolTip(name)
            self.categories.setItem(i, 0, item)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            share = amount / total if total else 0
            bar.setValue(round(1000 * share))
            bar.setFormat(f"{share:.1%}")
            bar.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.categories.setCellWidget(i, 1, bar)
            self.categories.setItem(i, 2, QTableWidgetItem(f"{amount:.2f}"))
        self._draw_categories(groups)
        self._fill_merchant(expenses)

    def _draw_categories(self, groups):
        items = [(k,v) for k,v in groups.most_common() if v > 0]
        display = items[:5]
        if len(items)>5:
            display += [("其余分类",sum(v for _,v in items[5:]))]
        self.pie_canvas.set_items(display)

    def _draw_trend(self, expenses):
        months = Counter()
        for row in expenses:
            months[row.month] += row.net_amount
        self.trend_canvas.set_items(sorted(months.items()))

    # ---- 商家排行 ----
    def _fill_merchant(self, expenses: List[Transaction]) -> None:
        cnt = Counter()
        num = Counter()
        for t in expenses:
            name = t.counterparty or "(无商家)"
            cnt[name] += t.net_amount
            num[name] += 1
        items = sorted(cnt.items(), key=lambda kv: -kv[1])
        self.merchant_table.setRowCount(len(items))
        for i, (name, amount) in enumerate(items):
            self.merchant_table.setItem(i, 0, QTableWidgetItem(name))
            self.merchant_table.setItem(i, 1, QTableWidgetItem(str(num[name])))
            self.merchant_table.setItem(i, 2, QTableWidgetItem(f"{amount:.2f}"))
