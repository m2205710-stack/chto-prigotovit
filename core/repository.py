"""Чтение базы данных SQLite в модели приложения."""
import sqlite3

from .models import Ingredient, Product, Recipe


class DatabaseError(Exception):
    pass


class Repository:
    def __init__(self, path: str):
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            self._load(con)
            con.close()
        except sqlite3.Error as e:
            raise DatabaseError(f"Не удалось открыть базу данных: {e}") from e
        if not self.recipes or not self.products:
            raise DatabaseError("База данных пуста")

    def _load(self, con):
        self.categories = [r[0] for r in con.execute(
            "SELECT name FROM categories WHERE name <> 'Базовые продукты' ORDER BY position")]
        self.products: dict[int, Product] = {}
        for pid, name, cat, unit, icon, basic, group in con.execute(
                "SELECT p.id, p.name, c.name, p.unit, p.icon, p.is_basic, p.subst_group "
                "FROM products p JOIN categories c ON c.id = p.category_id ORDER BY c.position, p.id"):
            self.products[pid] = Product(pid, name, cat, unit, icon, bool(basic), group)
        meals: dict[int, list[str]] = {}
        for rid, m in con.execute(
                "SELECT rm.recipe_id, m.name FROM recipe_meal_types rm "
                "JOIN meal_types m ON m.id = rm.meal_type_id ORDER BY m.id"):
            meals.setdefault(rid, []).append(m)
        ings: dict[int, list[Ingredient]] = {}
        for rid, pid, amount, note in con.execute(
                "SELECT recipe_id, product_id, amount, note FROM recipe_ingredients ORDER BY recipe_id, position"):
            ings.setdefault(rid, []).append(Ingredient(self.products[pid], amount, note or ""))
        self.recipes: list[Recipe] = []
        for rid, name, t, d, s, steps, image in con.execute(
                "SELECT id, name, cook_time, difficulty, servings, steps, image FROM recipes ORDER BY id"):
            self.recipes.append(Recipe(rid, name, t, d, s, steps.split("\n"), image or "",
                                       meals.get(rid, []), ings.get(rid, [])))

    @property
    def selectable_products(self) -> list[Product]:
        return [p for p in self.products.values() if not p.is_basic]

    @property
    def basic_products(self) -> list[Product]:
        return [p for p in self.products.values() if p.is_basic]
