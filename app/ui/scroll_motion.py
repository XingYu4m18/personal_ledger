"""垂直滚轮缓动和滑块淡入淡出。"""
from PySide6.QtCore import QObject, QEvent, Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import QApplication, QAbstractScrollArea, QAbstractItemView, QGraphicsOpacityEffect


class ScrollMotion(QObject):
    def __init__(self, area):
        super().__init__(area)
        self.bar = area.verticalScrollBar()
        if isinstance(area, QAbstractItemView):
            area.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.slide = QPropertyAnimation(self.bar, b"value", self)
        self.slide.setDuration(165)
        self.slide.setEasingCurve(QEasingCurve.OutCubic)
        effect = QGraphicsOpacityEffect(self.bar)
        effect.setOpacity(.50)
        self.bar.setGraphicsEffect(effect)
        self.fade = QPropertyAnimation(effect, b"opacity", self)
        self.fade.setDuration(180)
        self.rest = QTimer(self, singleShot=True, interval=550)
        self.rest.timeout.connect(self.dim)
        self.bar.valueChanged.connect(self.reveal)
        self.bar.installEventFilter(self)
        area.viewport().installEventFilter(self)

    def opacity(self, target):
        effect = self.fade.targetObject()
        if self.fade.state() == QPropertyAnimation.Running and self.fade.endValue() == target:
            return
        self.fade.stop()
        self.fade.setStartValue(effect.opacity())
        self.fade.setEndValue(target)
        self.fade.start()

    def reveal(self):
        self.opacity(1.)
        self.rest.start()

    def dim(self):
        if not self.bar.underMouse() and not self.bar.isSliderDown():
            self.opacity(.50)

    def eventFilter(self, obj, event):
        kind = event.type()
        if obj is self.bar:
            if kind == QEvent.Enter:
                self.reveal()
            elif kind == QEvent.Leave or kind == QEvent.MouseButtonRelease:
                self.rest.start()
        if kind in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Hide):
            self.slide.stop()
        if kind != QEvent.Wheel:
            return False
        if event.modifiers() or not event.pixelDelta().isNull() or event.phase() != Qt.NoScrollPhase:
            self.slide.stop()
            return False
        delta = event.angleDelta()
        if not delta.y() or abs(delta.x()) > abs(delta.y()):
            return False
        bar = self.bar
        position = bar.value()
        base = self.slide.endValue() if self.slide.state() == QPropertyAnimation.Running else position
        if (base - position) * delta.y() > 0:
            base = position
        distance = min(bar.pageStep(), bar.singleStep() * QApplication.wheelScrollLines())
        target = max(bar.minimum(), min(bar.maximum(), round(base - delta.y() * distance / 120)))
        if target == position:
            self.slide.stop()
            return False
        self.slide.stop()
        self.slide.setStartValue(position)
        self.slide.setEndValue(target)
        self.slide.start()
        self.reveal()
        event.accept()
        return True


class ScrollInstaller(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and isinstance(obj, QAbstractScrollArea):
            if not hasattr(obj, "_scroll_motion"):
                obj._scroll_motion = ScrollMotion(obj)
        return False
