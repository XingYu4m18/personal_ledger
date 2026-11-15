"""现代化浅色主题配色与 QSS 样式。"""

from __future__ import annotations

from PySide6.QtGui import QPalette, QColor

# 配色
COLOR_BG = "#f8f7f2"          # 最外层背景
COLOR_SIDEBAR = "#dbeaf4"     # 侧边栏
COLOR_CARD = "#ffffff"        # 卡片
COLOR_CARD2 = "#f6f8fb"       # 次级卡片
COLOR_BORDER = "#d6dfe2"
COLOR_TEXT = "#192e38"
COLOR_TEXT_DIM = "#526773"
COLOR_ACCENT = "#235e9a"      # 主色 蓝
COLOR_ACCENT_DARK = "#285d99"
COLOR_GREEN = "#15715e"
COLOR_RED = "#a94734"
COLOR_YELLOW = "#f9e2af"
COLOR_ORANGE = "#fab387"
COLOR_PURPLE = "#cba6f7"

QSS = f"""
* {{
    font-family: "Microsoft YaHei UI";
    font-size: 13px;
    color: {COLOR_TEXT};
}}

QMainWindow, QWidget#root {{
    background-color: {COLOR_BG};
}}

QDialog, QMessageBox, QInputDialog, QFileDialog, QProgressDialog, QWizard {{
    background-color: {COLOR_CARD};
}}

QAbstractItemView {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT};
    selection-background-color: #d8eafa;
    selection-color: {COLOR_TEXT};
}}

/* ---------- 侧边栏 ---------- */
QFrame#sidebar {{
    background-color: {COLOR_SIDEBAR};
    border: none;
}}
QLabel#appTitle {{
    font-size: 17px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}
QLabel#appSubtitle {{
    font-size: 11px;
    color: {COLOR_TEXT_DIM};
}}
QListWidget#nav {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget#nav::item {{
    padding: 5px 12px;
    margin: 2px 8px;
    border-radius: 8px;
    color: {COLOR_TEXT_DIM};
    font-size: 14px;
}}
QListWidget#nav::item:hover {{
    background-color: {COLOR_CARD};
    color: {COLOR_TEXT};
}}
QListWidget#nav::item:selected {{
    background-color: #bdd7ea;
    color: #143f62;
    border-left: 3px solid #285d99;
    font-weight: 700;
}}

/* ---------- 卡片 ---------- */
QFrame#card {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}
QLabel#cardTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}
QLabel#hint {{
    color: {COLOR_TEXT_DIM};
    font-size: 12px;
}}

/* ---------- 统计数字卡 ---------- */
QLabel#statValue {{
    font-size: 22px;
    font-weight: 700;
    color: {COLOR_ACCENT};
}}
QLabel#statLabel {{
    color: {COLOR_TEXT_DIM};
    font-size: 12px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background-color: {COLOR_CARD2};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}}
QPushButton:focus {{border-color: #558caf;}}
QPushButton:hover {{
    background-color: #eaf1f8;
    border-color: {COLOR_ACCENT};
}}
QPushButton:pressed {{
    background-color: #d9e8f5;
}}
QPushButton:disabled {{
    color: #6c7086;
    background-color: {COLOR_CARD};
}}
QPushButton#calendarDay {{
    padding: 2px 4px;
}}
QPushButton#primary {{
    background-color: {COLOR_ACCENT_DARK};
    border: none;
    color: white;
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background-color: {COLOR_ACCENT};
}}
QPushButton#danger {{
    color: {COLOR_RED};
    border-color: {COLOR_RED};
    background-color: transparent;
}}
QPushButton#danger:hover {{
    background-color: rgba(243, 139, 168, 0.15);
}}
QPushButton#matchBtn {{
    padding: 3px 8px;
    font-size: 12px;
    border-radius: 6px;
}}

/* ---------- 输入框 ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {{
    background-color: {COLOR_CARD2};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {COLOR_ACCENT_DARK};
    selection-color: white;
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{
    border-color: {COLOR_ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_CARD2};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: #d8eafa;
    selection-color: {COLOR_TEXT};
}}

/* ---------- 复选框 ---------- */
QCheckBox {{
    spacing: 8px;
}}
/* ---------- 表格 ---------- */
QTableView {{
    outline: 0;
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 0;
    border: none;
    gridline-color: {COLOR_BORDER};
    alternate-background-color: {COLOR_CARD2};
    selection-background-color: #d8eafa;
    selection-color: {COLOR_TEXT};
}}
QTableView::item {{
    padding: 4px 8px;
    border: none;
    border-bottom: 1px solid #e7ebed;
}}
QHeaderView::section {{
    background-color: #edf3f6;
    color: #3c5665;
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    border-right: none;
    padding: 8px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background-color: {COLOR_CARD2};
    border: none;
}}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_TEXT_DIM};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {COLOR_BORDER};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QSplitter::handle {{
    background: transparent;
}}
QSplitter::handle:hover {{
    background: {COLOR_ACCENT_DARK};
}}
QSplitter::handle:pressed {{
    background: {COLOR_ACCENT};
}}

/* ---------- 菜单 ---------- */
QMenu {{
    background-color: {COLOR_CARD2};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {COLOR_ACCENT_DARK};
    color: white;
}}

/* ---------- 工具提示 ---------- */
QToolTip {{
    background-color: {COLOR_CARD2};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px;
}}

/* ---------- 拖拽区 ---------- */
QFrame#dropzone {{
    background-color: {COLOR_CARD};
    border: 2px dashed {COLOR_BORDER};
    border-radius: 14px;
}}
QFrame#dropzone[dragActive="true"] {{
    border-color: {COLOR_ACCENT};
    background-color: #e3f0f7;
}}
QLabel#dropzoneText {{
    color: {COLOR_TEXT_DIM};
    font-size: 14px;
}}
QLabel#dropzoneIcon {{
    font-size: 40px;
}}

/* ---------- 标签/分组 ---------- */
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COLOR_ACCENT};
    font-weight: 600;
}}

QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    background-color: {COLOR_CARD};
}}
QTabBar::tab {{
    background: transparent;
    color: {COLOR_TEXT_DIM};
    padding: 8px 18px;
    border: none;
}}
QTabBar::tab:selected {{
    color: {COLOR_ACCENT};
    border-bottom: 2px solid {COLOR_ACCENT};
}}

QLabel#brandMark {{background: #285d79; border-radius: 8px;}}
QLabel#pageTitle {{font-size: 26px; font-weight: 700;}}
QLabel#sectionTitle {{font-size: 16px; font-weight: 600;}}
QLabel#appTitle {{color: #163d58; font-size: 19px;}}
QPushButton#calendarDay {{background: transparent; border: none; border-radius: 9px;}}
QPushButton#calendarDay:hover {{background: #dcebf7;}}
QProgressBar {{background: #ebf1f5; color: #173950; text-align:center; border: none; border-radius: 4px;}}
QProgressBar::chunk {{background: #9ac6e2; border-radius: 4px;}}
QScrollArea {{border: none;}}
QListWidget#fileQueue {{background: {COLOR_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px; padding: 8px;}}
QListWidget#fileQueue::item {{padding: 9px;}}
QFrame#statTile {{
    background-color: {COLOR_CARD2};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
QFrame#statTile[tone="expense"] {{background: #fff0e9; border-color: #efd6c9;}}
QFrame#statTile[tone="income"] {{background: #e6f5ec; border-color: #cde5d6;}}
QFrame#statTile[tone="pending"] {{background: #f3eefb; border-color: #ded3ed;}}
QFrame#dropzone {{background: #eff7fb; border-color: #9fbdd3;}}
QLabel#dropzoneIcon {{color: #285d99;}}
QFrame#statTile:hover {{
    border-color: {COLOR_ACCENT};
    background-color: #e4eff9;
}}
QFrame#statTile[highlighted="true"] {{
    border-color: {COLOR_ACCENT};
}}
"""


def light_palette() -> QPalette:
    """返回全局浅色调色板，用于补齐 QSS 未覆盖控件的默认背景。"""
    p = QPalette()
    p.setColor(QPalette.Window, QColor(COLOR_BG))
    p.setColor(QPalette.WindowText, QColor(COLOR_TEXT))
    p.setColor(QPalette.Base, QColor(COLOR_CARD))
    p.setColor(QPalette.AlternateBase, QColor(COLOR_CARD2))
    p.setColor(QPalette.Text, QColor(COLOR_TEXT))
    p.setColor(QPalette.Button, QColor(COLOR_CARD2))
    p.setColor(QPalette.ButtonText, QColor(COLOR_TEXT))
    p.setColor(QPalette.BrightText, QColor(COLOR_RED))
    p.setColor(QPalette.Highlight, QColor("#d8eafa"))
    p.setColor(QPalette.HighlightedText, QColor(COLOR_TEXT))
    p.setColor(QPalette.ToolTipBase, QColor(COLOR_CARD2))
    p.setColor(QPalette.ToolTipText, QColor(COLOR_TEXT))
    p.setColor(QPalette.Link, QColor(COLOR_ACCENT))
    p.setColor(QPalette.PlaceholderText, QColor(COLOR_TEXT_DIM))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#6c7086"))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#6c7086"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#6c7086"))
    return p


# 分类专用配色（循环使用）
CATEGORY_COLORS = [
    "#235e9a", "#15715e", "#f9e2af", "#fab387", "#a94734",
    "#cba6f7", "#94e2d5", "#f5c2e7", "#89dceb", "#e0e0e0",
]


def color_for(index: int) -> str:
    return CATEGORY_COLORS[index % len(CATEGORY_COLORS)]


