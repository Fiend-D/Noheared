#!/usr/bin/env python3
"""检查案件的节奏：空窗期、开头结尾、台词长度、串话、身份线索。

    python3 tools/pacing.py case8 [case9 ...]     # 检查 case.json，不改文件

“空窗期”指全图任何地方都没有台词、也没有音效的时间段。玩家可以去任何房间，
所以只要某处有人在说话就不算空窗。compose_case.py 编译剧本时会跑同样的检查，
有“错误”就不写 case.json。

只依赖标准库。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "game", "cases")

MAX_GAP = 20.0  # 单段空窗上限（秒）
NOTABLE_GAP = 10.0  # 超过这个长度的空窗算一次“明显空窗”
NOTABLE_EVERY = 300.0  # 每这么多秒最多一次明显空窗
MAX_OPENING = 10.0  # 开场多久之内必须有声音
MAX_TAIL = 15.0  # 最后一句结束后最多留白
MAX_LINE_SECONDS = 12.0
MAX_LINE_CHARS = 60
MAX_PARALLEL = 3  # 同时有人说话的房间数上限
MIN_MENTIONS = 2  # 每个身份至少被别人叫到几次
MIN_LINES = 5  # 每个角色至少几句台词
OVERLAP_TOLERANCE = 0.3

_DIRECTION = re.compile(r"（[^）]*）|\([^)]*\)")


def spoken(text: str) -> str:
    return _DIRECTION.sub("", text).strip()


def _intervals(case: dict) -> list[tuple[float, float]]:
    out = [(l["start"], l["start"] + l["duration"]) for l in case.get("voice_lines", [])]
    out += [(s["time"], s["time"] + float(s.get("duration", 1.0))) for s in case.get("sfx", [])]
    return sorted(out)


def gaps(case: dict) -> list[tuple[float, float]]:
    """全图无声的时间段 (开始, 长度)，不含结尾留白。"""
    out = []
    t = 0.0
    for a, b in _intervals(case):
        if a > t:
            out.append((t, a - t))
        t = max(t, b)
    return out


def last_end(case: dict) -> float:
    return max((b for _, b in _intervals(case)), default=0.0)


def _room_at(track: list[dict], t: float) -> str:
    room = ""
    for k in track:
        if k["t"] > t + 1e-6:
            break
        room = k.get("room", room)
    return room


TITLES = ["小姐", "先生", "姐", "哥", "叔", "伯", "老师", "女士", "师傅", "总", "台长", "主任"]


def name_variants(name: str) -> list[str]:
    """别人称呼这个身份时可能用的词：全名；三个字以上时去掉姓（宋院长 → 院长）；两个字的人名加姓氏称呼（林婉 → 林小姐）。"""
    out = [name]
    if len(name) >= 3:
        out.append(name[1:])
    elif len(name) == 2:
        out += [name[0] + t for t in TITLES]
    return out


def check(case: dict) -> tuple[list[str], list[str]]:
    """返回 (错误, 提示)。"""
    errors: list[str] = []
    warnings: list[str] = []
    duration = float(case["duration"])
    lines = case.get("voice_lines", [])
    if not lines:
        return ["没有台词"], []

    all_gaps = gaps(case)
    first = _intervals(case)[0][0]
    if first > MAX_OPENING:
        errors.append(f"开场 {first:.1f}s 才有第一声，超过 {MAX_OPENING:.0f}s")
    for start, length in all_gaps:
        if length > MAX_GAP and start > 0.0:
            errors.append(f"{_mmss(start)} 起全图空窗 {length:.1f}s，超过 {MAX_GAP:.0f}s")
    notable = [g for g in all_gaps if g[1] >= NOTABLE_GAP and g[0] > 0.0]
    allowed = max(1, math.floor(duration / NOTABLE_EVERY))
    if len(notable) > allowed:
        where = "、".join(_mmss(s) for s, _ in notable)
        errors.append(f"{len(notable)} 段 ≥{NOTABLE_GAP:.0f}s 的空窗（{where}），这个时长最多 {allowed} 段")
    tail = duration - last_end(case)
    if tail > MAX_TAIL:
        errors.append(f"最后一声之后还有 {tail:.1f}s 留白，超过 {MAX_TAIL:.0f}s（把时长改短）")

    for l in lines:
        words = spoken(l["text"])
        if l["duration"] > MAX_LINE_SECONDS or len(words) > MAX_LINE_CHARS:
            warnings.append(f"{_mmss(l['start'])} {l['speaker']} 的台词太长（{len(words)} 字 / {l['duration']:.1f}s），拆成两句")

    tracks = {c["id"]: c.get("track", []) for c in case.get("characters", [])}
    placed = [(l, _room_at(tracks.get(l["speaker"], []), l["start"])) for l in lines]
    placed.sort(key=lambda p: p[0]["start"])
    for i, (a, room_a) in enumerate(placed):
        a_end = a["start"] + a["duration"]
        for b, room_b in placed[i + 1 :]:
            if b["start"] >= a_end - OVERLAP_TOLERANCE:
                break
            if room_a and room_a == room_b and a["speaker"] != b["speaker"]:
                warnings.append(f"{_mmss(b['start'])} {room_a} 里 {a['speaker']} 和 {b['speaker']} 同时说话，听不清")
    reported = 0.0
    for l, _ in placed:
        t = l["start"] + 0.01
        rooms = {r for m, r in placed if m["start"] <= t < m["start"] + m["duration"] and r}
        if len(rooms) > MAX_PARALLEL and t > reported:
            warnings.append(f"{_mmss(t)} 有 {len(rooms)} 个房间同时在说话，超过 {MAX_PARALLEL} 处")
            reported = t + 30.0

    for c in case.get("characters", []):
        own = [l for l in lines if l["speaker"] == c["id"]]
        if len(own) < MIN_LINES:
            warnings.append(f"{c['name']}（{c['id']}）只有 {len(own)} 句台词，玩家很难认出")
        variants = name_variants(c["name"])
        mentions = sum(1 for l in lines if l["speaker"] != c["id"] and any(v in spoken(l["text"]) for v in variants))
        if mentions < MIN_MENTIONS:
            warnings.append(f"{c['name']}（{c['id']}）只被别人叫到 {mentions} 次，身份缺少线索")
    return errors, warnings


def _mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="+")
    args = parser.parse_args()
    failed = False
    for case_id in args.cases:
        with open(os.path.join(CASES, case_id, "case.json"), encoding="utf-8") as f:
            case = json.load(f)
        errors, warnings = check(case)
        print(f"{case_id}：{len(errors)} 个错误，{len(warnings)} 条提示")
        for e in errors:
            print("  错误：" + e)
        for w in warnings:
            print("  提示：" + w)
        failed |= bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
