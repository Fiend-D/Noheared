#!/usr/bin/env python3
"""把旧版 PyQt 案件（legacy/unheared/cases/caseN.json + 整段角色 WAV）迁移为新格式。

输出：
  game/cases/<id>/case.json        新格式案件（地图、关键帧、逐句台词、问题）
  game/cases/<id>/audio/*.ogg      逐句台词片段
  game/audio/footsteps/*.ogg       脚步声循环

之后在 Godot 里运行导入命令把 case.json 转成 case.tres + map.tscn（见 README）。

用法：
  python tools/migrate_legacy_case.py            # 迁移全部案件
  python tools/migrate_legacy_case.py case5      # 只迁移指定案件
依赖：Python 3.10+ 标准库 + ffmpeg（需带 libvorbis）。
"""

from __future__ import annotations

import argparse
import array
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(ROOT, "legacy", "unheared")
GAME = os.path.join(ROOT, "game")

# 旧版每 16ms 走 2.5 / 5 像素。
WALK_SPEED = 150.0
RUN_SPEED = 300.0
STAIR_SPEED_FACTOR = 0.5
# 旧版以 y=460 为上下层分界，只有带楼梯的案件才分层。
FLOOR_DIVIDER_Y = 460
FLOOR_NAMES = {"case5": ["上层", "下层"]}
DEFAULT_FLOOR_NAMES = ["一层", "二层"]
# 移动需要在下一段开始前完成，留一点余量。
MOVE_BUDGET = 0.95
ROOM_MARGIN = 12

SILENCE_THRESHOLD = 400
SCAN_STEP = 24
TAIL_PADDING = 0.25
MIN_CLIP = 0.3


@dataclass
class Area:
    name: str
    x: float
    y: float
    w: float
    h: float
    floor: int = 0

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)

    def contains(self, p: tuple[float, float]) -> bool:
        return self.x <= p[0] <= self.x + self.w and self.y <= p[1] <= self.y + self.h

    def clamp(self, p: tuple[float, float], margin: float = ROOM_MARGIN) -> tuple[float, float]:
        m = min(margin, self.w / 2 - 1, self.h / 2 - 1)
        return (
            min(max(p[0], self.x + m), self.x + self.w - m),
            min(max(p[1], self.y + m), self.y + self.h - m),
        )

    def polygon(self) -> list[list[float]]:
        return [
            [self.x, self.y],
            [self.x + self.w, self.y],
            [self.x + self.w, self.y + self.h],
            [self.x, self.y + self.h],
        ]


@dataclass
class Link:
    """门或楼梯。`ends[name]` 是在该房间一侧的进出点。"""

    name: str
    a: str
    b: str
    stair: bool
    center: tuple[float, float]
    size: tuple[float, float]
    ends: dict[str, tuple[float, float]]


def dist(p, q) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def is_stair(door: dict) -> bool:
    return "楼梯" in door["name"]


def door_transit(door: dict, frm: Area, to: Area) -> tuple[tuple[float, float], tuple[float, float]]:
    """移植自旧版 `_get_door_transit_points`：穿门时门两侧的进出点。"""
    dx, dy, dw, dh = door["x"], door["y"], door["width"], door["height"]
    dcx, dcy = dx + dw / 2, dy + dh / 2
    fcx, fcy = frm.center
    tcx, tcy = to.center
    margin, span = 10, 14
    y_overlap = min(frm.y + frm.h, to.y + to.h) - max(frm.y, to.y)
    if y_overlap <= 20:
        edge_y = dy if fcy < dcy else dy + dh
        toward_y = dy if tcy < dcy else dy + dh
        entry = (max(dx + margin, min(fcx, dx + dw - margin)), edge_y - span if fcy < dcy else edge_y + span)
        exit_ = (max(dx + margin, min(tcx, dx + dw - margin)), toward_y - span if tcy < dcy else toward_y + span)
    else:
        edge_x = dx if fcx < dcx else dx + dw
        toward_x = dx if tcx < dcx else dx + dw
        entry = (edge_x - span if fcx < dcx else edge_x + span, max(dy + margin, min(fcy, dy + dh - margin)))
        exit_ = (toward_x - span if tcx < dcx else toward_x + span, max(dy + margin, min(tcy, dy + dh - margin)))
    return frm.clamp(entry, 6), to.clamp(exit_, 6)


class Layout:
    def __init__(self, case_id: str, scene: dict):
        self.areas = [Area(a["name"], a["x"], a["y"], a["width"], a["height"]) for a in scene["areas"]]
        self.by_name = {a.name: a for a in self.areas}
        has_stairs = any(is_stair(d) for d in scene.get("doors", []))
        if has_stairs:
            for a in self.areas:
                a.floor = 1 if a.center[1] >= FLOOR_DIVIDER_Y else 0
        floors = max(a.floor for a in self.areas) + 1
        self.floor_names = (FLOOR_NAMES.get(case_id, DEFAULT_FLOOR_NAMES) * 2)[:floors]

        self.links: list[Link] = []
        for d in scene.get("doors", []):
            a, b = self.by_name.get(d["area1"]), self.by_name.get(d["area2"])
            if not a or not b:
                print(f"  警告：门 {d['name']} 引用了不存在的房间，已跳过", file=sys.stderr)
                continue
            center = (d["x"] + d["width"] / 2, d["y"] + d["height"] / 2)
            if is_stair(d):
                ends = {a.name: a.clamp(center, 24), b.name: b.clamp(center, 24)}
            else:
                ea, eb = door_transit(d, a, b)
                ends = {a.name: ea, b.name: eb}
            self.links.append(Link(d["name"], a.name, b.name, is_stair(d), center, (d["width"], d["height"]), ends))

    def area_at(self, p) -> Area | None:
        for a in self.areas:
            if a.contains(p):
                return a
        return None

    def snap(self, p) -> tuple[tuple[float, float], Area]:
        """把点放进某个房间内（旧数据偶尔有点落在墙上）。"""
        a = self.area_at(p)
        if a is None:
            a = min(self.areas, key=lambda r: dist(r.clamp(p, 0), p))
        return a.clamp(p, 0) if a.contains(p) else a.clamp(p), a

    def route(self, src: str, dst: str) -> list[Link]:
        if src == dst:
            return []
        prev: dict[str, tuple[str, Link] | None] = {src: None}
        queue = deque([src])
        while queue:
            cur = queue.popleft()
            for link in self.links:
                if cur not in (link.a, link.b):
                    continue
                nxt = link.b if cur == link.a else link.a
                if nxt in prev:
                    continue
                prev[nxt] = (cur, link)
                if nxt == dst:
                    queue.clear()
                    break
                queue.append(nxt)
        if dst not in prev:
            return []
        path = []
        node = dst
        while prev[node] is not None:
            parent, link = prev[node]
            path.append(link)
            node = parent
        return list(reversed(path))

    def to_json(self) -> dict:
        return {
            "floors": self.floor_names,
            "rooms": [{"name": a.name, "floor": a.floor, "polygon": a.polygon()} for a in self.areas],
            "doors": [
                {"name": l.name, "room_a": l.a, "room_b": l.b, "position": list(l.center), "size": list(l.size)}
                for l in self.links
                if not l.stair
            ],
            "stairs": [
                {"name": l.name, "room_a": l.a, "room_b": l.b, "end_a": list(l.ends[l.a]), "end_b": list(l.ends[l.b])}
                for l in self.links
                if l.stair
            ],
        }


def build_track(layout: Layout, positions: list[dict], duration: float) -> list[dict]:
    """把旧版“时间段 + 目标点”转换成确定性的关键帧：每段开始时出发，沿门洞路线走到目标点后停住。"""
    segs = sorted(positions, key=lambda p: p["start"])
    if not segs:
        return []
    cur, cur_area = layout.snap(tuple(segs[0]["position"]))
    keys = [{"t": 0.0, "p": list(cur), "m": "idle", "room": cur_area.name}]

    for i, seg in enumerate(segs[1:], start=1):
        target, target_area = layout.snap(tuple(seg["position"]))
        if dist(cur, target) < 0.5:
            continue
        movement = "run" if seg.get("movement") == "run" else "walk"
        speed = RUN_SPEED if movement == "run" else WALK_SPEED
        legs: list[tuple[tuple[float, float], float, str]] = []
        here, here_area = cur, cur_area.name
        for link in layout.route(cur_area.name, target_area.name):
            other = link.b if here_area == link.a else link.a
            entry, exit_ = link.ends[here_area], link.ends[other]
            legs.append((entry, dist(here, entry) / speed, here_area))
            factor = STAIR_SPEED_FACTOR if link.stair else 1.0
            legs.append((exit_, dist(entry, exit_) / (speed * factor), other))
            here, here_area = exit_, other
        legs.append((target, dist(here, target) / speed, target_area.name))

        depart = float(seg["start"])
        next_start = float(segs[i + 1]["start"]) if i + 1 < len(segs) else float(duration)
        budget = max(next_start - depart, 0.1) * MOVE_BUDGET
        total = sum(leg[1] for leg in legs)
        scale = min(1.0, budget / total) if total > 0 else 1.0

        keys.append({"t": round(depart, 3), "p": [round(cur[0], 1), round(cur[1], 1)], "m": movement, "room": cur_area.name})
        t = depart
        for n, (point, leg_time, room) in enumerate(legs):
            t += leg_time * scale
            last = n == len(legs) - 1
            keys.append({"t": round(t, 3), "p": [round(point[0], 1), round(point[1], 1)], "m": "idle" if last else movement, "room": room})
        cur, cur_area = target, target_area
    return keys


def read_mono(path: str) -> tuple[array.array, int]:
    with wave.open(path, "rb") as wf:
        channels, width, rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    if width != 2:
        raise ValueError(f"{path}: 只支持 16-bit PCM")
    samples = array.array("h")
    samples.frombytes(raw)
    if sys.byteorder == "big":
        samples.byteswap()
    if channels == 2:
        samples = array.array("h", ((samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples), 2)))
    return samples, rate


def last_voiced(samples: array.array, start: int, end: int) -> int:
    window = samples[start:end:SCAN_STEP]
    for i in range(len(window) - 1, -1, -1):
        if abs(window[i]) > SILENCE_THRESHOLD:
            return start + i * SCAN_STEP
    return -1


def encode_ogg(samples: array.array, rate: int, out_path: str, tmp_dir: str) -> None:
    tmp = os.path.join(tmp_dir, os.path.basename(out_path) + ".wav")
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        data = array.array("h", samples)
        if sys.byteorder == "big":
            data.byteswap()
        wf.writeframes(data.tobytes())
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:a", "libvorbis", "-q:a", "4", out_path],
        check=True,
    )
    os.remove(tmp)


def legacy_audio_path(case_id: str, legacy: dict, char_id: str) -> str | None:
    rel = (legacy.get("audio_tracks") or {}).get(char_id)
    if not rel:
        rel = f"audio/{case_id}/{legacy['characters'][char_id]['name']}.wav"
    path = os.path.join(LEGACY, rel)
    return path if os.path.exists(path) else None


def split_voice_lines(case_id: str, legacy: dict, out_dir: str, jobs: ThreadPoolExecutor, tmp_dir: str) -> list[dict]:
    duration = float(legacy["duration"])
    lines = [
        {"speaker": d["character"], "start": float(d["start"]), "end": float(d["end"]), "text": d["text"]}
        for d in legacy.get("dialogues", [])
    ]
    lines.sort(key=lambda l: l["start"])
    by_speaker: dict[str, list[int]] = {}
    for i, l in enumerate(lines):
        by_speaker.setdefault(l["speaker"], []).append(i)

    result: list[dict] = [
        {"speaker": l["speaker"], "start": l["start"], "duration": round(max(l["end"] - l["start"], 1.0), 3), "text": l["text"]}
        for l in lines
    ]
    futures = []
    for speaker, idxs in by_speaker.items():
        path = legacy_audio_path(case_id, legacy, speaker)
        if path is None:
            print(f"  {speaker}: 没有音频，只保留字幕")
            continue
        samples, rate = read_mono(path)
        if len(samples) / rate < duration * 0.9:
            print(f"  {speaker}: 录音长度 {len(samples) / rate:.0f}s 与案件时长 {duration:.0f}s 不对齐，只保留字幕")
            continue
        for n, i in enumerate(idxs):
            line = lines[i]
            s = int(line["start"] * rate)
            window_end = lines[idxs[n + 1]]["start"] if n + 1 < len(idxs) else duration
            e = min(int(window_end * rate), len(samples))
            last = last_voiced(samples, s, e)
            if last < 0:
                continue
            clip_end = min(last + int(TAIL_PADDING * rate), e)
            if (clip_end - s) / rate < MIN_CLIP:
                continue
            name = f"{speaker}_{i:04d}.ogg"
            result[i]["duration"] = round((clip_end - s) / rate, 3)
            result[i]["audio"] = f"audio/{name}"
            futures.append(jobs.submit(encode_ogg, samples[s:clip_end], rate, os.path.join(out_dir, "audio", name), tmp_dir))
    for f in futures:
        f.result()
    return result


def convert_questions(legacy: dict) -> list[dict]:
    names = {c["name"] for c in legacy["characters"].values()}
    out = []
    for q in legacy.get("questions", []):
        options = q.get("options", [])
        kind = "character" if options and all(o in names for o in options) else "choice"
        out.append({"id": q["id"], "kind": kind, "prompt": q["question"], "options": options, "answer": q["answer"]})
    return out


def migrate(case_id: str, jobs: ThreadPoolExecutor) -> None:
    src = os.path.join(LEGACY, "cases", f"{case_id}.json")
    with open(src, encoding="utf-8") as f:
        legacy = json.load(f)
    print(f"== {case_id}: {legacy['name']}")
    out_dir = os.path.join(GAME, "cases", case_id)
    audio_dir = os.path.join(out_dir, "audio")
    shutil.rmtree(audio_dir, ignore_errors=True)
    os.makedirs(audio_dir, exist_ok=True)

    layout = Layout(case_id, legacy["scene"])
    characters = []
    for n, (cid, c) in enumerate(legacy["characters"].items(), start=1):
        characters.append(
            {
                "id": cid,
                "name": c["name"],
                "label": str(n),
                "color": c.get("color", "#ffffff"),
                "track": build_track(layout, c.get("positions", []), legacy["duration"]),
            }
        )
    with tempfile.TemporaryDirectory(prefix="unheard_migrate_") as tmp:
        voice_lines = split_voice_lines(case_id, legacy, out_dir, jobs, tmp)

    case = {
        "format": 1,
        "id": case_id,
        "title": legacy["name"],
        "description": legacy.get("description", ""),
        "duration": legacy["duration"],
        "truth": legacy.get("truth", ""),
        "map": layout.to_json(),
        "characters": characters,
        "voice_lines": voice_lines,
        "sfx": [],
        "questions": convert_questions(legacy),
    }
    with open(os.path.join(out_dir, "case.json"), "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=1)
    voiced = sum(1 for l in voice_lines if "audio" in l)
    print(f"  {len(characters)} 名角色，{len(voice_lines)} 句台词（{voiced} 句有语音），{len(layout.links)} 个门/楼梯")


def migrate_footsteps(jobs: ThreadPoolExecutor) -> None:
    out = os.path.join(GAME, "audio", "footsteps")
    os.makedirs(out, exist_ok=True)
    futures = []
    for name in ("walk", "run"):
        src = os.path.join(LEGACY, "audio", "footsteps", f"{name}.wav")
        if os.path.exists(src):
            futures.append(
                jobs.submit(
                    subprocess.run,
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-c:a", "libvorbis", "-q:a", "4", os.path.join(out, f"{name}.ogg")],
                    check=True,
                )
            )
    for f in futures:
        f.result()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="*", help="例如 case1 case5；默认全部")
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        sys.exit("需要 ffmpeg")
    cases = args.cases or sorted(
        (os.path.splitext(f)[0] for f in os.listdir(os.path.join(LEGACY, "cases")) if f.endswith(".json")),
        key=lambda s: int("".join(ch for ch in s if ch.isdigit()) or 0),
    )
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as jobs:
        migrate_footsteps(jobs)
        for case_id in cases:
            migrate(case_id, jobs)


if __name__ == "__main__":
    main()
