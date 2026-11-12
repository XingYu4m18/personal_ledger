"""账本界面的线性图标，按显示尺寸生成高分辨率图像。"""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "import": "M12 3v11m-4-4 4 4 4-4 M4 14v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5",
    "export": "M12 15V4m-4 4 4-4 4 4 M4 14v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5",
    "ledger": "M6 3.5h13v17H6a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2z M8 4v16 M11 8h5 M11 12h4",
    "rules": "M4 7h7m5 0h4 M4 17h3m5 0h8 M11 4v6h5V4z M7 14v6h5v-6z",
    "trend": "M4 4v16h16 M7 15l4-5 4 2 5-7",
    "folder": "M3 7V5h7l2 2h9v12H3z",
    "calendar": "M4 6h16v14H4z M4 10h16 M8 3v5 M16 3v5 M8 14h2 M14 14h2",
    "plus": "M12 5v14 M5 12h14",
}


def icon(name, color="#315977", size=20):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           f'<path d="{PATHS[name]}" fill="none" stroke="{color}" stroke-width="1.7" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    image = QPixmap(size * 3, size * 3)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    image.setDevicePixelRatio(3)
    return QIcon(image)
