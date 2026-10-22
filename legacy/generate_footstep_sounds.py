#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成脚步声音效
walk: 高跟鞋（清脆短促的咔嗒声）
run:  运动鞋（较沉闷的噗噗声）
"""

import os
import numpy as np
import wave


def generate_highheel_step(sample_rate=24000, amplitude=0.45):
    """生成高跟鞋单步声音（清脆咔嗒）"""
    # 非常短促：约 90ms
    duration_ms = 90
    num_samples = int(sample_rate * duration_ms / 1000)
    t = np.arange(num_samples) / sample_rate
    
    # 主频：约 1800Hz 的高频正弦波，快速衰减
    freq_main = 1800
    env_main = np.exp(-t / 0.015)  # 15ms 衰减常数
    signal = np.sin(2 * np.pi * freq_main * t) * env_main * 0.6
    
    # 高频谐波（3600Hz），增加清脆感
    freq_harm = 3600
    env_harm = np.exp(-t / 0.008)
    signal += np.sin(2 * np.pi * freq_harm * t) * env_harm * 0.25
    
    # 短促高频 click（类似鞋跟撞击）
    click_samples = int(sample_rate * 0.008)  # 8ms
    click = np.random.uniform(-1, 1, click_samples)
    click_env = np.exp(-np.arange(click_samples) / (sample_rate * 0.003))
    signal[:click_samples] += click * click_env * 0.35
    
    # 低切：去除低频浑浊，让声音更清脆
    # 简单高通：用差分近似
    signal = np.diff(signal, prepend=signal[0]) * 0.5 + signal * 0.5
    
    signal = np.clip(signal * amplitude, -1.0, 1.0)
    return (signal * 32767).astype(np.int16)


def generate_sneaker_step(sample_rate=24000, amplitude=0.4):
    """生成运动鞋单步声音（较沉闷的噗噗声）"""
    # 稍长：约 160ms
    duration_ms = 160
    num_samples = int(sample_rate * duration_ms / 1000)
    t = np.arange(num_samples) / sample_rate
    
    # 带通噪声（中低频，类似橡胶摩擦）
    noise = np.random.uniform(-1, 1, num_samples)
    # 简单低通滤波（保留 200Hz 以下）
    alpha = 0.3
    filtered_noise = np.zeros_like(noise, dtype=np.float64)
    filtered_noise[0] = noise[0]
    for i in range(1, num_samples):
        filtered_noise[i] = alpha * filtered_noise[i - 1] + (1 - alpha) * noise[i]
    
    # 包络：稍柔和的上升和衰减
    env = np.exp(-t / 0.05)  # 50ms 衰减常数
    signal = filtered_noise * env * 0.5
    
    # 低频 thud（约 120Hz 正弦波）
    freq_thud = 120
    env_thud = np.exp(-t / 0.04)
    signal += np.sin(2 * np.pi * freq_thud * t) * env_thud * 0.5
    
    # 极低频共鸣（约 60Hz），增加厚重感
    freq_low = 60
    env_low = np.exp(-t / 0.08)
    signal += np.sin(2 * np.pi * freq_low * t) * env_low * 0.2
    
    signal = np.clip(signal * amplitude, -1.0, 1.0)
    return (signal * 32767).astype(np.int16)


def build_loop(step_func, output_path, steps_per_second=2.0, total_duration=3.0,
               amplitude=0.4, sample_rate=24000):
    """将单步声音组合成循环音效"""
    total_samples = int(sample_rate * total_duration)
    step_interval = int(sample_rate / steps_per_second)
    
    track = np.zeros(total_samples, dtype=np.float64)
    step_sample = step_func(sample_rate, amplitude).astype(np.float64)
    
    for i in range(0, total_samples, step_interval):
        end = min(i + len(step_sample), total_samples)
        track[i:end] += step_sample[:end - i]
    
    # 归一化防止削波
    max_val = np.max(np.abs(track))
    if max_val > 0.75 * 32767:
        track = track * (0.75 * 32767 / max_val)
    
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
    print("walk -> 高跟鞋（清脆咔嗒声）")
    print("run  -> 运动鞋（沉闷噗噗声）")
    
    # 高跟鞋（走路）：2步/秒，较轻
    build_loop(
        generate_highheel_step,
        os.path.join(output_dir, 'walk.wav'),
        steps_per_second=2.0,
        total_duration=3.0,
        amplitude=0.35
    )
    
    # 运动鞋（跑步）：4步/秒，稍重
    build_loop(
        generate_sneaker_step,
        os.path.join(output_dir, 'run.wav'),
        steps_per_second=4.0,
        total_duration=3.0,
        amplitude=0.4
    )
    
    print(f"\n=== 完成！已保存到 {output_dir}/ ===")


if __name__ == '__main__':
    main()
