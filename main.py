"""«Что приготовить?» — подбор блюд из продуктов, которые есть дома.

Запуск: python main.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from PySide6.QtCore import QLibraryInfo, QTranslator                   # noqa: E402
from PySide6.QtGui import QFont, QIcon                                 # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox                # noqa: E402

from core.repository import DatabaseError, Repository                  # noqa: E402
from ui import theme                                                   # noqa: E402

ASSETS = os.path.join(BASE, "assets")


def main():
    if sys.platform == "win32":
        try:   # отдельный значок приложения на панели задач Windows
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("misis.chto_prigotovit")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("Что приготовить?")
    tr = QTranslator(app)     # русские надписи в стандартных окнах (выбор файла и т. п.)
    if tr.load("qtbase_ru", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(tr)
    theme.load_fonts(ASSETS)
    f = QFont(theme.SANS)
    f.setPointSizeF(10.5)
    app.setFont(f)
    app.setStyleSheet(theme.stylesheet())
    icon = QIcon(os.path.join(ASSETS, "app.ico")) if os.path.exists(os.path.join(ASSETS, "app.ico")) \
        else QIcon(os.path.join(ASSETS, "icons", "cooking.png"))
    app.setWindowIcon(icon)

    try:
        repo = Repository(os.path.join(ASSETS, "cookbook.db"))
    except DatabaseError as e:
        QMessageBox.critical(None, "Что приготовить?",
                             f"{e}.\n\nФайл assets/cookbook.db не найден или повреждён. "
                             "Переустановите приложение.")
        return 1

    from ui.main_window import MainWindow
    win = MainWindow(repo, icon)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
