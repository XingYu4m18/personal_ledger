"""规则管理页：分类管理、规则列表、编辑、导入导出、命中测试。"""

from __future__ import annotations

from .icons import icon

from typing import List

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QDialogButtonBox,
    QLineEdit, QComboBox, QCheckBox, QFormLayout, QFileDialog,
    QMessageBox, QInputDialog, QListWidget, QListWidgetItem, QGroupBox,
    QAbstractItemView, QHeaderView, QMenu, QSplitter, QTableView,
    QGraphicsOpacityEffect,
)

from ..models import Transaction
from ..rules import MATCH_FIELDS, MATCH_MODES, load_config, save_config
from ..rules.engine import RuleEngine
from .table_page import TransactionModel
from .theme import COLOR_ACCENT
from .widgets import FittedColumns, autosize_button


class RuleEditDialog(QDialog):
    def __init__(self, categories: List[str], rule: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑规则" if rule else "新增规则")
        self.setMinimumWidth(420)
        self.categories = categories
        self.rule = dict(rule) if rule else {
            "name": "", "enabled": True, "priority": 100,
            "match_field": "counterparty", "match_mode": "contains",
            "keyword": "", "category": categories[0] if categories else "其他",
        }
        self._build()

    def _build(self) -> None:
        form = QFormLayout(self)
        form.setSpacing(12)

        self.name_edit = QLineEdit(self.rule["name"])
        self.name_edit.setPlaceholderText("例如：食堂吃饭、游戏充值")

        self.field_combo = QComboBox()
        for value, label in MATCH_FIELDS:
            self.field_combo.addItem(label, value)
        idx = self.field_combo.findData(self.rule["match_field"])
        self.field_combo.setCurrentIndex(max(idx, 0))

        self.mode_combo = QComboBox()
        for value, label in MATCH_MODES:
            self.mode_combo.addItem(label, value)
        idx = self.mode_combo.findData(self.rule["match_mode"])
        self.mode_combo.setCurrentIndex(max(idx, 0))

        self.keyword_edit = QLineEdit(self.rule["keyword"])
        self.keyword_edit.setPlaceholderText("商家关键字或正则表达式")

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        for c in self.categories:
            self.category_combo.addItem(c)
        self.category_combo.setCurrentText(self.rule["category"])

        self.enabled_check = QCheckBox("启用此规则")
        self.enabled_check.setChecked(self.rule["enabled"])

        form.addRow("规则名称", self.name_edit)
        form.addRow("匹配字段", self.field_combo)
        form.addRow("匹配方式", self.mode_combo)
        form.addRow("关键字/正则", self.keyword_edit)
        form.addRow("目标分类", self.category_combo)
        form.addRow("", self.enabled_check)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写规则名称。")
            return
        if not self.keyword_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写关键字或正则。")
            return
        self.rule = {
            "name": self.name_edit.text().strip(),
            "enabled": self.enabled_check.isChecked(),
            "priority": self.rule.get("priority", 100),
            "match_field": self.field_combo.currentData(),
            "match_mode": self.mode_combo.currentData(),
            "keyword": self.keyword_edit.text().strip(),
            "category": self.category_combo.currentText().strip(),
        }
        self.accept()

    def result_rule(self) -> dict:
        return self.rule


class MatchViewDialog(QDialog):
    """展示某条规则实际命中并归类的消费记录明细（字段与账单明细一致，支持点列头排序）。"""

    def __init__(self, rule: dict, matched: List[Transaction], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"命中记录：{rule['name']}")
        self.resize(1000, 560)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        mode_label = dict(MATCH_MODES).get(rule["match_mode"], rule["match_mode"])
        info = QLabel(
            f"规则「{rule['name']}」：{mode_label} “{rule['keyword']}” → {rule['category']}　"
            f"共命中 {len(matched)} 条支出"
        )
        info.setWordWrap(True)
        lay.addWidget(info)

        self.model = TransactionModel()
        self.model.set_data(matched)

        table = QTableView()
        table.setModel(self.model)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSortingEnabled(True)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(table, 1)

        tool_row = QHBoxLayout()
        tool_row.addStretch(1)
        tool_row.addWidget(autosize_button(table, profile="matches"))
        lay.addLayout(tool_row)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        btns.clicked.connect(self.reject)
        lay.addWidget(btns)


class RulesPage(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main = None
        self._build_ui()

    def set_main(self, main) -> None:
        self.main = main

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        head = QHBoxLayout()
        title = QLabel("规则管理")
        title.setObjectName("pageTitle")
        head.addWidget(title)
        head.addStretch()
        self.test_toggle = QPushButton("测试规则")
        self.test_toggle.setCheckable(True)
        head.addWidget(self.test_toggle)
        self.more = QPushButton("更多")
        self.more.setToolTip("对选中的规则执行操作")
        head.addWidget(self.more)
        add = QPushButton(icon("plus", "#ffffff"), "新增规则")
        add.setObjectName("primary")
        add.clicked.connect(lambda: self._add_rule())
        head.addWidget(add)
        layout.addLayout(head)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["启用", "顺序", "名称", "关键字/正则", "匹配字段", "匹配方式", "分类"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setToolTip("双击规则可编辑；勾选首列可启用")
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 50)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(3, 240)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 110)
        FittedColumns(self.table)
        initial_height = self.table.horizontalHeader().sizeHint().height() + 6 * self.table.verticalHeader().defaultSectionSize()
        self.table.setMinimumHeight(86)
        self.table.cellDoubleClicked.connect(lambda row, col: self._edit_rule(row) if col else None)
        self.table.itemChanged.connect(self._on_item_changed)
        menu = QMenu(self.more)
        menu.addAction("查看命中", lambda: self._show_matches(self.table.currentRow()))
        menu.addSeparator()
        up = menu.addAction("上移", lambda: self._move_rule(-1))
        down = menu.addAction("下移", lambda: self._move_rule(1))
        menu.addSeparator()
        menu.addAction("删除规则", self._delete_rule)
        menu.aboutToShow.connect(lambda: up.setEnabled(self.table.currentRow() > 0))
        menu.aboutToShow.connect(lambda: down.setEnabled(self.table.currentRow() < self.table.rowCount() - 1))
        self.more.setMenu(menu)
        self.more.setEnabled(False)
        self.table.itemSelectionChanged.connect(lambda: self.more.setEnabled(bool(self.table.selectedItems())))
        split = QSplitter(Qt.Vertical)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)
        split.addWidget(self.table)
        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        split.addWidget(lower)
        layout.addWidget(split, 1)

        test_box = QWidget()
        test_layout = QHBoxLayout(test_box)
        test_layout.setContentsMargins(0, 0, 0, 0)
        self.test_edit = QLineEdit()
        self.test_edit.setPlaceholderText("输入一段商家或商品文字…")
        self.test_btn = QPushButton("测试")
        self.test_btn.clicked.connect(self._test)
        self.test_result = QLabel("")
        self.test_result.setObjectName("hint")
        test_layout.addWidget(self.test_edit, 1)
        test_layout.addWidget(self.test_btn)
        test_layout.addWidget(self.test_result, 2)

        lower_layout.addWidget(test_box)
        test_box.hide()
        self.test_toggle.toggled.connect(test_box.setVisible)
        self.test_toggle.toggled.connect(lambda opened: self.test_edit.setFocus() if opened else None)
        self.test_edit.returnPressed.connect(self._test)

        categories = QHBoxLayout()
        categories.addWidget(QLabel("消费分类"))
        self.cat_list = QComboBox()
        categories.addWidget(self.cat_list)
        for label, slot in [("新增分类", self._add_category), ("删除分类", self._remove_category)]:
            button = QPushButton(label)
            button.clicked.connect(slot)
            categories.addWidget(button)
        categories.addStretch()
        cards_button = QPushButton("我的银行卡")
        cards_button.clicked.connect(self._cards)
        categories.addWidget(cards_button)
        lower_layout.addLayout(categories)

        # 未分类支出：便于对照未命中规则的记录
        self.uncat_box = QGroupBox("未分类支出")
        uncat_layout = QVBoxLayout(self.uncat_box)
        uncat_head = QHBoxLayout()
        uncat_hint = QLabel("以下支出未命中任何规则，可据此新增或调整规则。")
        uncat_hint.setObjectName("hint")
        self.uncat_model = TransactionModel()
        self.uncat_table = QTableView()
        self.uncat_table.setModel(self.uncat_model)
        self.uncat_table.setAlternatingRowColors(True)
        self.uncat_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.uncat_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.uncat_table.setSortingEnabled(True)
        self.uncat_table.setWordWrap(False)
        self.uncat_table.verticalHeader().setVisible(False)
        self.uncat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.uncat_table.horizontalHeader().setStretchLastSection(True)
        uncat_head.addWidget(uncat_hint, 1)
        uncat_head.addWidget(autosize_button(self.uncat_table, profile="uncategorized"))
        uncat_layout.addLayout(uncat_head)
        uncat_layout.addWidget(self.uncat_table, 1)

        lower_layout.addWidget(self.uncat_box, 1)
        split.setSizes([initial_height, 380])
        from PySide6.QtCore import QSettings
        from ..database import default_path
        settings = QSettings(str(default_path().with_name("table-layout.ini")), QSettings.IniFormat)
        state = settings.value("rules/verticalSplit")
        if state:
            split.restoreState(state)
        split.splitterMoved.connect(lambda *_: settings.setValue("rules/verticalSplit", split.saveState()))

        # 规则文件操作
        file_row = QHBoxLayout()
        self.btn_save = QPushButton("保存规则")
        self.btn_save_as = QPushButton("规则另存为…")
        self.btn_load = QPushButton("导入规则…")
        self.btn_default = QPushButton("恢复默认规则")
        self.btn_save.clicked.connect(self._save)
        self.btn_save_as.clicked.connect(self._save_as)
        self.btn_load.clicked.connect(self._load)
        self.btn_default.clicked.connect(self._reset_default)
        file_row.addWidget(self.btn_save)
        file_row.addWidget(self.btn_save_as)
        file_row.addWidget(self.btn_load)
        file_row.addWidget(self.btn_default)
        file_row.addStretch(1)
        self.file_label = QLabel("")
        self.file_label.setObjectName("hint")
        file_row.addWidget(self.file_label)
        layout.addLayout(file_row)

    # ---- 刷新 ----
    def refresh(self) -> None:
        self._reload_category_list()
        self._reload_table()
        self._reload_uncategorized()

    def highlight_uncategorized(self) -> None:
        """将“未分类支出”模块短暂高亮并渐淡直至消失。"""
        overlay = QFrame(self.uncat_box)
        overlay.setObjectName("highlightOverlay")
        overlay.setStyleSheet("#highlightOverlay { background-color: %s; border-radius: 6px; }" % COLOR_ACCENT)
        overlay.setGeometry(self.uncat_box.rect())
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(effect)
        overlay.show()
        overlay.raise_()
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(1300)
        anim.setStartValue(0.45)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutQuad)
        anim.finished.connect(overlay.deleteLater)
        anim.start()

    def _reload_category_list(self) -> None:
        self.cat_list.clear()
        if self.main is None:
            return
        for c in self.main.engine.categories:
            self.cat_list.addItem(c)

    def _reload_uncategorized(self) -> None:
        if self.main is None:
            self.uncat_model.set_data([])
            return
        uncat = [t for t in self.main.transactions if t.is_expense and not t.category]
        self.uncat_model.set_data(uncat)

    def _reload_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        if self.main is not None:
            rules = self.main.engine.rules
            self.table.setRowCount(len(rules))
            for i, r in enumerate(rules):
                cb_item = QTableWidgetItem()
                cb_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                cb_item.setCheckState(Qt.Checked if r["enabled"] else Qt.Unchecked)
                self.table.setItem(i, 0, cb_item)

                field_label = dict(MATCH_FIELDS).get(r["match_field"], r["match_field"])
                mode_label = dict(MATCH_MODES).get(r["match_mode"], r["match_mode"])

                self.table.setItem(i, 1, QTableWidgetItem(str(i + 1)))
                self.table.setItem(i, 2, QTableWidgetItem(r["name"]))
                self.table.setItem(i, 3, QTableWidgetItem(r["keyword"]))
                self.table.setItem(i, 4, QTableWidgetItem(field_label))
                self.table.setItem(i, 5, QTableWidgetItem(mode_label))
                self.table.setItem(i, 6, QTableWidgetItem(r["category"]))

        self.table.blockSignals(False)
        self.more.setEnabled(bool(self.table.selectedItems()))
        self._update_file_label()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """规则表内勾选“启用”时，立即重新分析并刷新统计。"""
        if item.column() == 0:
            self._sync_checkboxes()

    def _show_matches(self, row: int) -> None:
        if self.main is None or row < 0 or row >= len(self.main.engine.rules):
            return
        rule = self.main.engine.rules[row]
        matched = [t for t in self.main.transactions if self.main.engine.applied_rule_index(t) == row]
        dlg = MatchViewDialog(rule, matched, self)
        dlg.exec()

    def _update_file_label(self) -> None:
        if self.main and self.main.config_path:
            self.file_label.setText(f"规则文件：{self.main.config_path}")
        else:
            self.file_label.setText("规则文件：未保存（使用内置默认）")

    # ---- 规则操作 ----
    def _sync_checkboxes(self) -> None:
        """把启用勾选状态写回 engine。"""
        if self.main is None:
            return
        for i, r in enumerate(self.main.engine.rules):
            item = self.table.item(i, 0)
            if item:
                r["enabled"] = item.checkState() == Qt.Checked
        self._renumber()
        self._reclassify()

    def _renumber(self) -> None:
        if self.main is None:
            return
        n = len(self.main.engine.rules)
        for i, r in enumerate(self.main.engine.rules):
            r["priority"] = (n - i) * 10

    def _add_rule(self, rule: dict | None = None) -> None:
        if self.main is None:
            return
        cats = self.main.engine.categories
        if rule is None:
            dlg = RuleEditDialog(cats, None, self)
            if dlg.exec() != QDialog.Accepted:
                return
            rule = dlg.result_rule()
        if rule["category"] not in self.main.engine.categories:
            self.main.engine.categories.append(rule["category"])
        self.main.engine.rules.append(rule)
        self._renumber()
        self._reload_table()
        self._reclassify()

    def _edit_rule(self, row: int) -> None:
        if self.main is None or row < 0 or row >= len(self.main.engine.rules):
            return
        r = self.main.engine.rules[row]
        dlg = RuleEditDialog(self.main.engine.categories, r, self)
        if dlg.exec() != QDialog.Accepted:
            return
        new_rule = dlg.result_rule()
        if new_rule["category"] not in self.main.engine.categories:
            self.main.engine.categories.append(new_rule["category"])
        self.main.engine.rules[row] = new_rule
        self._reload_table()
        self._reclassify()

    def _delete_rule(self) -> None:
        if self.main is None:
            return
        row = self.table.currentRow()
        if row < 0:
            return
        self.main.engine.rules.pop(row)
        self._renumber()
        self._reload_table()
        self._reclassify()

    def _move_rule(self, direction: int) -> None:
        if self.main is None:
            return
        row = self.table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= len(self.main.engine.rules):
            return
        rules = self.main.engine.rules
        rules[row], rules[target] = rules[target], rules[row]
        self._renumber()
        self._reload_table()
        self.table.setCurrentCell(target, 0)
        self._reclassify()

    def _reclassify(self) -> bool:
        if self.main is None:
            return
        self.main.engine.sync_config()
        if not self.main.reclassify():
            return False
        self._reload_uncategorized()
        self.changed.emit()
        return True

    def _cards(self):
        from ..transfers import normalize
        dialog = QDialog(self)
        dialog.setWindowTitle("我的银行卡")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("本人卡与微信、支付宝之间的充值和提现不计收支。"))
        cards = list(self.main.engine.config.get("own_cards", []))
        listing = QListWidget()
        layout.addWidget(listing)
        for bank, tail in cards:
            listing.addItem(f"{bank}（{tail}）")
        inputs = QHBoxLayout()
        name = QLineEdit()
        name.setPlaceholderText("银行名称，例如工行")
        digits = QLineEdit()
        digits.setPlaceholderText("请输入银行卡尾号四位")
        digits.setMaxLength(4)
        add = QPushButton("添加")
        remove = QPushButton("移除选中")
        for widget in (name, digits, add, remove):
            inputs.addWidget(widget)
        layout.addLayout(inputs)

        def append():
            bank, tail = normalize(name.text().strip()), digits.text().strip()
            if not bank or len(tail) != 4 or not tail.isascii() or not tail.isdigit():
                QMessageBox.information(dialog, "银行卡", "请输入银行名称和四位数字尾号。")
                return False
            if [bank, tail] not in cards:
                cards.append([bank, tail])
                listing.addItem(f"{bank}（{tail}）")
            name.clear()
            digits.clear()
            return True

        def delete():
            row = listing.currentRow()
            if row >= 0:
                cards.pop(row)
                listing.takeItem(row)

        add.clicked.connect(append)
        remove.clicked.connect(delete)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: dialog.accept() if not (name.text() or digits.text()) or append() else None)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            self.main.engine.config["own_cards"] = cards
            self._reclassify()

    # ---- 分类操作 ----
    def _add_category(self) -> None:
        if self.main is None:
            return
        name, ok = QInputDialog.getText(self, "新增分类", "分类名称：")
        if ok and name.strip():
            self.main.engine.add_category(name.strip())
            self._reload_category_list()
            self._reload_table()
            self.main.persist()

    def _remove_category(self) -> None:
        if self.main is None:
            return
        cat = self.cat_list.currentText()
        if not cat:
            return
        used = any(r["category"] == cat for r in self.main.engine.rules)
        if used:
            QMessageBox.warning(self, "无法删除", f"分类“{cat}”正被规则使用，请先移除相关规则。")
            return
        if cat in self.main.engine.categories:
            self.main.engine.categories.remove(cat)
        self._reload_category_list()
        self._reload_table()
        self.main.persist()

    # ---- 测试 ----
    def _test(self) -> None:
        text = self.test_edit.text().strip()
        if not text:
            self.test_result.setText("请输入测试文字")
            return
        if self.main is None:
            return
        engine: RuleEngine = self.main.engine
        for r in engine._compiled:
            if not r["enabled"]:
                continue
            if RuleEngine.test_rule(r, text):
                self.test_result.setText(f"✅ 命中规则「{r['name']}」→ {r['category']}")
                return
        self.test_result.setText("❌ 未命中任何规则（将归为未分类）")

    # ---- 文件操作 ----
    def _save(self) -> None:
        if self.main is None:
            return
        if not self.main.config_path:
            self._save_as()
            return
        self._sync_checkboxes()
        data = self.main.engine.sync_config()
        save_config(data, self.main.config_path)
        self._update_file_label()

    def _save_as(self) -> None:
        if self.main is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "规则另存为", "rules.json", "JSON 文件 (*.json)")
        if not path:
            return
        self._sync_checkboxes()
        data = self.main.engine.sync_config()
        save_config(data, path)
        self._update_file_label()

    def _load(self) -> None:
        if self.main is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "导入规则", "", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            data = load_config(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导入失败", f"规则文件解析失败：{e}")
            return
        self.main.load_config(data, path)
        self.refresh()
        if not self._reclassify():
            return
        QMessageBox.information(self, "导入成功", "规则已导入并重新分类。")

    def _reset_default(self) -> None:
        if self.main is None:
            return
        r = QMessageBox.question(self, "确认", "将恢复为内置默认规则，当前规则会被覆盖。是否继续？")
        if r != QMessageBox.Yes:
            return
        from ..rules.schema import default_config
        self.main.load_config(default_config(), None)
        self.refresh()
        self._reclassify()