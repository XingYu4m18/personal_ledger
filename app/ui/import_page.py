"""数据导入页：拖拽/选择文件，解析预览，导入并分类。"""

from __future__ import annotations

from .icons import icon

import os
from typing import List

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
)

from ..parser import detect_platform
from ..models import PLATFORM_WECHAT, PLATFORM_ALIPAY


class DropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropzone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(190)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.icon = QLabel()
        self.icon.setPixmap(icon("import", size=40).pixmap(QSize(40, 40), self.devicePixelRatioF()))
        self.icon.setObjectName("dropzoneIcon")
        self.icon.setAlignment(Qt.AlignCenter)
        self.text = QLabel("拖拽微信 Excel 或支付宝 CSV 文件到此处")
        self.text.setObjectName("dropzoneText")
        self.text.setAlignment(Qt.AlignCenter)
        self.sub = QLabel("支持 .xlsx / .xls / .csv，可一次拖入多个月份")
        self.sub.setObjectName("hint")
        self.sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon)
        layout.addWidget(self.text)
        layout.addWidget(self.sub)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragActive", "true")
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("dragActive", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event) -> None:
        self.setProperty("dragActive", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
        paths = [p for p in paths if p.lower().endswith((".xlsx", ".xls", ".csv"))]
        if paths:
            self.files_dropped.emit(paths)


class ImportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main = None
        self._files: List[str] = []
        self._build_ui()

    def set_main(self, main) -> None:
        self.main = main

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        title = QLabel("数据导入")
        title.setObjectName("pageTitle")
        sub = QLabel("导入微信 / 支付宝月度账单，自动识别平台并预处理。")
        sub.setObjectName("hint")
        layout.addWidget(title)
        layout.addWidget(sub)

        self.drop = DropZone()
        self.drop.files_dropped.connect(self._add_files)
        layout.addWidget(self.drop)

        btn_row = QHBoxLayout()
        self.btn_choose = QPushButton(icon("folder"), "选择文件")
        self.btn_choose.clicked.connect(self._choose_files)
        self.btn_clear = QPushButton("清空列表")
        self.btn_clear.clicked.connect(self._clear_files)
        btn_row.addWidget(self.btn_choose)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.file_list = QListWidget()
        self.file_list.setObjectName("fileQueue")
        layout.addWidget(self.file_list, 1)

        self.btn_import = QPushButton(icon("import", "#ffffff"), "预览并分类")
        self.btn_import.setObjectName("primary")
        self.btn_import.setMinimumHeight(40)
        self.btn_import.clicked.connect(self._do_import)
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(self.btn_import)
        layout.addLayout(footer)

        layout.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("hint")
        layout.addWidget(self.status)
        self._refresh_list()

    def _add_files(self, paths: List[str]) -> None:
        for p in paths:
            if p not in self._files:
                self._files.append(p)
        self._refresh_list()

    def _choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择账单文件", os.path.expanduser("~"),
            "账单文件 (*.xlsx *.xls *.csv);;所有文件 (*.*)"
        )
        if paths:
            self._add_files(list(paths))

    def _clear_files(self) -> None:
        self._files.clear()
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.file_list.clear()
        self.file_list.setVisible(bool(self._files))
        self.btn_clear.setVisible(bool(self._files))
        self.btn_import.setVisible(bool(self._files))
        for p in self._files:
            plat = detect_platform(p)
            tag = "微信" if plat == PLATFORM_WECHAT else "支付宝"
            item = QListWidgetItem(f"[{tag}]  {os.path.basename(p)}")
            item.setToolTip(p)
            self.file_list.addItem(item)
        self.status.setText(f"已选择 {len(self._files)} 个文件")

    def _do_import(self) -> None:
        if not self._files:
            QMessageBox.information(self, "提示", "请先添加账单文件。")
            return
        if self.main is None:
            return
        try:
            summary = self.main.import_files(self._files)
            if summary is None:
                return
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "导入失败", str(e))
            return
        QMessageBox.information(
            self, "导入完成",
            "\n".join(summary["files"]) + f"\n\n账本共 {summary['笔数']} 条记录\n"
            f"　　支出 {summary['支出笔数']} 笔，共 ¥{summary['支出总额']}\n"
            f"　　收入 {summary['收入笔数']} 笔，共 ¥{summary['收入总额']}\n"
            f"　　未分类支出 {summary['未分类笔数']} 笔"
        )

    def refresh_summary(self, stats: dict) -> None:
        if not stats:
            self.status.setText("尚未导入数据")
            return
        self.status.setText(
            f"当前共 {stats['笔数']} 条记录 · 支出 ¥{stats['支出总额']} · 收入 ¥{stats['收入总额']}"
        )