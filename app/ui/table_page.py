"""账单明细页：表格展示 + 勾选 + 筛选 + 批量归类 + 右键菜单 + 高级查找。"""

from __future__ import annotations

from .icons import icon

import re
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QLineEdit,
    QComboBox, QTableView, QMenu, QPushButton, QAbstractItemView,
    QHeaderView, QMessageBox, QDialog, QCheckBox, QFormLayout,
    QDoubleSpinBox,
)

from ..models import (
    Transaction, UNCATEGORIZED, PLATFORM_WECHAT, PLATFORM_ALIPAY,
)
from .theme import (
    COLOR_TEXT, COLOR_RED, COLOR_ACCENT, COLOR_GREEN, COLOR_TEXT_DIM,
)
from .widgets import autosize_button

_COLS = [
    ("时间", "time"),
    ("平台", "platform_label"),
    ("方向", "direction"),
    ("金额", "amount"),
    ("分类", "category"),
    ("交易对方", "counterparty"),
    ("商品说明", "goods"),
    ("平台类型", "platform_type"),
    ("支付方式", "payment_method"),
    ("状态", "status"),
]

_DEFAULT_COLS = len(_COLS)
_COLS += [
    ("交易单号", "txn_id"), ("商户单号", "merchant_id"),
    ("原支付单号", "original_order_id"), ("退款单号", "refund_id"),
    ("备注", "remark"), ("退款关联", "refund_note"), ("计入金额", "net_amount"),
]

_SEARCH_FIELDS = [
    ("任意字段", ""),
    ("交易对方", "counterparty"),
    ("商品说明", "goods"),
    ("平台类型", "platform_type"),
    ("支付方式", "payment_method"),
    ("状态", "status"),
    ("交易单号", "txn_id"),
]


class TransactionModel(QAbstractTableModel):
    """交易表格模型，可选择性在最前面显示一列复选框。"""

    checkedChanged = Signal()

    def __init__(self, show_checkbox: bool = False):
        super().__init__()
        self._show_checkbox = show_checkbox
        self._all: List[Transaction] = []
        self._rows: List[Transaction] = []
        self._checked: set = set()
        self._category_filter: str = ""
        self._search: str = ""
        self._direction_filter: str = ""
        self._date_start: Optional[datetime] = None
        self._date_end: Optional[datetime] = None
        self._regex = None
        self._regex_field: str = ""
        self._amount_min: Optional[float] = None
        self._amount_max: Optional[float] = None
        self._platform: str = ""
        self._sort_column: Optional[int] = None
        self._sort_order = Qt.AscendingOrder

    @property
    def _offset(self) -> int:
        return 1 if self._show_checkbox else 0

    # ---- 数据源 ----
    def set_data(self, txns: List[Transaction]) -> None:
        self._all = list(txns)
        self._checked.clear()
        self.checkedChanged.emit()
        self.apply_filter()

    def set_filters(
        self,
        search: str = "",
        category: str = "",
        direction: str = "",
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
        regex: str = "",
        regex_field: str = "",
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        platform: str = "",
    ) -> None:
        self._search = search.strip().lower()
        self._category_filter = category
        self._direction_filter = direction
        self._date_start = date_start
        self._date_end = date_end
        if regex:
            try:
                self._regex = re.compile(regex)
            except re.error:
                self._regex = None
        else:
            self._regex = None
        self._regex_field = regex_field
        self._amount_min = amount_min
        self._amount_max = amount_max
        self._platform = platform
        self.apply_filter()

    # ---- 排序 ----
    @staticmethod
    def _sort_key_for(column: int):
        key = _COLS[column][1]

        def keyfn(t: Transaction):
            if key == "time":
                return t.time or datetime.min
            if key in ("amount", "net_amount"):
                return getattr(t, key)
            return str(getattr(t, key, "") or "")

        return keyfn

    def sort(self, column: int, order=Qt.AscendingOrder) -> None:
        if self._show_checkbox and column == 0:
            return
        data_col = column - self._offset
        self._sort_column = data_col
        self._sort_order = order
        self._rows.sort(key=self._sort_key_for(data_col), reverse=(order == Qt.DescendingOrder))
        self.layoutChanged.emit()

    # ---- 过滤 ----
    def _regex_match(self, t: Transaction) -> bool:
        if self._regex is None:
            return True
        if self._regex_field:
            text = str(getattr(t, self._regex_field, "") or "")
            return bool(self._regex.search(text))
        hay = " ".join([
            t.counterparty, t.goods, t.txn_type, t.original_category,
            t.payment_method, t.status, t.txn_id,
        ])
        return bool(self._regex.search(hay))

    def apply_filter(self) -> None:
        rows = []
        for t in self._all:
            if self._direction_filter and t.accounting_direction != self._direction_filter:
                continue
            if self._category_filter:
                if self._category_filter == UNCATEGORIZED:
                    if t.category_display != UNCATEGORIZED:
                        continue
                elif t.category_display != self._category_filter:
                    continue
            if self._date_start or self._date_end:
                if t.time is None:
                    continue
                if self._date_start and t.time < self._date_start:
                    continue
                if self._date_end and t.time > self._date_end:
                    continue
            if self._amount_min is not None and t.amount < self._amount_min:
                continue
            if self._amount_max is not None and t.amount > self._amount_max:
                continue
            if self._platform and t.platform != self._platform:
                continue
            if self._regex is not None and not self._regex_match(t):
                continue
            if self._search:
                hay = " ".join([
                    t.counterparty, t.goods, t.txn_type,
                    t.original_category, t.payment_method,
                ]).lower()
                if self._search not in hay:
                    continue
            rows.append(t)
        if self._sort_column is not None:
            rows.sort(key=self._sort_key_for(self._sort_column),
                      reverse=(self._sort_order == Qt.DescendingOrder))
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    # ---- 模型基础 ----
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._rows)

    def column_options(self):
        return [(i + self._offset, label, key, i < _DEFAULT_COLS)
                for i, (label, key) in enumerate(_COLS)]

    def preferred_widths(self, table, available):
        metrics = table.fontMetrics()
        samples = {"time": "2026-09-30 23:59:59", "platform_label": "支付宝",
                   "direction": "不计收支", "amount": "9999.99", "category": "生活服务",
                   "platform_type": "商户消费", "payment_method": "工行储蓄卡碰友日立减",
                   "status": "已全额退款", "txn_id": "0" * 24, "merchant_id": "0" * 22,
                   "refund_id": "0" * 22, "original_order_id": "0" * 22}
        widths = [34] if self._show_checkbox else []
        flexible = {}
        for i, label, key, _ in self.column_options():
            if table.isColumnHidden(i):
                widths.append(0)
                continue
            header_width = table.horizontalHeader().fontMetrics().horizontalAdvance(label) + 32
            widths.append(max(metrics.horizontalAdvance(samples.get(key, label)) + 30, header_width))
            if key in ("counterparty", "goods"):
                flexible[i] = 3 if key == "goods" else 2
        extra = max(0, available - sum(widths))
        if flexible:
            left = extra
            for index, weight in flexible.items():
                share = extra * weight // sum(flexible.values())
                widths[index] += share
                left -= share
            widths[max(flexible)] += left
        return widths

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(_COLS) + self._offset

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if self._show_checkbox and section == 0:
                return ""
            return _COLS[section - self._offset][0]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        if self._show_checkbox and index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if self._show_checkbox and index.column() == 0:
            if role == Qt.CheckStateRole:
                t = self._rows[index.row()]
                return Qt.Checked if id(t) in self._checked else Qt.Unchecked
            return None
        t = self._rows[index.row()]
        key = _COLS[index.column() - self._offset][1]
        val = getattr(t, key, "")

        if role == Qt.ToolTipRole:
            if t.own_card:
                return f"{val} · 本人账户划转：{t.own_card}，不计收支"
            if t.refund_note:
                return f"{val} · {t.refund_note} · 计入收支 {t.net_amount:.2f} 元"
            return str(val)
        if role == Qt.DisplayRole:
            if key in ("amount", "net_amount"):
                return f"{val:.2f}"
            if key == "time" and t.time:
                return t.time.strftime("%Y-%m-%d %H:%M:%S")
            if key == "direction" and t.own_card:
                return t.accounting_direction
            if key == "category":
                return t.category_display
            return val

        if role == Qt.ForegroundRole:
            if key == "amount" and t.direction == "收入":
                return QColor(COLOR_GREEN)
            if key == "category":
                if t.direction == "收入":
                    return QColor(COLOR_GREEN)
                if t.category_display == UNCATEGORIZED:
                    return QColor(COLOR_RED)
                if t.direction == "不计收支":
                    return QColor(COLOR_TEXT_DIM)
                return QColor(COLOR_ACCENT)
            if key == "direction":
                if t.direction == "收入":
                    return QColor(COLOR_GREEN)
                if t.direction == "不计收支":
                    return QColor(COLOR_TEXT_DIM)
            return None

        if role == Qt.TextAlignmentRole:
            if key in ("amount", "net_amount"):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            if key in ("time", "platform_label", "direction", "status"):
                return int(Qt.AlignCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if self._show_checkbox and index.isValid() and index.column() == 0 and role == Qt.CheckStateRole:
            t = self._rows[index.row()]
            if value == Qt.Checked:
                self._checked.add(id(t))
            else:
                self._checked.discard(id(t))
            self.dataChanged.emit(index, index)
            self.checkedChanged.emit()
            return True
        return False

    def toggle_checked_row(self, row: int) -> None:
        """点击复选框列时切换该行的勾选状态。"""
        if self._show_checkbox and 0 <= row < len(self._rows):
            t = self._rows[row]
            newval = Qt.Unchecked if id(t) in self._checked else Qt.Checked
            self.setData(self.index(row, 0), newval, Qt.CheckStateRole)

    # ---- 选中 ----
    def checked_txns(self) -> List[Transaction]:
        return [t for t in self._rows if id(t) in self._checked]

    def clear_checked(self) -> None:
        self._checked.clear()
        if self._rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._rows) - 1, 0))
        self.checkedChanged.emit()

    def txns(self) -> List[Transaction]:
        return self._rows

    def rows_at(self, indexes) -> List[Transaction]:
        seen = {}
        for idx in indexes:
            t = self._rows[idx.row()]
            seen[id(t)] = t
        return list(seen.values())


class AdvancedSearchDialog(QDialog):
    """高级查找：正则 / 字段 / 金额范围 / 平台。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级查找")
        self.setMinimumWidth(440)
        self._clear = False
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        f1 = QFormLayout()
        self.field_combo = QComboBox()
        for label, val in _SEARCH_FIELDS:
            self.field_combo.addItem(label, val)
        self.regex_edit = QLineEdit()
        self.regex_edit.setPlaceholderText("例如 \\b外卖\\b（支持完整正则）")
        f1.addRow("匹配字段", self.field_combo)
        f1.addRow("正则表达式", self.regex_edit)
        lay.addLayout(f1)

        self.amount_check = QCheckBox("启用金额范围筛选")
        lay.addWidget(self.amount_check)
        ar = QHBoxLayout()
        self.amount_min = QDoubleSpinBox()
        self.amount_min.setRange(0, 1e12)
        self.amount_min.setDecimals(2)
        self.amount_min.setValue(0)
        self.amount_max = QDoubleSpinBox()
        self.amount_max.setRange(0, 1e12)
        self.amount_max.setDecimals(2)
        self.amount_max.setValue(1000000)
        ar.addWidget(QLabel("金额区间"))
        ar.addWidget(self.amount_min)
        ar.addWidget(QLabel("~"))
        ar.addWidget(self.amount_max)
        ar.addStretch(1)
        lay.addLayout(ar)

        pf_row = QHBoxLayout()
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("全部平台", "")
        self.platform_combo.addItem("微信", PLATFORM_WECHAT)
        self.platform_combo.addItem("支付宝", PLATFORM_ALIPAY)
        pf_row.addWidget(QLabel("平台"))
        pf_row.addWidget(self.platform_combo)
        pf_row.addStretch(1)
        lay.addLayout(pf_row)

        btns = QHBoxLayout()
        self.btn_apply = QPushButton("应用筛选")
        self.btn_apply.setObjectName("primary")
        self.btn_clear = QPushButton("清除高级筛选")
        self.btn_cancel = QPushButton("取消")
        self.btn_apply.clicked.connect(self._accept)
        self.btn_clear.clicked.connect(self._do_clear)
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_clear)
        btns.addWidget(self.btn_cancel)
        lay.addLayout(btns)

    def _accept(self) -> None:
        if self.amount_check.isChecked() and self.amount_min.value() > self.amount_max.value():
            QMessageBox.warning(self, "金额范围", "最低金额不能高于最高金额")
            return
        pattern = self.regex_edit.text().strip()
        if pattern:
            try:
                re.compile(pattern)
            except re.error as e:  # noqa: PERF203
                QMessageBox.warning(self, "正则错误", f"正则表达式无效：{e}")
                return
        self._clear = False
        self.accept()

    def _do_clear(self) -> None:
        self._clear = True
        self.accept()

    def clear_requested(self) -> bool:
        return self._clear

    def result_filter(self) -> dict:
        res: dict = {"platform": self.platform_combo.currentData()}
        res["regex"] = self.regex_edit.text().strip()
        res["regex_field"] = self.field_combo.currentData()
        if self.amount_check.isChecked():
            res["amount_min"] = self.amount_min.value()
            res["amount_max"] = self.amount_max.value()
        else:
            res["amount_min"] = None
            res["amount_max"] = None
        return res


class TablePage(QWidget):
    """账单明细页。"""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main = None
        self.model = TransactionModel(show_checkbox=True)
        self._date_start: Optional[datetime] = None
        self._date_end: Optional[datetime] = None
        self._regex: str = ""
        self._regex_field: str = ""
        self._amount_min: Optional[float] = None
        self._amount_max: Optional[float] = None
        self._platform: str = ""
        self._build_ui()

    def set_main(self, main) -> None:
        self.main = main

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        title = QLabel("账单明细")
        title.setObjectName("cardTitle")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # 筛选栏
        filter_bar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索商家 / 商品 / 类型…")
        self.search_edit.setClearButtonEnabled(True)

        self.category_combo = QComboBox()
        self.category_combo.addItem("全部分类", "")
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("全部方向", "")
        self.direction_combo.addItems(["支出", "收入", "不计收支"])

        self.time_btn = QPushButton(icon("calendar"), "全部时间")
        self.time_btn.clicked.connect(self._show_time_menu)
        self.btn_advanced = QPushButton("高级查找")
        self.btn_advanced.clicked.connect(self._advanced_search)

        self.search_edit.textChanged.connect(self._apply_filter)
        self.category_combo.currentIndexChanged.connect(self._apply_filter)
        self.direction_combo.currentIndexChanged.connect(self._apply_filter)

        self.btn_batch = QPushButton("批量归类选中")
        self.btn_batch.setObjectName("primary")
        self.btn_batch.clicked.connect(self._batch_categorize)

        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self._delete_checked)

        filter_bar.addWidget(self.category_combo)
        filter_bar.addWidget(self.direction_combo)
        filter_bar.addWidget(self.time_btn)
        filter_bar.addWidget(self.btn_advanced)
        filter_bar.addWidget(self.search_edit, 1)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.btn_batch)
        actions.addWidget(self.btn_delete)
        layout.addLayout(filter_bar)
        layout.addLayout(actions)

        # 表格
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.clicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table, 1)

        # 底部信息栏：记录数 + 选中净额 + 自动列宽
        info_bar = QHBoxLayout()
        self.count_label = QLabel("")
        self.count_label.setObjectName("hint")
        self.selected_label = QLabel("")
        self.selected_label.setObjectName("hint")
        self.selected_label.setStyleSheet(f"color:{COLOR_ACCENT};")
        info_bar.addWidget(self.count_label)
        info_bar.addWidget(self.selected_label)
        info_bar.addStretch(1)
        info_bar.addWidget(autosize_button(self.table, profile="transactions"))
        layout.addLayout(info_bar)

        self.model.checkedChanged.connect(self._update_count)
        self._update_count()

    # ---- 刷新 ----
    def refresh(self, all_txns: List[Transaction]) -> None:
        self._reload_categories()
        self.model.set_data(all_txns)
        self._update_count()

    def _reload_categories(self) -> None:
        cats = []
        if self.main is not None and self.main.engine is not None:
            cats = list(self.main.engine.categories)
        cur_cat = self.category_combo.currentData()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("全部分类", "")
        for c in cats:
            self.category_combo.addItem(c, c)
        self.category_combo.addItem(UNCATEGORIZED, UNCATEGORIZED)
        idx = self.category_combo.findData(cur_cat)
        self.category_combo.setCurrentIndex(max(idx, 0))
        self.category_combo.blockSignals(False)

    # ---- 筛选 ----
    def _current_direction(self) -> str:
        return self.direction_combo.currentText() if self.direction_combo.currentIndex() != 0 else ""

    def _apply_filter(self) -> None:
        self.model.set_filters(
            search=self.search_edit.text(),
            category=self.category_combo.currentData(),
            direction=self._current_direction(),
            date_start=self._date_start,
            date_end=self._date_end,
            regex=self._regex,
            regex_field=self._regex_field,
            amount_min=self._amount_min,
            amount_max=self._amount_max,
            platform=self._platform,
        )
        self._update_count()

    def _update_count(self) -> None:
        shown = self.model.rowCount()
        total = len(self.model._all) if self.model else 0
        self.count_label.setText(f"显示 {shown} / 共 {total} 条记录")
        self.selected_label.setText(self._selected_summary())

    def _selected_summary(self) -> str:
        checked = self.model.checked_txns()
        if not checked:
            return ""
        income = sum(t.net_amount for t in checked if t.is_income)
        expense = sum(t.net_amount for t in checked if t.is_expense)
        net = income - expense
        s = f"选中 {len(checked)} 笔"
        if net < 0:
            s += f" · 支出 ¥{-net:.2f}"
        elif net > 0:
            s += f" · 收入 ¥{net:.2f}"
        else:
            s += f" · ¥0.00"
        return s

    def _on_cell_clicked(self, index) -> None:
        """单击复选框列即切换勾选（支持多选）。"""
        if index.isValid() and index.column() == 0:
            self.model.toggle_checked_row(index.row())

    # ---- 全部时间快捷筛选 ----
    def _show_time_menu(self) -> None:
        self.main.choose_period()

    def set_period(self, period, label):
        from datetime import time
        self._date_start = datetime.combine(period[0], time.min) if period else None
        self._date_end = datetime.combine(period[1], time.max) if period else None
        self.time_btn.setText(label)
        self._apply_filter()

    # ---- 高级查找 ----
    def _advanced_search(self) -> None:
        dlg = AdvancedSearchDialog(self)
        dlg.regex_edit.setText(self._regex)
        dlg.field_combo.setCurrentIndex(max(0, dlg.field_combo.findData(self._regex_field)))
        dlg.platform_combo.setCurrentIndex(max(0, dlg.platform_combo.findData(self._platform)))
        if self._amount_min is not None:
            dlg.amount_check.setChecked(True)
            dlg.amount_min.setValue(self._amount_min)
            dlg.amount_max.setValue(self._amount_max)
        if dlg.exec() != QDialog.Accepted:
            return
        if dlg.clear_requested():
            self._regex = ""
            self._regex_field = ""
            self._amount_min = None
            self._amount_max = None
            self._platform = ""
            self._apply_filter()
            return
        f = dlg.result_filter()
        self._regex = f["regex"]
        self._regex_field = f["regex_field"]
        self._amount_min = f["amount_min"]
        self._amount_max = f["amount_max"]
        self._platform = f["platform"]
        self._apply_filter()

    # ---- 供外部（统计分析页）跳转设置筛选 ----
    def set_external_direction(self, direction: str) -> None:
        idx = self.direction_combo.findText(direction)
        if idx >= 0:
            self.direction_combo.setCurrentIndex(idx)
        self._apply_filter()

    def set_external_category(self, category: str) -> None:
        self._reload_categories()
        idx = self.category_combo.findData(category)
        if idx < 0:
            idx = self.category_combo.findText(category)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        self._apply_filter()

    def clear_filters(self) -> None:
        self.search_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.direction_combo.setCurrentIndex(0)
        self._regex = ""
        self._regex_field = ""
        self._amount_min = None
        self._amount_max = None
        self._platform = ""
        self._apply_filter()

    # ---- 上下文菜单 ----
    def _selected(self) -> List[Transaction]:
        indexes = self.table.selectionModel().selectedRows()
        return self.model.rows_at(indexes)

    def _show_context_menu(self, pos) -> None:
        selected = self._selected()
        if not selected:
            return
        menu = QMenu(self)
        if len(selected) == 1 and selected[0].platform == "wechat" and selected[0].is_refund_record:
            refund = selected[0]
            if refund.refund_note in ("退款待匹配", "退款金额待核对"):
                menu.addAction("选择退款对应的支付", lambda: self._choose_payment(refund))
            if refund.manual_payment_key:
                menu.addAction("撤销人工匹配", lambda: self._link_payment(refund, ""))
        cat_menu = menu.addMenu("设为分类")
        cats = []
        if self.main is not None:
            cats = [c for c in self.main.engine.categories] + [UNCATEGORIZED]
        for c in cats:
            act = cat_menu.addAction(c)
            act.triggered.connect(lambda _=False, c=c: self._assign_category(c, None))
        cat_menu.addAction("恢复自动分类").triggered.connect(lambda: self._assign_category(None))
        if selected:
            one = selected[0]
            menu.addSeparator()
            act_rule = menu.addAction(f"将“{one.counterparty}”存为新规则")
            act_rule.triggered.connect(lambda: self._save_as_rule(selected))
        menu.exec(QCursor.pos())

    def _choose_payment(self, refund):
        from PySide6.QtWidgets import QInputDialog
        from ..refunds import manual_candidates
        from ..models import unique_key
        payments = manual_candidates(self.main.transactions, refund)
        if not payments:
            QMessageBox.information(self, "退款匹配", "没有可用候选，请核对金额或导入更早的账单。")
            return
        labels = [f"{i}. {p.time:%Y-%m-%d %H:%M}  ¥{p.amount:.2f}  {p.counterparty}  {p.goods}  {p.txn_id}"
                  for i, p in enumerate(payments, 1)]
        choice, ok = QInputDialog.getItem(self, "匹配退款", "选择原支付（最近在前）", labels, 0, False)
        if ok:
            self._link_payment(refund, unique_key(payments[labels.index(choice)]))

    def _link_payment(self, refund, key):
        from ..refunds import reconcile
        refund.manual_payment_key = key
        reconcile(self.main.transactions)
        self.main.reclassify()

    def _assign_category(self, category: str, targets: Optional[List[Transaction]] = None) -> None:
        selected = targets if targets is not None else self._selected()
        if not selected:
            return
        for t in selected:
            if t.direction == "支出":
                t.manual_category = None if category is None else ("" if category == UNCATEGORIZED else category)
                self.main.engine.classify_one(t)
        self.model.dataChanged.emit(QModelIndex(), QModelIndex())
        self.model.apply_filter()
        self._update_count()
        self.changed.emit()

    def _batch_categorize(self) -> None:
        checked = self.model.checked_txns()
        if not checked:
            QMessageBox.information(self, "提示", "请先在表格中勾选要归类的记录行。")
            return
        cats = []
        if self.main is not None:
            cats = self.main.engine.categories + [UNCATEGORIZED]
        menu = QMenu(self)
        for c in cats:
            act = menu.addAction(c)
            act.triggered.connect(lambda _=False, c=c: self._assign_checked_category(c))
        menu.exec(QCursor.pos())

    def _assign_checked_category(self, category: str) -> None:
        checked = self.model.checked_txns()
        if not checked:
            return
        for t in checked:
            if t.direction == "支出":
                t.manual_category = None if category is None else ("" if category == UNCATEGORIZED else category)
                self.main.engine.classify_one(t)
        self.model.dataChanged.emit(QModelIndex(), QModelIndex())
        self.model.clear_checked()
        self.model.apply_filter()
        self._update_count()
        self.changed.emit()

    def _delete_checked(self) -> None:
        """删除勾选的消费记录（需二次确认）。"""
        checked = self.model.checked_txns()
        if not checked:
            QMessageBox.information(self, "提示", "请先勾选要删除的消费记录。")
            return
        ret = QMessageBox.question(
            self, "确认删除",
            f"确定删除选中的 {len(checked)} 笔记录吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        if self.main is not None:
            self.main.delete_transactions({id(t) for t in checked})

    def _save_as_rule(self, selected: List[Transaction]) -> None:
        if self.main is None:
            return
        names = sorted({t.counterparty for t in selected if t.counterparty})
        if not names:
            return
        keyword = names[0]
        default_cat = selected[0].category if selected[0].category else (
            self.main.engine.categories[0] if self.main.engine.categories else "其他"
        )
        self.main.add_rule_from_merchant(keyword, default_cat)