#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据剧本生成时间轴对齐的语音音频文件
使用 edge-tts 引擎，支持中文和按角色区分音色
按案件分目录存储，避免不同案件音频串扰
用法: python generate_audio.py
"""

import os
import json
import tempfile
import asyncio
import shutil

from pydub import AudioSegment


CHARACTER_VOICES = {
    'A': 'zh-CN-YunyangNeural',
    'B': 'zh-CN-XiaoxiaoNeural',
    'C': 'zh-CN-YunxiaNeural',
    'D': 'zh-CN-XiaoyiNeural',
    'E': 'zh-CN-XiaoxiaoNeural',
    'F': 'zh-CN-YunyangNeural',
    'G': 'zh-CN-YunxiNeural',
    'H': 'zh-CN-YunyangNeural',
    'I': 'zh-CN-YunjianNeural',
    'J': 'zh-CN-XiaoxiaoNeural',
    'K': 'zh-CN-XiaoyiNeural',
    'L': 'zh-CN-XiaoniNeural',
    'M': 'zh-CN-XiaobeiNeural',
}


async def generate_speech_edge(text, mp3_path, voice):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(mp3_path)


def mp3_to_wav(mp3_path, wav_path):
    import subprocess
    cmd = [
        'ffmpeg', '-y', '-i', mp3_path,
        '-acodec', 'pcm_s16le',
        '-ar', '24000',
        '-ac', '1',
        wav_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        audio = AudioSegment.from_mp3(mp3_path)
        audio.export(wav_path, format='wav')
    return wav_path


def generate_speech_sync(text, temp_dir, character, index, voice):
    mp3_path = os.path.join(temp_dir, f"{character}_{index}.mp3")
    wav_path = os.path.join(temp_dir, f"{character}_{index}.wav")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate_speech_edge(text, mp3_path, voice))
        finally:
            loop.close()

        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
            mp3_to_wav(mp3_path, wav_path)
            os.remove(mp3_path)
            return wav_path

        return None
    except Exception as e:
        print(f"    生成失败: {e}")
        return None


def build_character_track(character, dialogues, duration_seconds, output_path, temp_dir):
    voice = CHARACTER_VOICES.get(character, 'zh-CN-XiaoxiaoNeural')
    print(f"  构建角色 {character} 的音频轨道 (音色: {voice})...")

    base_audio = AudioSegment.silent(duration=duration_seconds * 1000)

    for i, dialogue in enumerate(dialogues):
        text = dialogue['text']
        start_ms = int(dialogue['start'] * 1000)

        wav_path = generate_speech_sync(text, temp_dir, character, i, voice)

        if wav_path and os.path.exists(wav_path):
            speech = AudioSegment.from_wav(wav_path)

            if start_ms + len(speech) > len(base_audio):
                available = len(base_audio) - start_ms
                if available > 0:
                    speech = speech[:available]
                else:
                    continue

            base_audio = base_audio.overlay(speech, position=start_ms)
            print(f"    [{dialogue['start']}s] {text[:30]}...")
        else:
            print(f"    跳过: {text[:30]}...")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    base_audio.export(output_path, format="wav")
    print(f"  已导出: {output_path} ({len(base_audio)/1000:.1f}s)")
    return True


def process_case(case_file, output_dir, temp_dir):
    with open(case_file, 'r', encoding='utf-8') as f:
        case_data = json.load(f)

    case_name = case_data.get('name', '未知案件')
    duration = case_data.get('duration', 120)
    case_id = os.path.splitext(os.path.basename(case_file))[0]

    print(f"\n=== 处理案件: {case_name} (ID: {case_id}, 时长: {duration}s) ===")

    character_dialogues = {}
    for dialogue in case_data.get('dialogues', []):
        character = dialogue.get('character')
        if character:
            if character not in character_dialogues:
                character_dialogues[character] = []
            character_dialogues[character].append(dialogue)

    audio_tracks = case_data.get('audio_tracks', {})
    generated_files = []

    for character, dialogues in character_dialogues.items():
        audio_file = audio_tracks.get(character)
        if audio_file:
            output_path = os.path.join(output_dir, audio_file)
            build_character_track(character, dialogues, duration, output_path, temp_dir)
            generated_files.append(output_path)
        else:
            print(f"  警告: 角色 {character} 没有对应的 audio_tracks 配置")

    return generated_files


def main():
    output_dir = 'unheared'
    os.makedirs(output_dir, exist_ok=True)

    temp_dir = tempfile.mkdtemp(prefix='audio_gen_')
    print(f"临时目录: {temp_dir}")

    try:
        cases_dir = 'unheared/cases'
        case_files = sorted([f for f in os.listdir(cases_dir) if f.endswith('.json')])

        all_generated = []
        for case_file in case_files:
            case_path = os.path.join(cases_dir, case_file)
            files = process_case(case_path, output_dir, temp_dir)
            all_generated.extend(files)

        print(f"\n=== 全部完成！共生成 {len(all_generated)} 个音频文件 ===")
        for f in all_generated:
            print(f"  - {f}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"已清理临时目录")


if __name__ == '__main__':
    main()
