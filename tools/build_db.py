"""Собирает базу данных assets/cookbook.db из справочников data/.

Запуск: python tools/build_db.py
Проверяет, что все ингредиенты рецептов есть в справочнике продуктов.
"""
import os
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from data import products as P          # noqa: E402
from data import recipes as RC          # noqa: E402
from core.models import MEAL_TYPES      # noqa: E402

DB = os.path.join(ROOT, "assets", "cookbook.db")

SCHEMA = """
CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, position INTEGER NOT NULL);
CREATE TABLE products (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    unit TEXT NOT NULL, icon TEXT NOT NULL, is_basic INTEGER NOT NULL DEFAULT 0,
    subst_group INTEGER);
CREATE TABLE meal_types (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE recipes (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, cook_time INTEGER NOT NULL,
    difficulty TEXT NOT NULL, servings INTEGER NOT NULL, steps TEXT NOT NULL, image TEXT);
CREATE TABLE recipe_meal_types (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    meal_type_id INTEGER NOT NULL REFERENCES meal_types(id),
    PRIMARY KEY (recipe_id, meal_type_id));
CREATE TABLE recipe_ingredients (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    amount REAL, note TEXT, position INTEGER NOT NULL,
    PRIMARY KEY (recipe_id, product_id));
"""


def snake(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def build(path=DB, verbose=True):
    recipes = RC.load_all()
    errors = []
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    cat_ids = {}
    for pos, c in enumerate(P.CATEGORIES + ["Базовые продукты"]):
        cat_ids[c] = con.execute("INSERT INTO categories(name, position) VALUES (?, ?)", (c, pos)).lastrowid
    prod = {}
    rows = [(c, p, False) for c, ps in P.PRODUCTS.items() for p in ps]
    rows += [("Базовые продукты", p, True) for p in P.BASIC]
    for cat, (name, unit, icon), basic in rows:
        if name in prod:
            errors.append(f"Продукт повторяется: {name}")
            continue
        icon = snake(icon)
        if not os.path.exists(os.path.join(ROOT, "assets", "icons", icon + ".png")):
            errors.append(f"Нет значка {icon} для «{name}»")
        prod[name] = con.execute(
            "INSERT INTO products(name, category_id, unit, icon, is_basic) VALUES (?,?,?,?,?)",
            (name, cat_ids[cat], unit, icon, int(basic))).lastrowid
    for g, names in enumerate(P.SUBSTITUTES, 1):
        for n in names:
            if n not in prod:
                errors.append(f"Группа замены: нет продукта «{n}»")
            con.execute("UPDATE products SET subst_group = ? WHERE name = ?", (g, n))
    meal_ids = {m: con.execute("INSERT INTO meal_types(name) VALUES (?)", (m,)).lastrowid for m in MEAL_TYPES}
    names = set()
    for r in recipes:
        if r["name"] in names:
            errors.append(f"Рецепт повторяется: {r['name']}")
            continue
        names.add(r["name"])
        rid = con.execute(
            "INSERT INTO recipes(name, cook_time, difficulty, servings, steps, image) VALUES (?,?,?,?,?,?)",
            (r["name"], r["minutes"], r["difficulty"], r["servings"], "\n".join(r["steps"]), r["photo"])).lastrowid
        for m in r["meals"]:
            con.execute("INSERT INTO recipe_meal_types VALUES (?,?)", (rid, meal_ids[m]))
        seen = set()
        for pos, (pname, amount, note) in enumerate(r["ingredients"]):
            if pname not in prod:
                errors.append(f"«{r['name']}»: нет продукта «{pname}» в справочнике")
                continue
            if pname in seen:
                errors.append(f"«{r['name']}»: продукт «{pname}» указан дважды")
                continue
            seen.add(pname)
            con.execute("INSERT INTO recipe_ingredients VALUES (?,?,?,?,?)",
                        (rid, prod[pname], amount, note, pos))
        basic_names = {p[0] for p in P.BASIC}
        if all(pn in basic_names for (pn, _, _) in r["ingredients"]):
            errors.append(f"«{r['name']}»: нет ни одного небазового ингредиента")
    con.commit()
    con.close()
    if verbose:
        counts = {m: sum(m in r["meals"] for r in recipes) for m in MEAL_TYPES}
        print(f"Продуктов: {len(prod)}, рецептов: {len(names)}; по приёмам пищи: {counts}")
        for e in errors:
            print("ОШИБКА:", e)
    return errors


if __name__ == "__main__":
    sys.exit(1 if build() else 0)
