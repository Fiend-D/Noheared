#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成脚步声循环音效
使用 numpy 合成简单的走路/跑动脚步声
用法: python generate_footstep_sounds.py
"""

import os
import numpy as np
import wave


def generate_single_footstep(sample_rate=24000, duration_ms=350, freq_base=80, amplitude=0.3):
    """生成单个脚步声（带衰减的噪声脉冲）"""
    num_samples = int(sample_rate * duration_ms / 1000)
    
    # 生成白噪声
    noise = np.random.uniform(-1, 1, num_samples)
    
    # 应用包络：极快上升，指数衰减
    t = np.linspace(0, 1, num_samples)
    # 前 5% 快速上升，之后指数衰减
    envelope = np.where(
        t < 0.05,
        t / 0.05,
        np.exp(-(t - 0.05) * 12)
    )
    
    # 简单的低通滤波效果（让声音更闷，更像脚步声）
    filtered = np.zeros_like(noise, dtype=np.float64)
    alpha = 0.4  # 滤波系数，越小越"闷"
    filtered[0] = noise[0]
    for i in range(1, num_samples):
        filtered[i] = alpha * filtered[i - 1] + (1 - alpha) * noise[i]
    
    # 添加低频正弦波成分（增强"厚重感"）
    sine_wave = np.sin(2 * np.pi * freq_base * np.arange(num_samples) / sample_rate)
    sine_env = np.exp(-t * 10)
    
    signal = filtered * envelope * amplitude * 0.7 + sine_wave * sine_env * amplitude * 0.3
    
    # 转换为 int16
    signal = np.clip(signal, -1.0, 1.0)
    return (signal * 32767).astype(np.int16)


def generate_footstep_loop(output_path, steps_per_second=2.0, total_duration=3.0, 
                           step_duration_ms=350, freq_base=80, amplitude=0.25):
    """生成循环脚步声"""
    sample_rate = 24000
    total_samples = int(sample_rate * total_duration)
    
    step_interval = int(sample_rate / steps_per_second)
    
    track = np.zeros(total_samples, dtype=np.float64)
    
    # 生成单个脚步声样本
    step_sample = generate_single_footstep(sample_rate, step_duration_ms, freq_base, amplitude)
    
    for i in range(0, total_samples, step_interval):
        end = min(i + len(step_sample), total_samples)
        track[i:end] += step_sample[:end - i].astype(np.float64)
    
    # 防止削波，归一化
    max_val = np.max(np.abs(track))
    if max_val > 0.8 * 32767:
        track = track * (0.8 * 32767 / max_val)
    
    int16_data = np.clip(track, -32767, 32767).astype(np.int16)
    
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_data.tobytes())
    
    print(f"  已生成: {output_path} (步频={steps_per_second}Hz, 时长={total_duration}s)")
    return output_path


def main():
    output_dir = 'unheared/audio/footsteps'
    os.makedirs(output_dir, exist_ok=True)
    
    print("=== 生成脚步声音效 ===")
    
    # 走路脚步声：约 2 步/秒，声音较闷、较轻
    generate_footstep_loop(
        os.path.join(output_dir, 'walk.wav'),
        steps_per_second=2.0,
        total_duration=3.0,
        step_duration_ms=380,
        freq_base=70,
        amplitude=0.22
    )
    
    # 跑动脚步声：约 4 步/秒，声音更急促、稍重
    generate_footstep_loop(
        os.path.join(output_dir, 'run.wav'),
        steps_per_second=4.0,
        total_duration=3.0,
        step_duration_ms=280,
        freq_base=100,
        amplitude=0.32
    )
    
    print(f"\n=== 完成！脚步声音效已保存到 {output_dir}/ ===")


if __name__ == '__main__':
    main()
