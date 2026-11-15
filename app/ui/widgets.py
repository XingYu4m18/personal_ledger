"""表格列宽始终合计为可用宽度，内部边界由用户拖动。"""
from PySide6.QtCore import QObject, QEvent, Qt, QSettings, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QHeaderView, QPushButton, QMenu, QStyledItemDelegate, QStyle, QAbstractItemView
from ..database import default_path


class RowDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, index)
        if option.state & QStyle.State_Selected:
            from PySide6.QtGui import QColor
            painter.save()
            painter.setPen(QColor("#287bb5"))
            rect = option.rect
            painter.drawLine(rect.topLeft(), rect.topRight())
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())
            header = self.parent().horizontalHeader()
            visible = [header.logicalIndex(i) for i in range(header.count())
                       if not header.isSectionHidden(header.logicalIndex(i))]
            if visible and index.column() == visible[0]:
                painter.drawLine(rect.topLeft(), rect.bottomLeft())
            if visible and index.column() == visible[-1]:
                painter.drawLine(rect.topRight(), rect.bottomRight())
            painter.restore()


class RowSelection(QObject):
    """Apply row selection consistently to clicks, modifier clicks and drags."""

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self.anchor = None
        self.active = False
        table.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            index = self.table.indexAt(event.position().toPoint())
            if not index.isValid():
                return False
            self.active = True
            self.start = index.row()
            selection = self.table.selectionModel()
            self.base = {i.row() for i in selection.selectedRows()}
            self.control = bool(event.modifiers() & Qt.ControlModifier)
            if index.column() == 0 and getattr(self.table.model(), "_show_checkbox", False):
                self.control = not bool(event.modifiers() & Qt.ShiftModifier)
            if event.modifiers() & Qt.ShiftModifier and self.anchor is not None:
                self.start = self.anchor
            else:
                self.anchor = self.start
            self.removing = self.control and index.row() in self.base
            self.apply(index)
            # Preserve native checkbox toggling without letting the view reset selection.
            if index.flags() & Qt.ItemIsUserCheckable:
                from PySide6.QtWidgets import QStyleOptionViewItem
                option = QStyleOptionViewItem()
                self.table.itemDelegate().initStyleOption(option, index)
                option.rect = self.table.visualRect(index)
                indicator = self.table.style().subElementRect(QStyle.SE_ItemViewItemCheckIndicator, option, self.table)
                if indicator.contains(event.position().toPoint()):
                    state = index.data(Qt.CheckStateRole)
                    checked = state == Qt.Checked or state == Qt.Checked.value
                    self.table.model().setData(index, Qt.Unchecked if checked else Qt.Checked, Qt.CheckStateRole)
            return True
        if kind == QEvent.MouseMove and self.active:
            index = self.table.indexAt(event.position().toPoint())
            if index.isValid():
                self.apply(index)
                self.table.scrollTo(index)
            return True
        if kind == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton and self.active:
            self.active = False
            return True
        return False

    def apply(self, index):
        rows = set(range(min(self.start, index.row()), max(self.start, index.row()) + 1))
        if self.control:
            rows = self.base - rows if self.removing else self.base | rows
        model = self.table.model()
        selected = QItemSelection()
        for row in sorted(rows):
            selected.select(model.index(row, 0), model.index(row, model.columnCount() - 1))
        selection = self.table.selectionModel()
        selection.select(selected, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        selection.setCurrentIndex(index, QItemSelectionModel.NoUpdate)


def configure_selection(table):
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    table.setDragEnabled(False)
    table.setItemDelegate(RowDelegate(table))
    table._row_selection = RowSelection(table)


class FittedColumns(QObject):
    def __init__(self, table, profile=None):
        super().__init__(table)
        self.table = table
        configure_selection(table)
        self.header = table.horizontalHeader()
        self.header.setStretchLastSection(False)
        self.header.setSectionResizeMode(QHeaderView.Interactive)
        self.header.setMinimumSectionSize(8)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preferred = getattr(table.model(), "preferred_widths", None)
        self.weights = self.widths()
        self.busy = False
        self.settings = None
        if profile:
            self.options = table.model().column_options()
            self.settings = QSettings(str(default_path().with_name("table-layout.ini")), QSettings.IniFormat)
            self.settings.beginGroup(profile)
            self.restore()
            self.header.setContextMenuPolicy(Qt.CustomContextMenu)
            self.header.customContextMenuRequested.connect(self.open_menu)
        table.viewport().installEventFilter(self)
        self.header.sectionResized.connect(self.column_changed)
        self.fit()

    def restore(self, defaults=False):
        self.busy = True
        visible_count = 0
        for index, _, key, default in self.options:
            visible = default if defaults else self.settings.value("visible/" + key, default, type=bool)
            self.table.setColumnHidden(index, not visible)
            visible_count += visible
        if not visible_count:
            self.table.setColumnHidden(self.options[0][0], False)
        self.busy = False
        stored = self.settings.value("widths", [])
        if not defaults and isinstance(stored, list) and len(stored) == self.header.count():
            try:
                self.weights = [max(1, int(x)) for x in stored]
                self.preferred = None
            except (TypeError, ValueError):
                pass

    def save(self):
        if self.settings is None:
            return
        for index, _, key, _ in self.options:
            self.settings.setValue("visible/" + key, not self.table.isColumnHidden(index))
        if self.preferred:
            self.settings.remove("widths")
        else:
            self.settings.setValue("widths", self.weights)
        self.settings.sync()

    def open_menu(self, pos):
        menu = QMenu(self.table)
        menu.addAction("自动调整可见列宽", self.autosize)
        menu.addSeparator()
        count = sum(not self.table.isColumnHidden(i) for i, *_ in self.options)
        for i, label, _, _ in self.options:
            visible = not self.table.isColumnHidden(i)
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(visible)
            action.setEnabled(not visible or count > 1)
            action.triggered.connect(lambda checked, index=i: self.toggle(index, checked))
        menu.addSeparator()
        menu.addAction("恢复默认列和宽度", self.reset)
        menu.exec(self.header.mapToGlobal(pos))

    def toggle(self, index, visible):
        self.busy = True
        self.table.setColumnHidden(index, not visible)
        self.busy = False
        if visible and not self.preferred:
            self.weights[index] = self.table.model().preferred_widths(self.table, self.table.viewport().width())[index]
        self.fit()
        self.save()

    def reset(self):
        self.restore(defaults=True)
        self.autosize()

    def widths(self):
        return [self.header.sectionSize(i) for i in range(self.header.count())]

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Resize, QEvent.Show):
            self.fit()
        return False

    def apply(self, widths):
        self.busy = True
        try:
            for i, width in enumerate(widths):
                if not self.table.isColumnHidden(i):
                    self.header.resizeSection(i, width)
        finally:
            self.busy = False

    def fit(self):
        width = self.table.viewport().width()
        weights = self.preferred(self.table, width) if self.preferred else self.weights
        indices = [i for i in range(len(weights)) if not self.table.isColumnHidden(i)]
        if not indices or width < 8 * len(indices):
            return
        minimum = min(32, width // len(indices))
        flexible = [max(1, value - minimum) for value in (weights[i] for i in indices)]
        remaining = width - minimum * len(indices)
        total = sum(flexible)
        widths = []
        cumulative = previous = 0
        for weight in flexible:
            cumulative += weight
            edge = round(remaining * cumulative / total)
            widths.append(minimum + edge - previous)
            previous = edge
        result = [0] * len(weights)
        for i, size in zip(indices, widths):
            result[i] = size
        self.apply(result)

    def column_changed(self, index, old, new):
        if self.busy:
            return
        widths = self.widths()
        following = next((i for i in range(index + 1, len(widths)) if not self.table.isColumnHidden(i)), None)
        if following is None:
            widths[index] = old
        else:
            minimum = min(32, self.table.viewport().width() // len(widths))
            delta = max(minimum - old, min(new - old, widths[following] - minimum))
            widths[index] = old + delta
            widths[following] -= delta
        self.apply(widths)
        self.preferred = None
        self.weights = widths
        self.save()

    def autosize(self):
        self.preferred = getattr(self.table.model(), "preferred_widths", None)
        if self.preferred:
            self.fit()
            self.save()
            return
        self.busy = True
        try:
            self.table.resizeColumnsToContents()
            self.weights = self.widths()
        finally:
            self.busy = False
        self.fit()


def autosize_button(table, text="自动列宽", profile=None):
    columns = FittedColumns(table, profile)
    button = QPushButton(text)
    button.setObjectName("autosizeBtn")
    button.setToolTip("按内容分配当前可用宽度")
    button.clicked.connect(columns.autosize)
    return button
