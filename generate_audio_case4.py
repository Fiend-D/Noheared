#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
from pydub import AudioSegment

# 角色到音色的映射
CHARACTER_VOICES = {
    'A': 'YunyangNeural',      # 管家 - 男声，专业稳重
    'B': 'YunxiNeural',         # 继承人 - 男声，阳光活泼
    'C': 'XiaoxiaoNeural',      # 秘书 - 女声，温暖亲切
    'D': 'YunjianNeural',       # 厨师 - 男声，激情有力
    'E': 'YunxiaNeural',        # 园丁 - 男声，年轻可爱
    'F': 'XiaoyiNeural'         # 侦探 - 女声，活泼轻快
}

def generate_speech(text, voice, output_file):
    """使用 edge-tts 生成语音"""
    cmd = [
        'edge-tts',
        '--voice', f'zh-CN-{voice}',
        '--text', text,
        '--write-media', output_file
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"生成语音失败: {e}")
        return False

def create_silent_audio(duration_ms):
    """创建指定时长的静音音频"""
    return AudioSegment.silent(duration=duration_ms)

def process_case(case_file):
    """处理单个案件的音频生成"""
    with open(case_file, 'r', encoding='utf-8') as f:
        case = json.load(f)
    
    case_name = case['name']
    case_id = case_file.split('/')[-1].split('.')[0]
    duration = case['duration']
    dialogues = case['dialogues']
    audio_tracks = case['audio_tracks']
    
    print(f"处理案件: {case_name} (时长: {duration}秒)")
    
    # 创建音频目录
    audio_dir = f"unheared/audio/{case_id}"
    os.makedirs(audio_dir, exist_ok=True)
    
    # 按角色分组对话
    character_dialogues = {}
    for char_id, audio_file in audio_tracks.items():
        character_dialogues[char_id] = []
    
    for dialogue in dialogues:
        char_id = dialogue['character']
        if char_id in character_dialogues:
            character_dialogues[char_id].append(dialogue)
    
    # 为每个角色生成音频轨道
    for char_id, dialogues in character_dialogues.items():
        if not dialogues:
            continue
        
        voice = CHARACTER_VOICES.get(char_id, 'XiaoxiaoNeural')
        audio_file = audio_tracks[char_id]
        output_path = os.path.join('unheared', audio_file)
        
        print(f"  生成角色 {char_id} 的音频...")
        
        # 创建总长度的静音轨道
        total_duration = duration * 1000  # 转换为毫秒
        final_audio = create_silent_audio(total_duration)
        
        # 为每个对话生成语音并叠加到轨道
        for dialogue in dialogues:
            text = dialogue['text']
            start = dialogue['start'] * 1000  # 转换为毫秒
            end = dialogue['end'] * 1000
            
            # 生成临时语音文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp_path = tmp.name
            
            if generate_speech(text, voice, tmp_path):
                # 读取生成的语音
                speech = AudioSegment.from_mp3(tmp_path)
                
                # 计算需要的语音长度
                required_duration = end - start
                if len(speech) > required_duration:
                    speech = speech[:required_duration]
                elif len(speech) < required_duration:
                    # 如果语音太短，添加静音
                    silence = create_silent_audio(required_duration - len(speech))
                    speech = speech + silence
                
                # 叠加到总轨道
                final_audio = final_audio.overlay(speech, position=start)
                
                # 清理临时文件
                os.unlink(tmp_path)
            else:
                print(f"    警告: 无法生成对话: {text}")
        
        # 导出最终音频
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 先导出为临时文件，再用 ffmpeg 转换为 WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            temp_wav = tmp.name
        
        final_audio.export(temp_wav, format='wav')
        
        # 使用 ffmpeg 确保正确的 WAV 格式
        cmd = [
            'ffmpeg', '-y',
            '-i', temp_wav,
            '-acodec', 'pcm_s16le',
            '-ar', '24000',
            '-ac', '1',
            output_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  生成完成: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"  转换失败: {e}")
        finally:
            if os.path.exists(temp_wav):
                os.unlink(temp_wav)

if __name__ == '__main__':
    case_file = 'unheared/cases/case4.json'
    process_case(case_file)
    print("所有音频生成完成！")
