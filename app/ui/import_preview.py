"""在独立的流水和规则副本上检查本次导入。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QSplitter, QTableView, QVBoxLayout, QWidget,
)

from ..models import unique_key
from ..rules.engine import RuleEngine
from ..transfers import apply_transfers
from .rules_page import RulesPage
from .table_page import TransactionModel
from .widgets import FittedColumns


class ImportPreview(QDialog):
    def __init__(self, rows, keys, config, messages, parent=None):
        super().__init__(parent)
        self.setWindowTitle("核对账单与分类")
        self.resize(1160, 850)
        self.config_path = None
        self.all_rows = rows
        self.transactions = [row for row in rows if unique_key(row) in keys]
        self.engine = RuleEngine(config)

        layout = QVBoxLayout(self)
        summary = QLabel("\n".join(messages))
        summary.setWordWrap(True)
        layout.addWidget(summary)
        split = QSplitter(Qt.Vertical)
        layout.addWidget(split, 1)
        top = QWidget()
        detail = QVBoxLayout(top)
        detail.addWidget(QLabel("本次账单与预计分类"))
        table = QTableView()
        self.model = TransactionModel()
        table.setModel(self.model)
        table.setSortingEnabled(True)
        table.verticalHeader().hide()
        FittedColumns(table, profile="importPreview")
        detail.addWidget(table)
        split.addWidget(top)

        self.rules = RulesPage()
        self.rules.set_main(self)
        self.rules.uncat_box.hide()
        for widget in (self.rules.btn_save, self.rules.btn_save_as, self.rules.file_label):
            widget.hide()
        split.addWidget(self.rules)
        split.setSizes([360, 400])
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.addButton("确定导入", QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.reclassify()
        self.rules.refresh()

    def reclassify(self):
        self.engine = RuleEngine(self.engine.sync_config())
        apply_transfers(self.all_rows, self.engine.config.get("own_cards", []))
        self.engine.classify_all(self.all_rows)
        self.model.set_data(self.transactions)
        return True

    def load_config(self, config, path):
        config.setdefault("own_cards", self.engine.config.get("own_cards", []))
        self.engine = RuleEngine(config)

    def persist(self):
        return self.reclassify()
