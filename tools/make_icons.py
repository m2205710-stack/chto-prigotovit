"""Готовит значки продуктов в стиле Microsoft Fluent Emoji 3D (лицензия MIT).

У каждого продукта свой значок. Если в наборе нет подходящего, значок
собирается из похожих: перекраской, сочетанием двух значков или как
пакет/баночка нужного цвета с маленькой картинкой.

Исходники лежат в assets/icons_src (PNG 256×256), результат — assets/icons (128×128).
Запуск: python tools/make_icons.py
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "assets", "icons_src")
DST = os.path.join(ROOT, "assets", "icons")
FONT = os.path.join(ROOT, "assets", "fonts", "Nunito-ExtraBold.ttf")
W = 256          # рабочий размер
OUT = 128        # итоговый размер


# ---------------------------------------------------------------- базовые операции
def load(name):
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    if im.size != (W, W):
        im = im.resize((W, W), Image.LANCZOS)
    return np.array(im).astype(np.float32)


def hsv(a):
    return cv2.cvtColor(np.clip(a[..., :3], 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV_FULL).astype(np.float32)


def hexhsv(color):
    c = color.lstrip("#")
    rgb = np.array([[[int(c[i:i + 2], 16) for i in (0, 2, 4)]]], np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV_FULL)[0, 0].astype(np.float32)


def region(a, hue=None, s=(0, 256), v=(0, 256), box=None, alpha=40):
    """Маска пикселей по тону (диапазон в градусах, можно через 0), насыщенности и яркости."""
    H = hsv(a)
    h_deg = H[..., 0] * 360 / 256
    m = a[..., 3] > alpha
    if hue is not None:
        lo, hi = hue
        m &= ((h_deg >= lo) & (h_deg <= hi)) if lo <= hi else ((h_deg >= lo) | (h_deg <= hi))
    m &= (H[..., 1] >= s[0]) & (H[..., 1] < s[1]) & (H[..., 2] >= v[0]) & (H[..., 2] < v[1])
    if box:
        x0, y0, x1, y1 = (int(t * W) for t in box)
        bm = np.zeros_like(m)
        bm[y0:y1, x0:x1] = True
        m &= bm
    return m


def tint(a, mask, color, keep_sat=False, contrast=1.0):
    """Перекрашивает область в цвет, сохраняя объём (светотень) исходника."""
    if not mask.any():
        return a
    H = hsv(a)
    th, ts, tv = hexhsv(color)
    vm = H[..., 2][mask].mean()
    sm = H[..., 1][mask].mean()
    out = H.copy()
    out[..., 0] = np.where(mask, th, H[..., 0])
    rel_s = (H[..., 1] + 12) / (sm + 12)
    out[..., 1] = np.where(mask, H[..., 1] if keep_sat else np.clip(ts * np.clip(rel_s, 0.35, 1.4), 0, 255), H[..., 1])
    rel_v = ((H[..., 2] / max(vm, 1)) - 1) * contrast + 1
    out[..., 2] = np.where(mask, np.clip(tv * rel_v, 0, 255), H[..., 2])
    res = a.copy()
    res[..., :3] = cv2.cvtColor(out.astype(np.uint8), cv2.COLOR_HSV2RGB_FULL).astype(np.float32)
    # мягкий край маски, чтобы не было ступенек
    soft = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.8)[..., None]
    res[..., :3] = a[..., :3] * (1 - soft) + res[..., :3] * soft
    return res


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def to_arr(im):
    return np.array(im.convert("RGBA")).astype(np.float32)


def place(canvas, icon, scale, cx, cy, angle=0, shadow=True, flip=False):
    """Кладёт значок (массив или имя) поверх холста: масштаб, центр в долях, поворот."""
    im = to_img(load(icon) if isinstance(icon, str) else icon)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=False)
    size = int(W * scale)
    im = im.resize((size, size), Image.LANCZOS)
    base = to_img(canvas)
    x, y = int(cx * W - size / 2), int(cy * W - size / 2)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        alpha = im.split()[3].point(lambda p: int(p * 0.28))
        sh.putalpha(alpha)
        sh = Image.composite(Image.new("RGBA", im.size, (70, 40, 20, 255)), sh, alpha)
        sh.putalpha(alpha)
        sh = sh.filter(ImageFilter.GaussianBlur(4))
        base.alpha_composite(sh, (x + 3, y + 5))
    base.alpha_composite(im, (x, y))
    return to_arr(base)


def blank():
    return np.zeros((W, W, 4), np.float32)


def badge(a, icon, scale=0.42, cx=0.74, cy=0.74):
    return place(a, icon, scale, cx, cy)


def text_badge(a, text, color="#C8553D"):
    im = to_img(a)
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, 58)
    tw = d.textlength(text, font=font)
    w, h = tw + 34, 74
    x1, y1 = W - 6, W - 8
    x0, y0 = x1 - w, y1 - h
    d.rounded_rectangle([x0 + 3, y0 + 5, x1 + 3, y1 + 5], radius=h / 2, fill=(90, 40, 20, 70))
    d.rounded_rectangle([x0, y0, x1, y1], radius=h / 2, fill=color)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2 - 3), text, font=font, fill="white", anchor="mm")
    return to_arr(im)


# ---------------------------------------------------------------- пакет и баночка
def pack(color, icon=None, label="#FFFFFF", narrow=False):
    """Бумажный пакет в объёмном стиле с цветной этикеткой и картинкой."""
    S = 4 * W
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    x0, x1 = (0.27, 0.73) if narrow else (0.2, 0.8)
    x0, x1 = int(x0 * S), int(x1 * S)
    y0, y1 = int(0.13 * S), int(0.92 * S)
    rgb = np.array([int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
    # тень под пакетом
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([x0 + 20, y1 - 50, x1 - 20, y1 + 40], fill=(80, 45, 20, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)))
    # тело с горизонтальным градиентом объёма
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0 + 60, x1, y1], radius=70, fill=255)
    grad = np.zeros((S, S, 4), np.float32)
    xs = np.linspace(0, 1, x1 - x0)
    shade = 1.18 - 0.42 * xs ** 1.2 + 0.10 * np.exp(-((xs - 0.18) / 0.08) ** 2)
    ys = np.linspace(0, 1, S)[:, None]
    vshade = 1.0 - 0.10 * np.clip((ys - 0.75) / 0.2, 0, 1)
    col = np.clip(rgb[None, None, :] * shade[None, :, None] * vshade[..., None], 0, 255)
    grad[:, x0:x1, :3] = col
    grad[..., 3] = 255
    body = Image.fromarray(grad.astype(np.uint8), "RGBA")
    body.putalpha(mask)
    im.alpha_composite(body)
    # загнутый верх (гармошка)
    top = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    td = ImageDraw.Draw(top)
    dark = tuple(int(c * 0.82) for c in rgb) + (255,)
    td.rounded_rectangle([x0 + 8, y0, x1 - 8, y0 + 150], radius=40, fill=dark)
    n = 9
    step = (x1 - x0 - 16) / n
    for i in range(n):
        xa = x0 + 8 + i * step
        td.polygon([(xa, y0 + 4), (xa + step / 2, y0 - 36), (xa + step, y0 + 4)], fill=dark)
    for i in range(1, n):
        xa = x0 + 8 + i * step
        td.line([(xa, y0 + 10), (xa, y0 + 140)], fill=tuple(int(c * 0.7) for c in rgb) + (160,), width=6)
    im.alpha_composite(top)
    # блик
    hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle([x0 + 40, y0 + 200, x0 + 90, y1 - 120], radius=25, fill=(255, 255, 255, 70))
    im.alpha_composite(hl.filter(ImageFilter.GaussianBlur(10)))
    # этикетка
    lb = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    lx0, lx1 = x0 + int((x1 - x0) * 0.14), x1 - int((x1 - x0) * 0.14)
    ly0, ly1 = int(0.40 * S), int(0.80 * S)
    ImageDraw.Draw(lb).rounded_rectangle([lx0, ly0, lx1, ly1], radius=60, fill=label)
    im.alpha_composite(lb)
    a = to_arr(im.resize((W, W), Image.LANCZOS))
    if icon is not None:
        a = place(a, icon, 0.36 if narrow else 0.4, 0.5, 0.6, shadow=False)
    return a


def jar(fill, icon=None, label="#FFFFFF", icon_scale=0.42):
    """Стеклянная банка, наполненная продуктом нужного цвета."""
    a = load("jar")
    glass = region(a, hue=(170, 230), s=(8, 256), v=(150, 256), box=(0, 0.2, 1, 1))
    a = tint(a, glass, fill, contrast=0.6)
    lab = region(a, s=(0, 40), v=(100, 200), box=(0.2, 0.4, 0.8, 0.7))
    a = tint(a, lab, label, contrast=0.4)
    if icon is not None:
        a = place(a, icon, icon_scale, 0.5, 0.55, shadow=False)
    return a


def shaker(color, icon=None):
    a = load("salt")
    body = region(a, s=(0, 120), v=(120, 256), box=(0.1, 0.33, 0.9, 1))
    a = tint(a, body, color, contrast=0.7)
    if icon is not None:
        a = badge(a, icon, 0.4, 0.76, 0.76)
    return a


def bottle(color, icon=None):
    a = load("lotion_bottle")
    pink = region(a, hue=(300, 40), s=(25, 256))
    a = tint(a, pink, color)
    if icon is not None:
        a = badge(a, icon, 0.42, 0.74, 0.76)
    return a


def can(color, icon=None):
    a = load("canned_food")
    red = region(a, hue=(330, 25), s=(90, 256), box=(0, 0, 1, 1))
    a = tint(a, red, color)
    if icon is not None:
        a = place(a, icon, 0.4, 0.5, 0.52, shadow=False)
    return a


def recolor(name, color, contrast=1.0, **rk):
    a = load(name)
    return tint(a, region(a, **rk), color, contrast=contrast)


# ---------------------------------------------------------------- значки продуктов
def pumpkin():
    """Тыква из фонаря Джека: убираем вырезанное лицо, закрашивая его гладкой моделью цвета."""
    a = load("jack_o_lantern")
    H = hsv(a)
    alpha = a[..., 3] > 200
    orange = (H[..., 0] < 40) & (H[..., 1] > 120) & (H[..., 2] > 140)
    zone = np.zeros_like(alpha)
    zone[int(W * 0.30):int(W * 0.88), int(W * 0.12):int(W * 0.88)] = True
    face = alpha & ~orange & zone
    face = cv2.dilate(face.astype(np.uint8), np.ones((7, 7), np.uint8), iterations=3).astype(bool) & alpha
    yy, xx = np.mgrid[0:W, 0:W]
    x, y = xx / W - 0.5, yy / W - 0.5
    terms = [x ** i * y ** j for i in range(5) for j in range(5 - i)]
    good = orange & alpha & zone
    A = np.stack([t[good] for t in terms], 1)
    F = np.stack([t[face] for t in terms], 1)
    out = a.copy()
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, a[..., c][good], rcond=None)
        out[..., c][face] = np.clip(F @ coef, 0, 255)
    soft = cv2.GaussianBlur(face.astype(np.float32), (0, 0), 3)[..., None]
    out[..., :3] = a[..., :3] * (1 - soft) + out[..., :3] * soft
    # рёбра тыквы
    ribs = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(ribs)
    for cx, rx in ((0.5, 0.11), (0.5, 0.26)):
        d.arc([int((cx - rx) * W), int(0.24 * W), int((cx + rx) * W), int(0.92 * W)], 0, 360, fill=255, width=5)
    ribs = np.array(ribs.filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255 * (out[..., 3] > 200)
    rib_zone = np.zeros_like(ribs)
    rib_zone[int(0.3 * W):int(0.9 * W)] = 1
    out[..., :3] *= (1 - 0.22 * ribs * rib_zone)[..., None]
    return out


def bun():
    """Булочка для бургера: верхняя половина булки из значка гамбургера, с кунжутом."""
    h = load("hamburger")
    top = h.copy()
    top[int(W * 0.43):, :, 3] = 0
    ys, xs = np.nonzero(top[..., 3] > 20)
    crop = to_img(top).crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    side = max(crop.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2 + side // 8))
    return place(blank(), to_arr(sq), 0.92, 0.5, 0.48)


def mackerel():
    """Скумбрия: рыба серо-зелёного цвета с тёмными волнистыми полосами на спинке."""
    a = recolor("fish", "#7FA89A", hue=(170, 260), s=(30, 256))
    im = to_img(a)
    stripes = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(stripes)
    for k in range(6):
        x = W * (0.22 + 0.09 * k)
        d.line([(x, W * 0.30), (x + 10, W * 0.40), (x - 4, W * 0.50)], fill=255, width=7)
    body = Image.fromarray(((a[..., 3] > 200) & (MI_hsv(a)[..., 0] > 0)).astype(np.uint8) * 255)
    stripes = Image.fromarray(np.minimum(np.array(stripes), np.array(body))).filter(ImageFilter.GaussianBlur(1.5))
    dark = Image.new("RGBA", (W, W), (40, 60, 70, 255))
    dark.putalpha(stripes.point(lambda p: int(p * 0.75)))
    im.alpha_composite(dark)
    return to_arr(im)


def leaf(color):
    """Лист без серых линий ветра."""
    a = load("leaf_fluttering_in_wind")
    H = hsv(a)
    a[..., 3] = np.where(H[..., 1] < 45, 0, a[..., 3])
    return tint(a, region(a, hue=(40, 180), s=(30, 256)), color)


def MI_hsv(a):
    return hsv(a)


def liver():
    """Куриная печень: две гладкие глянцевые доли тёмно-бордового цвета."""
    lobe = recolor("egg", "#7A2233", contrast=1.2)
    im = to_img(lobe).resize((W, int(W * 0.66)), Image.LANCZOS)
    sq = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    sq.alpha_composite(im, (0, int(W * 0.17)))
    lobe = to_arr(sq)
    return place(place(blank(), lobe, 0.92, 0.40, 0.42, angle=24), lobe, 0.84, 0.62, 0.64, angle=-14)


def sausage_slice(color, fat_dots=0, seed=1):
    """Ломтик колбасы: диск из рыбного пирожка, перекрашенный целиком, с кусочками сала."""
    a = load("fish_cake_with_swirl")
    swirl = region(a, hue=(320, 30), s=(70, 256), box=(0.2, 0.2, 0.8, 0.8))
    swirl = cv2.dilate(swirl.astype(np.uint8), np.ones((5, 5), np.uint8), iterations=2)
    rgb = cv2.inpaint(np.clip(a[..., :3], 0, 255).astype(np.uint8), swirl, 9, cv2.INPAINT_TELEA)
    a[..., :3] = rgb.astype(np.float32)
    a = tint(a, region(a, v=(40, 256)), color, contrast=0.8)
    if fat_dots:
        im = to_img(a)
        d = ImageDraw.Draw(im)
        rng = np.random.default_rng(seed)
        alpha = a[..., 3]
        n = 0
        while n < fat_dots:
            x, y = rng.uniform(0.25, 0.75) * W, rng.uniform(0.25, 0.72) * W
            if alpha[int(y), int(x)] > 250 and alpha[int(y) - 14, int(x)] > 250:
                r = rng.uniform(5, 9)
                d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=(250, 236, 228, 255))
                n += 1
        a = to_arr(im)
    return a


def defs():
    """Словарь: имя значка -> функция, возвращающая массив 256×256×4."""
    D = {}

    def add(name, fn):
        assert name not in D, name
        D[name] = fn

    # --- мясо и птица
    add("chicken_fillet", lambda: recolor("cut_of_meat", "#F2B5A2", hue=(330, 25), s=(80, 256)))
    add("chicken_thigh", lambda: recolor("poultry_leg", "#F0B49F", hue=(5, 45), s=(60, 256), box=(0, 0.25, 1, 1)))
    add("poultry_leg", lambda: load("poultry_leg"))
    add("chicken_wings", lambda: place(place(blank(), "poultry_leg", 0.74, 0.40, 0.46, angle=18),
                                       "poultry_leg", 0.74, 0.62, 0.58, angle=-28, flip=True))
    add("chicken_liver", liver)
    add("chicken_mince", lambda: tint(tint(load("cooked_rice"), region(load("cooked_rice"), s=(0, 60), v=(150, 256)), "#F2B3A3"),
                                      region(load("cooked_rice"), hue=(320, 30), s=(120, 256)), "#F4EDE2", contrast=0.8))
    add("cut_of_meat", lambda: load("cut_of_meat"))
    add("pig_face", lambda: load("pig_face"))
    add("meat_mince", lambda: tint(tint(load("cooked_rice"), region(load("cooked_rice"), s=(0, 60), v=(150, 256)), "#C8473F"),
                                   region(load("cooked_rice"), hue=(320, 30), s=(120, 256)), "#F4EDE2", contrast=0.8))
    add("meat_on_bone", lambda: load("meat_on_bone"))
    add("bacon", lambda: load("bacon"))
    add("ham", lambda: recolor("meat_on_bone", "#E88A8C", hue=(345, 45), s=(70, 256)))
    add("hot_dog", lambda: load("hot_dog"))
    add("salami", lambda: sausage_slice("#A8303A", fat_dots=9))
    add("boiled_sausage", lambda: sausage_slice("#F0AFA8"))
    # --- рыба
    add("white_fish", lambda: recolor("cut_of_meat", "#F4EEE6", contrast=0.8, hue=(330, 25), s=(80, 256)))
    add("fish", lambda: load("fish"))
    add("salmon", lambda: recolor("cut_of_meat", "#F48A5C", hue=(330, 25), s=(80, 256)))
    add("herring", lambda: recolor("fish", "#8696A8", hue=(170, 260), s=(30, 256)))
    add("tuna_can", lambda: can("#2F6FB3", "fish"))
    add("sprats_can", lambda: can("#D9A23A", "fish"))
    add("fish_can", lambda: can("#4E8F68", "fish"))
    add("crab", lambda: load("crab"))
    add("shrimp", lambda: load("shrimp"))
    # --- овощи и зелень
    add("potato", lambda: load("potato"))
    add("carrot", lambda: load("carrot"))
    add("onion", lambda: load("onion"))
    add("green_onion", lambda: recolor("sheaf_of_rice", "#6DB24A", hue=(20, 70), s=(60, 256)))
    add("garlic", lambda: load("garlic"))
    add("tomato", lambda: load("tomato"))
    add("cherry_tomatoes", lambda: place(place(place(blank(), "tomato", 0.56, 0.32, 0.62), "tomato", 0.56, 0.68, 0.62),
                                         "tomato", 0.56, 0.5, 0.36))
    add("cucumber", lambda: load("cucumber"))
    add("pickles", lambda: jar("#B9C98A", "cucumber", label="#F6F1E4"))
    add("cabbage", lambda: recolor("leafy_green", "#C9DE9C", hue=(60, 160), s=(30, 256)))
    add("sauerkraut", lambda: jar("#EFE3B0", "leafy_green", label="#F6F1E4"))
    add("broccoli", lambda: load("broccoli"))
    add("cauliflower", lambda: recolor("broccoli", "#F1E7CC", contrast=0.9, hue=(60, 170), s=(30, 256), box=(0, 0, 1, 0.62)))
    add("beet", lambda: recolor("onion", "#7E1E46", hue=(0, 60), s=(30, 256), box=(0, 0.18, 1, 1)))
    add("bell_pepper", lambda: load("bell_pepper"))
    add("hot_pepper", lambda: load("hot_pepper"))
    add("zucchini", lambda: recolor("cucumber", "#8DBF5A", hue=(60, 170), s=(30, 256)))
    add("eggplant", lambda: load("eggplant"))
    add("pumpkin", pumpkin)
    add("brown_mushroom", lambda: load("brown_mushroom"))
    add("corn_can", lambda: can("#F2C443", "ear_of_corn"))
    add("pea_pod", lambda: load("pea_pod"))
    add("beans", lambda: load("beans"))
    add("chickpeas", lambda: recolor("blueberries", "#E3C38E", hue=(200, 320), s=(30, 256)))
    add("lettuce", lambda: load("leafy_green"))
    add("dill", lambda: recolor("herb", "#5FA37A", hue=(50, 150), s=(30, 256)))
    add("parsley", lambda: recolor("shamrock", "#3F8F3A", hue=(60, 170), s=(30, 256)))
    add("cilantro", lambda: recolor("four_leaf_clover", "#6BBF5E", hue=(60, 170), s=(30, 256)))
    add("herb", lambda: load("herb"))
    add("avocado", lambda: load("avocado"))
    add("olive", lambda: load("olive"))
    add("ginger_root", lambda: load("ginger_root"))
    add("radish", lambda: recolor("tomato", "#D8336E", hue=(330, 30), s=(80, 256)))
    # --- фрукты и ягоды
    add("red_apple", lambda: load("red_apple"))
    add("banana", lambda: load("banana"))
    add("tangerine", lambda: load("tangerine"))
    add("lemon", lambda: load("lemon"))
    add("pear", lambda: load("pear"))
    add("kiwi_fruit", lambda: load("kiwi_fruit"))
    add("grapes", lambda: load("grapes"))
    add("strawberry", lambda: load("strawberry"))
    add("cherries", lambda: load("cherries"))
    add("blueberries", lambda: load("blueberries"))
    add("frozen_berries", lambda: badge(place(place(blank(), "blueberries", 0.72, 0.42, 0.5), "strawberry", 0.5, 0.66, 0.36),
                                        "snowflake", 0.42, 0.74, 0.76))
    add("raisins", lambda: recolor("grapes", "#6E3F25", hue=(220, 330), s=(30, 256)))
    add("chestnut", lambda: load("chestnut"))
    # --- молочные
    add("glass_of_milk", lambda: load("glass_of_milk"))
    add("kefir", lambda: tint(tint(load("tumbler_glass"), region(load("tumbler_glass"), hue=(15, 60), s=(60, 256)), "#F3EFE6", contrast=0.6),
                              region(load("tumbler_glass"), hue=(170, 220), s=(90, 256), box=(0.2, 0.3, 0.8, 0.6)), "#FFFFFF", contrast=0.5))
    add("cream_20", lambda: text_badge(tint(load("pouring_liquid"), region(load("pouring_liquid"), hue=(180, 230), s=(90, 256)), "#F6EEDF", contrast=0.6), "20"))
    add("cream_33", lambda: text_badge(tint(load("pouring_liquid"), region(load("pouring_liquid"), hue=(180, 230), s=(90, 256)), "#F6EEDF", contrast=0.6), "33"))
    add("sour_cream", lambda: jar("#F7F3EA", None, label="#7FB0D6"))
    add("cottage_cheese", lambda: recolor("cooked_rice", "#8FB8DE", hue=(320, 30), s=(120, 256)))
    add("yogurt", lambda: tint(tint(load("bowl_with_spoon"), region(load("bowl_with_spoon"), hue=(200, 260), s=(60, 256), v=(0, 170)), "#F7F2EA", contrast=0.5),
                               region(load("bowl_with_spoon"), hue=(190, 250), s=(60, 256), v=(170, 256)), "#F2A7B8"))
    add("butter", lambda: load("butter"))
    add("cheese_wedge", lambda: load("cheese_wedge"))
    add("processed_cheese", lambda: load("fondue"))
    add("mozzarella", lambda: recolor("egg", "#F8F5EF", contrast=0.8))
    add("feta", lambda: recolor("cheese_wedge", "#F5F2EA", contrast=0.8, hue=(30, 70), s=(60, 256)))
    add("parmesan", lambda: recolor("cheese_wedge", "#E2A63A", hue=(30, 70), s=(60, 256)))
    add("mascarpone", lambda: recolor("custard", "#F3E6C4", contrast=0.8, hue=(10, 50), s=(40, 256)))
    add("cream_cheese", lambda: recolor("butter", "#F6F3EC", contrast=0.8, hue=(35, 65), s=(80, 256)))
    add("condensed_milk", lambda: can("#3E78C2", "glass_of_milk"))
    add("dulce_de_leche", lambda: can("#9A5A2A", "honey_pot"))
    # --- яйца
    add("egg", lambda: load("egg"))
    # --- крупы и макароны
    add("pasta_pack", lambda: pack("#F2C14E", "spaghetti"))
    add("spaghetti", lambda: load("spaghetti"))
    add("steaming_bowl", lambda: load("steaming_bowl"))
    add("lasagna_pack", lambda: pack("#C8553D", "flatbread"))
    add("cooked_rice", lambda: load("cooked_rice"))
    add("buckwheat", lambda: recolor("cooked_rice", "#8A5A36", s=(0, 60), v=(150, 256)))
    add("oats", lambda: load("bowl_with_spoon"))
    add("semolina_pack", lambda: pack("#9FC3E6", "bowl_with_spoon"))
    add("millet", lambda: recolor("cooked_rice", "#F2C443", s=(0, 60), v=(150, 256)))
    add("split_peas_pack", lambda: pack("#8DBF5A", "pea_pod"))
    add("lentils_pack", lambda: pack("#E58A3A", "beans"))
    add("granola_pack", lambda: pack("#B9834F", "peanuts"))
    add("barley_pack", lambda: pack("#B8A88A", "cooked_rice"))
    # --- хлеб и выпечка
    add("white_bread", lambda: recolor("bread", "#F1C27A", hue=(15, 60), s=(40, 256)))
    add("rye_bread", lambda: recolor("bread", "#6B3F2A", hue=(15, 60), s=(40, 256)))
    add("baguette_bread", lambda: load("baguette_bread"))
    add("toast_bread", lambda: load("bread"))
    add("flatbread", lambda: load("flatbread"))
    add("tortilla", lambda: load("taco"))
    add("cookie", lambda: load("cookie"))
    add("savoiardi", lambda: badge(recolor("baguette_bread", "#F3D58E", hue=(15, 60), s=(40, 256)), "sparkles", 0.36, 0.76, 0.26))
    add("breadcrumbs", lambda: recolor("rice_cracker", "#C98B4A", hue=(200, 320), s=(20, 256)))
    # --- соусы и приправы
    add("canned_food", lambda: load("canned_food"))
    add("tomatoes_in_juice", lambda: jar("#D9473B", "tomato", label="#F6F1E4"))
    add("mayonnaise", lambda: jar("#F7F0D8", "egg", label="#F6F1E4", icon_scale=0.34))
    add("ketchup", lambda: bottle("#D63A2F", "tomato"))
    add("mustard", lambda: jar("#E0B22B", None, label="#F6F1E4"))
    add("soy_sauce", lambda: bottle("#5A3A2A", "beans"))
    add("olive_oil", lambda: bottle("#B9B23A", "olive"))
    add("vinegar", lambda: bottle("#D9DCE6", "red_apple"))
    add("honey_pot", lambda: load("honey_pot"))
    add("paprika", lambda: shaker("#D9442F", "hot_pepper"))
    add("bay_leaf", lambda: recolor("fallen_leaf", "#8E9E57", hue=(290, 80), s=(40, 256)))
    add("khmeli_suneli", lambda: shaker("#8C8A3E", "herb"))
    add("cumin", lambda: shaker("#B48A4E", "seedling"))
    add("cinnamon", lambda: shaker("#8A4E2B", "wood"))
    add("sesame", lambda: recolor("peanuts", "#F1E3C0", contrast=0.8, hue=(10, 50), s=(40, 256)))
    add("tahini", lambda: jar("#C9A06B", None, label="#F6F1E4"))
    add("korean_spice", lambda: shaker("#E5762E", "carrot"))
    # --- прочие продукты
    add("flour_pack", lambda: pack("#F4EEE2", "sheaf_of_rice", label="#E9DCC6"))
    add("starch_pack", lambda: pack("#7FA9D9", "potato"))
    add("baking_powder", lambda: pack("#E35D6A", "sparkles", narrow=True))
    add("soda_pack", lambda: pack("#F0A33A", "test_tube", narrow=True))
    add("yeast_pack", lambda: pack("#5E9E5A", "bread", narrow=True))
    add("cocoa_pack", lambda: pack("#7A4A2E", "chocolate_bar"))
    add("chocolate_bar", lambda: load("chocolate_bar"))
    add("vanilla_sugar", lambda: pack("#F2D16B", "blossom", narrow=True))
    add("powdered_sugar", lambda: pack("#F4B6C8", "snowflake"))
    add("gelatin_pack", lambda: pack("#9A7FD1", "custard", narrow=True))
    add("hot_beverage", lambda: load("hot_beverage"))
    add("bouillon_cube", lambda: recolor("ice", "#E9AE3A", hue=(150, 260), s=(20, 256)))
    # --- новые продукты (версия 2)
    add("frozen_dumplings", lambda: badge(pack("#5B8FD1", "dumpling"), "snowflake", 0.36, 0.78, 0.24))
    add("vermicelli_pack", lambda: pack("#E35D6A", "spaghetti", narrow=True))
    add("cornflakes_pack", lambda: pack("#3E78C2", "ear_of_corn"))
    add("corn_grits_pack", lambda: pack("#F2C443", "ear_of_corn", narrow=True))
    add("barley_grits", lambda: recolor("cooked_rice", "#C9A877", s=(0, 60), v=(150, 256)))
    add("peanut_butter", lambda: jar("#C98B4A", "peanuts", label="#F6F1E4"))
    add("sorrel", lambda: place(blank(), leaf("#4F9A3A"), 1.0, 0.5, 0.5))
    add("bun", bun)
    add("corn_cob", lambda: load("ear_of_corn"))
    add("popcorn", lambda: load("popcorn"))
    add("cod_liver_can", lambda: can("#8A5A36", recolor("cut_of_meat", "#E9C7A0", hue=(330, 25), s=(80, 256))))
    add("squid", lambda: load("squid"))
    add("arugula", lambda: place(place(blank(), leaf("#3B7A2E"), 0.85, 0.40, 0.42, angle=35),
                                 leaf("#5C9A3E"), 0.75, 0.62, 0.62, angle=-40, flip=True))
    add("pineapple", lambda: load("pineapple"))
    add("mackerel", mackerel)
    add("pork_ribs", lambda: place(place(blank(), recolor("meat_on_bone", "#D9705A", hue=(330, 40), s=(60, 256)), 0.72, 0.38, 0.40, angle=20),
                                   recolor("meat_on_bone", "#D9705A", hue=(330, 40), s=(60, 256)), 0.72, 0.62, 0.62, angle=-15))
    add("duck", lambda: load("duck"))
    add("puff_pastry", lambda: pack("#E9C46A", "croissant"))
    add("jam", lambda: jar("#B5283A", "strawberry", label="#F6F1E4"))
    add("ice_cream_tub", lambda: load("ice_cream"))
    # --- базовые продукты
    add("salt", lambda: load("salt"))
    add("sugar_cube", lambda: recolor("ice", "#EAE2D2", contrast=1.15, hue=(150, 260), s=(20, 256)))
    add("black_pepper", lambda: shaker("#4A403A"))
    add("vegetable_oil", lambda: bottle("#F2C230"))
    add("droplet", lambda: load("droplet"))
    return D


def save(a, name, folder=DST):
    im = to_img(a).resize((OUT, OUT), Image.LANCZOS)
    im.save(os.path.join(folder, name + ".png"), optimize=True)


def main(only=None):
    os.makedirs(DST, exist_ok=True)
    D = defs()
    for name, fn in D.items():
        if only and name not in only:
            continue
        save(fn(), name)
    # значки интерфейса — как есть
    for f in ["fork_and_knife_with_plate", "stopwatch", "bar_chart", "shopping_cart", "cooking", "memo",
              "clipboard", "party_popper", "thinking_face", "magnifying_glass_tilted_right", "sunrise",
              "pot_of_food", "shallow_pan_of_food", "sandwich", "shortcake"]:
        if os.path.exists(os.path.join(SRC, f + ".png")):
            save(load(f), f)
    print(f"значков продуктов: {len(D)}")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
