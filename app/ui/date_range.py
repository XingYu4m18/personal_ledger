"""并排显示连续两个月，第二次点击才提交区间。"""
from calendar import Calendar, SUNDAY, monthrange
from datetime import date
from functools import partial

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


def shift_month(day, offset):
    year, month = divmod(day.year * 12 + day.month - 1 + offset, 12)
    return date(year, month + 1, 1)


class DateRangeDialog(QDialog):
    def __init__(self, period, anchor, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择时间段")
        self.period = period
        self.month = (period[0] if period else anchor).replace(day=1)
        self.start = self.preview = None
        self.days = {}
        root = QVBoxLayout(self)
        nav = QHBoxLayout()
        for label, offset in [("≪ 上一年", -12), ("‹ 上月", -1), ("下月 ›", 1), ("下一年 ≫", 12)]:
            button = QPushButton(label)
            button.clicked.connect(partial(self.navigate, offset))
            nav.addWidget(button)
        root.addLayout(nav)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)
        self.months = QHBoxLayout()
        root.addLayout(self.months)
        self.hint = QLabel("请选择开始日期")
        root.addWidget(self.hint)
        footer = QHBoxLayout()
        for label, action in [("今天", self.today), ("全部时间", self.clear), ("取消", self.reject)]:
            button = QPushButton(label)
            button.clicked.connect(action)
            footer.addWidget(button)
        root.addLayout(footer)
        self.render()

    def navigate(self, offset):
        self.month = shift_month(self.month, offset)
        self.render()

    def render(self):
        self.days.clear()
        while self.months.count():
            panel = self.months.takeAt(0).widget()
            panel.hide()
            panel.deleteLater()
        for offset in (0, 1):
            month = shift_month(self.month, offset)
            panel = QWidget()
            layout = QGridLayout(panel)
            title = QPushButton(f"{month:%Y年%m月} · 选整月")
            title.clicked.connect(partial(self.whole_month, month))
            layout.addWidget(title, 0, 0, 1, 7)
            for col, name in enumerate("日一二三四五六"):
                layout.addWidget(QLabel(name, alignment=Qt.AlignCenter), 1, col)
            for row, week in enumerate(Calendar(SUNDAY).monthdayscalendar(month.year, month.month), 2):
                for col, number in enumerate(week):
                    if number:
                        day = month.replace(day=number)
                        button = QPushButton(str(number))
                        button.setObjectName("calendarDay")
                        button.ensurePolished()
                        metrics = button.fontMetrics()
                        button.setMinimumSize(max(42, metrics.horizontalAdvance("88") + 14),
                                              max(34, metrics.height() + 10))
                        button.setAutoDefault(False)
                        button.clicked.connect(partial(self.pick, day))
                        button.installEventFilter(self)
                        self.days[button] = day
                        layout.addWidget(button, row, col)
            layout.setRowStretch(8, 1)
            self.months.addWidget(panel)
        self.highlight()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter and self.start and obj in self.days:
            self.preview = self.days[obj]
            self.highlight()
        return super().eventFilter(obj, event)

    def highlight(self):
        span = sorted((self.start, self.preview or self.start)) if self.start else self.period
        for button, day in self.days.items():
            style = ""
            if span and span[0] <= day <= span[1]:
                style = "background:#dae7fc;color:#203e70;" if day not in span else "background:#345ea8;color:white;"
            button.setStyleSheet(style)

    def pick(self, day):
        if self.start:
            self.period = tuple(sorted((self.start, day)))
            self.accept()
        else:
            self.start = self.preview = day
            self.hint.setText(f"开始日期 {day}，请选择结束日期")
            self.highlight()

    def whole_month(self, month):
        self.period = month, month.replace(day=monthrange(month.year, month.month)[1])
        self.accept()

    def today(self):
        self.period = (date.today(), date.today())
        self.accept()

    def clear(self):
        self.period = None
        self.accept()
