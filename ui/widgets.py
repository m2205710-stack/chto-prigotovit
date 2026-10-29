"""Общие элементы интерфейса."""
import os

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QFont, QLinearGradient
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout,
                               QLabel, QLayout, QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from . import theme

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
_icon_cache: dict = {}


def icon_pixmap(name: str, size: int) -> QPixmap:
    """Значок продукта из assets/icons с учётом масштаба экрана."""
    key = (name, size)
    if key not in _icon_cache:
        pm = QPixmap(os.path.join(ASSETS, "icons", name + ".png"))
        if pm.isNull():
            pm = QPixmap(os.path.join(ASSETS, "icons", "fork_and_knife_with_plate.png"))
        dpr = 2.0
        pm = pm.scaled(int(size * dpr), int(size * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        _icon_cache[key] = pm
    return _icon_cache[key]


def icon_label(name: str, size: int) -> QLabel:
    lb = QLabel()
    lb.setPixmap(icon_pixmap(name, size))
    lb.setFixedSize(size, size)
    lb.setAttribute(Qt.WA_TranslucentBackground)
    return lb


def dish_pixmap(image: str, w: int, h: int, radius: int = 14) -> QPixmap:
    """Фото блюда, обрезанное по размеру со скруглёнными углами.
    Если фото нет — тёплая заглушка со значком тарелки."""
    dpr = 2.0
    out = QPixmap(int(w * dpr), int(h * dpr))
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w * dpr, h * dpr, radius * dpr, radius * dpr)
    p.setClipPath(path)
    src = None
    if image:
        # картинка-стикер блюда (assets/dish_art), если её нет — фото (assets/photos)
        for folder in ("dish_art", "photos"):
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                f = os.path.join(ASSETS, folder, image + ext)
                if os.path.exists(f):
                    src = QPixmap(f)
                    break
            if src is not None:
                break
    if src is not None and not src.isNull():
        s = src.scaled(int(w * dpr), int(h * dpr), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap(int((w * dpr - s.width()) / 2), int((h * dpr - s.height()) / 2), s)
    else:
        g = QLinearGradient(0, 0, w * dpr, h * dpr)
        g.setColorAt(0, QColor("#F6E4D2"))
        g.setColorAt(1, QColor("#EFD3C2"))
        p.fillRect(0, 0, int(w * dpr), int(h * dpr), g)
        ic = QPixmap(os.path.join(ASSETS, "icons", "fork_and_knife_with_plate.png"))
        side = int(min(w, h) * dpr * 0.5)
        ic = ic.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p.setOpacity(0.85)
        p.drawPixmap(int((w * dpr - ic.width()) / 2), int((h * dpr - ic.height()) / 2), ic)
    p.end()
    out.setDevicePixelRatio(dpr)
    return out


_credits = None


def photo_credit(image: str) -> str:
    """Подпись к фото: автор и лицензия (обязательно для фото с Wikimedia Commons)."""
    global _credits
    if _credits is None:
        import json
        try:
            with open(os.path.join(ASSETS, "photos", "credits.json"), encoding="utf-8") as f:
                _credits = json.load(f)
        except (OSError, ValueError):
            _credits = {}
    if os.path.exists(os.path.join(ASSETS, "dish_art", image + ".jpg")):
        return ""                       # показывается стикер, а не фото
    c = _credits.get(image)
    if not c or not os.path.exists(os.path.join(ASSETS, "photos", image + ".jpg")):
        return ""
    author = c.get("author", "")
    if len(author) > 60:
        author = author[:57] + "…"
    return f"Фото: {author}, {c.get('license', '')} · Wikimedia Commons"


def shadow(widget: QWidget, blur=28, dy=6, alpha=28):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(90, 55, 30, alpha))
    widget.setGraphicsEffect(eff)


def label(text: str, name: str = "", wrap=False) -> QLabel:
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    return lb


def set_selected(w: QWidget, value: bool):
    w.setProperty("selected", "true" if value else "false")
    w.style().unpolish(w)
    w.style().polish(w)
    for child in w.findChildren(QWidget):
        child.style().unpolish(child)
        child.style().polish(child)


class FlowLayout(QLayout):
    """Раскладка «потоком»: элементы переносятся на новую строку."""

    def __init__(self, parent=None, spacing=10):
        super().__init__(parent)
        self._items = []
        self._sp = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do(self, rect, test):
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = r.x(), r.y(), 0
        for it in self._items:
            if it.widget() is not None and it.widget().isHidden():
                continue
            hint = it.sizeHint()
            nx = x + hint.width() + self._sp
            if nx - self._sp > r.right() + 1 and line_h > 0:
                x = r.x()
                y += line_h + self._sp
                nx = x + hint.width() + self._sp
                line_h = 0
            if not test:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x = nx
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


class ClickableFrame(QFrame):
    clicked = Signal()

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setObjectName(name)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("selected", "false")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class ProductTile(ClickableFrame):
    """Плитка продукта: значок + название, выбирается щелчком."""
    toggled = Signal(int, bool)

    def __init__(self, product, parent=None):
        super().__init__("tile", parent)
        self.product = product
        self.selected = False
        self.setFixedSize(124, 116)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 12, 6, 8)
        lay.setSpacing(4)
        ic = icon_label(product.icon, 52)
        lay.addWidget(ic, 0, Qt.AlignHCenter)
        name = QLabel(product.name)
        name.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        name.setWordWrap(True)
        lay.addWidget(name, 1)
        self.setToolTip(product.name)
        self.clicked.connect(lambda: self.toggled.emit(self.product.id, not self.selected))

    def set_selected(self, value: bool):
        if value != self.selected:
            self.selected = value
            set_selected(self, value)


class Chip(QFrame):
    """Выбранный продукт на панели справа, с крестиком."""
    removed = Signal(int)

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.setObjectName("chip")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(5)
        lay.addWidget(icon_label(product.icon, 20))
        lay.addWidget(QLabel(product.name))
        x = QToolButton()
        x.setObjectName("chipX")
        x.setText("×")
        x.setCursor(Qt.PointingHandCursor)
        x.setToolTip("Убрать из выбора")
        x.clicked.connect(lambda: self.removed.emit(product.id))
        lay.addWidget(x)


class MetaChip(QFrame):
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("metaChip")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 10, 4)
        lay.setSpacing(6)
        if icon:
            lay.addWidget(icon_label(icon, 18))
        lay.addWidget(QLabel(text))


class PercentBar(QWidget):
    """Тонкая полоска степени соответствия."""

    def __init__(self, percent: int, parent=None):
        super().__init__(parent)
        self.percent = percent
        self.setFixedHeight(8)
        self.setMinimumWidth(110)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.C["line"]))
        p.drawRoundedRect(r, 4, 4)
        w = max(8, int(r.width() * self.percent / 100))
        col = QColor(theme.C["green"] if self.percent == 100 else theme.C["accent"])
        p.setBrush(col)
        p.drawRoundedRect(QRect(r.x(), r.y(), w, r.height()), 4, 4)


class CheckCircle(QWidget):
    """Кружок-отметка выбора блюда."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked = False
        self.setFixedSize(28, 28)

    def set_checked(self, v):
        self.checked = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(2, 2, -2, -2)
        if self.checked:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.C["accent"]))
            p.drawEllipse(r)
            pen = p.pen()
            pen.setColor(QColor("white"))
            pen.setWidthF(2.6)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            c = r.center()
            path = QPainterPath()
            path.moveTo(c.x() - 5.5, c.y() + 0.5)
            path.lineTo(c.x() - 1.5, c.y() + 4.5)
            path.lineTo(c.x() + 6, c.y() - 4)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        else:
            pen = p.pen()
            pen.setColor(QColor(theme.C["line_strong"]))
            pen.setWidthF(2)
            p.setPen(pen)
            p.setBrush(QColor("white"))
            p.drawEllipse(r)


class Toast(QFrame):
    """Короткое всплывающее сообщение внизу окна."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 10, 18, 10)
        self.text = QLabel()
        lay.addWidget(self.text)
        self.hide()
        self._timer = QTimer(self, singleShot=True, interval=1800)
        self._timer.timeout.connect(self.hide)

    def show_message(self, msg: str):
        self.text.setText(msg)
        self.adjustSize()
        par = self.parentWidget()
        self.move((par.width() - self.width()) // 2, par.height() - self.height() - 96)
        self.raise_()
        self.show()
        self._timer.start()


ANIMATIONS = not os.environ.get("NO_ANIM")


def fade_in(widget: QWidget, ms=220):
    if not ANIMATIONS:
        return
    eff = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start(QPropertyAnimation.DeleteWhenStopped)


def clear_layout(layout):
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif it.layout() is not None:
            clear_layout(it.layout())
