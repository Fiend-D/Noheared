#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json
from PIL import Image, ImageDraw, ImageFont

WALL = (110, 145, 200)
WALL_HI = (150, 190, 240)
FURN = (80, 110, 170)
FURN2 = (100, 135, 200)


def wall_seg(d, x1, y1, x2, y2):
    if x1 == x2:
        d.line([(x1, y1), (x2, y2)], fill=WALL_HI, width=1)
        d.line([(x1 - 1, y1), (x2 - 1, y2)], fill=WALL, width=4)
        d.line([(x1 - 2, y1), (x2 - 2, y2)], fill=WALL_HI, width=1)
    else:
        d.line([(x1, y1), (x2, y2)], fill=WALL_HI, width=1)
        d.line([(x1, y1 - 1), (x2, y2 - 1)], fill=WALL, width=4)
        d.line([(x1, y1 - 2), (x2, y2 - 2)], fill=WALL_HI, width=1)


def corner_dot(d, x, y):
    d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=WALL_HI)


def bed(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.rectangle([x + 3, y + 3, x + int(w * 0.35), y + int(h * 0.25)], outline=FURN, width=1)
    d.arc([x + 3, y + int(h * 0.25) - 4, x + int(w * 0.35), y + int(h * 0.25) + 4], 0, 180, fill=FURN, width=1)
    d.line([(x + 3, y + h - 4), (x + w - 3, y + h - 4)], fill=FURN, width=2)


def desk(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.line([(x + 4, y + h // 2), (x + w - 4, y + h // 2)], fill=FURN2, width=1)
    cx, cy = x + w // 2, y + h + 6
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=FURN, width=1)
    d.line([(cx, cy + 4), (cx, cy + 10)], fill=FURN, width=1)


def sofa(d, x, y, w, h):
    d.rounded_rectangle([x, y, x + w, y + h], radius=4, outline=FURN, width=2)
    d.line([(x + 6, y + 4), (x + w - 6, y + 4)], fill=FURN2, width=1)
    d.arc([x + 2, y + 2, x + 8, y + h - 2], 90, 270, fill=FURN, width=1)
    d.arc([x + w - 8, y + 2, x + w - 2, y + h - 2], 270, 90, fill=FURN, width=1)


def dining(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    for i in range(w // 20):
        cx = x + 12 + i * 20
        if cx + 4 > x + w - 4:
            break
        d.ellipse([cx - 4, y - 7, cx + 4, y], outline=FURN, width=1)
        d.ellipse([cx - 4, y + h, cx + 4, y + h + 7], outline=FURN, width=1)


def long_table(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    for i in range(4):
        cx = x + w * (i + 1) // 5
        d.ellipse([cx - 4, y - 7, cx + 4, y], outline=FURN, width=1)
        d.ellipse([cx - 4, y + h, cx + 4, y + h + 7], outline=FURN, width=1)


def shelf(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    n = max(2, h // 16)
    for i in range(1, n):
        ly = y + h * i // n
        d.line([(x + 2, ly), (x + w - 2, ly)], fill=FURN2, width=1)


def wardrobe(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.line([(x + w // 2, y + 3), (x + w // 2, y + h - 3)], fill=FURN, width=1)
    d.ellipse([x + w // 2 - 3, y + h // 2 - 3, x + w // 2 + 3, y + h // 2 + 3], outline=FURN2, width=1)
    d.line([(x + 2, y + 8), (x + w - 2, y + 8)], fill=FURN2, width=1)


def nightstand(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=1)
    d.ellipse([x + w // 2 - 3, y - 6, x + w // 2 + 3, y], outline=FURN2, width=1)
    d.line([(x + w // 2, y - 6), (x + w // 2, y - 10)], fill=FURN2, width=1)


def counter(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.line([(x + 2, y + 6), (x + w - 2, y + 6)], fill=FURN2, width=2)
    d.line([(x + 2, y + h - 4), (x + w - 2, y + h - 4)], fill=FURN2, width=1)


def stove(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    for i in range(2):
        bx = x + w * (i + 1) // 3
        d.ellipse([bx - 5, y + 5, bx + 5, y + 15], outline=FURN, width=1)
        d.ellipse([bx - 3, y + 7, bx + 3, y + 13], outline=FURN2, width=1)
    d.line([(x + 3, y + h - 4), (x + w - 3, y + h - 4)], fill=FURN2, width=1)


def sink(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.ellipse([x + 4, y + 4, x + w - 4, y + h - 4], outline=FURN, width=1)
    d.ellipse([x + 6, y + 6, x + w - 6, y + h - 6], outline=FURN2, width=1, fill=None)
    d.line([(x + 2, y - 2), (x + w - 2, y - 2)], fill=FURN2, width=2)


def fridge(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.line([(x + w // 2, y + 2), (x + w // 2, y + h - 2)], fill=FURN, width=1)
    d.ellipse([x + w // 2 - 2, y + 10, x + w // 2 + 2, y + 14], outline=FURN2, width=1)


def piano(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    kw = int(w * 0.4)
    d.rectangle([x + w - kw, y + 3, x + w - 3, y + h - 3], outline=FURN2, width=1)
    for i in range(5):
        d.line([(x + w - kw + i * kw // 6, y + 3), (x + w - kw + i * kw // 6, y + h - 3)], fill=FURN2, width=1)
    d.arc([x, y + h - 8, x + w - kw, y + h + 2], 180, 0, fill=FURN, width=1)


def reception(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.line([(x + 3, y + 8), (x + w - 3, y + 8)], fill=FURN2, width=2)
    d.line([(x + 3, y + h - 6), (x + w - 3, y + h - 6)], fill=FURN2, width=1)
    d.line([(x + w // 2, y + 8), (x + w // 2, y + h - 6)], fill=FURN2, width=1)


def plant(d, x, y, sz):
    d.rectangle([x - sz // 2, y, x + sz // 2, y + sz - 4], outline=FURN, width=1)
    d.ellipse([x - sz // 2, y - sz // 2, x + sz // 2, y + sz // 2], outline=FURN2, width=1)
    d.line([(x, y - sz // 2), (x, y)], fill=FURN, width=1)


def wine_rack(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    for i in range(1, 5):
        d.line([(x + 2, y + h * i // 5), (x + w - 2, y + h * i // 5)], fill=FURN2, width=1)
    for j in range(3):
        bx = x + w * (j + 1) // 4
        d.rectangle([bx - 3, y + 5, bx + 3, y + h // 2], outline=FURN, width=1)
        d.ellipse([bx - 3, y + h // 2 - 2, bx + 3, y + h // 2 + 2], fill=FURN2)


def barrel(d, x, y, w, h):
    d.ellipse([x, y, x + w, y + h], outline=FURN, width=2)
    d.ellipse([x + 2, y + 2, x + w - 2, y + h - 2], outline=FURN2, width=1)
    d.line([(x + w // 2, y + 2), (x + w // 2, y + h - 2)], fill=FURN, width=1)
    d.arc([x + 2, y - 3, x + w - 2, y + 3], 0, 180, fill=FURN, width=1)
    d.arc([x + 2, y + h - 3, x + w - 2, y + h + 3], 180, 360, fill=FURN, width=1)


def card_table(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    for i in range(4):
        cx = x + (w // 2) if i < 2 else x + (w // 2)
        cy = y - 6 if i % 2 == 0 else y + h + 6
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=FURN, width=1)


def round_table(d, x, y, w, h):
    d.ellipse([x, y, x + w, y + h], outline=FURN, width=2)
    d.ellipse([x + 2, y + 2, x + w - 2, y + h - 2], outline=FURN2, width=1)
    d.line([(x + w // 2, y + 2), (x + w // 2, y + h - 2)], fill=FURN2, width=1)
    d.line([(x + 2, y + h // 2), (x + w - 2, y + h // 2)], fill=FURN2, width=1)


def roulette(d, x, y, w, h):
    d.ellipse([x, y, x + w, y + h], outline=FURN, width=2)
    d.ellipse([x + w // 3, y + h // 3, x + 2 * w // 3, y + 2 * h // 3], outline=FURN2, width=1)
    for i in range(8):
        a = i * 45
        import math
        rad = math.radians(a)
        rx = x + w // 2 + int(w // 2 * 0.8 * math.cos(rad))
        ry = y + h // 2 + int(h // 2 * 0.8 * math.sin(rad))
        d.ellipse([rx - 2, ry - 2, rx + 2, ry + 2], fill=FURN2)


def easel(d, x, y, w, h):
    d.line([(x, y + h), (x + w // 2, y), (x + w, y + h)], fill=FURN, width=2)
    d.line([(x + w // 2, y), (x + w // 2, y + h)], fill=FURN2, width=1)
    d.rectangle([x + 4, y + 8, x + w - 4, y + h - 4], outline=FURN, width=1)
    d.line([(x + 6, y + 10), (x + w - 6, y + 10)], fill=FURN2, width=1)


def display_case(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.line([(x + 2, y + 8), (x + w - 2, y + 8)], fill=FURN2, width=2)
    d.rectangle([x + 6, y + 12, x + w - 6, y + h - 4], outline=FURN2, width=1)
    d.line([(x + w // 2, y + 12), (x + w // 2, y + h - 4)], fill=FURN2, width=1)


def podium(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.line([(x + 2, y + 6), (x + w - 2, y + 6)], fill=FURN2, width=1)


def railing(d, x, y, w, h):
    d.line([(x, y), (x + w, y)], fill=FURN, width=2)
    d.line([(x, y), (x, y + h)], fill=FURN, width=1)
    d.line([(x + w, y), (x + w, y + h)], fill=FURN, width=1)
    for i in range(w // 20):
        px = x + i * 20
        d.line([(px, y), (px, y + h)], fill=FURN2, width=1)


def decorative_pillar(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=1)
    d.line([(x + 3, y + 3), (x + w - 3, y + 3)], fill=FURN2, width=1)
    d.line([(x + 3, y + h - 3), (x + w - 3, y + h - 3)], fill=FURN2, width=1)


def stage(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN2, width=2)
    d.line([(x + 10, y + 4), (x + w - 10, y + 4)], fill=FURN, width=1)
    d.line([(x + 4, y + 10), (x + w - 4, y + 10)], fill=FURN, width=1)


def vanity(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    d.ellipse([x + 4, y - 10, x + w - 4, y + 2], outline=FURN2, width=1)
    d.line([(x + w // 2, y - 10), (x + w // 2, y)], fill=FURN2, width=1)


def boxes(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h // 2], outline=FURN, width=1)
    d.rectangle([x + 2, y + h // 2, x + w - 2, y + h], outline=FURN, width=1)
    d.line([(x + 2, y + h // 2), (x + w - 2, y + h // 2)], fill=FURN2, width=1)


def map_table(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    cx, cy = x + w // 2, y + h // 2
    d.line([(cx, y + 4), (cx, y + h - 4)], fill=FURN2, width=1)
    d.line([(x + 4, cy), (x + w - 4, cy)], fill=FURN2, width=1)
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], outline=FURN2, width=1)
    d.line([(cx, cy - 6), (cx, cy + 6)], fill=FURN2, width=1)
    d.line([(cx - 6, cy), (cx + 6, cy)], fill=FURN2, width=1)


def fountain(d, x, y, w, h):
    d.ellipse([x, y, x + w, y + h], outline=FURN, width=2)
    d.ellipse([x + 6, y + 6, x + w - 6, y + h - 6], outline=FURN2, width=1)
    d.ellipse([x + w // 2 - 4, y + 4, x + w // 2 + 4, y + 12], outline=FURN2, width=1)
    d.line([(x + w // 2, y + 12), (x + w // 2, y + h // 2)], fill=FURN2, width=1)


def book(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=1)
    d.line([(x + 3, y + 2), (x + 3, y + h - 2)], fill=FURN2, width=1)


def filing_cabinet(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], outline=FURN, width=2)
    for i in range(3):
        dy2 = y + 4 + i * (h - 8) // 3
        d.line([(x + 2, dy2), (x + w - 2, dy2)], fill=FURN2, width=1)
    d.ellipse([x + w // 2 - 2, y + h - 8, x + w // 2 + 2, y + h - 4], outline=FURN2, width=1)


def sofa_table(d, x, y, w, h):
    d.ellipse([x, y, x + w, y + h], outline=FURN, width=1)
    d.line([(x + w // 2, y + 2), (x + w // 2, y + h - 2)], fill=FURN2, width=1)
    d.line([(x + 2, y + h // 2), (x + w - 2, y + h // 2)], fill=FURN2, width=1)


FURNITURE = {
    'bed': bed,
    'desk': desk,
    'sofa': sofa,
    'dining': dining,
    'long_table': long_table,
    'shelf': shelf,
    'wardrobe': wardrobe,
    'nightstand': nightstand,
    'counter': counter,
    'stove': stove,
    'sink': sink,
    'fridge': fridge,
    'piano': piano,
    'reception': reception,
    'wine_rack': wine_rack,
    'barrel': barrel,
    'card_table': card_table,
    'round_table': round_table,
    'roulette': roulette,
    'easel': easel,
    'display_case': display_case,
    'podium': podium,
    'railing': railing,
    'pillar': decorative_pillar,
    'stage': stage,
    'vanity': vanity,
    'boxes': boxes,
    'map_table': map_table,
    'fountain': fountain,
    'book': book,
    'filing': filing_cabinet,
    'sofa_table': sofa_table,
    'plant': plant,
}


def draw_furniture(d, items, xoff=0, yoff=0):
    for item in items:
        fn = FURNITURE.get(item[0])
        if not fn:
            continue
        if item[0] == 'plant':
            fn(d, item[1] + xoff, item[2] + yoff, item[3])
        else:
            fn(d, item[1] + xoff, item[2] + yoff, item[3], item[4])


# Room-type -> furniture definitions
# (type, x, y, w, h)   — all relative to room origin
def get_furniture(name, w, h):
    m = 8
    name = name.replace('房间1', '卧室').replace('房间2', '卧室')
    cw, ch = w - 2 * m, h - 2 * m

    plans = {
        '大厅': [
            ('reception', m + 10, m + int(ch * 0.3), min(55, cw // 3), min(28, ch // 3)),
            ('sofa', m + cw - min(55, cw // 3), m + 4, min(50, cw // 3), min(18, ch // 5)),
            ('sofa', m + cw - min(55, cw // 3), m + ch - min(22, ch // 4), min(50, cw // 3), min(18, ch // 5)),
            ('plant', m + 8, m + ch - 10, 10),
            ('sofa_table', m + cw // 2 - 10, m + ch // 2 - 8, 18, 14),
        ],
        '餐厅': [
            ('dining', m + cw // 2 - 30, m + 4, 60, min(28, ch - 8)),
            ('dining', m + cw // 2 - 30, m + ch - min(32, ch // 2), 60, min(28, ch - 8)),
        ],
        '宴会厅': [
            ('long_table', m + 10, m + 8, min(100, cw - 20), 24),
            ('long_table', m + 10, m + ch - 32, min(100, cw - 20), 24),
        ],
        '厨房': [
            ('counter', m + 8, m + 4, min(80, cw - 16), 24),
            ('stove', m + 10, m + ch // 2 - 12, min(36, cw // 3), 22),
            ('sink', m + 52, m + ch // 2 - 12, min(36, cw // 3), 22),
            ('counter', m + 8, m + ch - 28, min(80, cw - 16), 20),
        ],
        '酒窖': [
            ('wine_rack', m + 8, m + 4, min(40, cw // 3 - 4), min(60, ch - 8)),
            ('wine_rack', m + cw - min(40, cw // 3 - 4), m + 4, min(40, cw // 3 - 4), min(60, ch - 8)),
            ('barrel', m + cw // 2 - 14, m + ch - 32, 26, 24),
        ],
        '老板套房':
        lambda: [
            ('bed', m + 4, m + 4, min(55, cw // 2), min(34, ch // 2)),
            ('desk', m + cw - min(45, cw // 2), m + 4, min(40, cw // 2), min(24, ch // 3)),
            ('wardrobe', m + cw - min(32, cw // 4), m + ch - min(50, ch - 40), min(28, cw // 4), min(46, ch - 40)),
            ('sofa', m + 4, m + ch - min(22, ch // 4), min(50, cw // 2), min(18, ch // 5)),
        ],
        '客房A': lambda: [
            ('bed', m + 4, m + 4, min(48, cw // 2), min(30, ch // 2)),
            ('nightstand', m + cw // 2 + 4, m + 4, 10, 10),
            ('desk', m + 4, m + ch - min(28, ch // 2), min(38, cw - 8), min(22, ch // 3)),
            ('wardrobe', m + cw - min(26, cw // 4), m + 4, min(22, cw // 4), min(42, ch - 8)),
        ],
        '客房B': lambda: [
            ('bed', m + 4, m + 4, min(48, cw // 2), min(30, ch // 2)),
            ('nightstand', m + cw // 2 + 4, m + 4, 10, 10),
            ('desk', m + 4, m + ch - min(28, ch // 2), min(38, cw - 8), min(22, ch // 3)),
            ('wardrobe', m + cw - min(26, cw // 4), m + 4, min(22, cw // 4), min(42, ch - 8)),
        ],
        '客房C': lambda: [
            ('bed', m + 4, m + 4, min(48, cw // 2), min(30, ch // 2)),
            ('nightstand', m + cw // 2 + 4, m + 4, 10, 10),
            ('desk', m + 4, m + ch - min(28, ch // 2), min(38, cw - 8), min(22, ch // 3)),
            ('wardrobe', m + cw - min(26, cw // 4), m + 4, min(22, cw // 4), min(42, ch - 8)),
        ],
        '露台': [
            ('plant', m + 8, m + 8, 10),
            ('plant', m + cw // 2, m + 8, 10),
            ('plant', m + cw - 18, m + h // 2 - 8, 10),
            ('round_table', m + cw // 2 - 10, m + ch - 24, 20, 18),
        ],
        '卧室': [
            ('bed', m + 4, m + 4, min(55, cw // 2), min(34, ch // 2)),
            ('wardrobe', m + cw - min(28, cw // 4), m + 4, min(24, cw // 4), min(40, ch - 8)),
            ('desk', m + 4, m + ch - min(28, ch // 2), min(38, cw - 8), min(22, ch // 3)),
        ],
        '走廊': [
            ('pillar', m + cw // 4, m + 4, 8, ch - 8),
            ('pillar', m + cw * 3 // 4, m + 4, 8, ch - 8),
        ],
        '化妆间': [
            ('vanity', m + cw // 2 - 18, m + 4, 36, min(24, ch // 2)),
            ('desk', m + 4, m + ch - min(28, ch // 2), min(36, cw // 3), min(22, ch // 3)),
            ('shelf', m + cw - min(36, cw // 3), m + 4, min(32, cw // 3), min(50, ch - 8)),
        ],
        '舞台': [
            ('stage', m + 10, m + ch // 2 - 20, cw - 20, 40),
            ('podium', m + cw // 2 - 10, m + 4, min(24, cw // 3), min(16, ch // 4)),
        ],
        '道具室': [
            ('shelf', m + 8, m + 4, min(40, cw // 2), min(40, ch - 8)),
            ('shelf', m + cw - min(40, cw // 2), m + 4, min(40, cw // 2), min(40, ch - 8)),
            ('boxes', m + cw // 2 - 12, m + ch - 30, 26, 22),
        ],
        '展厅': [
            ('display_case', m + 10, m + 8, min(50, cw // 3), min(40, ch - 16)),
            ('display_case', m + cw - min(50, cw // 3) - 10, m + 8, min(50, cw // 3), min(40, ch - 16)),
            ('podium', m + cw // 2 - 12, m + ch // 2 - 10, 24, 20),
        ],
        '办公室': [
            ('desk', m + 8, m + 8, min(45, cw // 2), min(24, ch // 3)),
            ('shelf', m + cw - min(40, cw // 3), m + 8, min(36, cw // 3), min(60, ch - 16)),
            ('filing', m + 8, m + ch - min(30, ch // 3), min(24, cw // 3), min(26, ch // 3)),
        ],
        '仓库': [
            ('shelf', m + 8, m + 4, min(45, cw // 2), min(50, ch - 8)),
            ('shelf', m + cw - min(45, cw // 2), m + 4, min(45, cw // 2), min(50, ch - 8)),
            ('boxes', m + cw // 2 - 12, m + ch // 2 - 12, 26, 22),
        ],
        '书房': [
            ('desk', m + cw // 2 - 20, m + 8, 40, min(24, ch // 3)),
            ('shelf', m + 8, m + ch // 2, min(35, cw // 3), min(40, ch // 2 - 8)),
            ('shelf', m + cw - min(35, cw // 3), m + 8, min(35, cw // 3), min(50, ch - 16)),
            ('book', m + cw // 2 + 8, m + 8, 12, 16),
        ],
        '客厅': [
            ('sofa', m + 8, m + 8, min(55, cw // 2), min(20, ch // 4)),
            ('sofa', m + 8, m + ch - min(24, ch // 4), min(55, cw // 2), min(20, ch // 4)),
            ('sofa_table', m + cw // 2 - 10, m + ch // 2 - 10, 20, 18),
            ('shelf', m + cw - min(36, cw // 3), m + 8, min(32, cw // 3), min(50, ch - 16)),
        ],
        '花园': [
            ('fountain', m + cw // 2 - 14, m + ch // 2 - 14, 28, 28),
            ('plant', m + 10, m + 10, 10),
            ('plant', m + cw - 18, m + 10, 10),
            ('plant', m + 10, m + ch - 18, 10),
            ('plant', m + cw - 18, m + ch - 18, 10),
        ],
        '露天甲板': [
            ('railing', m, m + 4, cw, 10),
            ('railing', m, m + ch - 14, cw, 10),
        ],
        '赌场': [
            ('card_table', m + cw // 2 - 18, m + 8, 34, 26),
            ('roulette', m + cw // 2 - 18, m + ch // 2 + 8, 34, 34),
            ('round_table', m + 8, m + ch - 34, 28, 26),
            ('round_table', m + cw - 36, m + ch - 34, 28, 26),
        ],
        '音乐厅': [
            ('piano', m + cw // 2 - 20, m + 8, 40, min(28, ch // 3)),
            ('stage', m + cw // 2 - 30, m + ch // 2, 60, min(30, ch // 3)),
        ],
        '医务室': [
            ('bed', m + 8, m + ch // 2 - 14, min(55, cw - 16), 28),
            ('desk', m + cw - min(40, cw // 3), m + 8, min(36, cw // 3), min(22, ch // 3)),
            ('filing', m + cw - min(28, cw // 4), m + ch - min(30, ch // 3), min(24, cw // 4), min(26, ch // 3)),
            ('shelf', m + 8, m + 8, min(35, cw // 3), min(30, ch // 3)),
        ],
        '船长室': [
            ('bed', m + 4, m + ch // 2, min(50, cw // 2), min(30, ch // 2 - 4)),
            ('desk', m + cw - min(45, cw // 2), m + 4, min(40, cw // 2), min(24, ch // 3)),
            ('map_table', m + cw // 2 - 16, m + ch // 2 - 14, 32, 28),
            ('wardrobe', m + 4, m + 4, min(26, cw // 3), min(40, ch // 2 - 4)),
        ],
        '豪华套房': [
            ('bed', m + 4, m + 4, min(60, cw // 2), min(36, ch // 2)),
            ('desk', m + cw - min(45, cw // 2), m + 4, min(40, cw // 2), min(24, ch // 3)),
            ('sofa', m + 4, m + ch - min(22, ch // 4), min(50, cw // 2), min(18, ch // 5)),
            ('wardrobe', m + cw - min(28, cw // 4), m + ch - min(46, ch - 36), min(24, cw // 4), min(42, ch - 36)),
        ],
        '普通客房': lambda: [
            ('bed', m + 4, m + 4, min(48, cw // 2), min(30, ch // 2)),
            ('desk', m + 4, m + ch - min(28, ch // 2), min(38, cw - 8), min(22, ch // 3)),
            ('wardrobe', m + cw - min(26, cw // 4), m + 4, min(22, cw // 4), min(42, ch - 8)),
        ],
        '船员休息室': [
            ('sofa', m + 8, m + 8, min(55, cw // 2), min(20, ch // 4)),
            ('sofa', m + 8, m + ch - min(24, ch // 4), min(55, cw // 2), min(20, ch // 4)),
            ('round_table', m + cw // 2 - 10, m + ch // 2 - 10, 20, 18),
            ('shelf', m + cw - min(36, cw // 3), m + 8, min(32, cw // 3), min(50, ch - 16)),
        ],
        '会客厅': [
            ('sofa', m + 8, m + 8, min(50, cw // 2), min(18, ch // 4)),
            ('sofa', m + 8, m + ch - min(22, ch // 4), min(50, cw // 2), min(18, ch // 4)),
            ('sofa_table', m + cw // 2 - 10, m + ch // 2 - 8, 20, 16),
            ('shelf', m + cw - min(32, cw // 3), m + 8, min(28, cw // 3), min(45, ch - 16)),
        ],
        '画室': [
            ('easel', m + cw // 2 - 12, m + 8, 24, min(30, ch // 2)),
            ('shelf', m + 8, m + ch // 2, min(35, cw - 16), min(30, ch // 2 - 8)),
            ('desk', m + cw - min(40, cw // 2), m + 8, min(36, cw // 2), min(22, ch // 3)),
        ],
        '主人卧室': [
            ('bed', m + 4, m + 4, min(55, cw // 2), min(34, ch // 2)),
            ('wardrobe', m + cw - min(28, cw // 4), m + 4, min(24, cw // 4), min(42, ch - 8)),
            ('desk', m + 4, m + ch - min(28, ch // 2), min(38, cw - 8), min(22, ch // 3)),
            ('nightstand', m + cw // 2 + 4, m + 4, 10, 10),
        ],
    }

    result = plans.get(name)
    if result is None:
        return []
    if callable(result):
        return result()
    return result


def generate_case_background(case_file, output_dir):
    with open(case_file, 'r', encoding='utf-8') as f:
        case_data = json.load(f)

    scene = case_data.get('scene', {})
    areas = scene.get('areas', [])
    doors = scene.get('doors', [])

    max_x = max((a['x'] + a['width'] for a in areas), default=800)
    max_y = max((a['y'] + a['height'] for a in areas), default=400)
    padding = 30
    canvas_w = int(max_x + padding * 2)
    canvas_h = int(max_y + padding * 2)

    bg_color = (13, 17, 28)
    img = Image.new('RGB', (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(img)

    # Grid
    grid_color = (20, 28, 46)
    for gx in range(0, canvas_w, 40):
        draw.line([(gx, 0), (gx, canvas_h)], fill=grid_color, width=1)
    for gy in range(0, canvas_h, 40):
        draw.line([(0, gy), (canvas_w, gy)], fill=grid_color, width=1)

    # Room fills
    room_fill = (22, 32, 56)
    for area in areas:
        ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
        draw.rectangle([ax - 2, ay - 2, ax + aw + 2, ay + ah + 2], fill=room_fill)

    # Build door-edge map
    door_edges = {}
    for door in doors:
        dx, dy, dw, dh = door['x'], door['y'], door['width'], door['height']
        dcx, dcy = dx + dw / 2, dy + dh / 2
        for area in areas:
            ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
            edges = []
            snap = 20
            if abs(dcy - ay) < snap and ax - snap <= dcx <= ax + aw + snap:
                edges.append(('top', area['name']))
            if abs(dcy - (ay + ah)) < snap and ax - snap <= dcx <= ax + aw + snap:
                edges.append(('bottom', area['name']))
            if abs(dcx - ax) < snap and ay - snap <= dcy <= ay + ah + snap:
                edges.append(('left', area['name']))
            if abs(dcx - (ax + aw)) < snap and ay - snap <= dcy <= ay + ah + snap:
                edges.append(('right', area['name']))
            for edge, name in edges:
                door_edges.setdefault((name, edge), []).append((dx, dy, dw, dh))

    # Draw furniture before walls (so walls overlay)
    for area in areas:
        items = get_furniture(area['name'], area['width'], area['height'])
        draw_furniture(draw, items, area['x'], area['y'])

    # Draw walls with gaps
    for area in areas:
        ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
        top_doors = door_edges.get((area['name'], 'top'), [])
        bottom_doors = door_edges.get((area['name'], 'bottom'), [])
        left_doors = door_edges.get((area['name'], 'left'), [])
        right_doors = door_edges.get((area['name'], 'right'), [])

        for y_or_x, horiz, doors_on, start, end in [
            (ay, True, top_doors, ax, ax + aw),
            (ay + ah, True, bottom_doors, ax, ax + aw),
            (ax, False, left_doors, ay, ay + ah),
            (ax + aw, False, right_doors, ay, ay + ah),
        ]:
            segs = []
            cur = start
            ds = sorted(doors_on, key=lambda d: d[0] if horiz else d[1])
            for door in ds:
                ds2 = door[0] if horiz else door[1]
                de2 = ds2 + (door[2] if horiz else door[3])
                if cur < ds2 - 1:
                    segs.append((cur, ds2))
                cur = max(cur, de2)
            if cur < end:
                segs.append((cur, end))
            for s, e in segs:
                if horiz:
                    wall_seg(draw, s, y_or_x, e, y_or_x)
                else:
                    wall_seg(draw, y_or_x, s, y_or_x, e)

    # Door jamb lines
    for door in doors:
        x, y, w, h = door['x'], door['y'], door['width'], door['height']
        if w > h:
            draw.line([(x, y - 3), (x, y + 3)], fill=WALL, width=2)
            draw.line([(x + w, y - 3), (x + w, y + 3)], fill=WALL, width=2)
        else:
            draw.line([(x - 3, y), (x + 3, y)], fill=WALL, width=2)
            draw.line([(x - 3, y + h), (x + 3, y + h)], fill=WALL, width=2)

    # Corner dots
    for area in areas:
        ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
        for cx, cy in [(ax, ay), (ax + aw, ay), (ax, ay + ah), (ax + aw, ay + ah)]:
            corner_dot(draw, cx, cy)

    # Load font
    font = None
    for fp in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]:
        try:
            font = ImageFont.truetype(fp, 14)
            break
        except:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Stair markers
    for sd in [d for d in doors if '楼梯' in d['name']]:
        x, y, w, h = sd['x'], sd['y'], sd['width'], sd['height']
        cx, cy = x + w // 2, y + h // 2
        for i in range(4):
            sy = cy - h // 2 + 3 + i * (h - 6) // 4
            draw.line([(x + 4, sy), (x + w - 4, sy)], fill=(90, 120, 175), width=1)
        a1 = next((a for a in areas if a['name'] == sd['area1']), None)
        a2 = next((a for a in areas if a['name'] == sd['area2']), None)
        if a1 and a2:
            d1 = (cx - (a1['x'] + a1['width'] / 2))**2 + (cy - (a1['y'] + a1['height'] / 2))**2
            d2 = (cx - (a2['x'] + a2['width'] / 2))**2 + (cy - (a2['y'] + a2['height'] / 2))**2
            if d2 < d1:
                dest, closer_cy = sd['area1'], a2['y'] + a2['height'] / 2
                target_cy = a1['y'] + a1['height'] / 2
            else:
                dest, closer_cy = sd['area2'], a1['y'] + a1['height'] / 2
                target_cy = a2['y'] + a2['height'] / 2
            arrow = "\u2191" if target_cy < closer_cy else "\u2193"
        else:
            dest, arrow = '', "\u21c5"
        draw.text((cx - 4, cy - 9), arrow, fill=(120, 150, 210))
        if dest:
            bb = draw.textbbox((0, 0), dest, font=font)
            dw = bb[2] - bb[0]
            draw.text((cx - dw // 2, cy + 4), dest, fill=(140, 175, 220), font=font)

    # Room labels
    for area in areas:
        ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
        name = area['name']
        bb = draw.textbbox((0, 0), name, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        tx = ax + (aw - tw) / 2
        ty = ay + (ah - th) / 2
        draw.text((tx + 1, ty + 1), name, fill=(13, 17, 28), font=font)
        draw.text((tx, ty), name, fill=(150, 190, 240), font=font)
        draw.line([(tx, ty + th + 3), (tx + tw, ty + th + 3)], fill=(80, 110, 170), width=1)

    # Save
    case_id = os.path.splitext(os.path.basename(case_file))[0]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'{case_id}_bg.png')
    img.save(output_path)
    print(f"  {output_path} ({canvas_w}x{canvas_h})")
    return output_path


def main():
    cases_dir = 'unheared/cases'
    output_dir = 'unheared/resources/backgrounds'
    print("=== \u751f\u6210\u6848\u4ef6\u80cc\u666f\u56fe ===")
    case_files = sorted([f for f in os.listdir(cases_dir) if f.endswith('.json')])
    for case_file in case_files:
        case_path = os.path.join(cases_dir, case_file)
        generate_case_background(case_path, output_dir)
    print(f"\n=== \u5b8c\u6210\uff01\u80cc\u666f\u56fe\u4fdd\u5b58\u5728 {output_dir}/ ===")


if __name__ == '__main__':
    main()
