"""Рисует картинки-стикеры блюд в стиле значков продуктов (Microsoft Fluent Emoji 3D, лицензия MIT).

У каждого блюда: тарелка с главным объёмным значком блюда и 2–4 значка основных продуктов вокруг.
Фон — свой тёплый цвет для каждого раздела (завтраки, супы, вторые, салаты, перекусы, десерты).
Результат — assets/dish_art/<slug>.jpg (760×540, для экрана рецепта и карточек подбора).

Запуск: python tools/make_dish_art.py [slug ...]   (без параметров — все блюда)
"""
import importlib
import os
import pkgutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import make_icons as MI                   # noqa: E402
from data import recipes as RC            # noqa: E402

OUT = os.path.join(ROOT, "assets", "dish_art")
W, HGT = 760, 540

# раздел -> (цвет сверху, цвет снизу)
PALETTE = {
    "r1_zavtraki": ("#FCF0D2", "#F6DDB0"),
    "r2_supy": ("#FBE3D3", "#F3C9B0"),
    "r3_vtorye": ("#F8E1D6", "#EDC4B3"),
    "r4_salaty": ("#EAF1DA", "#D5E4BC"),
    "r5_perekusy": ("#FBEBD6", "#F2D3AE"),
    "r6_deserty": ("#FBE5EA", "#F2C9D3"),
    "r7_zavtraki2": ("#FCF0D2", "#F6DDB0"),
    "r8_supy2": ("#FBE3D3", "#F3C9B0"),
    "r9_vtorye2": ("#F8E1D6", "#EDC4B3"),
    "s1_salaty2": ("#EAF1DA", "#D5E4BC"),
    "s2_perekusy2": ("#FBEBD6", "#F2D3AE"),
    "s3_deserty2": ("#FBE5EA", "#F2C9D3"),
}

# Части основ, которые можно перекрашивать (диапазоны тона в градусах, см. make_icons.region)
BASE_MASKS = {
    "cooked_rice": {"heap": dict(s=(0, 60), v=(150, 256)), "bowl": dict(hue=(320, 30), s=(120, 256))},
    "steaming_bowl": {"bowl": dict(hue=(300, 12), s=(100, 256))},
    "tumbler_glass": {"drink": dict(hue=(15, 65), s=(60, 256))},
    "poultry_leg": {"meat": dict(hue=(355, 42), s=(60, 256))},
    "doughnut": {"icing": dict(hue=(290, 355), s=(60, 256)), "dough": dict(hue=(0, 45), s=(60, 256)),
                 "all": dict(s=(40, 256))},
    "rice_cracker": {"cracker": dict(hue=(15, 45), s=(60, 256)), "nori": dict(hue=(200, 300), s=(20, 256))},
    "pot_of_food": {"soup": dict(hue=(10, 42), s=(110, 256), v=(150, 256), box=(0.15, 0.1, 0.85, 0.62))},
    "bowl_with_spoon": {"inside": dict(hue=(228, 275), s=(60, 256)), "bowl": dict(hue=(190, 228), s=(60, 256))},
    "spaghetti": {"sauce": dict(hue=(320, 20), s=(50, 256), box=(0.2, 0.3, 0.8, 0.75)),
                  "balls": dict(hue=(345, 35), s=(40, 256), v=(0, 190), box=(0.3, 0.42, 0.72, 0.68))},
    "green_salad": {"leaves": dict(hue=(80, 160), s=(60, 256))},
    "shallow_pan_of_food": {"food": dict(hue=(40, 65), s=(80, 256), v=(150, 256))},
    "pancakes": {"cake": dict(hue=(18, 45), s=(60, 256), v=(150, 256))},
    "falafel": {"ball": dict(hue=(340, 40), s=(30, 256))},
    "curry_rice": {"curry": dict(hue=(10, 40), s=(110, 256), v=(150, 256))},
    "cooking": {"white": dict(s=(0, 40), v=(200, 256), box=(0.2, 0.2, 0.75, 0.7))},
    "pie": {"crust": dict(hue=(15, 50), s=(50, 256))},
    "birthday_cake": {"body": dict(hue=(15, 45), s=(60, 256), box=(0, 0.45, 1, 1))},
    "shortcake": {"sponge": dict(hue=(15, 45), s=(70, 256))},
    "bread": {"crust": dict(hue=(15, 50), s=(40, 256))},
    "french_fries": {"fries": dict(hue=(40, 65), s=(80, 256)), "box": dict(hue=(320, 20), s=(100, 256))},
    "flatbread": {"bread": dict(hue=(0, 50), s=(20, 256))},
    "custard": {"top": dict(hue=(10, 45), s=(40, 256), v=(0, 140)), "body": dict(hue=(15, 45), s=(60, 256), v=(140, 256))},
}
CERAMIC = "#EFE8DF"


def H(base, tint=None, top=None, inside=None, grain=None):
    """Главная картинка: основа, перекраска частей {часть: цвет}, добавка сверху,
    продукты внутри миски и зернистость поверхности (для каш)."""
    return (base, tuple(sorted((tint or {}).items())), top, tuple(inside or ()), grain)


SOUP, IN, SAUCE, LEAF, FOOD, CAKE, BALL, CURRY = "soup", "inside", "sauce", "leaves", "food", "cake", "ball", "curry"

# slug -> (главная картинка, [значки продуктов вокруг])
SPEC = {
    # завтраки
    "omlet": (H("cooking", {"white": "#F5D667"}), ["egg", "glass_of_milk", "butter"]),
    "omlet_ovoshchi": (H("cooking", {"white": "#F5D667"}, "bell_pepper"), ["tomato", "bell_pepper", "green_onion"]),
    "yaichnica_pomidory": (H("cooking", None, "tomato"), ["tomato", "egg"]),
    "shakshuka": (H("shallow_pan_of_food", {FOOD: "#D9452F"}, "egg"), ["tomato", "egg", "bell_pepper"]),
    "syrniki": (H("pancakes", {CAKE: "#F0C98A"}, "sour_cream"), ["cottage_cheese", "egg", "flour_pack"]),
    "zapekanka": (H("pie", {"crust": "#F2D9A0"}, "raisins"), ["cottage_cheese", "sour_cream", "egg"]),
    "lenivye_vareniki": (H("dumpling", None, "sour_cream"), ["cottage_cheese", "sour_cream", "butter"]),
    "ovsyanka": (H("cooked_rice", {"heap": "#D9BE8C", "bowl": "#7FA9D9"}, None, ["blueberries", "strawberry"], "#B8935C"), ["oats", "glass_of_milk", "butter"]),
    "mannaya_kasha": (H("cooked_rice", {"heap": "#F3EBD9", "bowl": "#E9A23A"}, None, ["butter", "frozen_berries"], "#E2D3B4"), ["semolina_pack", "glass_of_milk", "butter"]),
    "risovaya_kasha": (H("cooked_rice", {"heap": "#F5F0E6", "bowl": "#8DBF5A"}, None, ["raisins", "butter"], None), ["cooked_rice", "glass_of_milk", "butter"]),
    "pshennaya_kasha": (H("cooked_rice", {"heap": "#F2C443", "bowl": "#3E78C2"}, None, ["pumpkin", "butter"], "#D9A42A"), ["millet", "pumpkin", "glass_of_milk"]),
    "grechka_moloko": (H("cooked_rice", {"heap": "#8A5A36", "bowl": CERAMIC}, "glass_of_milk", ["butter"], "#5E3A20"), ["buckwheat", "glass_of_milk", "butter"]),
    "bliny": (H("flatbread", None, "sour_cream"), ["glass_of_milk", "egg", "flour_pack"]),
    "oladi": (H("pancakes", {CAKE: "#E3A55A"}, "honey_pot"), ["kefir", "egg", "flour_pack"]),
    "pankeyki": (H("pancakes", None, "blueberries"), ["glass_of_milk", "egg", "butter"]),
    "draniki": (H("pancakes", {CAKE: "#9E5B2A"}, "potato"), ["potato", "onion", "sour_cream"]),
    "grenki_sladkie": (H("bread", {"crust": "#E8B06A"}, "cinnamon"), ["egg", "glass_of_milk", "cinnamon"]),
    "buterbrody_goryachie": (H("sandwich", None, "cheese_wedge"), ["cheese_wedge", "tomato", "baguette_bread"]),
    "tost_avokado": (H("toast_bread", None, "avocado"), ["avocado", "egg", "lemon"]),
    "ovsyanoblin": (H("flatbread", {"bread": "#E3C88E"}, "cheese_wedge"), ["oats", "egg", "cheese_wedge"]),
    "tvorog_yagody": (H("cottage_cheese", None, "strawberry"), ["strawberry", "sour_cream", "honey_pot"]),
    "smuzi_banan": (H("cup_with_straw", None, "banana"), ["banana", "glass_of_milk", "oats"]),
    # супы
    "borshch": (H("pot_of_food", {SOUP: "#B52A3F"}, "dill"), ["beet", "cabbage", "carrot"]),
    "shchi": (H("pot_of_food", {SOUP: "#D9C77A"}, "cabbage"), ["cabbage", "potato", "carrot"]),
    "sup_lapsha": (H("steaming_bowl", None, "chicken_thigh"), ["chicken_thigh", "carrot", "parsley"]),
    "gorohovyy_sup": (H("pot_of_food", {SOUP: "#C9B23E"}, "meat_on_bone"), ["split_peas_pack", "meat_on_bone", "potato"]),
    "sup_frikadelki": (H("pot_of_food", {SOUP: "#E8C46A"}, "falafel"), ["meat_mince", "potato", "dill"]),
    "solyanka": (H("pot_of_food", {SOUP: "#D2552E"}, "lemon"), ["salami", "pickles", "olive", "lemon"]),
    "rassolnik": (H("pot_of_food", {SOUP: "#CFC08A"}, "pickles"), ["pickles", "barley_pack", "potato"]),
    "uha": (H("pot_of_food", {SOUP: "#E9B949"}, "fish"), ["white_fish", "potato", "dill"]),
    "gribnoy_sup": (H("pot_of_food", {SOUP: "#C8A57A"}, "brown_mushroom"), ["brown_mushroom", "potato", "onion"]),
    "syrnyy_sup": (H("pot_of_food", {SOUP: "#F0D27A"}, "processed_cheese"), ["processed_cheese", "chicken_fillet", "potato"]),
    "tykvennyy_sup": (H("pot_of_food", {SOUP: "#F08A1E"}, "pumpkin"), ["pumpkin", "cream_20", "carrot"]),
    "sup_brokkoli": (H("pot_of_food", {SOUP: "#8DBF5A"}, "broccoli"), ["broccoli", "cream_20", "potato"]),
    "harcho": (H("pot_of_food", {SOUP: "#A0442A"}, "cilantro"), ["cut_of_meat", "cooked_rice", "chestnut"]),
    "fasolevyy_sup": (H("pot_of_food", {SOUP: "#D97845"}, "beans"), ["beans", "potato", "carrot"]),
    "chechevichnyy_sup": (H("pot_of_food", {SOUP: "#E8A030"}, "parsley"), ["lentils_pack", "carrot", "lemon"]),
    "okroshka": (H("cooked_rice", {"heap": "#F4F1EA", "bowl": "#5E9E5A"}, None, ["cucumber", "radish", "dill"]), ["cucumber", "radish", "egg", "kefir"]),
    # вторые блюда
    "kurica_makarony_ovoshchi": (H("spaghetti", {SAUCE: "#E04A3A"}, "chicken_fillet"), ["chicken_fillet", "tomato", "bell_pepper"]),
    "makarony_ovoshchi": (H("spaghetti", {"balls": "erase", SAUCE: "#F2E3B8"}, "cucumber"), ["tomato", "cucumber", "cheese_wedge"]),
    "makarony_syr": (H("spaghetti", {"balls": "erase", SAUCE: "#F2B83A"}, "cheese_wedge"), ["cheese_wedge", "butter"]),
    "kurica_duhovka": (H("poultry_leg", None, "garlic"), ["garlic", "paprika"]),
    "kurica_kartofel": (H("poultry_leg", None, "potato"), ["potato", "onion", "garlic"]),
    "kurica_smetana": (H("shallow_pan_of_food", {FOOD: "#F1E3C2"}, "dill"), ["chicken_fillet", "sour_cream", "dill"]),
    "otbivnye": (H("shallow_pan_of_food", {FOOD: "#E0A54A"}, "chicken_fillet"), ["chicken_fillet", "egg", "flour_pack"]),
    "teriyaki": (H("curry_rice", {CURRY: "#7A3A22"}, "sesame"), ["chicken_thigh", "soy_sauce", "sesame"]),
    "pechen_smetana": (H("shallow_pan_of_food", {FOOD: "#7A2E30"}, "onion"), ["chicken_liver", "onion", "sour_cream"]),
    "kotlety": (H("falafel", {BALL: "#8A4A2E"}, "dill"), ["meat_mince", "onion", "white_bread"]),
    "tefteli": (H("falafel", {BALL: "#A34A30"}, "tomato"), ["meat_mince", "cooked_rice", "canned_food"]),
    "makarony_po_flotski": (H("spaghetti", {SAUCE: "#8A4A30"}, "onion"), ["meat_mince", "onion"]),
    "plov": (H("curry_rice", {CURRY: "#E07A2E"}, "carrot"), ["chicken_thigh", "carrot", "garlic"]),
    "grechka_po_kupecheski": (H("shallow_pan_of_food", {FOOD: "#8A5A36"}, "carrot"), ["buckwheat", "pig_face", "carrot"]),
    "grechka_griby": (H("shallow_pan_of_food", {FOOD: "#8A5A36"}, "brown_mushroom"), ["buckwheat", "brown_mushroom", "onion"]),
    "ris_ovoshchi": (H("curry_rice", {CURRY: "#C9B23E"}, "pea_pod"), ["bell_pepper", "ear_of_corn", "pea_pod"]),
    "gulyash": (H("pot_of_food", {SOUP: "#8E3A22"}, "cut_of_meat"), ["cut_of_meat", "onion", "paprika"]),
    "befstroganov": (H("shallow_pan_of_food", {FOOD: "#C9925A"}, "sour_cream"), ["cut_of_meat", "sour_cream", "onion"]),
    "zharkoe": (H("pot_of_food", {SOUP: "#B97A3A"}, "potato"), ["pig_face", "potato", "carrot"]),
    "myaso_po_francuzski": (H("shallow_pan_of_food", {FOOD: "#F2C24A"}, "tomato"), ["pig_face", "cheese_wedge", "tomato"]),
    "golubcy": (H("tamale", None, "cabbage"), ["cabbage", "meat_mince", "cooked_rice"]),
    "lenivye_golubcy": (H("falafel", {BALL: "#A87048"}, "cabbage"), ["cabbage", "meat_mince", "cooked_rice"]),
    "farshirovannye_percy": (H("bell_pepper", None, "meat_mince"), ["meat_mince", "cooked_rice", "tomato"]),
    "kapusta_sosiski": (H("shallow_pan_of_food", {FOOD: "#D9C77A"}, "hot_dog"), ["cabbage", "hot_dog", "carrot"]),
    "ovoshchnoe_ragu": (H("pot_of_food", {SOUP: "#D8742E"}, "zucchini"), ["zucchini", "eggplant", "potato"]),
    "kartoshka_griby": (H("shallow_pan_of_food", {FOOD: "#E6B04A"}, "potato"), ["potato", "brown_mushroom", "onion"]),
    "pyure": (H("cooked_rice", {"heap": "#F3E3B0", "bowl": "#C8553D"}, None, ["butter", "dill"], "#E3CC8E"), ["potato", "glass_of_milk", "butter"]),
    "kartofel_po_derevenski": (H("french_fries", None, "garlic"), ["potato", "garlic", "paprika"]),
    "bolonieze": (H("spaghetti", {SAUCE: "#B8332A"}, "parmesan"), ["meat_mince", "tomato", "parmesan"]),
    "karbonara": (H("spaghetti", {"balls": "erase", SAUCE: "#F4E6C2"}, "bacon"), ["bacon", "egg", "parmesan"]),
    "pasta_kurica_slivki": (H("spaghetti", {"balls": "erase", SAUCE: "#F6EAD2"}, "cream_20"), ["chicken_fillet", "cream_20", "cheese_wedge"]),
    "lazanya": (H("shallow_pan_of_food", {FOOD: "#D9693A"}, "cheese_wedge"), ["lasagna_pack", "meat_mince", "cheese_wedge"]),
    "ryba_ovoshchi": (H("fish", None, "tomato"), ["potato", "tomato", "lemon"]),
    "rybnye_kotlety": (H("falafel", {BALL: "#D8A45A"}, "lemon"), ["white_fish", "onion", "egg"]),
    "mintay": (H("fish", None, "lemon"), ["lemon", "flour_pack"]),
    "losos": (H("salmon", None, "lemon"), ["lemon", "garlic", "parsley"]),
    "pizza": (H("pizza"), ["salami", "mozzarella", "tomato"]),
    "kesadilya": (H("stuffed_flatbread", None, "cheese_wedge"), ["chicken_fillet", "cheese_wedge", "bell_pepper"]),
    "shaurma": (H("burrito", None, "cabbage"), ["chicken_fillet", "cabbage", "tomato"]),
    "oladi_kabachok": (H("pancakes", {CAKE: "#C8C06A"}, "zucchini"), ["zucchini", "egg", "dill"]),
    # салаты
    "salat_ovoshchi": (H("green_salad", None, "cucumber"), ["tomato", "cucumber", "dill"]),
    "grecheskiy": (H("green_salad", None, "feta"), ["tomato", "cucumber", "olive", "feta"]),
    "cezar": (H("green_salad", {LEAF: "#A8C96A"}, "chicken_fillet"), ["chicken_fillet", "lettuce", "parmesan"]),
    "olivie": (H("green_salad", {LEAF: "#EFE2B4"}, "pea_pod"), ["potato", "pea_pod", "egg", "boiled_sausage"]),
    "vinegret": (H("green_salad", {LEAF: "#A8304A"}, "pickles"), ["beet", "potato", "pickles"]),
    "krabovyy": (H("green_salad", {LEAF: "#F1E6C8"}, "crab"), ["crab", "ear_of_corn", "egg"]),
    "mimoza": (H("green_salad", {LEAF: "#F2D25A"}, "fish_can"), ["fish_can", "egg", "potato"]),
    "shuba": (H("green_salad", {LEAF: "#9B2D5A"}, "herring"), ["herring", "beet", "potato"]),
    "vitaminnyy": (H("green_salad", {LEAF: "#CFE3A0"}, "carrot"), ["cabbage", "carrot", "cucumber"]),
    "salat_tunec": (H("green_salad", None, "tuna_can"), ["tuna_can", "egg", "lettuce"]),
    "kapreze": (H("green_salad", None, "mozzarella"), ["tomato", "mozzarella", "herb"]),
    "svekla_chesnok": (H("green_salad", {LEAF: "#8E2140"}, "garlic"), ["beet", "garlic", "mayonnaise"]),
    "morkov_koreyskaya": (H("green_salad", {LEAF: "#F08A2A"}, "korean_spice"), ["carrot", "garlic", "korean_spice"]),
    "salat_kurica_ogurec": (H("green_salad", {LEAF: "#EDE5C9"}, "egg"), ["chicken_fillet", "cucumber", "egg"]),
    # перекусы
    "farshirovannye_yayca": (H("egg", None, "dill"), ["mayonnaise", "dill", "cheese_wedge"]),
    "brusketta": (H("baguette_bread", None, "tomato"), ["tomato", "herb", "garlic"]),
    "rulet_lavash": (H("burrito", None, "lettuce"), ["chicken_fillet", "cucumber", "lettuce"]),
    "sendvich": (H("sandwich", None, "chicken_fillet"), ["chicken_fillet", "tomato", "cheese_wedge"]),
    "humus": (H("cooked_rice", {"heap": "#E3C38E", "bowl": "#9A7FD1"}, None, ["chickpeas", "olive", "parsley"], "#C9A06B"), ["chickpeas", "carrot", "cucumber"]),
    "grenki_chesnok": (H("rye_bread", None, "garlic"), ["garlic", "vegetable_oil"]),
    "yogurt_granola": (H("cooked_rice", {"heap": "#F7F2EA", "bowl": "#F2A7B8"}, None, ["blueberries", "strawberry", "banana"]), ["granola_pack", "banana", "blueberries"]),
    "fruktovyy_salat": (H("cooked_rice", {"heap": "#F6EEE2", "bowl": "#F2C14E"}, None, ["banana", "strawberry", "grapes", "kiwi_fruit"]), ["banana", "kiwi_fruit", "tangerine", "grapes"]),
    "syrnye_palochki": (H("french_fries", {"fries": "#E9B45A", "box": "#3E78C2"}, "mozzarella"), ["mozzarella", "egg", "breadcrumbs"]),
    "pechenye_yabloki": (H("red_apple", None, "cinnamon"), ["honey_pot", "raisins", "cinnamon"]),
    # десерты
    "sharlotka": (H("pie", None, "red_apple"), ["red_apple", "egg", "flour_pack"]),
    "brauni": (H("chocolate_bar"), ["egg", "butter", "cocoa_pack"]),
    "ovsyanoe_pechene": (H("cookie", None, "raisins"), ["oats", "raisins", "butter"]),
    "chizkeyk": (H("shortcake", {"sponge": "#F5E2A8"}, "blueberries"), ["cream_cheese", "cookie", "egg"]),
    "tiramisu": (H("shortcake", {"sponge": "#7A4A2E"}, "hot_beverage"), ["mascarpone", "savoiardi", "hot_beverage"]),
    "panna_kotta": (H("custard", {"body": "#F6EEDF", "top": "#C8304A"}, "frozen_berries"), ["cream_33", "frozen_berries"]),
    "bananovyy_hleb": (H("bread", {"crust": "#B8784A"}, "banana"), ["banana", "chestnut", "egg"]),
    "maffiny": (H("cupcake", None, "chocolate_bar"), ["cocoa_pack", "chocolate_bar", "egg"]),
    "zebra": (H("birthday_cake", {"body": "#8A5A3A"}, "cocoa_pack"), ["cocoa_pack", "sour_cream", "egg"]),
    "keks_v_kruzhke": (H("teacup_without_handle", None, "cocoa_pack"), ["cocoa_pack", "egg", "glass_of_milk"]),
    "pirog_vishnya": (H("pie", {"crust": "#E8B07A"}, "cherries"), ["cherries", "sour_cream", "butter"]),
    "morkovnyy_keks": (H("birthday_cake", {"body": "#E88A3A"}, "carrot"), ["carrot", "chestnut", "cream_cheese"]),
    "muraveynik": (H("birthday_cake", {"body": "#A0683A"}, "chestnut"), ["cookie", "dulce_de_leche", "chestnut"]),
    "blinnyy_tort": (H("pancakes", {CAKE: "#F3D7A6"}, "strawberry"), ["sour_cream", "strawberry", "powdered_sugar"]),
    "kartoshka_pirozhnoe": (H("falafel", {BALL: "#5A3424"}, "cocoa_pack"), ["cookie", "condensed_milk", "cocoa_pack"]),
    "tvorozhnyy_krem": (H("ice_cream", None, "strawberry"), ["cottage_cheese", "strawberry", "cream_33"]),
    "yagodnoe_zhele": (H("custard", {"body": "#D8354F", "top": "#9E1E3A"}, "blueberries"), ["frozen_berries", "gelatin_pack"]),
    "morozhenoe": (H("soft_ice_cream"), ["cream_33", "condensed_milk", "vanilla_sugar"]),
}

# ---------------------------------------------------------------- версия 2: ещё 130 блюд
SPEC.update({
    # завтраки
    "yayca_varenye": (H("boiled_eggs"), ["egg", "toast_bread", "butter"]),
    "yaichnica_kolbasa": (H("cooking", None, "boiled_sausage"), ["egg", "boiled_sausage"]),
    "angliyskiy_zavtrak": (H("bento_box", None, "egg"), ["bacon", "beans", "hot_dog", "tomato"]),
    "kasha_druzhba": (H("cooked_rice", {"heap": "#F3DE9A", "bowl": "#E35D6A"}, None, ["butter"], "#E0B85A"), ["cooked_rice", "millet", "glass_of_milk"]),
    "kukuruznaya_kasha": (H("cooked_rice", {"heap": "#F5C542", "bowl": "#7FA9D9"}, None, ["butter"], "#E0A020"), ["corn_grits_pack", "glass_of_milk", "butter"]),
    "yachnevaya_kasha": (H("cooked_rice", {"heap": "#CDB07A", "bowl": "#B8784A"}, None, ["butter"], "#9E8050"), ["barley_grits", "glass_of_milk", "butter"]),
    "molochnyy_sup_vermishel": (H("steaming_bowl", {"bowl": "#F2E8D8"}, "glass_of_milk"), ["vermicelli_pack", "glass_of_milk", "butter"]),
    "lenivaya_ovsyanka": (H("oat_jar"), ["oats", "yogurt", "blueberries"]),
    "ovsyanaya_zapekanka": (H("pie", {"crust": "#D9BE8C"}, "red_apple"), ["oats", "red_apple", "egg"]),
    "bananovye_oladi": (H("pancakes", {CAKE: "#E8C25A"}, "banana"), ["banana", "egg", "flour_pack"]),
    "hlopya_moloko": (H("cooked_rice", {"heap": "#F0B84A", "bowl": CERAMIC}, "cornflakes_pack", ["banana"], "#C97A1E"), ["cornflakes_pack", "glass_of_milk", "banana"]),
    "lapshevnik": (H("custard", {"body": "#F2D58A", "top": "#C98B4A"}, "raisins"), ["steaming_bowl", "cottage_cheese", "egg"]),
    "sosiski_goroshek": (H("hot_dog", None, "pea_pod"), ["hot_dog", "pea_pod", "butter"]),
    "lavash_yayco": (H("flatbread", {"bread": "#F0D9A8"}, "egg"), ["flatbread", "egg", "cheese_wedge"]),
    "tost_arahis": (H("toast_bread", None, "peanut_butter"), ["peanut_butter", "banana"]),
    # супы
    "kartofelnyy_sup": (H("pot_of_food", {SOUP: "#E6C27A"}, "potato"), ["potato", "carrot", "onion"]),
    "sup_klyocki": (H("pot_of_food", {SOUP: "#F2D88A"}, "dumpling"), ["chicken_thigh", "flour_pack", "egg"]),
    "grechnevyy_sup": (H("pot_of_food", {SOUP: "#C9985A"}, "buckwheat"), ["buckwheat", "potato", "carrot"]),
    "sup_sosiski": (H("pot_of_food", {SOUP: "#E8B85A"}, "hot_dog"), ["hot_dog", "vermicelli_pack", "potato"]),
    "svekolnik": (H("cooked_rice", {"heap": "#E58AA8", "bowl": "#7FA9D9"}, None, ["cucumber", "egg", "dill"]), ["beet", "cucumber", "kefir"]),
    "zelyonyy_borshch": (H("pot_of_food", {SOUP: "#8DAA3A"}, "sorrel"), ["sorrel", "egg", "potato"]),
    "tomatnyy_sup": (H("pot_of_food", {SOUP: "#D9341F"}, "herb"), ["tomatoes_in_juice", "garlic", "cream_20"]),
    "minestrone": (H("pot_of_food", {SOUP: "#C96A3A"}, "spaghetti"), ["zucchini", "beans", "tomato"]),
    "sup_losos": (H("pot_of_food", {SOUP: "#F4E2C2"}, "salmon"), ["salmon", "cream_20", "potato"]),
    "lukovyy_sup": (H("pot_of_food", {SOUP: "#B8783A"}, "onion"), ["onion", "baguette_bread", "cheese_wedge"]),
    "sup_cvetnaya": (H("pot_of_food", {SOUP: "#EFE6C8"}, "cauliflower"), ["cauliflower", "potato", "carrot"]),
    "kukuruznyy_sup": (H("pot_of_food", {SOUP: "#F5C93A"}, "corn_cob"), ["corn_can", "potato", "cream_20"]),
    "gaspacho": (H("tumbler_glass", {"drink": "#D63A2A"}, "cucumber"), ["tomato", "cucumber", "bell_pepper"]),
    # вторые блюда
    "pelmeni": (H("pelmeni_pile", None, "sour_cream"), ["frozen_dumplings", "sour_cream", "dill"]),
    "vareniki_kartoshka": (H("dumpling", None, "potato"), ["potato", "flour_pack", "onion"]),
    "blinchiki_myaso": (H("flatbread", {"bread": "#F2C27A"}, "meat_mince"), ["meat_mince", "glass_of_milk", "egg"]),
    "sosiski_makarony": (H("spaghetti", {"balls": "erase", SAUCE: "#F2D9A0"}, "hot_dog"), ["hot_dog", "pasta_pack", "butter"]),
    "kart_zapekanka_farsh": (H("pie", {"crust": "#E8C25A"}, "meat_mince"), ["potato", "meat_mince", "cheese_wedge"]),
    "varenyy_kartofel": (H("cooked_rice", {"heap": "#F2DB8A", "bowl": CERAMIC}, None, ["potato", "dill"]), ["potato", "butter", "dill"]),
    "gratin": (H("shallow_pan_of_food", {FOOD: "#F5E3B0"}, "cream_20"), ["potato", "cream_20", "cheese_wedge"]),
    "kabachki_zharenye": (H("zucchini", None, "garlic"), ["zucchini", "garlic", "mayonnaise"]),
    "baklazhany_pomidory": (H("eggplant", None, "tomato"), ["eggplant", "tomato", "garlic"]),
    "lecho": (H("pot_of_food", {SOUP: "#E04A2A"}, "bell_pepper"), ["bell_pepper", "tomato", "onion"]),
    "cvetnaya_klyar": (H("cauliflower", None, "egg"), ["cauliflower", "egg", "flour_pack"]),
    "brokkoli_syr": (H("broccoli", None, "cheese_wedge"), ["broccoli", "cheese_wedge", "cream_20"]),
    "kapustnye_kotlety": (H("falafel", {BALL: "#C9C06A"}, "cabbage"), ["cabbage", "egg", "semolina_pack"]),
    "grechaniki": (H("falafel", {BALL: "#6E4A30"}, "buckwheat"), ["buckwheat", "meat_mince", "onion"]),
    "nut_tomaty": (H("shallow_pan_of_food", {FOOD: "#C8502E"}, "chickpeas"), ["chickpeas", "tomatoes_in_juice", "onion"]),
    "chechevica_ovoshchi": (H("shallow_pan_of_food", {FOOD: "#E89A3A"}, "lentils_pack"), ["lentils_pack", "carrot", "bell_pepper"]),
    "lobio": (H("cooked_rice", {"heap": "#8E3A2A", "bowl": "#E9A23A"}, None, ["beans", "cilantro"]), ["beans", "chestnut", "cilantro"]),
    "gorohovoe_pyure": (H("cooked_rice", {"heap": "#E8C84A", "bowl": "#2E8B8B"}, None, ["bacon"]), ["split_peas_pack", "bacon", "onion"]),
    "rizotto": (H("curry_rice", {CURRY: "#E8D8B0"}, "brown_mushroom"), ["cooked_rice", "brown_mushroom", "parmesan"]),
    "lapsha_vok": (H("takeout_box", None, "chicken_fillet"), ["steaming_bowl", "chicken_fillet", "soy_sauce"]),
    "zhyulen": (H("fondue", None, "brown_mushroom"), ["chicken_fillet", "brown_mushroom", "cream_20"]),
    "chahohbili": (H("shallow_pan_of_food", {FOOD: "#C9341F"}, "chicken_thigh"), ["chicken_thigh", "tomato", "cilantro"]),
    "rulety_kurica": (H("burrito", None, "cheese_wedge"), ["chicken_fillet", "cheese_wedge", "garlic"]),
    "krylyshki": (H("chicken_wings", None, "honey_pot"), ["honey_pot", "soy_sauce", "garlic"]),
    "utka_yabloki": (H("poultry_leg", {"meat": "#A8582A"}, "red_apple"), ["duck", "red_apple", "honey_pot"]),
    "holodec": (H("custard", {"body": "#E2D6B8", "top": "#E2D6B8"}, "carrot"), ["poultry_leg", "gelatin_pack", "garlic"]),
    "pechenochnyy_tort": (H("birthday_cake", {"body": "#7A3A2A"}, "chicken_liver"), ["chicken_liver", "carrot", "mayonnaise"]),
    "svinina_kislo_sladkaya": (H("curry_rice", {CURRY: "#D9442A"}, "bell_pepper"), ["pig_face", "bell_pepper", "ketchup"]),
    "rebryshki": (H("pork_ribs", None, "honey_pot"), ["pork_ribs", "honey_pot", "garlic"]),
    "azu": (H("pot_of_food", {SOUP: "#9A4A2A"}, "pickles"), ["cut_of_meat", "pickles", "potato"]),
    "govyadina_brokkoli": (H("takeout_box", None, "broccoli"), ["cut_of_meat", "broccoli", "soy_sauce"]),
    "chili": (H("pot_of_food", {SOUP: "#A8301F"}, "hot_pepper"), ["meat_mince", "beans", "tomatoes_in_juice"]),
    "pirog_kurica": (H("pie", {"crust": "#E0A050"}, "chicken_fillet"), ["chicken_fillet", "potato", "kefir"]),
    "ryba_marinad": (H("fish", None, "carrot"), ["white_fish", "carrot", "onion"]),
    "ryba_polski": (H("fish", None, "egg"), ["white_fish", "egg", "butter"]),
    "skumbriya": (H("mackerel", None, "lemon"), ["mackerel", "lemon", "dill"]),
    "kartoshka_seledka": (H("herring", None, "potato"), ["herring", "potato", "onion"]),
    "kalmary": (H("squid", None, "onion"), ["squid", "onion", "sour_cream"]),
    "krevetki_chesnok": (H("fried_shrimp", None, "garlic"), ["shrimp", "garlic", "lemon"]),
    # салаты
    "ogurcy_smetana": (H("green_salad", {LEAF: "#F4F0E6"}, "cucumber"), ["cucumber", "sour_cream", "dill"]),
    "salat_redis": (H("green_salad", {LEAF: "#F4F0E6"}, "radish"), ["radish", "egg", "green_onion"]),
    "salat_fasol": (H("green_salad", {LEAF: "#B8564A"}, "beans"), ["beans", "white_bread", "corn_can"]),
    "salat_vetchina": (H("green_salad", {LEAF: "#F2E2B8"}, "ham"), ["ham", "cheese_wedge", "cucumber"]),
    "salat_kolbasa": (H("green_salad", {LEAF: "#F2D25A"}, "salami"), ["salami", "corn_can", "egg"]),
    "morkov_syr": (H("green_salad", {LEAF: "#F29A3A"}, "cheese_wedge"), ["carrot", "cheese_wedge", "garlic"]),
    "obzhorka": (H("green_salad", {LEAF: "#C9A070"}, "cut_of_meat"), ["cut_of_meat", "pickles", "carrot"]),
    "salat_pechen_treski": (H("green_salad", {LEAF: "#EFE2B4"}, "cod_liver_can"), ["cod_liver_can", "egg", "potato"]),
    "salat_kalmary": (H("green_salad", {LEAF: "#F6F2EA"}, "squid"), ["squid", "egg", "cucumber"]),
    "salat_krevetki": (H("green_salad", None, "avocado"), ["shrimp", "avocado", "cherry_tomatoes"]),
    "salat_ananas": (H("green_salad", {LEAF: "#F5DC7A"}, "pineapple"), ["chicken_fillet", "pineapple", "cheese_wedge"]),
    "tiffani": (H("green_salad", {LEAF: "#E8DFA8"}, "grapes"), ["chicken_fillet", "grapes", "chestnut"]),
    "salat_kor_morkov": (H("green_salad", {LEAF: "#F29A3A"}, "chicken_fillet"), ["chicken_fillet", "carrot", "korean_spice"]),
    "yabloko_morkov": (H("green_salad", {LEAF: "#F7B04A"}, "red_apple"), ["red_apple", "carrot", "raisins"]),
    "teplyy_salat": (H("green_salad", {LEAF: "#C97A3A"}, "bell_pepper"), ["zucchini", "eggplant", "feta"]),
    "kartofelnyy_salat": (H("green_salad", {LEAF: "#F2DB8A"}, "potato"), ["potato", "pickles", "mustard"]),
    "rukkola": (H("green_salad", {LEAF: "#3E7F35"}, "cherry_tomatoes"), ["arugula", "cherry_tomatoes", "parmesan"]),
    # перекусы
    "buterbrod_kolbasa": (H("toast_bread", None, "boiled_sausage"), ["white_bread", "boiled_sausage", "cheese_wedge"]),
    "buterbrody_shproty": (H("rye_bread", None, "sprats_can"), ["sprats_can", "rye_bread", "cucumber"]),
    "buterbrody_tvorog": (H("baguette_bread", None, "cottage_cheese"), ["cottage_cheese", "dill", "garlic"]),
    "pashtet": (H("toast_bread", None, "chicken_liver"), ["chicken_liver", "carrot", "butter"]),
    "ikra_kabachkovaya": (H("cooked_rice", {"heap": "#D98A3A", "bowl": "#F2E8D8"}, None, ["zucchini"]), ["zucchini", "carrot", "canned_food"]),
    "hachapuri": (H("stuffed_flatbread", None, "egg"), ["cheese_wedge", "kefir", "flour_pack"]),
    "sosiski_testo": (H("hot_dog"), ["hot_dog", "flour_pack", "yeast_pack"]),
    "sloyki": (H("croissant", None, "ham"), ["puff_pastry", "ham", "cheese_wedge"]),
    "pirozhki": (H("pirozhki_pile", None, "potato"), ["potato", "kefir", "flour_pack"]),
    "chebureki": (H("taco", None, "meat_mince"), ["flatbread", "meat_mince", "onion"]),
    "burger": (H("hamburger"), ["bun", "meat_mince", "tomato"]),
    "naggetsy": (H("falafel", {BALL: "#E0A54A"}, "ketchup"), ["chicken_fillet", "breadcrumbs", "egg"]),
    "shampinony_farsh": (H("brown_mushroom", None, "cheese_wedge"), ["brown_mushroom", "cheese_wedge", "onion"]),
    "rulety_vetchina": (H("ham", None, "garlic"), ["ham", "cheese_wedge", "mayonnaise"]),
    "rulety_baklazhan": (H("eggplant", None, "cheese_wedge"), ["eggplant", "garlic", "tomato"]),
    "pomidory_syr": (H("tomato", None, "cheese_wedge"), ["tomato", "garlic", "mayonnaise"]),
    "malosolnye": (H("pickles", None, "dill"), ["cucumber", "garlic", "dill"]),
    "kanape": (H("cheese_wedge", None, "grapes"), ["cheese_wedge", "grapes"]),
    "lukovye_kolca": (H("doughnut", {"all": "#E3A850"}, "onion"), ["onion", "breadcrumbs", "egg"]),
    "chipsy_lavash": (H("flatbread", {"bread": "#E8B06A"}, "paprika"), ["flatbread", "paprika"]),
    "syrnye_chipsy": (H("rice_cracker", {"cracker": "#F2C43A", "nori": "#F2C43A"}, "cheese_wedge"), ["cheese_wedge", "paprika"]),
    "yablochnye_chipsy": (H("green_apple", None, "cinnamon"), ["red_apple", "cinnamon"]),
    "hrustyashchiy_nut": (H("chickpeas", None, "paprika"), ["chickpeas", "paprika", "vegetable_oil"]),
    "kukuruza_varenaya": (H("corn_cob", None, "butter"), ["corn_cob", "butter"]),
    "popkorn": (H("popcorn"), ["popcorn", "butter"]),
    "molochnyy_kokteyl": (H("bubble_tea", None, "ice_cream_tub"), ["glass_of_milk", "ice_cream_tub", "banana"]),
    # десерты
    "mannik": (H("pie", {"crust": "#F5DC9A"}, "semolina_pack"), ["semolina_pack", "kefir", "egg"]),
    "keks_izyum": (H("bread", {"crust": "#F0C88A"}, "raisins"), ["raisins", "butter", "egg"]),
    "medovik": (H("shortcake", {"sponge": "#D9A050"}, "honey_pot"), ["honey_pot", "sour_cream", "flour_pack"]),
    "tykvennyy_pirog": (H("pie", {"crust": "#E8862A"}, "pumpkin"), ["pumpkin", "egg", "cinnamon"]),
    "limonnik": (H("pie", {"crust": "#F2D54A"}, "lemon"), ["lemon", "butter", "flour_pack"]),
    "perevertysh": (H("shortcake", {"sponge": "#F2C46A"}, "pineapple"), ["pineapple", "egg", "butter"]),
    "tertyy_pirog": (H("pie", {"crust": "#D99A5A"}, "jam"), ["jam", "butter", "flour_pack"]),
    "shtrudel": (H("burrito", None, "red_apple"), ["flatbread", "red_apple", "cinnamon"]),
    "krambl": (H("pie", {"crust": "#C8784A"}, "frozen_berries"), ["frozen_berries", "oats", "butter"]),
    "gusinye_lapki": (H("cookie", None, "cottage_cheese"), ["cottage_cheese", "butter", "flour_pack"]),
    "medovoe_pechene": (H("cookie", None, "honey_pot"), ["honey_pot", "egg", "flour_pack"]),
    "batonchiki": (H("chocolate_bar", None, "oats"), ["oats", "honey_pot", "chestnut"]),
    "ponchiki": (H("doughnut"), ["kefir", "egg", "powdered_sugar"]),
    "hvorost": (H("pretzel", None, "powdered_sugar"), ["flour_pack", "egg", "sour_cream"]),
    "beze": (H("cloud", None, "egg"), ["egg", "lemon"]),
    "shokoladnyy_puding": (H("custard", {"body": "#6E3A24", "top": "#4A2418"}, "chocolate_bar"), ["glass_of_milk", "cocoa_pack", "starch_pack"]),
    "krem_bryule": (H("custard", {"body": "#F6E2A8", "top": "#C8782A"}, "vanilla_sugar"), ["cream_33", "egg", "vanilla_sugar"]),
    "banany_shokolad": (H("banana", None, "chocolate_bar"), ["banana", "chocolate_bar"]),
    "klubnika_slivki": (H("strawberry", None, "cream_33"), ["strawberry", "cream_33", "powdered_sugar"]),
    "fruktovyy_led": (H("shaved_ice", None, "strawberry"), ["strawberry", "tangerine", "honey_pot"]),
})

_DEFS = None


def fill_inside(a, inside_mask, items, grain):
    """Кладёт еду внутрь миски: зернистая поверхность и маленькие значки продуктов,
    обрезанные по форме содержимого миски (ложка остаётся сверху)."""
    ys, xs = np.nonzero(inside_mask)
    if not len(xs):
        return a
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    if grain:
        im = MI.to_img(a)
        d = ImageDraw.Draw(im)
        rng = np.random.default_rng(7)
        g = tuple(int(grain.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        for _ in range(170):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if inside_mask[int(y), int(x)]:
                r = rng.uniform(1.6, 3.2)
                d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=g + (200,))
        a = MI.to_arr(im)
    if items:
        n = len(items)
        span = (x1 - x0) / MI.W
        size = 0.36 if n <= 2 else 0.31
        top = y0 / MI.W
        hh = (y1 - y0) / MI.W
        for k, name in enumerate(items):
            cx = x0 / MI.W + span * (0.5 if n == 1 else 0.2 + 0.6 * k / (n - 1))
            cy = top + hh * (0.42 if k % 2 == 0 else 0.25)
            a = MI.place(a, MI.to_arr(icon(name, MI.W)), size, cx, cy, angle=(k * 37) % 50 - 25)
    return a


def hero_img(spec, size):
    base, tint, top, inside, grain = spec
    inside_mask = None
    if (inside or grain) and base == "cooked_rice":
        inside_mask = MI.region(MI.load(base), **BASE_MASKS[base]["heap"])
    if base in BASE_MASKS or not os.path.exists(os.path.join(MI.SRC, base + ".png")):
        a = MI.load(base) if os.path.exists(os.path.join(MI.SRC, base + ".png")) else MI.to_arr(icon(base, MI.W))
    else:
        a = MI.load(base)
    a0 = a.copy()                       # части ищем по исходной картинке, до перекраски
    for part, color in sorted(tint, key=lambda pc: pc[1] != "erase"):   # сначала стираем, потом красим
        mask = MI.region(a0, **BASE_MASKS[base][part])
        if color == "erase":
            m = MI.cv2.dilate(mask.astype(np.uint8), np.ones((5, 5), np.uint8), iterations=4)
            rgb = MI.cv2.inpaint(np.clip(a[..., :3], 0, 255).astype(np.uint8), m, 9, MI.cv2.INPAINT_TELEA)
            a[..., :3] = rgb.astype(np.float32)
        else:
            a = MI.tint(a, mask, color, contrast=0.8)
    if inside_mask is not None:
        a = fill_inside(a, inside_mask, inside, grain)
    if top:
        a = MI.place(a, MI.to_arr(icon(top, MI.W)), 0.40, 0.80, 0.78)
    return MI.to_img(a).resize((size, size), Image.LANCZOS)


def icon(name, size):
    """Значок как картинка PIL: свой значок продукта (make_icons) или исходник Fluent Emoji."""
    global _DEFS
    if _DEFS is None:
        _DEFS = MI.defs()
        _DEFS["boiled_eggs"] = lambda: MI.place(MI.place(MI.place(MI.blank(), "egg", 0.62, 0.32, 0.58, angle=-12),
                                                         "egg", 0.62, 0.68, 0.58, angle=12), "egg", 0.66, 0.5, 0.42)
        _DEFS["pirozhki_pile"] = lambda: MI.place(MI.place(MI.blank(), MI.recolor("dumpling", "#C98232", hue=(10, 60), s=(25, 256)), 0.72, 0.36, 0.58, angle=10),
                                                  MI.recolor("dumpling", "#D99440", hue=(10, 60), s=(25, 256)), 0.72, 0.62, 0.44, angle=-12)
        _DEFS["oat_jar"] = lambda: MI.jar("#E9D8B4", "blueberries", label="#F6F1E4")
        _DEFS["pelmeni_pile"] = lambda: MI.place(MI.place(MI.place(MI.blank(), "dumpling", 0.6, 0.32, 0.6, angle=15),
                                                          "dumpling", 0.6, 0.68, 0.6, angle=-15), "dumpling", 0.62, 0.5, 0.38)
        _DEFS["borscht_pot"] = lambda: MI.recolor("pot_of_food", "#B3243A", hue=(15, 45), s=(120, 256),
                                                  box=(0.2, 0.15, 0.8, 0.6))
    if name in _DEFS:
        im = MI.to_img(_DEFS[name]())
    else:
        im = Image.open(os.path.join(MI.SRC, name + ".png")).convert("RGBA")
    return im.resize((size, size), Image.LANCZOS)


def shadowed(base, im, x, y, blur=10, dy=10, alpha=0.30):
    a = im.split()[3].point(lambda p: int(p * alpha))
    sh = Image.new("RGBA", im.size, (90, 45, 20, 255))
    sh.putalpha(a)
    pad = blur * 3
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(sh, (pad, pad))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(big, (x - pad, y - pad + dy))
    base.alpha_composite(im, (x, y))


def hexrgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def render(slug, group):
    hero, ings = SPEC[slug]
    top, bottom = PALETTE[group]
    t, b = hexrgb(top), hexrgb(bottom)
    yy = np.linspace(0, 1, HGT)[:, None, None]
    xx = np.linspace(0, 1, W)[None, :, None]
    grad = t * (1 - yy) + b * yy
    grad = grad * (1 + 0.05 * np.exp(-(((xx - 0.5) / 0.45) ** 2 + ((yy - 0.45) / 0.5) ** 2)))
    bg = Image.fromarray(np.clip(np.broadcast_to(grad, (HGT, W, 3)), 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    # тарелка
    cx, cy, R = W // 2, int(HGT * 0.52), 205
    plate = Image.new("RGBA", (W, HGT), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    sh = Image.new("RGBA", (W, HGT), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([cx - R + 6, cy - R + 22, cx + R + 6, cy + R + 26], fill=(110, 55, 25, 70))
    bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    pd.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(255, 253, 249, 255))
    pd.ellipse([cx - R + 26, cy - R + 26, cx + R - 26, cy + R - 26], fill=(247, 241, 232, 255))
    pd.ellipse([cx - R + 34, cy - R + 34, cx + R - 34, cy + R - 34], fill=(252, 249, 244, 255))
    bg.alpha_composite(plate)

    hs = 300
    shadowed(bg, hero_img(hero, hs), cx - hs // 2, cy - hs // 2 - 8, blur=12, dy=12, alpha=0.32)

    # продукты вокруг
    spots = [(118, 400), (642, 400), (642, 128), (118, 128)]
    sizes = [132, 132, 116, 116]
    for (x, y), s, name in zip(spots, sizes, ings):
        shadowed(bg, icon(name, s), x - s // 2, y - s // 2, blur=8, dy=8, alpha=0.28)
    return bg.convert("RGB")


def groups():
    """slug фото -> раздел (файл data/recipes/<раздел>.py)."""
    out = {}
    RC.RECIPES.clear()
    for m in sorted(pkgutil.iter_modules(RC.__path__), key=lambda m: m.name):
        before = len(RC.RECIPES)
        full = f"{RC.__name__}.{m.name}"
        if full in sys.modules:
            importlib.reload(sys.modules[full])
        else:
            importlib.import_module(full)
        for r in RC.RECIPES[before:]:
            out[r["photo"]] = m.name
    return out


def main(only=None):
    os.makedirs(OUT, exist_ok=True)
    g = groups()
    missing = set(g) - set(SPEC)
    assert not missing, f"нет описания картинки: {missing}"
    heroes = [v[0] for v in SPEC.values()]
    dup = {h for h in heroes if heroes.count(h) > 1}
    assert not dup, f"одинаковые главные картинки: {dup}"
    for slug in g:
        if only and slug not in only:
            continue
        render(slug, g[slug]).save(os.path.join(OUT, slug + ".jpg"), quality=90)
    print("картинок блюд:", len(only) if only else len(g))


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
