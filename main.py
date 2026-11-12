"""月度账单分析软件 —— 程序入口。

在 Windows 下通过 `python main.py` 运行，或打包为目录版 exe 后直接双击运行。
"""

from __future__ import annotations

import os
import sys


def resource_path(relative: str) -> str:
    """兼容 PyInstaller 打包后资源路径。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from app.ui.theme import QSS, light_palette
    from app.ui.main_window import MainWindow

    from app.ui.scroll_motion import ScrollInstaller


    app = QApplication(sys.argv)
    scroll_installer = ScrollInstaller(app)
    app.installEventFilter(scroll_installer)
    app.setApplicationName("月度账单分析")
    app.setStyleSheet(QSS)
    app.setPalette(light_palette())

    config_path = None

    from app.portable import prepare_data
    from PySide6.QtWidgets import QMessageBox
    try:
        prepare_data()
        window = MainWindow(config_path=config_path)
    except Exception as error:
        QMessageBox.critical(None, "打开账本失败", f"请确认程序目录可写。\n{error}")
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
