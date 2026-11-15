"""主窗口：侧边导航 + 页面栈 + 全局状态管理。"""

from __future__ import annotations

import os
from typing import List

from .icons import icon
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel,
    QListWidget, QListWidgetItem, QStackedWidget, QFileDialog, QMessageBox,
    QPushButton,
)

from ..transfers import apply_transfers
from ..models import Transaction
from ..database import LedgerDatabase, default_path
from ..ledger import import_bills, in_period
from .date_range import DateRangeDialog
from datetime import date
from PySide6.QtWidgets import QDialog
from ..storage import export_excel, export_csv, summary_stats
from ..rules import default_config, load_config, save_config
from ..rules.engine import RuleEngine

from .import_page import ImportPage
from .table_page import TablePage
from .rules_page import RulesPage
from .stats_page import StatsPage

NAV_ITEMS = [
    ("数据导入", 0),
    ("账单明细", 1),
    ("规则管理", 2),
    ("统计分析", 3),
]


class MainWindow(QMainWindow):
    def __init__(self, config_path: str | None = None, database_path=None):
        super().__init__()
        self.setWindowIcon(icon("ledger", size=40))
        self.setWindowTitle("月度账单分析")
        self.resize(1280, 820)

        self.period = None
        self.transactions: List[Transaction] = []
        self.config_path: str | None = config_path
        self.initial_config_path = config_path
        self.database = LedgerDatabase(database_path or default_path())
        self.local_rules = self.database.path.with_name("custom_rules.json")
        self._restore()
        self._write_local_rules()

        self._build_ui()
        self._connect_pages()
        self.refresh_all()

    def _restore(self):
        self.transactions, settings = self.database.load()
        if settings is None:
            self.config_path = str(self.local_rules) if self.local_rules.exists() else self.initial_config_path
            self._load_initial_config()
        else:
            self.load_config(*settings)
        self.config_path = str(self.local_rules)
        apply_transfers(self.transactions, self.config.get("own_cards", []))
        self.engine.classify_all(self.transactions)

    def _write_local_rules(self):
        save_config(self.engine.sync_config(), str(self.local_rules))

    def persist(self):
        try:
            self.database.save(self.transactions, self.engine.sync_config(), self.config_path)
        except Exception as error:
            self._restore()
            self.refresh_all()
            QMessageBox.warning(self, "账本未保存", str(error))
            return False
        try:
            self._write_local_rules()
        except OSError as error:
            QMessageBox.warning(self, "规则文件未同步", f"账本已保存。\n{error}")
        return True

    # ---- 配置 ----
    def _load_initial_config(self) -> None:
        if self.config_path and os.path.exists(self.config_path):
            try:
                self.config = load_config(self.config_path)
            except Exception:  # noqa: BLE001
                self.config = default_config()
        else:
            self.config = default_config()
        self.engine = RuleEngine(self.config)

    def load_config(self, data: dict, path: str | None) -> None:
        if hasattr(self, "config") and "own_cards" not in data:
            data["own_cards"] = self.config.get("own_cards", [])
        self.config = data
        self.config_path = str(self.local_rules)
        self.engine = RuleEngine(data)

    # ---- UI ----
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(186)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 28, 12, 20)
        side_layout.setSpacing(6)

        app_title = QLabel("个人账本")
        app_title.setObjectName("appTitle")
        app_title.setAlignment(Qt.AlignCenter)
        brand = QHBoxLayout()
        brand.setContentsMargins(10, 0, 0, 0)
        mark = QLabel()
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(32, 32)
        mark.setPixmap(icon("ledger", "#ffffff", 24).pixmap(QSize(22, 22), self.devicePixelRatioF()))
        brand.addWidget(mark)
        brand.addWidget(app_title)
        brand.addStretch()
        side_layout.addLayout(brand)
        side_layout.addSpacing(18)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(20, 20))
        for (text, _), symbol in zip(NAV_ITEMS, ("import", "ledger", "rules", "trend")):
            item = QListWidgetItem(icon(symbol), text)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._switch_page)
        side_layout.addWidget(self.nav, 1)

        self.btn_export = QPushButton(icon("export"), "导出分析结果")
        self.btn_export.clicked.connect(self._export)
        side_layout.addWidget(self.btn_export)

        version = QLabel("个人账本　·　本地运行")
        version.setObjectName("appSubtitle")
        version.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(version)
        outer.addWidget(sidebar)

        # 页面栈
        self.stack = QStackedWidget()
        self.import_page = ImportPage()
        self.table_page = TablePage()
        self.rules_page = RulesPage()
        self.stats_page = StatsPage()
        for p in (self.import_page, self.table_page, self.rules_page, self.stats_page):
            self.stack.addWidget(p)
        outer.addWidget(self.stack, 1)

        self.nav.setCurrentRow(0)

    def _connect_pages(self) -> None:
        for p in (self.import_page, self.table_page, self.rules_page, self.stats_page):
            p.set_main(self)
        self.table_page.changed.connect(self._on_data_changed)
        self.rules_page.changed.connect(self._refresh_pages)

    # ---- 导航 ----
    def _switch_page(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        if row == 1:
            self.table_page.refresh(self.transactions)
        elif row == 2:
            self.rules_page.refresh()
        elif row == 3:
            self.stats_page.refresh(self.transactions)
        elif row == 0:
            self.import_page.refresh_summary(summary_stats(self.transactions))

    # ---- 核心数据流 ----
    def import_files(self, paths: List[str]) -> dict | None:
        from copy import deepcopy
        from .import_preview import ImportPreview
        keys = set()
        rows, messages = import_bills(deepcopy(self.transactions), paths, batch_keys=keys)
        preview = ImportPreview(rows, keys, deepcopy(self.engine.sync_config()), messages, self)
        if preview.exec() != QDialog.Accepted:
            return None
        self.transactions = rows
        self.load_config(preview.engine.sync_config(), self.config_path)
        if not self.reclassify():
            return None
        self.nav.setCurrentRow(3)  # 跳到统计页查看结果
        return {"files": messages, **summary_stats(self.transactions)}

    def choose_period(self):
        anchor = max((t.time.date() for t in self.transactions if t.time), default=date.today())
        dialog = DateRangeDialog(self.period, anchor, self)
        if dialog.exec() == QDialog.Accepted:
            self.set_period(dialog.period)

    def set_period(self, period):
        self.period = period
        label = "全部时间" if not period else f"{period[0]} 至 {period[1]}"
        self.table_page.set_period(period, label)
        self.stats_page.refresh(self.transactions)

    def reclassify(self) -> bool:
        """重新加载规则引擎并对全部交易分类。"""
        self.engine = RuleEngine(self.engine.sync_config())
        apply_transfers(self.transactions, self.engine.config.get("own_cards", []))
        self.engine.classify_all(self.transactions)
        if not self.persist():
            return False
        self._refresh_pages()
        return True

    def delete_transactions(self, ids: set) -> None:
        """按对象 id 删除勾选的消费记录并刷新页面。"""
        self.transactions = [t for t in self.transactions if id(t) not in ids]
        from ..refunds import reconcile
        reconcile(self.transactions)
        if self.persist():
            self._refresh_pages()

    def add_rule_from_merchant(self, keyword: str, category: str) -> None:
        if any(r["keyword"] == keyword and r["category"] == category for r in self.engine.rules):
            QMessageBox.information(self, "提示", f"规则“{keyword} → {category}”已存在。")
            return
        self.engine.rules.append({
            "name": f"商家-{keyword}",
            "enabled": True,
            "priority": 0,
            "match_field": "counterparty",
            "match_mode": "contains",
            "keyword": keyword,
            "category": category,
        })
        self.reclassify()
        self.nav.setCurrentRow(2)
        self.rules_page.refresh()

    def _refresh_pages(self) -> None:
        self.table_page.refresh(self.transactions)
        self.stats_page.refresh(self.transactions)
        self.import_page.refresh_summary(summary_stats(self.transactions))

    def _on_data_changed(self) -> None:
        if self.persist():
            self._refresh_pages()

    def refresh_all(self) -> None:
        self._refresh_pages()
        self.rules_page.refresh()

    # ---- 导出 ----
    def _export(self) -> None:
        rows = in_period(self.transactions, self.period)
        if not rows:
            QMessageBox.information(self, "提示", "当前时间范围内没有可导出的数据。")
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "导出分析结果", "账单分析结果.xlsx",
            "Excel 工作簿 (*.xlsx);;CSV 文件 (*.csv)"
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                export_csv(rows, path)
            else:
                if not path.lower().endswith(".xlsx"):
                    path += ".xlsx"
                export_excel(rows, path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导出失败", str(e))
            return
        QMessageBox.information(self, "导出完成", f"已导出到：\n{path}")