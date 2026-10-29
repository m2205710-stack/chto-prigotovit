"""Проверки требований ТЗ v1.1 на настоящей базе данных.
Запуск: python tests/test_tz.py   (или python -m pytest tests)"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core.matcher import MAX_RESULTS, match_recipes, shopping_list, with_substitutes  # noqa: E402
from core.models import MEAL_TYPES                                    # noqa: E402
from core.repository import Repository                                # noqa: E402

repo = Repository(os.path.join(ROOT, "assets", "cookbook.db"))
P = {p.name: p.id for p in repo.products.values()}
R = {r.name: r for r in repo.recipes}


def ids(*names):
    return {P[n] for n in names}


def test_control_example():
    """П. 3.4.2: «Макароны с овощами» — N = 4, K = 3, S = 75 %, не хватает сыра."""
    res = match_recipes(repo.recipes, ids("Макароны", "Помидоры", "Огурцы"), "Обед")
    m = next(r for r in res if r.recipe.name == "Макароны с овощами")
    assert (m.total, m.have, m.percent) == (4, 3, 75)
    assert [i.product.name for i in m.missing] == ["Сыр твёрдый"]


def test_threshold_limit_sort():
    """П. 3.4.1: только ≥ 50 %, не больше 10, сортировка по убыванию соответствия."""
    for meal in MEAL_TYPES:
        sel = ids("Яйца куриные", "Молоко", "Мука пшеничная", "Помидоры", "Картофель", "Куриное филе", "Сметана")
        res = match_recipes(repo.recipes, sel, meal)
        assert len(res) <= MAX_RESULTS
        assert all(r.percent >= 50 for r in res)
        assert all(meal in r.recipe.meal_types for r in res)
        keys = [(-r.percent, len(r.missing), r.recipe.cook_time) for r in res]
        assert keys == sorted(keys)


def test_basic_products_ignored():
    """П. 3.2.4: базовые продукты не влияют на соответствие и не попадают в список покупок."""
    r = R["Салат из свежих овощей"]
    assert {i.product.name for i in r.main_ingredients} == {"Помидоры", "Огурцы", "Укроп"}
    items = shopping_list([r], set())
    assert not any(i.product.is_basic for i in items)


def test_shopping_list_merges():
    """П. 3.7: одинаковые продукты из разных блюд — одна позиция с суммой количества."""
    a, b = R["Омлет классический"], R["Яичница с помидорами"]
    items = {i.product.name: i for i in shopping_list([a, b], set())}
    assert items["Яйца куриные"].amount == 3 + 2
    assert items["Масло сливочное"].amount == 10 + 10
    items = {i.product.name for i in shopping_list([a, b], ids("Яйца куриные"))}
    assert "Яйца куриные" not in items


def test_no_results():
    """BR-010: при отсутствии подходящих блюд список пуст (экран предлагает изменить параметры)."""
    assert match_recipes(repo.recipes, ids("Кинза"), "Десерт") == []


def test_data_requirements():
    """П. 5.2: объём и полнота базы."""
    assert len(repo.selectable_products) >= 80
    assert len(repo.recipes) >= 50
    assert len({r.name for r in repo.recipes}) == len(repo.recipes), "названия блюд не повторяются"
    for meal in MEAL_TYPES:
        assert sum(meal in r.meal_types for r in repo.recipes) >= 8, meal
    for r in repo.recipes:
        assert r.name and r.cook_time > 0 and r.difficulty in ("легко", "средне", "сложно")
        assert r.servings > 0 and r.steps and r.main_ingredients, r.name
    icons = [p.icon for p in repo.products.values()]
    assert len(icons) == len(set(icons)), "у каждого продукта свой значок"


def test_substitutes():
    """П. 3.4.1: взаимозаменяемые продукты — батон подходит вместо белого хлеба."""
    own = with_substitutes(ids("Батон", "Копчёная колбаса"), repo.products)
    res = match_recipes(repo.recipes, own, "Перекус")
    assert any(r.recipe.name == "Бутерброд с колбасой и сыром" for r in res)
    items = {i.product.name for i in shopping_list([R["Бутерброд с колбасой и сыром"]], own)}
    assert "Хлеб белый" not in items and "Варёная колбаса" not in items


def test_multi_meal():
    """BR-002: одно блюдо может относиться к нескольким приёмам пищи."""
    assert R["Драники"].meal_types == ["Завтрак", "Обед", "Ужин"]
    assert R["Омлет классический"].meal_types == ["Завтрак"]
    for r in repo.recipes:     # омлеты и яичницы — только на завтрак
        if "омлет" in r.name.lower() or "яичниц" in r.name.lower():
            assert "Ужин" not in r.meal_types, r.name


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            n += 1
            print("✓", fn.__doc__.strip().splitlines()[0])
    print(f"\nВсе проверки пройдены: {n}")
