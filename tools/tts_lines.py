#!/usr/bin/env python3
"""为新格式案件逐句生成语音，并回写 case.json 的 audio / duration 字段。

台词里的括号内容（如“（冷笑）”“（举杯）”）是表演提示：不会被念出来，
而是作为语气指令交给 CosyVoice 的 instruct 模式；字幕仍保留原文。

引擎：
  cosyvoice（默认）本地 CosyVoice2/3，按每个角色的参考音频克隆音色，支持语气指令。
                   需要在 CosyVoice 的 Python 环境中运行，见 README“配音”一节。
  edge             edge-tts 在线合成，不支持语气指令。

用法：
  python tools/tts_lines.py case6 case7                  # 生成缺失的、或由其他引擎生成的台词
  python tools/tts_lines.py case7 --force                # 全部重新生成
  python tools/tts_lines.py case7 --only 12 13           # 只生成指定下标的台词
  python tools/tts_lines.py case6 --engine edge --voice A=zh-CN-YunjianNeural

角色音色（cosyvoice）：优先用 case.json 中角色的 voice_prompt / voice_prompt_text；
没有时自动从该角色现有的语音片段里挑一句不带括号、3~10 秒的作为参考，复制到
tools/voice_prompts/<case>/<角色>.wav 并写回 case.json，之后重新生成也保持同一音色。

个别台词的语气指令偶尔会被念出来：在该句上加 "tts_instruct": false 后用 --only 重新生成。

生成后在 Godot 中重新导入：
  godot --headless --path game --import
  godot --headless --path game --script res://addons/case_editor/import_cli.gd -- case6 case7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "game", "cases")
PROMPTS = os.path.join(ROOT, "tools", "voice_prompts")
COSYVOICE_HOME = os.environ.get("COSYVOICE_HOME", os.path.expanduser("~/.local/share/unheard-tts/CosyVoice"))
COSYVOICE_MODEL = os.environ.get(
    "COSYVOICE_MODEL", os.path.expanduser("~/.local/share/unheard-tts/models/CosyVoice2-0.5B")
)

DIRECTION = re.compile(r"[（(]([^）)]*)[）)]")
LOUD_HINTS = ("尖叫", "大喊", "喊", "怒吼", "拍桌", "吼")
QUIET_HINTS = ("低声", "小声", "耳语", "自言自语", "喃喃")
CN_DIGITS = "零一二三四五六七八九"
PROMPT_MIN, PROMPT_MAX = 3.0, 10.0
MIN_GAP = 0.1
EDGE_VOICES = [
    "zh-CN-YunyangNeural",
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-XiaoyiNeural",
    "zh-CN-YunjianNeural",
]


def cardinal(n: int) -> str:
    if n < 10:
        return CN_DIGITS[n]
    if n >= 10000:
        return "".join(CN_DIGITS[int(d)] for d in str(n))
    out = ""
    for unit, value in (("千", 1000), ("百", 100), ("十", 10)):
        q, n = divmod(n, value)
        if q:
            out += CN_DIGITS[q] + unit
        elif out and n:
            out += "零" if not out.endswith("零") else ""
    if n:
        out += CN_DIGITS[n]
    return out[1:] if out.startswith("一十") else out


def spell_numbers(text: str) -> str:
    """模型的文本规范化前端不一定可用，阿拉伯数字自己转成中文：年份逐位读（83年的 → 八三年的，20年 → 二十年）。"""
    year = r"\d{4}(?=年)|\d{2}(?=年的|年代)"
    text = re.sub(year, lambda m: "".join(CN_DIGITS[int(d)] for d in m.group()), text)
    return re.sub(r"\d+", lambda m: cardinal(int(m.group())), text)


def split_directions(text: str) -> tuple[str, list[str]]:
    """返回（要念出来的文本，表演提示列表）。"""
    directions = [d.strip() for d in DIRECTION.findall(text) if d.strip()]
    spoken = spell_numbers(re.sub(r"\s+", " ", DIRECTION.sub("", text)).strip(" ，,。"))
    if not re.search(r"\w", spoken):  # 只有省略号之类：模型不出声，当作没有台词
        return "", directions
    if spoken and spoken[-1] not in "。！？!?…」”":
        spoken += "。"
    return spoken, directions


def loudness_for(directions: list[str]) -> float | None:
    joined = "".join(directions)
    if any(h in joined for h in LOUD_HINTS):
        return 0.9
    if any(h in joined for h in QUIET_HINTS):
        return 0.3
    return None


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())


# ---------------------------------------------------------------- engines


class CosyVoiceEngine:
    name = "cosyvoice"

    def __init__(self, model_dir: str):
        sys.path.insert(0, COSYVOICE_HOME)
        sys.path.insert(0, os.path.join(COSYVOICE_HOME, "third_party", "Matcha-TTS"))
        try:
            import torchaudio  # noqa: F401
            from cosyvoice.cli.cosyvoice import AutoModel
        except ImportError as e:
            sys.exit(f"无法导入 CosyVoice（{e}）。请用 CosyVoice 环境的 Python 运行本脚本，见 README。")
        self._torchaudio = sys.modules["torchaudio"]
        import torch

        self._torch = torch
        self.model = AutoModel(model_dir=model_dir)
        self.v3 = type(self.model).__name__ == "CosyVoice3"
        self._registered: set[str] = set()

    def _instruct(self, directions: list[str]) -> str:
        # 指令要短：长句会被模型当成正文念出来。
        text = f"{'，'.join(directions)}，用符合的语气说这句话"
        return f"You are a helpful assistant. {text}<|endofprompt|>" if self.v3 else f"{text}<|endofprompt|>"

    def synthesize(self, text: str, directions: list[str], speaker: dict, out_ogg: str, tmp: str) -> None:
        spk_id = speaker["key"]
        if spk_id not in self._registered:
            prompt_text = speaker["prompt_text"]
            if self.v3:
                prompt_text = f"You are a helpful assistant.<|endofprompt|>{prompt_text}"
            self.model.add_zero_shot_spk(prompt_text, speaker["prompt_wav"], spk_id)
            self._registered.add(spk_id)
        if directions:
            # 缓存的 spk 信息里带着参考音频的文本，instruct 模式下会被当成指令念出来，所以这里不能用 spk_id。
            gen = self.model.inference_instruct2(text, self._instruct(directions), speaker["prompt_wav"], stream=False)
        else:
            gen = self.model.inference_zero_shot(text, "", "", zero_shot_spk_id=spk_id, stream=False)
        speech = self._torch.cat([chunk["tts_speech"] for chunk in gen], dim=1)
        wav = os.path.join(tmp, os.path.basename(out_ogg) + ".wav")
        self._torchaudio.save(wav, speech, self.model.sample_rate)
        ffmpeg("-i", wav, "-ac", "1", "-ar", "24000", "-c:a", "libvorbis", "-q:a", "5", out_ogg)
        os.remove(wav)


class EdgeEngine:
    name = "edge"

    def __init__(self) -> None:
        import asyncio

        import edge_tts

        self._asyncio = asyncio
        self._edge = edge_tts

    def synthesize(self, text: str, directions: list[str], speaker: dict, out_ogg: str, tmp: str) -> None:
        mp3 = os.path.join(tmp, os.path.basename(out_ogg) + ".mp3")
        self._asyncio.run(self._edge.Communicate(text, speaker["edge_voice"]).save(mp3))
        ffmpeg("-i", mp3, "-ac", "1", "-ar", "24000", "-c:a", "libvorbis", "-q:a", "5", out_ogg)
        os.remove(mp3)


# ---------------------------------------------------------------- voices


def existing_clip(case_dir: str, line: dict, index: int) -> str | None:
    candidates = []
    if line.get("audio"):
        candidates.append(os.path.join(case_dir, line["audio"]))
    candidates.append(os.path.join(case_dir, "audio", f"{line['speaker']}_{index:04d}.ogg"))
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def pick_prompt(case_id: str, case_dir: str, case: dict, character: dict) -> tuple[str, str]:
    """为角色挑一段参考音频，转成 16k 单声道 wav 存到 tools/voice_prompts。返回（相对仓库路径，文本）。"""
    best = None
    for i, line in enumerate(case["voice_lines"]):
        if line["speaker"] != character["id"] or DIRECTION.search(line["text"]):
            continue
        clip = existing_clip(case_dir, line, i)
        if clip is None:
            continue
        dur = probe_duration(clip)
        if PROMPT_MIN <= dur <= PROMPT_MAX:
            score = abs(dur - 6.0)
            if best is None or score < best[0]:
                best = (score, clip, line["text"])
    if best is None:
        sys.exit(f"{case_id}/{character['id']}：找不到 3~10 秒、不带括号的现有语音作参考，请在 case.json 中手动指定 voice_prompt")
    out_dir = os.path.join(PROMPTS, case_id)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{character['id']}.wav")
    ffmpeg("-i", best[1], "-ac", "1", "-ar", "16000", out)
    return os.path.relpath(out, ROOT), best[2]


def prepare_speakers(case_id: str, case_dir: str, case: dict, engine: str, edge_overrides: dict) -> dict:
    speakers = {}
    for n, c in enumerate(case["characters"]):
        info = {"key": f"{case_id}_{c['id']}"}
        if engine == "cosyvoice":
            if not c.get("voice_prompt") or not os.path.exists(os.path.join(ROOT, c["voice_prompt"])):
                c["voice_prompt"], c["voice_prompt_text"] = pick_prompt(case_id, case_dir, case, c)
                print(f"  {c['id']} {c['name']}：参考音频 {c['voice_prompt']}（{c['voice_prompt_text'][:20]}…）")
            info["prompt_wav"] = os.path.join(ROOT, c["voice_prompt"])
            info["prompt_text"] = c["voice_prompt_text"]
        else:
            info["edge_voice"] = edge_overrides.get(c["id"]) or c.get("edge_voice") or EDGE_VOICES[n % len(EDGE_VOICES)]
        speakers[c["id"]] = info
    return speakers


# ---------------------------------------------------------------- driver


def fit_durations(lines: list[dict], case_duration: float) -> int:
    """语音可能比原来预留的更长：同一角色的下一句开始前必须说完，必要时顺延下一句。返回被顺延的句数。"""
    shifted = 0
    last_end: dict[str, float] = {}
    for line in sorted(lines, key=lambda l: l["start"]):
        prev = last_end.get(line["speaker"], -1.0)
        start = line["start"]
        if start < prev + MIN_GAP:
            start = round(prev + MIN_GAP, 3)
        start = round(min(start, max(case_duration - line["duration"], 0.0)), 3)
        if start != line["start"]:
            shifted += 1
            line["start"] = start
        last_end[line["speaker"]] = start + line["duration"]
    return shifted


def save_case(path: str, case: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def run_case(case_id: str, engine, args) -> None:
    case_dir = os.path.join(CASES, case_id)
    json_path = os.path.join(case_dir, "case.json")
    with open(json_path, encoding="utf-8") as f:
        case = json.load(f)
    print(f"== {case_id}: {case['title']}")
    speakers = prepare_speakers(case_id, case_dir, case, engine.name, dict(v.split("=", 1) for v in args.voice))
    # 参考音频可能取自即将被覆盖的片段，先全部准备好再开始生成。
    save_case(json_path, case)

    lines = case["voice_lines"]
    if args.only:
        todo = [i for i in args.only if 0 <= i < len(lines)]
    else:
        todo = [
            i
            for i, l in enumerate(lines)
            if args.force or l.get("tts") != engine.name or not l.get("audio") or not os.path.exists(os.path.join(case_dir, l["audio"]))
        ]
    print(f"  需要生成 {len(todo)} / {len(lines)} 句")
    audio_dir = os.path.join(case_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="unheard_tts_") as tmp:
        for n, i in enumerate(todo, start=1):
            line = lines[i]
            spoken, directions = split_directions(line["text"])
            if not spoken:
                line.pop("audio", None)
                continue
            rel = f"audio/{line['speaker']}_{hashlib.sha1(line['text'].encode()).hexdigest()[:10]}.ogg"
            instruct = directions if line.get("tts_instruct", True) else []
            engine.synthesize(spoken, instruct, speakers[line["speaker"]], os.path.join(case_dir, rel), tmp)
            line["audio"] = rel
            line["duration"] = round(probe_duration(os.path.join(case_dir, rel)), 3)
            line["tts"] = engine.name
            loud = loudness_for(directions)
            if loud is not None:
                line["loudness"] = loud
            save_case(json_path, case)
            elapsed = time.time() - started
            eta = elapsed / n * (len(todo) - n)
            print(f"  [{n}/{len(todo)}] {line['speaker']} {line['duration']:.1f}s  {spoken[:24]}  (剩余约 {eta / 60:.0f} 分钟)", flush=True)

    shifted = fit_durations(lines, float(case["duration"]))
    lines.sort(key=lambda l: l["start"])
    save_case(json_path, case)
    removed = remove_unreferenced(case_dir, case)
    print(f"  完成，{shifted} 句因语音变长而顺延，清理 {removed} 个旧文件；已更新 {os.path.relpath(json_path, ROOT)}")


def remove_unreferenced(case_dir: str, case: dict) -> int:
    used = {os.path.normpath(l["audio"]) for l in case["voice_lines"] if l.get("audio")}
    used |= {os.path.normpath(s["audio"]) for s in case.get("sfx", []) if s.get("audio")}
    removed = 0
    audio_dir = os.path.join(case_dir, "audio")
    for name in os.listdir(audio_dir):
        rel = os.path.normpath(os.path.join("audio", name))
        if rel not in used and (name.endswith(".ogg") or name.endswith(".ogg.import")):
            if name.endswith(".import") and rel[: -len(".import")] in used:
                continue
            os.remove(os.path.join(audio_dir, name))
            removed += 1
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cases", nargs="+", help="例如 case6 case7")
    parser.add_argument("--engine", choices=["cosyvoice", "edge"], default="cosyvoice")
    parser.add_argument("--model", default=COSYVOICE_MODEL, help="CosyVoice 模型目录")
    parser.add_argument("--force", action="store_true", help="全部重新生成")
    parser.add_argument("--only", type=int, nargs="*", help="只生成这些下标的台词")
    parser.add_argument("--voice", action="append", default=[], metavar="ID=VOICE", help="edge 引擎的角色音色")
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        sys.exit("需要 ffmpeg")
    engine = CosyVoiceEngine(args.model) if args.engine == "cosyvoice" else EdgeEngine()
    for case_id in args.cases:
        run_case(case_id, engine, args)


if __name__ == "__main__":
    main()
