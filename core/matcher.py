"""Алгоритм подбора блюд (п. 3.4.1 ТЗ) и формирование списка покупок (п. 3.7 ТЗ).

Модуль не зависит от интерфейса и базы данных — работает с моделями.
"""
from collections import OrderedDict

from .models import MatchResult, Recipe, ShoppingItem

MIN_PERCENT = 50
MAX_RESULTS = 10


def with_substitutes(selected: set[int], products) -> set[int]:
    """Набор продуктов пользователя вместе с их заменами из той же группы.
    products — словарь id -> Product (repository.products)."""
    groups = {products[i].group for i in selected if i in products and products[i].group}
    return set(selected) | {p.id for p in products.values() if p.group in groups}


def match_recipes(recipes: list[Recipe], selected: set[int], meal_type: str,
                  min_percent: int = MIN_PERCENT, limit: int = MAX_RESULTS) -> list[MatchResult]:
    results = []
    for r in recipes:
        if meal_type not in r.meal_types:                       # шаг 1
            continue
        main = r.main_ingredients                               # шаг 2
        if not main:
            continue
        have = [i for i in main if i.product.id in selected]    # шаг 3
        missing = [i for i in main if i.product.id not in selected]
        res = MatchResult(r, len(main), len(have), missing)     # шаг 4
        if res.percent >= min_percent:                          # шаг 5
            results.append(res)
    results.sort(key=lambda m: (-m.percent, len(m.missing), m.recipe.cook_time, m.recipe.name))  # шаг 6
    return results[:limit]                                      # шаг 7


def shopping_list(recipes: list[Recipe], selected: set[int],
                  category_order: list[str] | None = None) -> list[ShoppingItem]:
    """Единый список недостающих продуктов; одинаковые продукты суммируются."""
    items: "OrderedDict[int, ShoppingItem]" = OrderedDict()
    for r in recipes:
        for ing in r.main_ingredients:
            p = ing.product
            if p.id in selected:
                continue
            item = items.get(p.id)
            if item is None:
                item = items[p.id] = ShoppingItem(p, None)
            if ing.amount is not None:
                item.amount = (item.amount or 0) + ing.amount
            elif ing.note and ing.note not in item.notes:
                item.notes.append(ing.note)
    order = {c: n for n, c in enumerate(category_order or [])}
    return sorted(items.values(),
                  key=lambda i: (order.get(i.product.category, 99), i.product.category, i.product.name))
