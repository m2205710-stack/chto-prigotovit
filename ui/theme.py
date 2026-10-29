"""Оформление «Тёплая кухня»: цвета, шрифты и таблица стилей Qt (QSS)."""
import os

from PySide6.QtGui import QFontDatabase

C = dict(
    bg="#FBF6EE",        # фон окна — кремовый
    card="#FFFFFF",
    bar="#F3EADB",       # шапка и подвал
    accent="#C8553D",    # терракота
    accent_hover="#B4472F",
    accent_press="#9C3C27",
    soft="#F6DDD3",      # светлая терракота — выбранные элементы
    soft_text="#7A2E1C",
    green="#5E7F42",     # оливка — «есть»
    green_soft="#E5EDD8",
    text="#3A2E26",
    muted="#8A7B6E",
    line="#E8DCCB",
    line_strong="#D9C8B1",
    disabled="#E3D7C6",
)

SERIF = "Lora"
SANS = "Nunito"


def load_fonts(assets_dir: str):
    global SERIF, SANS
    fams = {}
    folder = os.path.join(assets_dir, "fonts")
    for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if f.endswith(".ttf"):
            fid = QFontDatabase.addApplicationFont(os.path.join(folder, f))
            if fid >= 0:
                fams[f.split("-")[0]] = QFontDatabase.applicationFontFamilies(fid)[0]
    SERIF = fams.get("Lora", "Georgia")
    SANS = fams.get("Nunito", "Segoe UI")


def stylesheet() -> str:
    c = C
    return f"""
* {{ font-family: "{SANS}"; color: {c['text']}; }}
QMainWindow, QWidget#page, QScrollArea, QScrollArea > QWidget > QWidget#scrollBody {{ background: {c['bg']}; }}
QScrollArea {{ border: none; }}

QWidget#header {{ background: {c['bar']}; border-bottom: 1px solid {c['line']}; }}
QWidget#footer {{ background: {c['bar']}; border-top: 1px solid {c['line']}; }}
QLabel#appTitle {{ font-family: "{SERIF}"; font-size: 19px; font-weight: 600; }}
QLabel#stepText {{ color: {c['muted']}; font-size: 13px; }}

QLabel#h1 {{ font-family: "{SERIF}"; font-size: 30px; font-weight: 600; }}
QLabel#h2 {{ font-family: "{SERIF}"; font-size: 22px; font-weight: 600; }}
QLabel#h3 {{ font-family: "{SERIF}"; font-size: 17px; font-weight: 600; }}
QLabel#sub {{ color: {c['muted']}; font-size: 15px; }}
QLabel#muted {{ color: {c['muted']}; font-size: 13px; }}
QLabel#hint {{ color: {c['accent']}; font-size: 13px; }}
QLabel#body {{ font-size: 15px; }}

QPushButton {{
    font-size: 14px; font-weight: 600; padding: 9px 18px; border-radius: 10px;
    border: 1px solid {c['line_strong']}; background: {c['card']}; color: {c['text']};
}}
QPushButton:hover {{ border-color: {c['accent']}; color: {c['accent']}; }}
QPushButton:pressed {{ background: {c['soft']}; }}
QPushButton#primary {{ background: {c['accent']}; border: 1px solid {c['accent']}; color: white; padding: 10px 26px; }}
QPushButton#primary:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; color: white; }}
QPushButton#primary:pressed {{ background: {c['accent_press']}; }}
QPushButton#primary:disabled {{ background: {c['disabled']}; border-color: {c['disabled']}; color: #FFFFFF; }}
QPushButton#big {{ font-size: 17px; padding: 14px 40px; border-radius: 14px; }}
QPushButton#link {{ border: none; background: transparent; color: {c['accent']}; padding: 4px 6px; font-weight: 600; }}
QPushButton#link:hover {{ color: {c['accent_hover']}; text-decoration: underline; }}

QPushButton#pill {{
    border-radius: 16px; padding: 6px 16px; font-weight: 600; font-size: 14px;
    background: transparent; border: 1px solid {c['line_strong']}; color: {c['muted']};
}}
QPushButton#pill:hover {{ color: {c['accent']}; border-color: {c['accent']}; }}
QPushButton#pill:checked {{ background: {c['accent']}; border-color: {c['accent']}; color: white; }}

QLineEdit#search {{
    background: {c['card']}; border: 1px solid {c['line']}; border-radius: 12px;
    padding: 10px 14px 10px 40px; font-size: 15px; selection-background-color: {c['soft']};
}}
QLineEdit#search:focus {{ border: 1px solid {c['accent']}; }}

QFrame#tile {{ background: {c['card']}; border: 1px solid {c['line']}; border-radius: 14px; }}
QFrame#tile:hover {{ border: 1px solid {c['line_strong']}; background: #FFFDF9; }}
QFrame#tile[selected="true"] {{ background: {c['soft']}; border: 2px solid {c['accent']}; }}
QFrame#tile QLabel {{ background: transparent; font-size: 13px; }}
QFrame#tile[selected="true"] QLabel {{ color: {c['soft_text']}; font-weight: 600; }}

QFrame#panel {{ background: {c['card']}; border: 1px solid {c['line']}; border-radius: 16px; }}
QFrame#panel QLabel {{ background: transparent; }}
QFrame#note {{ background: {c['bar']}; border-radius: 12px; }}
QFrame#note QLabel {{ background: transparent; color: {c['muted']}; font-size: 12px; }}

QFrame#chip {{ background: {c['soft']}; border-radius: 13px; }}
QFrame#chip QLabel {{ background: transparent; color: {c['soft_text']}; font-size: 13px; font-weight: 600; }}
QToolButton#chipX {{ border: none; background: transparent; color: {c['soft_text']}; font-size: 15px; font-weight: 700; padding: 0 2px; }}
QToolButton#chipX:hover {{ color: {c['accent']}; }}

QFrame#mealCard {{ background: {c['card']}; border: 1px solid {c['line']}; border-radius: 20px; }}
QFrame#mealCard:hover {{ border: 1px solid {c['accent']}; }}
QFrame#mealCard[selected="true"] {{ background: {c['soft']}; border: 2px solid {c['accent']}; }}
QFrame#mealCard QLabel {{ background: transparent; }}
QFrame#mealCard[selected="true"] QLabel {{ color: {c['soft_text']}; }}

QFrame#result {{ background: {c['card']}; border: 1px solid {c['line']}; border-radius: 18px; }}
QFrame#result:hover {{ border: 1px solid {c['line_strong']}; }}
QFrame#result[selected="true"] {{ border: 2px solid {c['accent']}; background: #FFFBF8; }}
QFrame#result QLabel {{ background: transparent; }}
QLabel#dishName {{ font-family: "{SERIF}"; font-size: 18px; font-weight: 600; }}
QLabel#percent {{ font-family: "{SERIF}"; font-size: 26px; font-weight: 600; color: {c['accent']}; }}
QLabel#okText {{ color: {c['green']}; font-size: 13px; font-weight: 600; }}
QLabel#missText {{ color: {c['muted']}; font-size: 13px; }}
QLabel#number {{ background: {c['bar']}; color: {c['muted']}; border-radius: 12px; font-size: 12px; font-weight: 700; }}

QFrame#metaChip {{ background: {c['bar']}; border-radius: 12px; }}
QFrame#metaChip QLabel {{ background: transparent; font-size: 13px; font-weight: 600; color: {c['text']}; }}

QFrame#ingRow {{ background: transparent; border-bottom: 1px solid {c['line']}; }}
QFrame#ingRow QLabel {{ background: transparent; font-size: 14px; }}
QFrame#ingRow QLabel#statusHave, QLabel#statusHave {{ background: {c['green_soft']}; color: {c['green']}; border-radius: 10px; padding: 3px 10px; font-size: 12px; font-weight: 700; }}
QFrame#ingRow QLabel#statusBuy, QLabel#statusBuy {{ background: {c['soft']}; color: {c['soft_text']}; border-radius: 10px; padding: 3px 10px; font-size: 12px; font-weight: 700; }}
QFrame#ingRow QLabel#statusBasic, QLabel#statusBasic {{ background: {c['bar']}; color: {c['muted']}; border-radius: 10px; padding: 3px 10px; font-size: 12px; font-weight: 700; }}
QLabel#stepNum {{ background: {c['accent']}; color: white; border-radius: 15px; font-weight: 700; font-size: 14px; }}
QLabel#stepText2 {{ font-size: 15px; }}

QFrame#toast {{ background: {c['text']}; border-radius: 12px; }}
QFrame#toast QLabel {{ color: white; background: transparent; font-size: 14px; font-weight: 600; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {c['line_strong']}; border-radius: 4px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ height: 0; background: none; }}
QScrollBar:horizontal {{ height: 0; }}
QToolTip {{ background: {c['text']}; color: white; border: none; padding: 6px 8px; border-radius: 6px; }}
QMessageBox {{ background: {c['bg']}; }}
"""
