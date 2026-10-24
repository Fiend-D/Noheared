#!/usr/bin/env python3
"""按房间名给案件地图自动铺地板、摆家具，写回 case.json（map.props 和房间的 floor_material）。

    python3 tools/furnish.py              # 只处理还没有家具的案件
    python3 tools/furnish.py case4 --force # 重摆指定案件
    python3 tools/furnish.py --dry-run

摆放规则：
  * 家具贴图不压到任何角色的行走轨迹、站位（含圆点半径），角色永远不会“穿过”家具；
  * 门口、楼梯口、房间名标签附近留空；
  * 每放一件挡路的家具都检查一次：监听者仍能从任一门口 / 楼梯口走到其它门口 / 楼梯口，否则不放。
同一案件多次运行结果相同（随机数以案件和房间名为种子）。生成后在编辑器里可以继续手动调整。
需要 numpy + scipy。
"""

from __future__ import annotations

import argparse
import json
import random
import zlib
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "game" / "cases"
CATALOG = json.loads((ROOT / "game" / "art" / "props" / "catalog.json").read_text(encoding="utf-8"))

RES = 2.0  # 栅格精度（地图像素）
WALL_GAP = 5.0  # 家具离墙中线的距离（墙宽 8）
DOT_CLEAR = 16.0  # 角色圆点半径 13 + 余量
DOOR_DEPTH = 42.0
DOOR_SIDE = 20.0
STAIR_CLEAR = 30.0
LISTENER_MARGIN = 6.0
FOOTPRINT = 0.82  # 与 Prop.FOOTPRINT 一致
PROP_GAP = 3.0

# (关键词, 地板, 户外, [(家具, 位置提示, 数量)])，按顺序匹配第一个包含关键词的房间名。
# 位置提示：top / bottom / side（左右墙）/ corner / center / any
TEMPLATES: list[tuple[tuple[str, ...], str, bool, list[tuple[str, str, int]]]] = [
    (("花园",), "grass", True, [("fountain", "center", 1), ("tree", "corner", 2), ("bench", "any", 1), ("bush", "any", 4)]),
    (("甲板",), "deck", True, [("deck_chair", "top", 4), ("lifebuoy", "bottom", 2), ("bench", "any", 1)]),
    (("露台",), "flagstone", True, [("round_table", "any", 2), ("plant", "corner", 4), ("bench", "any", 1), ("bush", "any", 2)]),
    (("书房",), "parquet", False, [("rug_persian", "center", 1), ("bookshelf", "top", 3), ("desk", "any", 1), ("armchair", "any", 1), ("plant", "corner", 1)]),
    (("会客厅", "客厅"), "wood", False, [("rug_persian", "center", 1), ("fireplace", "top", 1), ("sofa", "any", 1), ("coffee_table", "center", 1), ("armchair", "any", 2), ("bookshelf", "top", 1), ("plant", "corner", 2)]),
    (("大厅",), "marble", False, [("rug_persian", "center", 1), ("sofa", "top", 1), ("side_table", "any", 1), ("statue", "corner", 1), ("plant", "corner", 2)]),
    (("厨房",), "checker", False, [("stove", "top", 1), ("counter", "top", 1), ("sink", "top", 1), ("fridge", "corner", 1), ("round_table", "any", 1), ("barrel", "corner", 1), ("crates", "any", 1)]),
    (("宴会厅",), "marble", False, [("dining_table", "center", 2), ("piano", "corner", 1), ("plant", "corner", 2)]),
    (("餐厅",), "wood", False, [("dining_table", "center", 1), ("round_table", "any", 2), ("drawers", "top", 1), ("plant", "corner", 2)]),
    (("酒窖",), "flagstone", False, [("wine_rack", "top", 3), ("barrel", "any", 4), ("crates", "corner", 1)]),
    (("赌场",), "carpet", False, [("roulette", "center", 1), ("card_table", "any", 2), ("plant", "corner", 2)]),
    (("音乐厅",), "parquet", False, [("piano", "top", 1), ("theatre_seats", "any", 3), ("plant", "corner", 2)]),
    (("医务室",), "marble", False, [("hospital_bed", "top", 2), ("medicine_cabinet", "top", 1), ("chair", "any", 1), ("plant", "corner", 1)]),
    (("船长室",), "wood", False, [("map_table", "center", 1), ("bed_single", "top", 1), ("bookshelf", "top", 1), ("chair", "any", 1)]),
    (("船员休息室",), "concrete", False, [("bunk_bed", "top", 3), ("round_table", "any", 1), ("drawers", "any", 1)]),
    (("老板套房", "豪华套房", "主人卧室"), "carpet", False, [("rug_round", "center", 1), ("bed_double", "top", 1), ("nightstand", "top", 2), ("wardrobe", "top", 1), ("vanity", "any", 1), ("armchair", "any", 1), ("plant", "corner", 1)]),
    (("客房",), "wood", False, [("rug_round", "center", 1), ("bed_single", "top", 1), ("nightstand", "top", 1), ("wardrobe", "top", 1), ("chair", "any", 1), ("drawers", "any", 1)]),
    (("画室",), "wood", False, [("easel", "any", 3), ("rug_round", "center", 1), ("statue", "corner", 1), ("drawers", "top", 1), ("chair", "any", 1)]),
    (("化妆间",), "wood", False, [("vanity", "top", 2), ("clothes_rack", "any", 2), ("wardrobe", "top", 1), ("chair", "any", 1)]),
    (("舞台",), "parquet", False, [("piano", "corner", 1), ("chair", "any", 3), ("statue", "corner", 1)]),
    (("道具室",), "concrete", False, [("crates", "any", 2), ("clothes_rack", "any", 1), ("barrel", "corner", 2), ("statue", "any", 1)]),
    (("展厅",), "marble", False, [("display_case", "any", 4), ("statue", "corner", 2), ("plant", "corner", 1)]),
    (("会议室",), "wood", False, [("round_table", "center", 1), ("chair", "any", 4), ("plant", "corner", 2), ("side_table", "any", 1)]),
    (("茶水间",), "checker", False, [("counter", "top", 1), ("sink", "top", 1), ("fridge", "corner", 1), ("round_table", "any", 1), ("chair", "any", 2)]),
    (("前台",), "marble", False, [("desk", "any", 1), ("chair", "any", 2), ("plant", "corner", 2), ("bench", "any", 1)]),
    (("总经理室", "副总室", "财务室"), "parquet", False, [("desk", "any", 1), ("filing_cabinet", "top", 2), ("bookshelf", "top", 1), ("chair", "any", 2), ("plant", "corner", 1)]),
    (("办公室",), "wood", False, [("desk", "any", 1), ("filing_cabinet", "top", 3), ("bookshelf", "top", 1), ("chair", "any", 1), ("plant", "corner", 1)]),
    (("仓库",), "concrete", False, [("crates", "any", 3), ("barrel", "any", 3)]),
    (("走廊",), "carpet", False, [("plant", "corner", 2), ("side_table", "any", 1), ("statue", "any", 1)]),
    (("门厅",), "marble", False, [("bench", "any", 2), ("side_table", "any", 1), ("plant", "corner", 2)]),
    (("护士站",), "checker", False, [("desk", "any", 1), ("medicine_cabinet", "top", 1), ("filing_cabinet", "top", 1), ("chair", "any", 2), ("plant", "corner", 1)]),
    (("院长室",), "parquet", False, [("rug_persian", "center", 1), ("desk", "any", 1), ("bookshelf", "top", 2), ("filing_cabinet", "top", 1), ("armchair", "any", 1), ("plant", "corner", 1)]),
    (("档案室",), "concrete", False, [("filing_cabinet", "top", 4), ("crates", "any", 2)]),
    (("锅炉房",), "concrete", False, [("barrel", "any", 3), ("crates", "any", 2)]),
    (("洗衣房",), "checker", False, [("sink", "top", 1), ("clothes_rack", "any", 2), ("crates", "any", 2)]),
    (("活动室",), "wood", False, [("card_table", "any", 1), ("round_table", "any", 1), ("chair", "any", 2), ("bookshelf", "top", 1), ("piano", "corner", 1), ("plant", "corner", 1)]),
    (("病房",), "wood", False, [("hospital_bed", "top", 1), ("nightstand", "top", 1), ("chair", "any", 1), ("drawers", "any", 1)]),
    (("西翼",), "concrete", False, [("hospital_bed", "top", 3), ("crates", "any", 2), ("barrel", "corner", 1)]),
    (("值班室",), "concrete", False, [("bed_single", "top", 1), ("desk", "any", 1), ("chair", "any", 1), ("filing_cabinet", "top", 1)]),
    (("直播间",), "carpet", False, [("desk", "center", 1), ("chair", "any", 2), ("bookshelf", "top", 1), ("plant", "corner", 1)]),
    (("导播间",), "carpet", False, [("desk", "top", 2), ("chair", "any", 2), ("filing_cabinet", "top", 1)]),
    (("机房",), "concrete", False, [("filing_cabinet", "top", 4), ("desk", "any", 1), ("crates", "any", 1)]),
    (("唱片库",), "wood", False, [("bookshelf", "top", 4), ("display_case", "any", 1), ("crates", "any", 1)]),
    (("休息室",), "wood", False, [("sofa", "any", 1), ("coffee_table", "center", 1), ("armchair", "any", 1), ("fridge", "corner", 1), ("plant", "corner", 1)]),
    (("天台",), "concrete", True, [("crates", "any", 2), ("barrel", "any", 2), ("plant", "corner", 2), ("bench", "any", 1)]),
    (("水箱间",), "concrete", False, [("barrel", "any", 3), ("crates", "any", 1)]),
    (("楼梯间",), "concrete", False, [("plant", "corner", 1)]),
    (("房间",), "wood", False, [("bed_single", "top", 1), ("bookshelf", "top", 1), ("desk", "any", 1), ("chair", "any", 1), ("rug_round", "center", 1)]),
]  # fmt: skip


def template_for(name: str):
    for keys, floor, outdoor, props in TEMPLATES:
        if any(k in name for k in keys):
            return floor, outdoor, props
    return "wood", False, [("plant", "corner", 2)]


class RoomGrid:
    """一个房间的栅格：forbid = 家具贴图不能盖住的地方，used = 已放家具，block = 挡路范围。"""

    def __init__(self, room: dict) -> None:
        poly = np.array(room["polygon"], dtype=float)
        self.poly = poly
        self.x0, self.y0 = poly.min(axis=0)
        x1, y1 = poly.max(axis=0)
        self.w = int(np.ceil((x1 - self.x0) / RES))
        self.h = int(np.ceil((y1 - self.y0) / RES))
        ys, xs = np.mgrid[0 : self.h, 0 : self.w]
        self.px = self.x0 + (xs + 0.5) * RES
        self.py = self.y0 + (ys + 0.5) * RES
        self.inside = self._inside_polygon()
        dist = ndimage.distance_transform_edt(self.inside) * RES
        self.wall_dist = dist
        self.forbid = ~self.inside | (dist < WALL_GAP)
        self.used = np.zeros_like(self.inside)
        self.block = np.zeros_like(self.inside)

    def _inside_polygon(self) -> np.ndarray:
        x, y = self.px, self.py
        inside = np.zeros(x.shape, dtype=bool)
        n = len(self.poly)
        for i in range(n):
            (ax, ay), (bx, by) = self.poly[i], self.poly[(i + 1) % n]
            cond = (ay > y) != (by > y)
            xint = (bx - ax) * (y - ay) / np.where(by - ay == 0, 1e-9, by - ay) + ax
            inside ^= cond & (x < xint)
        return inside

    def contains(self, p) -> bool:
        i, j = self.cell(p)
        return 0 <= i < self.h and 0 <= j < self.w and bool(self.inside[i, j])

    def cell(self, p) -> tuple[int, int]:
        return int((p[1] - self.y0) / RES), int((p[0] - self.x0) / RES)

    def disc(self, p, r) -> np.ndarray:
        return (self.px - p[0]) ** 2 + (self.py - p[1]) ** 2 <= r * r

    def rect(self, cx, cy, w, h, grow=0.0) -> np.ndarray:
        return (np.abs(self.px - cx) <= w / 2 + grow) & (np.abs(self.py - cy) <= h / 2 + grow)

    def bounds(self):
        return self.x0, self.y0, self.x0 + self.w * RES, self.y0 + self.h * RES


def door_mouths(door: dict, grid: RoomGrid) -> tuple[np.ndarray, list]:
    """门在这个房间一侧留空的范围，以及往里退一点的门口点（用于连通性检查）。"""
    cx, cy = door["position"]
    w, h = door.get("size", [24, 10])
    x0, y0, x1, y1 = grid.bounds()
    # 门靠哪面墙：取门中心离得最近的边
    d = {"top": abs(cy - y0), "bottom": abs(cy - y1), "left": abs(cx - x0), "right": abs(cx - x1)}
    side = min(d, key=d.get)
    if side in ("top", "bottom"):
        half = max(w, 20) / 2 + DOOR_SIDE
        wall_y = y0 if side == "top" else y1
        depth_y = wall_y + (DOOR_DEPTH if side == "top" else -DOOR_DEPTH)
        zone = (np.abs(grid.px - cx) <= half) & (grid.py >= min(wall_y, depth_y) - 4) & (grid.py <= max(wall_y, depth_y) + 4)
        mouth = (cx, wall_y + (14 if side == "top" else -14))
    else:
        half = max(h, 20) / 2 + DOOR_SIDE
        wall_x = x0 if side == "left" else x1
        depth_x = wall_x + (DOOR_DEPTH if side == "left" else -DOOR_DEPTH)
        zone = (np.abs(grid.py - cy) <= half) & (grid.px >= min(wall_x, depth_x) - 4) & (grid.px <= max(wall_x, depth_x) + 4)
        mouth = (wall_x + (14 if side == "left" else -14), cy)
    return zone, [mouth]


def track_points(characters: list, room: dict, grid: RoomGrid) -> list:
    pts = []
    for c in characters:
        keys = c.get("track", [])
        for i, k in enumerate(keys):
            p = k["p"]
            if grid.contains(p):
                pts.append(p)
            if i + 1 < len(keys):
                q = keys[i + 1]["p"]
                n = max(int(np.hypot(q[0] - p[0], q[1] - p[1]) / 3.0), 1)
                for s in range(1, n):
                    t = s / n
                    m = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                    if grid.contains(m):
                        pts.append(m)
    return pts


def candidates(hint: str, grid: RoomGrid, w: float, h: float, rng: random.Random) -> list:
    x0, y0, x1, y1 = grid.bounds()
    lo_x, hi_x = x0 + WALL_GAP + w / 2, x1 - WALL_GAP - w / 2
    lo_y, hi_y = y0 + WALL_GAP + h / 2, y1 - WALL_GAP - h / 2
    if lo_x > hi_x or lo_y > hi_y:
        return []
    xs = list(np.arange(lo_x, hi_x + 0.1, 4.0))
    ys = list(np.arange(lo_y, hi_y + 0.1, 4.0))
    rng.shuffle(xs)
    rng.shuffle(ys)
    if hint == "top":
        return [(x, lo_y) for x in xs]
    if hint == "bottom":
        return [(x, hi_y) for x in xs]
    if hint == "side":
        return [(x, y) for y in ys for x in (lo_x, hi_x)]
    if hint == "corner":
        corners = [(lo_x, lo_y), (hi_x, lo_y), (lo_x, hi_y), (hi_x, hi_y)]
        rng.shuffle(corners)
        near = [(x, y) for x, y in ((cx + dx, cy + dy) for cx, cy in corners for dx in (0, 8, 16) for dy in (0, 8, 16))]
        return [(min(max(x, lo_x), hi_x), min(max(y, lo_y), hi_y)) for x, y in near]
    pts = [(x, y) for x in xs for y in ys]
    if hint == "center":
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        pts.sort(key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    return pts


def connected(grid: RoomGrid, seeds: list) -> bool:
    free = grid.inside & (grid.wall_dist >= LISTENER_MARGIN) & ~grid.block
    labels, _ = ndimage.label(free)
    ids = set()
    for p in seeds:
        i, j = grid.cell(p)
        i, j = min(max(i, 0), grid.h - 1), min(max(j, 0), grid.w - 1)
        if labels[i, j] == 0:
            return False
        ids.add(labels[i, j])
    return len(ids) <= 1


def furnish_room(case_id: str, room: dict, data: dict, ignore_tracks: bool = False) -> list:
    floor, outdoor, plan = template_for(room["name"])
    room.setdefault("floor_material", floor)
    if outdoor:
        room["outdoor"] = True
    grid = RoomGrid(room)
    seeds = []
    m = data["map"]
    for d in m["doors"]:
        if room["name"] in (d["room_a"], d["room_b"]):
            zone, mouths = door_mouths(d, grid)
            grid.forbid |= zone
            seeds += mouths
    for s in m.get("stairs", []):
        for end, name in ((s["end_a"], s["room_a"]), (s["end_b"], s["room_b"])):
            if name == room["name"]:
                grid.forbid |= grid.disc(end, STAIR_CLEAR)
                seeds.append(end)
    x0, y0, _, _ = grid.bounds()
    grid.forbid |= (grid.px < x0 + 14 * len(room["name"]) + 24) & (grid.py < y0 + 32)
    walk = np.zeros_like(grid.inside)
    for p in [] if ignore_tracks else track_points(data.get("characters", []), room, grid):
        walk |= grid.disc(p, DOT_CLEAR)
    rng = random.Random(zlib.crc32(f"{case_id}/{room['name']}".encode()))
    placed = []
    for prop_id, hint, count in plan:
        entry = CATALOG[prop_id]
        w, h = entry["size"]
        for _ in range(count):
            for x, y in candidates(hint, grid, w, h, rng):
                area = grid.rect(x, y, w, h)
                if (area & grid.forbid).any():
                    continue
                if not entry["rug"] and ((area & walk).any() or (grid.rect(x, y, w, h, PROP_GAP) & grid.used).any()):
                    continue
                if entry["block"]:
                    foot = grid.rect(x, y, w * FOOTPRINT, h * FOOTPRINT, LISTENER_MARGIN)
                    before = grid.block.copy()
                    grid.block |= foot
                    if not connected(grid, seeds):
                        grid.block = before
                        continue
                if not entry["rug"]:
                    grid.used |= area
                flip = rng.random() < 0.5 and hint not in ("top", "bottom")
                prop = {"type": prop_id, "position": [round(float(x), 1), round(float(y), 1)], "room": room["name"]}
                if flip:
                    prop["flip"] = True
                placed.append(prop)
                break
    # 地毯先画，压在其它家具下面
    placed.sort(key=lambda p: not CATALOG[p["type"]]["rug"])
    return placed


def furnish_case(case_dir: Path, force: bool, dry_run: bool, ignore_tracks: bool = False) -> None:
    path = case_dir / "case.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    m = data["map"]
    if m.get("props") and not force:
        print(f"{case_dir.name}: 已有家具，跳过（--force 重摆）")
        return
    props = []
    for room in m["rooms"]:
        got = furnish_room(data.get("id", case_dir.name), room, data, ignore_tracks)
        print(f"{case_dir.name} {room['name']}: {room['floor_material']}，{len(got)} 件")
        props += got
    m["props"] = props
    if not dry_run:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cases", nargs="*", help="案件 id，默认全部")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ignore-tracks", action="store_true", help="不避让角色轨迹（之后用 compose_case.py 让角色绕开家具）")
    args = ap.parse_args()
    dirs = [CASES / c for c in args.cases] if args.cases else sorted(p.parent for p in CASES.glob("*/case.json"))
    for d in dirs:
        furnish_case(d, args.force, args.dry_run, args.ignore_tracks)


if __name__ == "__main__":
    main()
