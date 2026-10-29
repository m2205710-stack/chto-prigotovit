"""Рецепты. Каждый файл модуля добавляет рецепты через функцию R().

R(название, приёмы_пищи, минут, сложность, порций, ингредиенты, шаги, фото)
  приёмы_пищи — буквы: З завтрак, О обед, У ужин, П перекус, Д десерт
  ингредиенты — (продукт, количество[, уточнение]); количество None = «по вкусу»
"""
import importlib
import pkgutil
import sys

MEALS = {"З": "Завтрак", "О": "Обед", "У": "Ужин", "П": "Перекус", "Д": "Десерт"}
RECIPES = []


def R(name, meals, minutes, difficulty, servings, ingredients, steps, photo=""):
    RECIPES.append(dict(
        name=name,
        meals=[MEALS[m] for m in meals],
        minutes=minutes,
        difficulty=difficulty,
        servings=servings,
        ingredients=[(i[0], i[1], i[2] if len(i) > 2 else "") for i in ingredients],
        steps=steps,
        photo=photo,
    ))


def load_all():
    RECIPES.clear()
    for m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        full = f"{__name__}.{m.name}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            importlib.import_module(full)
    return RECIPES
