"""Проходит основной сценарий без экрана и сохраняет снимки всех экранов.
Запуск: QT_QPA_PLATFORM=offscreen python tools/screenshots.py <папка> [продукты через ;] [приём пищи]"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication   # noqa: E402
from PySide6.QtGui import QFont              # noqa: E402

from core.repository import Repository       # noqa: E402
from ui import theme                          # noqa: E402


def main():
    out = sys.argv[1]
    prods = (sys.argv[2] if len(sys.argv) > 2 else "Помидоры;Огурцы;Макароны;Куриное филе").split(";")
    meal = sys.argv[3] if len(sys.argv) > 3 else "Обед"
    os.makedirs(out, exist_ok=True)
    app = QApplication(sys.argv)
    theme.load_fonts(os.path.join(ROOT, "assets"))
    f = QFont(theme.SANS)
    f.setPointSizeF(10.5)
    app.setFont(f)
    app.setStyleSheet(theme.stylesheet())
    from ui.main_window import MainWindow
    repo = Repository(os.path.join(ROOT, "assets", "cookbook.db"))
    w = MainWindow(repo)
    w.resize(1280, 820)
    w.show()

    def shot(name):
        for _ in range(5):
            app.processEvents()
        w.grab().save(os.path.join(out, name + ".png"))

    shot("0_home")
    w.go(1)
    shot("1a_products_empty")
    pp = w.pages[1]
    by_name = {p.name: p.id for p in repo.selectable_products}
    for n in prods:
        pp._toggle(by_name[n], True)
    shot("1b_products")
    pp.search.setText("сыр")
    shot("1c_search")
    pp.search.setText("")
    w.go(2)
    shot("2a_meal_empty")
    w.pages[2]._pick(meal)
    shot("2b_meal")
    w._primary()
    shot("3a_results")
    rp = w.pages[3]
    for res in w.state.results[:2]:
        rp._toggle(res.recipe.id)
    shot("3b_results_selected")
    if w.state.chosen:
        w._primary()
        shot("4_recipe")
        w._primary()
        shot("5_shopping")
    print("results:", [(r.percent, r.recipe.name) for r in w.state.results])


if __name__ == "__main__":
    main()
