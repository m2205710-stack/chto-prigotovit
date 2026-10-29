"""Главное окно: шапка с номером шага, экраны и подвал с кнопками навигации."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from .pages import AppState, HomePage, MealPage, ProductsPage, RecipesPage, ResultsPage, ShoppingPage
from .widgets import Toast, fade_in, icon_label, icon_pixmap, label

TOTAL_STEPS = 5


class StepDots(QWidget):
    def __init__(self):
        super().__init__()
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(6)
        self.dots = []
        for _ in range(TOTAL_STEPS):
            d = QLabel()
            d.setFixedSize(26, 6)
            self.dots.append(d)
            self.lay.addWidget(d)

    def set_step(self, n):
        for i, d in enumerate(self.dots, 1):
            col = "#C8553D" if i <= n else "#E3D7C6"
            d.setStyleSheet(f"background: {col}; border-radius: 3px;")


class MainWindow(QMainWindow):
    def __init__(self, repo, app_icon: QIcon | None = None):
        super().__init__()
        self.setWindowTitle("Что приготовить?")
        if app_icon:
            self.setWindowIcon(app_icon)
        self.setMinimumSize(1000, 650)
        self.resize(1280, 820)
        self.state = AppState(repo)

        central = QWidget()
        central.setObjectName("page")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # шапка
        self.header = QWidget()
        self.header.setObjectName("header")
        self.header.setFixedHeight(58)
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(24, 0, 28, 0)
        hl.setSpacing(10)
        hl.addWidget(icon_label("fork_and_knife_with_plate", 30))
        title = label("Что приготовить?", "appTitle")
        title.setCursor(Qt.PointingHandCursor)
        title.mousePressEvent = lambda e: self.new_search(confirm=True)
        hl.addWidget(title)
        hl.addStretch()
        self.step_lbl = label("", "stepText")
        hl.addWidget(self.step_lbl)
        hl.addSpacing(10)
        self.dots = StepDots()
        hl.addWidget(self.dots)
        root.addWidget(self.header)

        # экраны
        self.stack = QStackedWidget()
        self.home = HomePage(self.state)
        self.pages = [self.home, ProductsPage(self.state), MealPage(self.state), ResultsPage(self.state),
                      RecipesPage(self.state), ShoppingPage(self.state)]
        for p in self.pages:
            self.stack.addWidget(p)
            p.changed.connect(self._update_footer)
            p.go.connect(self.go)
        self.home.start.connect(lambda: self.go(1))
        self.pages[5].toast.connect(lambda m: self.toast.show_message(m))
        root.addWidget(self.stack, 1)

        # подвал
        self.footer = QWidget()
        self.footer.setObjectName("footer")
        self.footer.setFixedHeight(72)
        fl = QHBoxLayout(self.footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(12)
        self.back_btn = QPushButton("←  Назад")
        self.back_btn.clicked.connect(self.back)
        fl.addWidget(self.back_btn)
        self.new_btn = QPushButton("Новый подбор")
        self.new_btn.setObjectName("link")
        self.new_btn.clicked.connect(lambda: self.new_search(confirm=True))
        fl.addWidget(self.new_btn)
        fl.addStretch()
        self.status_lbl = label("", "muted")
        self.status_lbl.setStyleSheet("font-size: 14px; font-weight: 600;")
        fl.addWidget(self.status_lbl)
        self.hint_lbl = label("", "hint")
        fl.addWidget(self.hint_lbl)
        fl.addSpacing(8)
        self.next_btn = QPushButton()
        self.next_btn.setObjectName("primary")
        self.next_btn.clicked.connect(self._primary)
        fl.addWidget(self.next_btn)
        for b in (self.back_btn, self.new_btn, self.next_btn):
            b.setCursor(Qt.PointingHandCursor)
        root.addWidget(self.footer)

        self.setCentralWidget(central)
        self.toast = Toast(central)
        self.go(0)

    # навигация
    def go(self, idx: int):
        if idx == -1:
            self.new_search(confirm=False)
            return
        page = self.pages[idx]
        self.stack.setCurrentIndex(idx)
        page.on_enter()
        self.header.setVisible(idx != 0)
        self.footer.setVisible(idx != 0)
        if page.step:
            self.step_lbl.setText(f"Шаг {page.step} из {TOTAL_STEPS} · {page.title}")
            self.dots.set_step(page.step)
        self._update_footer()
        fade_in(page, 180)

    def back(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.go(idx - 1)

    def new_search(self, confirm: bool):
        idx = self.stack.currentIndex()
        if confirm and idx > 1 or (confirm and idx == 1 and self.state.selected):
            box = QMessageBox(QMessageBox.Question, "Новый подбор",
                              "Начать подбор заново? Выбранные продукты и блюда будут сброшены.", parent=self)
            yes = box.addButton("Начать заново", QMessageBox.AcceptRole)
            box.addButton("Отмена", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is not yes:
                return
        if idx == 0:
            return
        self.state.reset()
        self.go(0)

    def _primary(self):
        page = self.stack.currentWidget()
        if page.can_continue():
            page.on_primary()

    def _update_footer(self):
        page = self.stack.currentWidget()
        ok = page.can_continue()
        self.next_btn.setText(page.primary_text + ("  →" if page.step < TOTAL_STEPS else ""))
        self.next_btn.setEnabled(ok)
        self.next_btn.setVisible(bool(page.primary_text) and not (page.step == 3 and not self.state.results))
        self.hint_lbl.setText(page.hint())
        self.hint_lbl.setVisible(bool(page.hint()))
        self.status_lbl.setText(page.status())
        self.new_btn.setVisible(page.step >= 2 and page.step < TOTAL_STEPS)
