#!/usr/bin/env python3
"""把 AI 生成的 3x3 素材表切成游戏用的家具贴图和地板材质。

    python3 tools/art_sheets.py

输入在 tools/art_sources/：
  sheet_<组>.jpg  洋红底的家具表，按行排列 9 件，名字见 PROP_SHEETS
  sheet_floors.jpg 地板材质表，9 格，名字见 FLOORS
  title_*.jpg      案件选择界面：书桌背景、空白档案袋、照片表（名字见 PHOTOS）
  portraits_<n>.jpg 洋红底的人物肖像表，每格对应的角色见 PORTRAITS
  poster_<案件>.jpg 案件海报（竖版 3:4）

输出：
  game/art/props/<id>.png    去底、裁边后的家具（带透明通道）
  game/art/props/catalog.json 家具目录：地图尺寸、是否阻挡、是否贴地
  game/art/floors/<id>.jpg   地板材质
  game/art/exterior/<id>.jpg 建筑外的地面（sheet_exterior.jpg，名字见 EXTERIORS）
  game/art/title/            desk.jpg、folder.png、photo_<名字>.png
  game/art/portraits/<案件>/<角色 ID>.jpg  标记身份后人物徽章里的头像
  game/art/posters/<案件>.jpg 档案柜里的案件海报

需要 Pillow + numpy + scipy（系统 Python 即可）。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "tools" / "art_sources"
PROPS_OUT = ROOT / "game" / "art" / "props"
FLOORS_OUT = ROOT / "game" / "art" / "floors"
EXTERIOR_OUT = ROOT / "game" / "art" / "exterior"
# sheet_exterior.jpg：建筑外面的地面（case.json 的 map.backdrop 引用）
EXTERIORS = ["lawn", "hedge", "cobblestone", "ocean", "asphalt", "gravel", "forest", "sand", "dirt"]

PROP_SHEETS = {
    "living": [
        "sofa", "armchair", "coffee_table",
        "rug_persian", "fireplace", "bookshelf",
        "plant", "side_table", "desk",
    ],
    "bedroom": [
        "bed_double", "bed_single", "wardrobe",
        "nightstand", "vanity", "bunk_bed",
        "chair", "rug_round", "drawers",
    ],
    "kitchen": [
        "dining_table", "round_table", "counter",
        "stove", "sink", "fridge",
        "barrel", "wine_rack", "crates",
    ],
    "venue": [
        "piano", "roulette", "card_table",
        "theatre_seats", "display_case", "statue",
        "easel", "filing_cabinet", "clothes_rack",
    ],
    "outdoor": [
        "tree", "bush", "fountain",
        "bench", "deck_chair", "lifebuoy",
        "hospital_bed", "medicine_cabinet", "map_table",
    ],
}  # fmt: skip

TITLE_OUT = ROOT / "game" / "art" / "title"
# title_photos.jpg 里 9 张照片的名字（case.json 的 cover 字段引用）
PHOTOS = ["office", "theatre", "gallery", "study", "liner", "manor", "hotel", "tape", "street"]

FLOORS = [
    "wood", "parquet", "checker",
    "carpet", "marble", "deck",
    "flagstone", "grass", "concrete",
]  # fmt: skip

# 地图上的宽度（像素，人物圆点直径约 26）。高度按贴图比例。
# block=False 的是地毯一类，可以踩上去；rug=True 画在其它家具下面。
CATALOG = {
    "sofa": {"width": 70},
    "armchair": {"width": 30},
    "coffee_table": {"width": 44},
    "rug_persian": {"width": 84, "block": False, "rug": True},
    "fireplace": {"width": 54},
    "bookshelf": {"width": 40},
    "plant": {"width": 28},
    "side_table": {"width": 22},
    "desk": {"width": 50},
    "bed_double": {"width": 56},
    "bed_single": {"width": 36},
    "wardrobe": {"width": 40},
    "nightstand": {"width": 22},
    "vanity": {"width": 46},
    "bunk_bed": {"width": 38},
    "chair": {"width": 18},
    "rug_round": {"width": 54, "block": False, "rug": True},
    "drawers": {"width": 36},
    "dining_table": {"width": 96},
    "round_table": {"width": 56},
    "counter": {"width": 80},
    "stove": {"width": 40},
    "sink": {"width": 40},
    "fridge": {"width": 30},
    "barrel": {"width": 28},
    "wine_rack": {"width": 50},
    "crates": {"width": 44},
    "piano": {"width": 58},
    "roulette": {"width": 54},
    "card_table": {"width": 56},
    "theatre_seats": {"width": 92},
    "display_case": {"width": 56},
    "statue": {"width": 28},
    "easel": {"width": 36},
    "filing_cabinet": {"width": 24},
    "clothes_rack": {"width": 48},
    "tree": {"width": 72},
    "bush": {"width": 36},
    "fountain": {"width": 72},
    "bench": {"width": 54},
    "deck_chair": {"width": 26},
    "lifebuoy": {"width": 26, "block": False},
    "hospital_bed": {"width": 32},
    "medicine_cabinet": {"width": 32},
    "map_table": {"width": 56},
}

PORTRAITS_OUT = ROOT / "game" / "art" / "portraits"
POSTERS_OUT = ROOT / "game" / "art" / "posters"
# portraits_<n>.jpg：洋红底 3x3 肖像表，每格对应 "<案件>/<角色 ID>"，空串表示不用
PORTRAITS = [
    ["case1/A", "case1/B", "case1/C", "case2/D", "case2/E", "case2/F", "case2/G", "case3/H", "case3/I"],
    ["case3/J", "case3/K", "case3/L", "case3/M", "case4/A", "case4/B", "case4/C", "case4/D", "case4/E"],
    ["case4/F", "case5/A", "case5/B", "case5/C", "case5/D", "case5/E", "case5/F", "case5/G", "case5/H"],
    ["case5/I", "case5/J", "case6/A", "case6/B", "case6/C", "case6/D", "case6/E", "case6/F", "case6/G"],
    ["case6/H", "case6/I", "case6/J", "case7/A", "case7/B", "case7/C", "case7/D", "case7/E", "case7/F"],
    ["case7/G", "case7/H", "case8/A", "case8/B", "case8/C", "case8/D", "case8/E", "case8/F", "case8/G"],
    ["case8/H", "case9/A", "case9/B", "case9/C", "case9/D", "case9/E", "case9/F", "case9/G"],
]
# 肖像取边框内宽度的这一比例（贴顶、水平居中），让脸在圆形徽章里够大
PORTRAIT_FACE = 0.74
PORTRAIT_SIZE = 160
POSTER_SIZE = (600, 800)

## CATALOG 的宽度整体再乘这个系数（调整家具与房间的比例）。
SIZE_SCALE = 1.4
MAX_SPRITE = 256
FLOOR_SIZE = 320


def background_color(rgb: np.ndarray) -> np.ndarray:
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    return np.median(border, axis=0)


def key_out(rgb: np.ndarray, bg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """按到背景色的距离算透明度，再把半透明边缘里混进来的洋红减掉。"""
    dist = np.linalg.norm(rgb - bg, axis=2)
    alpha = np.clip((dist - 45.0) / 60.0, 0.0, 1.0)
    # 物体落在洋红底上的暗影也是洋红色相，距离判不出来；家具本身几乎没有 R、B 同时远高于 G 的颜色
    magenta = np.minimum(rgb[..., 0], rgb[..., 2]) - rgb[..., 1]
    alpha = np.minimum(alpha, np.clip(1.0 - (magenta - 35.0) / 45.0, 0.0, 1.0))
    safe = np.maximum(alpha, 1e-3)[..., None]
    unmixed = (rgb - (1.0 - alpha[..., None]) * bg) / safe
    color = np.where(alpha[..., None] > 0.02, np.clip(unmixed, 0, 255), 0)
    # 残余的洋红色调（R、B 高于 G）压回中性
    spill = np.clip(np.minimum(color[..., 0], color[..., 2]) - color[..., 1] - 30.0, 0, None)
    edge = (alpha < 0.95)[..., None]
    color = np.where(edge, color - spill[..., None] * np.array([1.0, 0.0, 1.0]), color)
    return np.clip(color, 0, 255), alpha


def split_sheet(path: Path, names: list[str]) -> None:
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w, _ = rgb.shape
    color, alpha = key_out(rgb, background_color(rgb))
    solid = ndimage.binary_closing(alpha > 0.3, iterations=3)
    labels, count = ndimage.label(solid)
    sizes = ndimage.sum(np.ones_like(alpha), labels, range(1, count + 1))
    centers = ndimage.center_of_mass(solid, labels, range(1, count + 1))
    cell_of = {}
    for i, (cy, cx) in enumerate(centers):
        if sizes[i] < 150:
            continue
        cell_of[i + 1] = min(int(cy * 3 / h), 2) * 3 + min(int(cx * 3 / w), 2)
    for cell, name in enumerate(names):
        members = [lab for lab, c in cell_of.items() if c == cell]
        if not members:
            raise SystemExit(f"{path.name}: 第 {cell + 1} 格（{name}）没切出东西")
        mask = np.isin(labels, members)
        ys, xs = np.nonzero(mask)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        a = np.where(ndimage.binary_dilation(mask, iterations=2), alpha, 0.0)[y0:y1, x0:x1]
        rgba = np.dstack([color[y0:y1, x0:x1], a * 255.0]).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA")
        img.thumbnail((MAX_SPRITE, MAX_SPRITE), Image.LANCZOS)
        img.save(PROPS_OUT / f"{name}.png", optimize=True)


def split_tiles(path: Path, names: list[str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(path).convert("RGB")
    w, h = img.size
    inset = 10
    for i, name in enumerate(names):
        r, c = divmod(i, 3)
        box = (c * w // 3 + inset, r * h // 3 + inset, (c + 1) * w // 3 - inset, (r + 1) * h // 3 - inset)
        tile = img.crop(box).resize((FLOOR_SIZE, FLOOR_SIZE), Image.LANCZOS)
        tile.save(out_dir / f"{name}.jpg", quality=88)


def title_assets() -> None:
    """案件选择界面：书桌背景、空白档案袋、案件照片。"""
    TITLE_OUT.mkdir(parents=True, exist_ok=True)
    desk = Image.open(SOURCES / "title_desk_bg.jpg").convert("RGB").resize((1920, 1080), Image.LANCZOS)
    desk.save(TITLE_OUT / "desk.jpg", quality=88)
    rgb = np.asarray(Image.open(SOURCES / "title_folder.jpg").convert("RGB"), dtype=np.float32)
    color, alpha = key_out(rgb, background_color(rgb))
    alpha = ndimage.minimum_filter(alpha, size=5)
    ys, xs = np.nonzero(alpha > 0.5)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    folder = Image.fromarray(np.dstack([color, alpha * 255.0]).astype(np.uint8), "RGBA").crop(box)
    folder.thumbnail((720, 720), Image.LANCZOS)
    folder.save(TITLE_OUT / "folder.png", optimize=True)
    with Image.open(SOURCES / "title_photos.jpg") as photos:
        sheet = np.asarray(photos.convert("RGB"), dtype=np.float32)
    color, alpha = key_out(sheet, background_color(sheet))
    h, w = alpha.shape
    for i, name in enumerate(PHOTOS):
        r, c = divmod(i, 3)
        cell = alpha[r * h // 3 : (r + 1) * h // 3, c * w // 3 : (c + 1) * w // 3] > 0.5
        ys, xs = np.nonzero(cell)
        y0, x0 = r * h // 3 + ys.min(), c * w // 3 + xs.min()
        y1, x1 = r * h // 3 + ys.max() + 1, c * w // 3 + xs.max() + 1
        rgba = np.dstack([color[y0:y1, x0:x1], alpha[y0:y1, x0:x1] * 255.0]).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA")
        img.thumbnail((256, 256), Image.LANCZOS)
        img.save(TITLE_OUT / f"photo_{name}.png", optimize=True)


def portraits() -> None:
    """人物肖像：每格去掉洋红底和米色边框，取头肩部分的正方形。"""
    for sheet, names in enumerate(PORTRAITS, start=1):
        with Image.open(SOURCES / f"portraits_{sheet}.jpg") as src:
            rgb = np.asarray(src.convert("RGB"), dtype=np.float32)
        _, alpha = key_out(rgb, background_color(rgb))
        h, w = alpha.shape
        for i, key in enumerate(names):
            r, c = divmod(i, 3)
            y_off, x_off = r * h // 3, c * w // 3
            ys, xs = np.nonzero(alpha[y_off : (r + 1) * h // 3, x_off : (c + 1) * w // 3] > 0.5)
            y0, x0 = y_off + ys.min(), x_off + xs.min()
            side = min(ys.max() - ys.min(), xs.max() - xs.min())
            border = int(side * 0.04)
            inner = side - 2 * border
            face = int(inner * PORTRAIT_FACE)
            left = x0 + border + (inner - face) // 2
            top = y0 + border
            crop = rgb[top : top + face, left : left + face].astype(np.uint8)
            out = PORTRAITS_OUT / f"{key}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(crop).resize((PORTRAIT_SIZE, PORTRAIT_SIZE), Image.LANCZOS).save(out, quality=90)


def posters() -> None:
    POSTERS_OUT.mkdir(parents=True, exist_ok=True)
    for src in sorted(SOURCES.glob("poster_*.jpg")):
        img = Image.open(src).convert("RGB")
        w, h = img.size
        cw = min(w, h * 3 // 4)
        ch = cw * 4 // 3
        img = img.crop(((w - cw) // 2, (h - ch) // 2, (w + cw) // 2, (h + ch) // 2))
        img.resize(POSTER_SIZE, Image.LANCZOS).save(POSTERS_OUT / f"{src.stem.removeprefix('poster_')}.jpg", quality=86)


def write_catalog() -> None:
    out = {}
    for sheet, names in PROP_SHEETS.items():
        for name in names:
            entry = CATALOG[name]
            with Image.open(PROPS_OUT / f"{name}.png") as img:
                aspect = img.height / img.width
            width = entry["width"] * SIZE_SCALE
            out[name] = {
                "sheet": sheet,
                "size": [round(width, 1), round(width * aspect, 1)],
                "block": entry.get("block", True),
                "rug": entry.get("rug", False),
            }
    (PROPS_OUT / "catalog.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    PROPS_OUT.mkdir(parents=True, exist_ok=True)
    FLOORS_OUT.mkdir(parents=True, exist_ok=True)
    for sheet, names in PROP_SHEETS.items():
        split_sheet(SOURCES / f"sheet_{sheet}.jpg", names)
    split_tiles(SOURCES / "sheet_floors.jpg", FLOORS, FLOORS_OUT)
    split_tiles(SOURCES / "sheet_exterior.jpg", EXTERIORS, EXTERIOR_OUT)
    write_catalog()
    title_assets()
    portraits()
    posters()
    print(f"{sum(len(n) for n in PROP_SHEETS.values())} 件家具，{len(FLOORS)} 种地板")


if __name__ == "__main__":
    main()
