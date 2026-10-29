from dataclasses import dataclass, field

MEAL_TYPES = ["Завтрак", "Обед", "Ужин", "Перекус", "Десерт"]


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category: str
    unit: str
    icon: str
    is_basic: bool
    group: int | None = None   # группа взаимозаменяемых продуктов


@dataclass(frozen=True)
class Ingredient:
    product: Product
    amount: float | None   # None — «по вкусу», количество в note
    note: str = ""


@dataclass
class Recipe:
    id: int
    name: str
    cook_time: int          # минуты
    difficulty: str         # легко / средне / сложно
    servings: int
    steps: list[str]
    image: str
    meal_types: list[str]
    ingredients: list[Ingredient] = field(default_factory=list)

    @property
    def main_ingredients(self) -> list[Ingredient]:
        """Ингредиенты без базовых продуктов — по ним считается соответствие."""
        return [i for i in self.ingredients if not i.product.is_basic]


@dataclass
class MatchResult:
    recipe: Recipe
    total: int              # N — небазовых ингредиентов
    have: int               # K — из них есть у пользователя
    missing: list[Ingredient]

    @property
    def percent(self) -> int:
        return round(self.have / self.total * 100) if self.total else 100


@dataclass
class ShoppingItem:
    product: Product
    amount: float | None
    notes: list[str] = field(default_factory=list)


_FRACTIONS = {0.25: "¼", 0.5: "½", 0.75: "¾"}


def fmt_amount(value: float | None) -> str:
    if value is None:
        return ""
    whole = int(value)
    frac = round(value - whole, 2)
    if frac == 0:
        return str(whole)
    if frac in _FRACTIONS:
        return (str(whole) if whole else "") + _FRACTIONS[frac]
    return f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def fmt_quantity(amount: float | None, unit: str, note: str = "") -> str:
    """«400 г», «½ шт.», «щепотка», «40 г (2 ст. л.)»."""
    if amount is None:
        return note or "по вкусу"
    text = f"{fmt_amount(amount)} {unit}"
    return f"{text} ({note})" if note else text
