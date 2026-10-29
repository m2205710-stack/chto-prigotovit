"""Экраны приложения (п. 3.1–3.7 ТЗ)."""
import os
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
                               QButtonGroup)

from core.matcher import match_recipes, shopping_list, with_substitutes
from core.models import fmt_quantity

from .widgets import (Chip, CheckCircle, ClickableFrame, FlowLayout, MetaChip, PercentBar, ProductTile,
                      clear_layout, dish_pixmap, fade_in, icon_label, label, photo_credit, set_selected, shadow)

MEAL_ICONS = {"Завтрак": "sunrise", "Обед": "pot_of_food", "Ужин": "shallow_pan_of_food",
              "Перекус": "sandwich", "Десерт": "shortcake"}
MEAL_HINTS = {"Завтрак": "каши, сырники, омлеты", "Обед": "супы и горячее", "Ужин": "горячее и салаты",
              "Перекус": "быстро и сытно", "Десерт": "выпечка и сладкое"}


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def scroll_wrap(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    inner.setObjectName("scrollBody")
    sa.setWidget(inner)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    return sa


class AppState:
    def __init__(self, repo):
        self.repo = repo
        self.reset()

    def reset(self):
        self.selected: set[int] = set()
        self.meal: str | None = None
        self.results = []
        self.chosen: list[int] = []        # id выбранных рецептов в порядке выбора

    @property
    def owned(self) -> set[int]:
        """Выбранные продукты вместе с взаимозаменяемыми (батон = белый хлеб)."""
        return with_substitutes(self.selected, self.repo.products)

    def chosen_recipes(self):
        by_id = {r.id: r for r in self.repo.recipes}
        return [by_id[i] for i in self.chosen if i in by_id]


class Page(QWidget):
    changed = Signal()          # изменилось состояние кнопок подвала
    go = Signal(int)            # перейти на экран
    step = 0
    title = ""
    primary_text = ""

    def __init__(self, state: AppState):
        super().__init__()
        self.setObjectName("page")
        self.state = state

    def on_enter(self):
        pass

    def can_continue(self) -> bool:
        return True

    def hint(self) -> str:
        return ""

    def status(self) -> str:
        return ""

    def on_primary(self):
        pass


# ---------------------------------------------------------------- главный экран
class HomePage(Page):
    start = Signal()

    def __init__(self, state):
        super().__init__(state)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 30, 40, 40)
        outer.addStretch(2)

        icons = QHBoxLayout()
        icons.setSpacing(14)
        icons.addStretch()
        for i, n in enumerate(["tomato", "cucumber", "egg", "poultry_leg", "cheese_wedge", "carrot", "brown_mushroom"]):
            ic = icon_label(n, 64 if i == 3 else 52)
            icons.addWidget(ic, 0, Qt.AlignBottom if i % 2 else Qt.AlignTop)
        icons.addStretch()
        outer.addLayout(icons)
        outer.addSpacing(26)

        t = label("Что приготовить?", "h1")
        t.setStyleSheet("font-size: 46px;")
        t.setAlignment(Qt.AlignCenter)
        outer.addWidget(t)
        s = label("Отметьте продукты, которые есть дома, — приложение подберёт блюда,\n"
                  "покажет понятные рецепты и составит список того, что нужно докупить.", "sub")
        s.setStyleSheet("font-size: 17px;")
        s.setAlignment(Qt.AlignCenter)
        outer.addWidget(s)
        outer.addSpacing(30)

        btn = QPushButton("Начать подбор")
        btn.setObjectName("primary")
        btn.setProperty("class", "big")
        btn.setStyleSheet("font-size: 18px; padding: 15px 46px; border-radius: 14px;")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.start.emit)
        outer.addWidget(btn, 0, Qt.AlignHCenter)
        outer.addSpacing(44)

        feats = QHBoxLayout()
        feats.setSpacing(18)
        feats.addStretch()
        n_rec = len(state.repo.recipes)
        for ic, head, text in [
            ("shopping_cart", f"{len(state.repo.selectable_products)} продуктов", "по категориям и с поиском"),
            ("cooking", f"{n_rec} {plural(n_rec, 'рецепт', 'рецепта', 'рецептов')}", "с точными граммовками"),
            ("memo", "Список покупок", "одним списком на все блюда"),
        ]:
            card = QFrame()
            card.setObjectName("panel")
            card.setFixedWidth(270)
            lay = QHBoxLayout(card)
            lay.setContentsMargins(14, 12, 14, 12)
            lay.addWidget(icon_label(ic, 36))
            col = QVBoxLayout()
            col.setSpacing(0)
            col.addWidget(label(head, "h3"))
            col.addWidget(label(text, "muted"))
            lay.addLayout(col, 1)
            feats.addWidget(card)
        feats.addStretch()
        outer.addLayout(feats)
        outer.addStretch(3)


# ---------------------------------------------------------------- выбор продуктов
class ProductsPage(Page):
    step = 1
    title = "Продукты"
    primary_text = "Далее"

    def __init__(self, state):
        super().__init__(state)
        repo = state.repo
        root = QHBoxLayout(self)
        root.setContentsMargins(32, 22, 24, 18)
        root.setSpacing(22)

        left = QVBoxLayout()
        left.setSpacing(12)
        left.addWidget(label("Что есть в холодильнике?", "h1"))
        left.addWidget(label("Отметьте продукты, которые есть у вас дома. Повторный щелчок снимает выбор.", "sub"))

        sbox = QWidget()
        sl = QHBoxLayout(sbox)
        sl.setContentsMargins(0, 4, 0, 0)
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Найти продукт, например «сыр»")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refilter)
        mag = icon_label("magnifying_glass_tilted_right", 20)
        mag.setParent(self.search)
        mag.move(13, 12)
        sl.addWidget(self.search)
        left.addWidget(sbox)

        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        tabs_wrap = QWidget()
        tabs_flow = FlowLayout(tabs_wrap, spacing=8)
        for i, c in enumerate(repo.categories):
            b = QPushButton(c)
            b.setObjectName("pill")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.tab_group.addButton(b, i)
            tabs_flow.addWidget(b)
        self.tab_group.button(0).setChecked(True)
        self.tab_group.idClicked.connect(self._tab_clicked)
        left.addWidget(tabs_wrap)

        self.found = label("", "muted")
        left.addWidget(self.found)

        grid_body = QWidget()
        self.flow = FlowLayout(grid_body, spacing=12)
        self.flow.setContentsMargins(2, 2, 8, 12)
        self.tiles: dict[int, ProductTile] = {}
        for p in repo.selectable_products:
            t = ProductTile(p)
            t.toggled.connect(self._toggle)
            self.tiles[p.id] = t
            self.flow.addWidget(t)
        self.empty = label("Ничего не найдено. Попробуйте другое название.", "sub")
        self.empty.setAlignment(Qt.AlignCenter)
        self.scroll = scroll_wrap(grid_body)
        left.addWidget(self.scroll, 1)
        left.addWidget(self.empty)
        root.addLayout(left, 1)

        # панель выбранных продуктов
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(290)
        shadow(panel, 30, 6, 20)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(18, 18, 18, 16)
        pl.setSpacing(10)
        top = QHBoxLayout()
        self.count_lbl = label("Выбрано: 0", "h3")
        top.addWidget(self.count_lbl)
        top.addStretch()
        self.clear_btn = QPushButton("Очистить всё")
        self.clear_btn.setObjectName("link")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear)
        top.addWidget(self.clear_btn)
        pl.addLayout(top)
        chips_body = QWidget()
        chips_body.setStyleSheet("background: transparent;")
        self.chips = FlowLayout(chips_body, spacing=6)
        self.chips_scroll = scroll_wrap(chips_body)
        self.chips_scroll.setStyleSheet("QScrollArea, QWidget#scrollBody { background: transparent; }")
        pl.addWidget(self.chips_scroll, 1)
        self.chips_empty = label("Пока ничего не выбрано.\nЩёлкните по продукту слева.", "muted")
        self.chips_empty.setAlignment(Qt.AlignCenter)
        pl.addWidget(self.chips_empty, 1)
        note = QFrame()
        note.setObjectName("note")
        nl = QHBoxLayout(note)
        nl.setContentsMargins(10, 10, 10, 10)
        nl.setSpacing(8)
        nl.addWidget(icon_label("salt", 24), 0, Qt.AlignTop)
        basics = ", ".join(p.name.lower() for p in repo.basic_products)
        nt = label(f"Базовые продукты ({basics}) отмечать не нужно — считаем, что они всегда есть дома.", wrap=True)
        nl.addWidget(nt, 1)
        pl.addWidget(note)
        root.addWidget(panel)

        self._cat = repo.categories[0]
        self._refilter()

    def on_enter(self):
        for pid, t in self.tiles.items():
            t.set_selected(pid in self.state.selected)
        self._rebuild_chips()

    def _tab_clicked(self, i):
        self._cat = self.state.repo.categories[i]
        if self.search.text():
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
        self._refilter()

    def _refilter(self):
        q = self.search.text().strip().lower()
        n = 0
        for t in self.tiles.values():
            vis = (q in t.product.name.lower()) if q else (t.product.category == self._cat)
            t.setVisible(vis)
            n += vis
        for b in self.tab_group.buttons():
            b.setEnabled(True)
        self.tab_group.setExclusive(not q)
        if q:
            for b in self.tab_group.buttons():
                b.setChecked(False)
            self.found.setText(f"Найдено: {n}")
        else:
            self.tab_group.setExclusive(True)
            self.tab_group.button(self.state.repo.categories.index(self._cat)).setChecked(True)
            self.found.setText(f"{self._cat} · {n} {plural(n, 'продукт', 'продукта', 'продуктов')}")
        self.empty.setVisible(n == 0)
        self.scroll.setVisible(n > 0)
        self.flow.invalidate()
        self.scroll.widget().adjustSize()
        self.scroll.verticalScrollBar().setValue(0)

    def _toggle(self, pid, on):
        if on:
            self.state.selected.add(pid)
        else:
            self.state.selected.discard(pid)
        self.tiles[pid].set_selected(on)
        self._rebuild_chips()

    def _clear(self):
        for pid in list(self.state.selected):
            self.tiles[pid].set_selected(False)
        self.state.selected.clear()
        self._rebuild_chips()

    def _rebuild_chips(self):
        clear_layout(self.chips)
        prods = self.state.repo.products
        order = [p.id for p in self.state.repo.selectable_products]
        for pid in sorted(self.state.selected, key=order.index):
            ch = Chip(prods[pid])
            ch.removed.connect(lambda i: self._toggle(i, False))
            self.chips.addWidget(ch)
        n = len(self.state.selected)
        self.count_lbl.setText(f"Выбрано: {n}")
        self.clear_btn.setVisible(n > 0)
        self.chips_scroll.setVisible(n > 0)
        self.chips_empty.setVisible(n == 0)
        self.changed.emit()

    def can_continue(self):
        return bool(self.state.selected)

    def hint(self):
        return "" if self.state.selected else "Выберите хотя бы один продукт"

    def status(self):
        n = len(self.state.selected)
        return f"Выбрано {n} {plural(n, 'продукт', 'продукта', 'продуктов')}" if n else ""

    def on_primary(self):
        self.go.emit(2)


# ---------------------------------------------------------------- приём пищи
class MealPage(Page):
    step = 2
    title = "Приём пищи"
    primary_text = "Подобрать блюда"

    def __init__(self, state):
        super().__init__(state)
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.addStretch(1)
        h = label("Для какого приёма пищи готовим?", "h1")
        h.setAlignment(Qt.AlignCenter)
        root.addWidget(h)
        s = label("Выберите один вариант — подберём блюда, которые подходят именно для него.", "sub")
        s.setAlignment(Qt.AlignCenter)
        root.addWidget(s)
        root.addSpacing(34)
        row = QHBoxLayout()
        row.setSpacing(18)
        row.addStretch()
        self.cards = {}
        for m in MEAL_ICONS:
            c = ClickableFrame("mealCard")
            c.setFixedSize(176, 210)
            lay = QVBoxLayout(c)
            lay.setContentsMargins(12, 26, 12, 20)
            lay.setSpacing(6)
            lay.addWidget(icon_label(MEAL_ICONS[m], 80), 0, Qt.AlignHCenter)
            lay.addSpacing(8)
            t = label(m, "h2")
            t.setAlignment(Qt.AlignCenter)
            lay.addWidget(t)
            d = label(MEAL_HINTS[m], "muted")
            d.setAlignment(Qt.AlignCenter)
            d.setWordWrap(True)
            lay.addWidget(d)
            lay.addStretch()
            c.clicked.connect(lambda m=m: self._pick(m))
            shadow(c, 26, 5, 18)
            self.cards[m] = c
            row.addWidget(c)
        row.addStretch()
        root.addLayout(row)
        root.addStretch(2)

    def on_enter(self):
        for m, c in self.cards.items():
            set_selected(c, m == self.state.meal)

    def _pick(self, m):
        self.state.meal = m
        self.on_enter()
        self.changed.emit()

    def can_continue(self):
        return self.state.meal is not None

    def hint(self):
        return "" if self.state.meal else "Выберите приём пищи"

    def status(self):
        return f"Выбрано: {self.state.meal.lower()}" if self.state.meal else ""

    def on_primary(self):
        st = self.state
        st.results = match_recipes(st.repo.recipes, st.owned, st.meal)
        valid = {r.recipe.id for r in st.results}
        st.chosen = [i for i in st.chosen if i in valid]
        self.go.emit(3)


# ---------------------------------------------------------------- результаты
class ResultCard(ClickableFrame):
    def __init__(self, n, res, parent=None):
        super().__init__("result", parent)
        self.res = res
        r = res.recipe
        self.setMinimumHeight(132)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 14, 22, 14)
        lay.setSpacing(16)
        self.check = CheckCircle()
        lay.addWidget(self.check, 0, Qt.AlignVCenter)
        ph = QLabel()
        ph.setPixmap(dish_pixmap(r.image, 150, 104, 12))
        ph.setFixedSize(150, 104)
        lay.addWidget(ph)
        mid = QVBoxLayout()
        mid.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(8)
        num = label(str(n), "number")
        num.setFixedSize(24, 24)
        num.setAlignment(Qt.AlignCenter)
        top.addWidget(num)
        nm = label(r.name, "dishName")
        top.addWidget(nm, 1)
        mid.addLayout(top)
        meta = QHBoxLayout()
        meta.setSpacing(6)
        meta.addWidget(MetaChip("stopwatch", fmt_time(r.cook_time)))
        meta.addWidget(MetaChip("", f"Сложность: {r.difficulty}"))
        meta.addWidget(MetaChip("", f"{r.servings} {plural(r.servings, 'порция', 'порции', 'порций')}"))
        meta.addStretch()
        mid.addLayout(meta)
        if res.missing:
            k = len(res.missing)
            names = ", ".join(i.product.name.lower() for i in res.missing[:4]) + ("…" if k > 4 else "")
            ml = label(f"Не хватает {k} {plural(k, 'продукта', 'продуктов', 'продуктов')}: {names}", "missText")
        else:
            ml = label("✓ Все продукты есть", "okText")
        ml.setWordWrap(True)
        mid.addWidget(ml)
        lay.addLayout(mid, 1)
        right = QVBoxLayout()
        right.setSpacing(4)
        right.addStretch()
        pc = label(f"{res.percent}%", "percent")
        if res.percent == 100:
            pc.setStyleSheet("color: #5E7F42;")
        pc.setAlignment(Qt.AlignRight)
        right.addWidget(pc)
        right.addWidget(label("совпадение", "muted"), 0, Qt.AlignRight)
        right.addWidget(PercentBar(res.percent))
        right.addStretch()
        lay.addLayout(right)

    def set_checked(self, v):
        self.check.set_checked(v)
        set_selected(self, v)


def fmt_time(m):
    if m < 60:
        return f"{m} мин"
    h, mm = divmod(m, 60)
    return f"{h} ч {mm} мин" if mm else f"{h} ч"


class ResultsPage(Page):
    step = 3
    title = "Подбор блюд"
    primary_text = "Показать рецепты"

    def __init__(self, state):
        super().__init__(state)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 22, 32, 10)
        root.setSpacing(6)
        self.h = label("", "h1")
        root.addWidget(self.h)
        self.sub = label("", "sub")
        self.sub.setWordWrap(True)
        root.addWidget(self.sub)
        root.addSpacing(8)
        body = QWidget()
        self.list = QVBoxLayout(body)
        self.list.setContentsMargins(4, 4, 12, 16)
        self.list.setSpacing(12)
        self.scroll = scroll_wrap(body)
        root.addWidget(self.scroll, 1)

        self.empty = QWidget()
        el = QVBoxLayout(self.empty)
        el.addStretch()
        el.addWidget(icon_label("thinking_face", 96), 0, Qt.AlignHCenter)
        el.addSpacing(10)
        t = label("Подходящих блюд не найдено", "h2")
        t.setAlignment(Qt.AlignCenter)
        el.addWidget(t)
        d = label("Ни в одном рецепте нет хотя бы половины нужных продуктов из вашего списка.\n"
                  "Добавьте ещё продукты или выберите другой приём пищи.", "sub")
        d.setAlignment(Qt.AlignCenter)
        el.addWidget(d)
        el.addSpacing(16)
        bl = QHBoxLayout()
        bl.addStretch()
        b1 = QPushButton("Изменить продукты")
        b1.setObjectName("primary")
        b1.clicked.connect(lambda: self.go.emit(1))
        b2 = QPushButton("Другой приём пищи")
        b2.clicked.connect(lambda: self.go.emit(2))
        for b in (b1, b2):
            b.setCursor(Qt.PointingHandCursor)
            bl.addWidget(b)
        bl.addStretch()
        el.addLayout(bl)
        el.addStretch(2)
        root.addWidget(self.empty, 1)
        self.cards = {}

    def on_enter(self):
        st = self.state
        clear_layout(self.list)
        self.cards = {}
        n = len(st.results)
        k = len(st.selected)
        if n:
            self.h.setText(f"Нашлось {n} {plural(n, 'блюдо', 'блюда', 'блюд')}")
            self.sub.setText(f"{st.meal} · из {k} {plural(k, 'вашего продукта', 'ваших продуктов', 'ваших продуктов')}. "
                             "Отметьте одно или несколько блюд, которые будете готовить.")
            for i, res in enumerate(st.results, 1):
                c = ResultCard(i, res)
                c.set_checked(res.recipe.id in st.chosen)
                c.clicked.connect(lambda rid=res.recipe.id: self._toggle(rid))
                self.cards[res.recipe.id] = c
                self.list.addWidget(c)
            self.list.addStretch()
            fade_in(self.scroll.widget())
        else:
            self.h.setText("")
            self.sub.setText("")
        self.h.setVisible(bool(n))
        self.sub.setVisible(bool(n))
        self.scroll.setVisible(bool(n))
        self.empty.setVisible(not n)
        self.scroll.verticalScrollBar().setValue(0)

    def _toggle(self, rid):
        ch = self.state.chosen
        if rid in ch:
            ch.remove(rid)
        else:
            ch.append(rid)
        self.cards[rid].set_checked(rid in ch)
        self.changed.emit()

    def can_continue(self):
        return bool(self.state.chosen)

    def hint(self):
        if not self.state.results:
            return ""
        return "" if self.state.chosen else "Выберите хотя бы одно блюдо"

    def status(self):
        n = len(self.state.chosen)
        return f"Выбрано блюд: {n}" if n else ""

    def on_primary(self):
        self.go.emit(4)


# ---------------------------------------------------------------- рецепты
class RecipesPage(Page):
    step = 4
    title = "Рецепты"
    primary_text = "Список покупок"

    def __init__(self, state):
        super().__init__(state)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 18, 32, 0)
        root.setSpacing(10)
        tabs_w = QWidget()
        self.tabs = FlowLayout(tabs_w, spacing=8)
        self.tabs_w = tabs_w
        root.addWidget(tabs_w)
        self.group = QButtonGroup(self)
        self.group.idClicked.connect(self._show)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 6, 12, 28)
        self.scroll = scroll_wrap(self.body)
        root.addWidget(self.scroll, 1)

    def on_enter(self):
        clear_layout(self.tabs)
        for b in self.group.buttons():
            self.group.removeButton(b)
        recs = self.state.chosen_recipes()
        for i, r in enumerate(recs):
            b = QPushButton(r.name)
            b.setObjectName("pill")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b, i)
            self.tabs.addWidget(b)
        self.tabs_w.setVisible(len(recs) > 1)
        if recs:
            self.group.button(0).setChecked(True)
            self._show(0)

    def _show(self, i):
        r = self.state.chosen_recipes()[i]
        sel = self.state.owned
        clear_layout(self.body_lay)

        top = QHBoxLayout()
        top.setSpacing(26)
        phcol = QVBoxLayout()
        phcol.setSpacing(6)
        ph = QLabel()
        ph.setPixmap(dish_pixmap(r.image, 380, 270, 18))
        ph.setFixedSize(380, 270)
        phcol.addWidget(ph)
        credit = photo_credit(r.image)
        if credit:
            cl = label(credit, "muted", wrap=True)
            cl.setStyleSheet("font-size: 11px;")
            cl.setMaximumWidth(380)
            phcol.addWidget(cl)
        phcol.addStretch()
        top.addLayout(phcol)
        info = QVBoxLayout()
        info.setSpacing(10)
        info.addWidget(label(" · ".join(r.meal_types), "muted"))
        t = label(r.name, "h1")
        t.setWordWrap(True)
        info.addWidget(t)
        meta = QHBoxLayout()
        meta.setSpacing(8)
        meta.addWidget(MetaChip("stopwatch", fmt_time(r.cook_time)))
        meta.addWidget(MetaChip("bar_chart", f"Сложность: {r.difficulty}"))
        meta.addWidget(MetaChip("fork_and_knife_with_plate", f"{r.servings} {plural(r.servings, 'порция', 'порции', 'порций')}"))
        meta.addStretch()
        info.addLayout(meta)
        miss = [i for i in r.main_ingredients if i.product.id not in sel]
        have_n = len(r.main_ingredients) - len(miss)
        summary = (f"Из ваших продуктов есть {have_n} из {len(r.main_ingredients)} основных ингредиентов. "
                   + (f"Докупить нужно: {', '.join(i.product.name.lower() for i in miss)}." if miss
                      else "Докупать ничего не нужно."))
        sm = label(summary, "body", wrap=True)
        info.addWidget(sm)
        info.addStretch()
        top.addLayout(info, 1)
        self.body_lay.addLayout(top)
        self.body_lay.addSpacing(22)

        cols = QHBoxLayout()
        cols.setSpacing(28)
        ing = QFrame()
        ing.setObjectName("panel")
        il = QVBoxLayout(ing)
        il.setContentsMargins(20, 18, 20, 18)
        il.setSpacing(0)
        il.addWidget(label("Ингредиенты", "h2"))
        il.addSpacing(8)
        for it in r.ingredients:
            row = QFrame()
            row.setObjectName("ingRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 9, 0, 9)
            rl.setSpacing(10)
            rl.addWidget(icon_label(it.product.icon, 26))
            namecol = QVBoxLayout()
            namecol.setSpacing(0)
            nm = label(it.product.name, wrap=True)
            namecol.addWidget(nm)
            if it.note and it.amount is not None:        # уточнение — под названием
                nt = label(it.note, "muted", wrap=True)
                nt.setStyleSheet("font-size: 12px;")
                namecol.addWidget(nt)
            rl.addLayout(namecol, 1)
            q = label(fmt_quantity(it.amount, it.product.unit, "" if it.amount is not None else it.note), "muted")
            q.setStyleSheet("font-size: 14px;")
            q.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rl.addWidget(q)
            if it.product.is_basic:
                st = label("базовый", "statusBasic")
            elif it.product.id in self.state.selected:
                st = label("есть", "statusHave")
            elif it.product.id in sel:          # есть взаимозаменяемый продукт
                st = label("замена", "statusHave")
                alts = [p.name for p in self.state.repo.products.values()
                        if p.id in self.state.selected and p.group == it.product.group]
                st.setToolTip("Подойдёт то, что у вас есть: " + ", ".join(alts))
                nm.setToolTip(st.toolTip())
                alt = label("у вас: " + ", ".join(a.lower() for a in alts), "muted")
                alt.setStyleSheet("font-size: 12px;")
                namecol.addWidget(alt)
            else:
                st = label("купить", "statusBuy")
            st.setFixedSize(78, 26)
            st.setAlignment(Qt.AlignCenter)
            rl.addWidget(st)
            il.addWidget(row)
        il.addStretch()
        ing.setFixedWidth(470)
        cols.addWidget(ing, 0, Qt.AlignTop)

        steps = QVBoxLayout()
        steps.setSpacing(14)
        steps.addWidget(label("Приготовление", "h2"))
        for n, s in enumerate(r.steps, 1):
            row = QHBoxLayout()
            row.setSpacing(14)
            num = label(str(n), "stepNum")
            num.setFixedSize(30, 30)
            num.setAlignment(Qt.AlignCenter)
            row.addWidget(num, 0, Qt.AlignTop)
            tx = label(s, "stepText2", wrap=True)
            tx.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row.addWidget(tx, 1)
            steps.addLayout(row)
        steps.addStretch()
        cols.addLayout(steps, 1)
        self.body_lay.addLayout(cols)
        self.body_lay.addStretch()
        self.scroll.verticalScrollBar().setValue(0)
        fade_in(self.body)

    def on_primary(self):
        self.go.emit(5)


# ---------------------------------------------------------------- список покупок
class ShoppingPage(Page):
    step = 5
    title = "Список покупок"
    primary_text = "Новый подбор"
    toast = Signal(str)

    def __init__(self, state):
        super().__init__(state)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 22, 32, 10)
        root.setSpacing(6)
        head = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(4)
        col.addWidget(label("Список покупок", "h1"))
        self.sub = label("", "sub", wrap=True)
        col.addWidget(self.sub)
        head.addLayout(col, 1)
        self.copy_btn = QPushButton("  Скопировать")
        self.save_btn = QPushButton("  Сохранить в файл")
        from .widgets import icon_pixmap
        from PySide6.QtGui import QIcon
        self.copy_btn.setIcon(QIcon(icon_pixmap("clipboard", 20)))
        self.save_btn.setIcon(QIcon(icon_pixmap("memo", 20)))
        for b in (self.copy_btn, self.save_btn):
            b.setCursor(Qt.PointingHandCursor)
            head.addWidget(b, 0, Qt.AlignBottom)
        self.copy_btn.clicked.connect(self._copy)
        self.save_btn.clicked.connect(self._save)
        root.addLayout(head)
        root.addSpacing(10)
        body = QWidget()
        self.lay = QVBoxLayout(body)
        self.lay.setContentsMargins(0, 0, 12, 20)
        self.lay.setSpacing(14)
        self.scroll = scroll_wrap(body)
        root.addWidget(self.scroll, 1)
        self.items = []

    def on_enter(self):
        st = self.state
        recs = st.chosen_recipes()
        self.items = shopping_list(recs, st.owned, st.repo.categories)
        names = ", ".join(f"«{r.name}»" for r in recs)
        self.sub.setText(f"Для {plural(len(recs), 'блюда', 'блюд', 'блюд')} {names}")
        clear_layout(self.lay)
        self.copy_btn.setVisible(bool(self.items))
        self.save_btn.setVisible(bool(self.items))
        if not self.items:
            w = QWidget()
            wl = QVBoxLayout(w)
            wl.addSpacing(40)
            wl.addWidget(icon_label("party_popper", 96), 0, Qt.AlignHCenter)
            t = label("Докупать ничего не нужно", "h2")
            t.setAlignment(Qt.AlignCenter)
            wl.addWidget(t)
            d = label("Все продукты для выбранных блюд у вас уже есть. Можно готовить!", "sub")
            d.setAlignment(Qt.AlignCenter)
            wl.addWidget(d)
            self.lay.addWidget(w)
            self.lay.addStretch()
            return
        groups: dict[str, list] = {}
        for it in self.items:
            groups.setdefault(it.product.category, []).append(it)
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        for k, (cat, its) in enumerate(groups.items()):
            card = QFrame()
            card.setObjectName("panel")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(18, 14, 18, 12)
            cl.setSpacing(0)
            cl.addWidget(label(cat, "h3"))
            cl.addSpacing(4)
            for it in its:
                row = QFrame()
                row.setObjectName("ingRow")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 8, 0, 8)
                rl.setSpacing(10)
                rl.addWidget(icon_label(it.product.icon, 28))
                rl.addWidget(label(it.product.name), 1)
                rl.addWidget(label(self._qty(it), "muted"))
                cl.addWidget(row)
            cl.addStretch()
            grid.addWidget(card, k // 2, k % 2, Qt.AlignTop)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.lay.addLayout(grid)
        n = len(self.items)
        self.lay.addWidget(label(f"Всего {n} {plural(n, 'позиция', 'позиции', 'позиций')}. "
                                 "Базовые продукты и то, что у вас уже есть, в список не включены.", "muted"))
        self.lay.addStretch()
        fade_in(self.scroll.widget())

    @staticmethod
    def _qty(it):
        if it.amount is not None:
            return fmt_quantity(it.amount, it.product.unit)
        return ", ".join(it.notes) or "по вкусу"

    def as_text(self):
        recs = self.state.chosen_recipes()
        lines = ["Список покупок — «Что приготовить?»",
                 "Для блюд: " + ", ".join(r.name for r in recs), ""]
        cat = None
        for it in self.items:
            if it.product.category != cat:
                cat = it.product.category
                if lines[-1] != "":
                    lines.append("")
                lines.append(cat)
            lines.append(f"  • {it.product.name} — {self._qty(it)}")
        return "\n".join(lines) + "\n"

    def _copy(self):
        QGuiApplication.clipboard().setText(self.as_text())
        self.toast.emit("Список скопирован в буфер обмена")

    def _save(self):
        default = os.path.join(os.path.expanduser("~"), "Documents" if os.path.isdir(
            os.path.join(os.path.expanduser("~"), "Documents")) else "", "Список покупок.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить список покупок", default, "Текстовый файл (*.txt)")
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(self.as_text())
        except OSError as e:
            QMessageBox.warning(self, "Не удалось сохранить",
                                f"Файл не сохранён: {e.strerror or e}. Попробуйте выбрать другую папку.")
            return
        self.toast.emit("Список сохранён: " + os.path.basename(path))

    def on_primary(self):
        self.go.emit(-1)        # новый подбор
