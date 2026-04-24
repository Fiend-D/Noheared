#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用edge-tts为case6生成角色音频
"""

import json
import os
import asyncio
import edge_tts

async def generate_tts(text, output_file, voice):
    """生成TTS音频文件"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

async def main():
    # 读取case6.json文件
    with open('/home/zhaohaipeng/WorkSpacee/qt/unheared/unheared/cases/case6.json', 'r', encoding='utf-8') as f:
        case = json.load(f)
    
    # 确保音频目录存在
    audio_dir = '/home/zhaohaipeng/WorkSpacee/qt/unheared/unheared/audio/case6'
    os.makedirs(audio_dir, exist_ok=True)
    
    # 角色语音映射
    voice_map = {
        'A': 'zh-CN-YunxiNeural',  # 老爷 - 男声
        'B': 'zh-CN-XiaoyiNeural',  # 夫人 - 女声
        'C': 'zh-CN-YunxiNeural',  # 管家 - 男声
        'D': 'zh-CN-YunxiNeural',  # 厨师 - 男声
        'E': 'zh-CN-XiaoyiNeural',  # 女仆 - 女声
        'F': 'zh-CN-YunxiNeural',  # 律师 - 男声
        'G': 'zh-CN-YunxiNeural',  # 医生 - 男声
        'H': 'zh-CN-XiaoyiNeural',  # 侄女 - 女声
        'I': 'zh-CN-YunxiNeural',  # 画家 - 男声
        'J': 'zh-CN-YunxiNeural',  # 侦探 - 男声
    }
    
    # 提取每个角色的对话
    character_dialogues = {}
    for dialogue in case.get('dialogues', []):
        character = dialogue.get('character')
        text = dialogue.get('text', '')
        if character and text:
            if character not in character_dialogues:
                character_dialogues[character] = []
            character_dialogues[character].append(text)
    
    # 为每个角色生成音频
    for character, dialogues in character_dialogues.items():
        if character not in voice_map:
            print(f"角色 {character} 没有对应的语音设置，跳过")
            continue
        
        # 合并对话为一个文本
        full_text = ' '.join(dialogues)
        
        # 生成音频文件路径
        output_file = os.path.join(audio_dir, f"{case['characters'][character]['name']}.wav")
        
        # 生成音频
        print(f"正在为 {case['characters'][character]['name']} 生成音频...")
        await generate_tts(full_text, output_file, voice_map[character])
        print(f"音频已保存到: {output_file}")
    
    print("\n所有音频文件生成完成！")

if __name__ == "__main__":
    asyncio.run(main())