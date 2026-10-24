#!/usr/bin/env python3
"""把剧本文件 game/cases/<id>/case.play 编译成 case.json。

剧本写“谁在什么时候走到哪、说什么”，脚本负责：
- 按房间矩形自动放门，按门 / 楼梯规划走位路线，生成关键帧（走 150 px/s，跑 300 px/s）；
- 台词按顺序排时间：说话的人先走到位再开口，说完再离开；
- 已有语音（同一角色、同一句文本）保留音频并用真实时长重新排时间；
- 保留 case.json 里已摆好的家具和地板材质；
- 检查节奏（tools/pacing.py）：全图空窗期过长、过多，开头、结尾留白过长时报错，不写 case.json。

用法：
  python3 tools/compose_case.py case8 [case9 ...]
  python3 tools/compose_case.py case8 --check     # 只检查、打印时间表，不写文件

剧本格式见 docs/case-authoring.md 第 12 节。
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pacing  # noqa: E402
from tts_lines import loudness_for, probe_duration, split_directions  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "game", "cases")

WALK_SPEED = 150.0
RUN_SPEED = 300.0
STAIR_FACTOR = 0.5
MOUTH_DEPTH = 6.0  # 门口关键帧离墙的距离
DOOR_WIDTH = 40.0
MAX_DOOR_GAP = 80.0
LINE_GAP = 0.4  # 一句说完到下一句开口
LEAD = 0.3  # 到位后多久开口 / 说完多久出发
CHARS_PER_SECOND = 4.3  # 没有语音时估算时长
TAIL_PAD = 8.0  # 时长写“自动”时，最后一声之后留的秒数
SPOT_STEP = 14.0
SPOT_INSET = 30.0
SPOT_CLEAR = 36.0  # 站位离门口、楼梯口的距离
SPOT_NEAR = 62.0  # 和别人说话时的理想距离
SPOT_MIN = 46.0
DELAY_WARN = 2.5
FOOTPRINT = 0.82  # 与 Prop.FOOTPRINT 一致
BODY = 13.0  # 绕开家具时角色圆点的半径
CATALOG_PATH = os.path.join(ROOT, "game", "art", "props", "catalog.json")

Point = tuple[float, float]


class PlayError(Exception):
    pass


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def parse_point(text: str) -> Point:
    x, y = text.lstrip("@").split(",")
    return float(x), float(y)


def parse_time(text: str) -> float:
    text = text.strip()
    if ":" in text:
        m, s = text.split(":")
        return int(m) * 60 + float(s)
    return float(text)


@dataclass
class Room:
    name: str
    floor: int
    x1: float
    y1: float
    x2: float
    y2: float
    material: str = ""
    outdoor: bool = False

    @property
    def center(self) -> Point:
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2

    def contains(self, p: Point, margin: float = 0.0) -> bool:
        return self.x1 + margin <= p[0] <= self.x2 - margin and self.y1 + margin <= p[1] <= self.y2 - margin


@dataclass
class Link:
    name: str
    a: str
    b: str
    stair: bool
    ends: dict[str, Point]
    position: Point = (0.0, 0.0)
    size: Point = (0.0, 0.0)
    closed: bool = False


@dataclass
class Character:
    id: str
    name: str
    color: str
    room: str
    pos: Point
    prompt: str = ""
    prompt_text: str = ""
    track: list[dict] = field(default_factory=list)
    free_at: float = 0.0  # 说完 / 走到之后最早能做下一件事的时间
    busy_reason: str = ""


class Play:
    def __init__(self, case_id: str, text: str):
        self.case_id = case_id
        self.header: dict[str, str] = {}
        self.floors: list[str] = []
        self.rooms: dict[str, Room] = {}
        self.links: list[Link] = []
        self.characters: dict[str, Character] = {}
        self.questions: list[dict] = []
        self.script: list[tuple[int, str]] = []
        self.blockers: dict[str, list[tuple[float, float, float, float]]] = {}
        self._parse(text)

    def set_props(self, props: list[dict]) -> None:
        """挡路的家具：角色站位不压在上面，房间内的路线绕开它们。"""
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
        self.blockers = {}
        for p in props:
            entry = catalog.get(p["type"])
            if not entry or not entry["block"]:
                continue
            x, y = p["position"]
            self.blockers.setdefault(p["room"], []).append((x, y, entry["size"][0] * FOOTPRINT / 2, entry["size"][1] * FOOTPRINT / 2))
        for ch in self.characters.values():
            start = self.free_point(self.rooms[ch.room], ch.pos)
            ch.pos = start
            ch.track[0]["p"] = list(start)

    def blocked(self, room: str, p: Point, pad: float = BODY) -> bool:
        return any(abs(p[0] - x) < w + pad and abs(p[1] - y) < h + pad for x, y, w, h in self.blockers.get(room, []))

    def clear(self, room: str, a: Point, b: Point, pad: float = BODY) -> bool:
        if room not in self.blockers:
            return True
        steps = max(int(dist(a, b) / 3), 1)
        return not any(
            self.blocked(room, (a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps), pad)
            for i in range(1, steps)
        )

    def detour(self, room: Room, a: Point, b: Point) -> list[Point]:
        """a→b 被家具挡住时，找一个（或两个）中间点绕过去；地方太窄就贴着家具走。"""
        for pad in (BODY, 4.0):
            if self.clear(room.name, a, b, pad):
                return []
            found = self._detour(room, a, b, pad)
            if found:
                return found
        return []

    def _detour(self, room: Room, a: Point, b: Point, pad: float) -> list[Point]:
        step = SPOT_STEP / 2
        xs, ys = _frange(room.x1 + 10, room.x2 - 10, step), _frange(room.y1 + 10, room.y2 - 10, step)
        free = {(i, j) for j, y in enumerate(ys) for i, x in enumerate(xs) if not self.blocked(room.name, (x, y), pad)}

        def pt(c: tuple[int, int]) -> Point:
            return xs[c[0]], ys[c[1]]

        def nearest_visible(p: Point) -> tuple[int, int] | None:
            ranked = sorted(free, key=lambda c: dist(pt(c), p))[:40]
            return next((c for c in ranked if self.clear(room.name, p, pt(c), pad)), None)

        src, dst = nearest_visible(a), nearest_visible(b)
        if src is None or dst is None:
            return []
        cost = {src: 0.0}
        prev: dict[tuple[int, int], tuple[int, int]] = {}
        heap = [(0.0, src)]
        while heap:
            c, cell = heapq.heappop(heap)
            if cell == dst:
                break
            if c > cost[cell]:
                continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nxt = (cell[0] + di, cell[1] + dj)
                if nxt not in free or (di and dj and ((cell[0] + di, cell[1]) not in free or (cell[0], cell[1] + dj) not in free)):
                    continue
                nc = c + math.hypot(di, dj)
                if nc < cost.get(nxt, math.inf):
                    cost[nxt], prev[nxt] = nc, cell
                    heapq.heappush(heap, (nc, nxt))
        if dst not in cost:
            return []
        cells = [dst]
        while cells[-1] != src:
            cells.append(prev[cells[-1]])
        pts = [a] + [pt(c) for c in reversed(cells)] + [b]
        out, i = [], 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1 and not self.clear(room.name, pts[i], pts[j], pad):
                j -= 1
            if j < len(pts) - 1:
                out.append((round(pts[j][0], 1), round(pts[j][1], 1)))
            i = j
        return out

    def free_point(self, room: Room, p: Point) -> Point:
        if not self.blocked(room.name, p):
            return p
        free = [
            (x, y)
            for y in _frange(room.y1 + SPOT_INSET, room.y2 - SPOT_INSET, SPOT_STEP / 2)
            for x in _frange(room.x1 + SPOT_INSET, room.x2 - SPOT_INSET, SPOT_STEP / 2)
            if not self.blocked(room.name, (x, y))
        ]
        return min(free, key=lambda q: dist(p, q), default=p)

    # ------------------------------------------------------------ parsing

    def _parse(self, text: str) -> None:
        section = "header"
        last_key = ""
        current_q: dict | None = None
        current_ch: Character | None = None
        for n, raw in enumerate(text.splitlines(), start=1):
            if raw.startswith("## "):
                section = raw[3:].strip()
                continue
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            try:
                indented = raw[0] in " \t"
                line = raw.strip()
                if section == "header":
                    if indented and last_key:
                        self.header[last_key] += "\n" + line
                        continue
                    key, value = re.split(r"[:：]", line, maxsplit=1)
                    last_key = key.strip()
                    self.header[last_key] = value.strip()
                elif section == "地图":
                    self._parse_map(line)
                elif section == "角色":
                    if indented and current_ch:
                        word, rest = line.split(None, 1)
                        if word != "音色":
                            raise PlayError(f"未知的角色属性 {word}")
                        path, prompt_text = rest.split(None, 1)
                        current_ch.prompt, current_ch.prompt_text = path, prompt_text.strip()
                    else:
                        current_ch = self._parse_character(line)
                elif section == "问题":
                    word, rest = line.split(None, 1)
                    if word == "问":
                        qid, prompt = rest.split(None, 1)
                        current_q = {"id": qid, "prompt": prompt.strip(), "options": [], "answer": ""}
                        self.questions.append(current_q)
                    elif word == "选项" and current_q:
                        current_q["options"] = [o.strip() for o in rest.split("/") if o.strip()]
                    elif word == "答案" and current_q:
                        current_q["answer"] = rest.strip()
                    else:
                        raise PlayError(f"无法理解：{line}")
                elif section == "剧本":
                    self.script.append((n, line))
                else:
                    raise PlayError(f"未知的段落 {section}")
            except PlayError as e:
                raise PlayError(f"第 {n} 行：{e}") from None
            except ValueError:
                raise PlayError(f"第 {n} 行：格式不对：{raw.strip()}") from None

    def _parse_map(self, line: str) -> None:
        words = line.split()
        kind = words[0]
        if kind == "楼层":
            self.floors = words[1:]
        elif kind == "房间":
            name, floor, p1, p2 = words[1], int(words[2]), parse_point(words[3]), parse_point(words[4])
            room = Room(name, floor, p1[0], p1[1], p2[0], p2[1])
            for opt in words[5:]:
                if opt == "户外":
                    room.outdoor = True
                elif opt.startswith("地板="):
                    room.material = opt.split("=", 1)[1]
                else:
                    raise PlayError(f"未知的房间选项 {opt}")
            self.rooms[name] = room
        elif kind == "门":
            a, b = self._room(words[1]), self._room(words[2])
            at = next((parse_point(w) for w in words[3:] if w.startswith("@")), None)
            link = self._make_door(a, b, at)
            link.closed = "关" in words[3:]
            self.links.append(link)
        elif kind == "楼梯":
            a, b = self._room(words[1]), self._room(words[2])
            ea, eb = parse_point(words[3]), parse_point(words[4])
            if not a.contains(ea, 4) or not b.contains(eb, 4):
                raise PlayError(f"楼梯 {a.name}-{b.name} 的两端必须分别在两个房间里")
            self.links.append(Link(f"{a.name}楼梯", a.name, b.name, True, {a.name: ea, b.name: eb}))
        else:
            raise PlayError(f"未知的地图条目 {kind}")

    def _make_door(self, a: Room, b: Room, at: Point | None) -> Link:
        if a.floor != b.floor:
            raise PlayError(f"门 {a.name}-{b.name} 两侧不在同一层，用楼梯")
        name = f"{a.name}-{b.name}"
        ox = (max(a.x1, b.x1), min(a.x2, b.x2))
        oy = (max(a.y1, b.y1), min(a.y2, b.y2))
        if ox[1] - ox[0] >= DOOR_WIDTH and (0 <= b.y1 - a.y2 <= MAX_DOOR_GAP or 0 <= a.y1 - b.y2 <= MAX_DOOR_GAP):
            upper, lower = (a, b) if a.y2 <= b.y1 else (b, a)
            x = at[0] if at else (ox[0] + ox[1]) / 2
            if not ox[0] + DOOR_WIDTH / 2 <= x <= ox[1] - DOOR_WIDTH / 2:
                raise PlayError(f"门 {name} 的位置不在两个房间相对的墙上")
            y = (upper.y2 + lower.y1) / 2
            ends = {upper.name: (x, upper.y2 - MOUTH_DEPTH), lower.name: (x, lower.y1 + MOUTH_DEPTH)}
            return Link(name, a.name, b.name, False, ends, (x, y), (DOOR_WIDTH, 20.0))
        if oy[1] - oy[0] >= DOOR_WIDTH and (0 <= b.x1 - a.x2 <= MAX_DOOR_GAP or 0 <= a.x1 - b.x2 <= MAX_DOOR_GAP):
            left, right = (a, b) if a.x2 <= b.x1 else (b, a)
            y = at[1] if at else (oy[0] + oy[1]) / 2
            if not oy[0] + DOOR_WIDTH / 2 <= y <= oy[1] - DOOR_WIDTH / 2:
                raise PlayError(f"门 {name} 的位置不在两个房间相对的墙上")
            x = (left.x2 + right.x1) / 2
            ends = {left.name: (left.x2 - MOUTH_DEPTH, y), right.name: (right.x1 + MOUTH_DEPTH, y)}
            return Link(name, a.name, b.name, False, ends, (x, y), (20.0, DOOR_WIDTH))
        raise PlayError(f"房间 {a.name} 和 {b.name} 没有相对的墙（间距不超过 {MAX_DOOR_GAP:.0f}）")

    def _parse_character(self, line: str) -> Character:
        words = line.split()
        cid, name, color, room = words[:4]
        r = self._room(room)
        pos = parse_point(words[4]) if len(words) > 4 else r.center
        if not r.contains(pos):
            raise PlayError(f"角色 {cid} 的起点不在 {room} 里")
        ch = Character(cid, name, color, room, pos)
        ch.track.append({"t": 0.0, "p": list(pos), "m": "idle", "room": room})
        self.characters[cid] = ch
        return ch

    def _room(self, name: str) -> Room:
        if name not in self.rooms:
            raise PlayError(f"没有房间 {name}")
        return self.rooms[name]

    # ------------------------------------------------------------ routing

    def route(self, src: str, dst: str) -> list[Link]:
        """按步行距离找最短的门 / 楼梯序列。"""
        best: dict[str, float] = {src: 0.0}
        prev: dict[str, tuple[str, Link]] = {}
        todo = {src}
        while todo:
            cur = min(todo, key=lambda r: best[r])
            todo.remove(cur)
            if cur == dst:
                break
            for link in self.links:
                if cur not in (link.a, link.b):
                    continue
                nxt = link.b if cur == link.a else link.a
                cost = best[cur] + dist(self.rooms[cur].center, link.ends[cur]) + dist(link.ends[nxt], self.rooms[nxt].center)
                if cost < best.get(nxt, math.inf):
                    best[nxt] = cost
                    prev[nxt] = (cur, link)
                    todo.add(nxt)
        if dst != src and dst not in prev:
            raise PlayError(f"{src} 到 {dst} 没有通路")
        path = []
        node = dst
        while node != src:
            node, link = prev[node]
            path.append(link)
        return list(reversed(path))

    def position_at(self, ch: Character, t: float) -> tuple[Point, str]:
        track = ch.track
        if t >= track[-1]["t"]:
            return tuple(track[-1]["p"]), track[-1]["room"]
        for k0, k1 in zip(track, track[1:]):
            if k0["t"] <= t < k1["t"]:
                f = (t - k0["t"]) / max(k1["t"] - k0["t"], 1e-6)
                p = (k0["p"][0] + (k1["p"][0] - k0["p"][0]) * f, k0["p"][1] + (k1["p"][1] - k0["p"][1]) * f)
                return p, k0["room"]
        return tuple(track[0]["p"]), track[0]["room"]

    def pick_spot(self, mover: Character, room: Room, t: float, near: Point | None) -> Point:
        others = []
        for ch in self.characters.values():
            if ch is mover:
                continue
            p, r = self.position_at(ch, t)
            if r == room.name:
                others.append(p)
        avoid = [link.ends[room.name] for link in self.links if room.name in link.ends]
        best, best_cost = room.center, math.inf
        y = room.y1 + SPOT_INSET
        while y <= room.y2 - SPOT_INSET:
            x = room.x1 + SPOT_INSET
            while x <= room.x2 - SPOT_INSET:
                p = (x, y)
                x += SPOT_STEP
                if any(dist(p, a) < SPOT_CLEAR for a in avoid) or self.blocked(room.name, p):
                    continue
                if p[0] < room.x1 + 110 and p[1] < room.y1 + 34:  # 房间名
                    continue
                if any(dist(p, o) < SPOT_MIN for o in others):
                    continue
                if near is not None:
                    cost = abs(dist(p, near) - SPOT_NEAR) * 3
                elif others:
                    cost = abs(min(dist(p, o) for o in others) - SPOT_NEAR) * 2 + dist(p, room.center) * 0.3
                else:
                    cost = dist(p, room.center)
                if cost < best_cost:
                    best, best_cost = p, cost
            y += SPOT_STEP
        return round(best[0], 1), round(best[1], 1)

    def move(self, ch: Character, depart: float, room_name: str, target: Point | None, near: str | None, run: bool) -> float:
        room = self._room(room_name)
        speed = RUN_SPEED if run else WALK_SPEED
        mode = "run" if run else "walk"
        legs: list[tuple[Point, float, str]] = []
        here, here_room = ch.pos, ch.room
        for link in self.route(ch.room, room_name):
            other = link.b if here_room == link.a else link.a
            entry, exit_ = link.ends[here_room], link.ends[other]
            legs.append((entry, dist(here, entry) / speed, here_room))
            if link.stair:
                # 爬楼梯时停在楼梯口，然后瞬间换到另一层，避免圆点在地图上划过别的房间
                legs.append((entry, dist(entry, exit_) / (speed * STAIR_FACTOR), here_room))
                legs.append((exit_, 0.05, other))
            else:
                legs.append((exit_, dist(entry, exit_) / speed, other))
            here, here_room = exit_, other
        rough_arrival = depart + sum(leg[1] for leg in legs) + dist(here, room.center) / speed
        if target is None:
            near_p = self.position_at(self.characters[near], rough_arrival)[0] if near else None
            target = self.pick_spot(ch, room, rough_arrival, near_p)
        if not room.contains(target, 8):
            raise PlayError(f"{target} 不在 {room_name} 里")
        target = self.free_point(room, target)
        legs.append((target, dist(here, target) / speed, room_name))
        legs = self._avoid_props(ch.pos, legs, speed)

        track = ch.track
        if track[-1]["t"] > depart + 1e-6:
            raise PlayError(f"角色 {ch.id} 在 {depart:.1f}s 出发，但之前的安排到 {track[-1]['t']:.1f}s 才结束")
        if abs(track[-1]["t"] - depart) < 1e-6:
            track[-1]["m"] = mode
        else:
            track.append({"t": round(depart, 3), "p": [round(ch.pos[0], 1), round(ch.pos[1], 1)], "m": mode, "room": ch.room})
        t = depart
        for i, (p, dt, r) in enumerate(legs):
            t += max(dt, 0.05)
            last = i == len(legs) - 1
            track.append({"t": round(t, 3), "p": [round(p[0], 1), round(p[1], 1)], "m": "idle" if last else mode, "room": r})
        ch.pos, ch.room = target, room_name
        return t


    def _avoid_props(self, start: Point, legs: list[tuple[Point, float, str]], speed: float) -> list:
        out = []
        prev, prev_room = start, None
        for p, dt, r in legs:
            if r == prev_room or prev_room is None:
                for w in self.detour(self.rooms[r], prev, p):
                    out.append((w, dist(prev, w) / speed, r))
                    prev = w
                dt = dist(prev, p) / speed if out and out[-1][2] == r else dt
            out.append((p, dt, r))
            prev, prev_room = p, r
        return out


def _frange(a: float, b: float, step: float) -> list[float]:
    n = int((b - a) // step)
    return [a + i * step for i in range(n + 1)]


@dataclass
class Compiled:
    lines: list[dict]
    sfx: list[dict]
    warnings: list[str]
    scenes: list[str]


def estimate(text: str) -> float:
    spoken, _ = split_directions(text)
    return round(len(spoken) / CHARS_PER_SECOND + 0.6, 2)


def compile_script(play: Play, case_dir: str, old_lines: dict, duration: float) -> Compiled:
    lines: list[dict] = []
    sfx: list[dict] = []
    warnings: list[str] = []
    scenes: list[str] = []
    cursor = 0.0
    scene_start = scene_line = 0
    line_re = re.compile(r"^(\w+)\s*[:：]\s*(.+?)\s*(?:\{([^}]*)\})?$")
    move_re = re.compile(r"^(\w+)\s*(->|=>)\s*(\S+)(?:\s+(\S+))?$")
    for n, raw in play.script:
        try:
            if raw.startswith("@"):
                if scene_line:
                    scenes.append(f"第 {scene_line} 行 {_mmss(scene_start)} → {_mmss(cursor)}")
                cursor = scene_start = parse_time(raw[1:])
                scene_line = n
                continue
            if raw.startswith("等 ") or raw.startswith("等\t"):
                arg = raw[1:].strip()
                if arg in play.characters:
                    cursor = max(cursor, play.characters[arg].free_at)
                else:
                    cursor += float(arg)
                continue
            if raw.startswith("~"):
                sfx.append(_sound(play, case_dir, raw[1:].split(), cursor))
                continue
            m = move_re.match(raw)
            if m and m.group(1) in play.characters:
                ch = play.characters[m.group(1)]
                depart = max(cursor, ch.free_at)
                if depart - cursor > DELAY_WARN:
                    warnings.append(f"第 {n} 行：{ch.id} 晚了 {depart - cursor:.1f}s 才出发（{ch.busy_reason}）")
                arg = m.group(4)
                target = near = None
                if arg:
                    if arg in play.characters:
                        near = arg
                    else:
                        target = parse_point(arg)
                arrival = play.move(ch, depart, m.group(3), target, near, m.group(2) == "=>")
                ch.free_at, ch.busy_reason = arrival + LEAD, f"第 {n} 行走到 {m.group(3)}"
                continue
            m = line_re.match(raw)
            if not m or m.group(1) not in play.characters:
                raise PlayError(f"无法理解：{raw}")
            ch = play.characters[m.group(1)]
            text = m.group(2)
            opts = (m.group(3) or "").split()
            start = max(cursor, ch.free_at)
            if start - cursor > DELAY_WARN:
                warnings.append(f"第 {n} 行：{ch.id} 的台词推迟了 {start - cursor:.1f}s（{ch.busy_reason}）")
            line = {"speaker": ch.id, "start": round(start, 3), "duration": estimate(text), "text": text}
            old = old_lines.get((ch.id, text))
            if old and old.get("audio") and os.path.exists(os.path.join(case_dir, old["audio"])):
                line.update({k: old[k] for k in ("duration", "audio", "tts") if k in old})
            _, directions = split_directions(text)
            loud = loudness_for(directions)
            for o in opts:
                if o == "无语气":
                    line["tts_instruct"] = False
                else:
                    loud = float(o)
            if loud is not None:
                line["loudness"] = loud
            lines.append(line)
            end = start + line["duration"]
            ch.free_at, ch.busy_reason = end + LEAD, f"第 {n} 行的台词"
            cursor = end + LINE_GAP
            if end > duration:
                warnings.append(f"第 {n} 行：台词在 {end:.1f}s 结束，超过案件时长")
        except PlayError as e:
            raise PlayError(f"第 {n} 行：{e}") from None
    if scene_line:
        scenes.append(f"第 {scene_line} 行 {_mmss(scene_start)} → {_mmss(cursor)}")
    lines.sort(key=lambda l: l["start"])
    return Compiled(lines, sfx, warnings, scenes)


def _mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def _sound(play: Play, case_dir: str, words: list[str], cursor: float) -> dict:
    """~ 标签 音频文件 房间|角色 [响度]"""
    label, audio, where = words[0], words[1], words[2]
    path = os.path.join(case_dir, audio)
    if not os.path.exists(path):
        raise PlayError(f"音效文件不存在：{audio}")
    ev = {"time": round(cursor, 3), "duration": round(probe_duration(path), 3), "audio": audio, "label": label}
    if where in play.characters:
        ev["attach_to"] = where
    else:
        c = play._room(where).center
        ev["position"] = [c[0], c[1]]
    ev["loudness"] = float(words[3]) if len(words) > 3 else 1.0
    return ev


def build(case_id: str, check: bool) -> None:
    case_dir = os.path.join(CASES, case_id)
    play_path = os.path.join(case_dir, "case.play")
    json_path = os.path.join(case_dir, "case.json")
    with open(play_path, encoding="utf-8") as f:
        play = Play(case_id, f.read())
    old = {}
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            old = json.load(f)
    old_lines = {(l["speaker"], l["text"]): l for l in old.get("voice_lines", [])}
    old_rooms = {r["name"]: r for r in old.get("map", {}).get("rooms", [])}
    old_chars = {c["id"]: c for c in old.get("characters", [])}

    play.set_props(old.get("map", {}).get("props", []))
    h = play.header
    auto = h["时长"].strip() == "自动"
    duration = math.inf if auto else float(h["时长"])
    compiled = compile_script(play, case_dir, old_lines, duration)
    if auto:
        ends = [l["start"] + l["duration"] for l in compiled.lines] + [s["time"] + s["duration"] for s in compiled.sfx]
        duration = math.ceil(max(ends, default=0.0) + TAIL_PAD)

    rooms = []
    for r in play.rooms.values():
        room = {"name": r.name, "floor": r.floor, "polygon": [[r.x1, r.y1], [r.x2, r.y1], [r.x2, r.y2], [r.x1, r.y2]]}
        material = r.material or old_rooms.get(r.name, {}).get("floor_material", "")
        if material:
            room["floor_material"] = material
        if r.outdoor:
            room["outdoor"] = True
        rooms.append(room)
    doors = [
        {"name": l.name, "room_a": l.a, "room_b": l.b, "position": list(l.position), "size": list(l.size)}
        | ({"open": False} if l.closed else {})
        for l in play.links
        if not l.stair
    ]
    stairs = [
        {"name": l.name, "room_a": l.a, "room_b": l.b, "end_a": list(l.ends[l.a]), "end_b": list(l.ends[l.b])}
        for l in play.links
        if l.stair
    ]
    characters = []
    for i, ch in enumerate(play.characters.values(), start=1):
        c = {"id": ch.id, "name": ch.name, "label": str(i), "color": ch.color, "track": ch.track}
        prompt = (ch.prompt, ch.prompt_text) if ch.prompt else (
            old_chars.get(ch.id, {}).get("voice_prompt"), old_chars.get(ch.id, {}).get("voice_prompt_text"))
        if prompt[0]:
            c["voice_prompt"], c["voice_prompt_text"] = prompt
        characters.append(c)
    names = [c.name for c in play.characters.values()]
    questions = []
    for q in play.questions:
        opts = q["options"]
        kind = "character" if not opts or all(o in names for o in opts) else "choice"
        out = {"id": q["id"], "kind": kind, "prompt": q["prompt"], "options": opts, "answer": q["answer"]}
        if q["answer"] not in (opts or names):
            raise PlayError(f"问题 {q['id']} 的答案不在选项里")
        questions.append(out)

    case = {
        "format": 1,
        "id": case_id,
        "title": h["标题"],
        "description": h.get("简介", ""),
        "duration": duration,
        "truth": h.get("真相", ""),
        "cover": h.get("封面", ""),
        "map": {
            "floors": play.floors or ["一层"],
            "backdrop": h.get("外景", ""),
            "rooms": rooms,
            "doors": doors,
            "stairs": stairs,
            "props": old.get("map", {}).get("props", []),
        },
        "characters": characters,
        "voice_lines": compiled.lines,
        "sfx": sorted(compiled.sfx, key=lambda s: s["time"]),
        "questions": questions,
    }
    voiced = sum(1 for l in compiled.lines if l.get("audio"))
    last = max((l["start"] + l["duration"] for l in compiled.lines), default=0)
    print(f"{case_id}：{len(characters)} 名角色，{len(compiled.lines)} 句台词（{voiced} 句有语音），最后一句在 {last / 60:.1f} 分钟结束")
    for w in compiled.warnings:
        print("  " + w)
    errors, notes = pacing.check(case)
    for w in notes:
        print("  节奏提示：" + w)
    for e in errors:
        print("  节奏错误：" + e)
    if check:
        print(f"  时长 {_mmss(duration)}")
        for scene in compiled.scenes:
            print("  场景 " + scene)
        return
    if errors:
        raise PlayError(f"节奏检查有 {len(errors)} 个错误，没有写入 case.json（用 --check 查看场景时间表）")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=1)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="+")
    parser.add_argument("--check", action="store_true", help="只检查，不写 case.json")
    args = parser.parse_args()
    for case_id in args.cases:
        try:
            build(case_id, args.check)
        except PlayError as e:
            sys.exit(f"{case_id}：{e}")


if __name__ == "__main__":
    main()
