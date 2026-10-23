#!/usr/bin/env python3
"""调整角色走位的时间，让角色先走到位再开口、说完再离开。

旧版案件里角色几乎是瞬移的，台词常常卡在“开始走”的那一刻；迁移成按速度行走的关键帧后，
就会出现“还没走到就开始说话”。本脚本只改关键帧时间，不改路线：

- 说话开始时还在走：把这段行走整体提前，在台词开始前 LEAD 秒到达；
- 说话途中出发：把这段行走整体推迟到台词结束后 LEAD 秒。

提前/推迟受前后关键帧和同一角色其他台词的约束；空间不够时压缩这段行走（走快一点）。

用法：
  python3 tools/fix_speech_timing.py            # 全部案件
  python3 tools/fix_speech_timing.py case7 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "game", "cases")
LEAD = 0.3
MIN_GAP = 0.2
# 压缩后的行走至少保留原时长的这一比例，否则太快不自然，宁可不改。
MIN_SCALE = 0.4


def walk_segments(track: list[dict]) -> list[tuple[int, int]]:
    """[(出发帧, 到达帧)]：出发帧的移动方式不是 idle，到达帧是之后第一个 idle 帧。"""
    out = []
    i = 0
    while i < len(track) - 1:
        if track[i]["m"] != "idle":
            j = i
            while j < len(track) - 1 and track[j]["m"] != "idle":
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def retime(track: list[dict], s: int, e: int, start: float, end: float) -> None:
    old_start, old_end = track[s]["t"], track[e]["t"]
    span = max(old_end - old_start, 1e-6)
    for k in range(s, e + 1):
        track[k]["t"] = round(start + (track[k]["t"] - old_start) / span * (end - start), 3)


def busy_windows(lines: list[dict], speaker: str) -> list[tuple[float, float]]:
    return sorted((l["start"], l["start"] + l["duration"]) for l in lines if l["speaker"] == speaker)


def fix_character(ch: dict, lines: list[dict], case_duration: float) -> tuple[int, int]:
    track = ch["track"]
    talk = busy_windows(lines, ch["id"])
    early = late = 0
    for s, e in walk_segments(track):
        dep, arr = track[s]["t"], track[e]["t"]
        span = arr - dep
        prev_t = track[s - 1]["t"] if s > 0 else 0.0
        next_t = track[e + 1]["t"] if e + 1 < len(track) else case_duration
        # 到达时已经在说话：提前到台词开始前到达。
        arriving = [a for a, b in talk if dep <= a < arr]
        if arriving:
            target_arr = arriving[0] - LEAD
            # 出发前最后一句台词说完才能走。
            floor = max([prev_t + MIN_GAP] + [b + LEAD for a, b in talk if b <= arriving[0] and b > prev_t])
            new_dep = max(target_arr - span, floor)
            if target_arr - new_dep >= span * MIN_SCALE:
                retime(track, s, e, new_dep, target_arr)
                early += 1
                continue
        # 出发时还在说话：推迟到说完再走。
        leaving = [b for a, b in talk if a < dep < b]
        if leaving:
            new_dep = leaving[-1] + LEAD
            ceiling = min([next_t - MIN_GAP] + [a - LEAD for a, b in talk if a >= leaving[-1] and a < next_t])
            new_arr = min(new_dep + span, ceiling)
            if new_arr - new_dep >= span * MIN_SCALE:
                retime(track, s, e, new_dep, new_arr)
                late += 1
    return early, late


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="*")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ids = args.cases or sorted(d for d in os.listdir(CASES) if os.path.exists(os.path.join(CASES, d, "case.json")))
    for case_id in ids:
        path = os.path.join(CASES, case_id, "case.json")
        with open(path, encoding="utf-8") as f:
            case = json.load(f)
        total_early = total_late = 0
        for ch in case["characters"]:
            early, late = fix_character(ch, case["voice_lines"], float(case["duration"]))
            total_early += early
            total_late += late
        print(f"{case_id}: 提前到位 {total_early} 段，推迟出发 {total_late} 段")
        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(case, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
