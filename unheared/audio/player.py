#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import numpy as np
import pygame


class AudioPlayer:
    def __init__(self):
        # 24000Hz 匹配音频文件，-16 表示 16bit 有符号，1 声道，512 缓冲区（低延迟）
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
            pygame.mixer.set_num_channels(32)
        else:
            # 切换到新案件时，先停掉所有已有的 channel，防止旧音频残留
            for i in range(32):
                pygame.mixer.Channel(i).stop()

        self._raw_arrays = {}        # track_id -> numpy int16 array
        self._channel_indices = {}   # track_id -> pygame channel index
        self._sounds = {}            # track_id -> current pygame Sound
        self._next_channel_index = 0
        self.duration = 0
        self._last_volumes = {}

        # 脚步声轨道
        self._footstep_sounds = {}      # 'walk'/'run' -> pygame Sound
        self._footstep_channels = {}    # 'walk'/'run' -> pygame Channel
        self._footstep_volumes = {}     # 'walk'/'run' -> last volume

        # 播放状态
        self._position = 0.0         # 当前播放位置（秒）
        self._start_time = None      # perf_counter 时间戳
        self._is_playing = False

    def add_track(self, track_id, file_path):
        import os
        import wave
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            self._raw_arrays[track_id] = None
            return

        with wave.open(abs_path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()

            raw_data = wf.readframes(n_frames)

            if sample_width == 2:
                arr = np.frombuffer(raw_data, dtype=np.int16)
            elif sample_width == 1:
                arr = np.frombuffer(raw_data, dtype=np.uint8).astype(np.int16) * 256 - 32768
            elif sample_width == 4:
                arr = np.frombuffer(raw_data, dtype=np.int32).astype(np.int16) // 256
            else:
                raise ValueError(f"Unsupported sample width: {sample_width}")

            # 立体声转单声道
            if n_channels == 2:
                arr = arr.reshape(-1, 2).mean(axis=1).astype(np.int16)

            self._raw_arrays[track_id] = arr
            track_duration = n_frames / framerate
            self.duration = max(self.duration, track_duration)

        # 分配固定 channel
        self._channel_indices[track_id] = self._next_channel_index
        self._next_channel_index += 1
        self._last_volumes[track_id] = 1.0
        self._sounds[track_id] = None

    def _make_sound(self, track_id, start_seconds=0):
        if track_id not in self._raw_arrays or self._raw_arrays[track_id] is None:
            return None

        arr = self._raw_arrays[track_id]
        start_sample = int(start_seconds * 24000)

        if start_sample >= len(arr):
            return None

        sliced = arr[start_sample:]
        return pygame.sndarray.make_sound(sliced)

    def play(self):
        self._start_time = time.perf_counter()
        self._is_playing = True

        for track_id, arr in self._raw_arrays.items():
            if arr is None:
                continue

            sound = self._make_sound(track_id, self._position)
            if sound:
                self._sounds[track_id] = sound
                ch = pygame.mixer.Channel(self._channel_indices[track_id])
                ch.play(sound)
                vol = self._last_volumes.get(track_id, 1.0)
                ch.set_volume(vol)

    def pause(self):
        if not self._is_playing:
            return

        # 计算已播放时间
        if self._start_time is not None:
            elapsed = time.perf_counter() - self._start_time
            self._position += elapsed
            self._start_time = None

        self._is_playing = False

        for idx in self._channel_indices.values():
            ch = pygame.mixer.Channel(idx)
            if ch.get_busy():
                ch.pause()

    def stop(self):
        self._is_playing = False
        self._position = 0.0
        self._start_time = None

        for idx in self._channel_indices.values():
            ch = pygame.mixer.Channel(idx)
            ch.stop()
        
        self.stop_footsteps()

    def set_position(self, position):
        was_playing = self._is_playing
        self._position = max(0.0, position)

        # 停止当前所有播放
        for idx in self._channel_indices.values():
            pygame.mixer.Channel(idx).stop()
        
        self.stop_footsteps()

        if was_playing:
            self._start_time = time.perf_counter()
            for track_id, arr in self._raw_arrays.items():
                if arr is None:
                    continue
                sound = self._make_sound(track_id, self._position)
                if sound:
                    self._sounds[track_id] = sound
                    ch = pygame.mixer.Channel(self._channel_indices[track_id])
                    ch.play(sound)
                    vol = self._last_volumes.get(track_id, 1.0)
                    ch.set_volume(vol)

    def get_position(self):
        if self._is_playing and self._start_time is not None:
            elapsed = time.perf_counter() - self._start_time
            pos = self._position + elapsed
            if pos >= self.duration:
                self._is_playing = False
                self._start_time = None
                self._position = 0.0  # 重置播放位置
                return self.duration
            return pos
        return self._position

    def is_playing(self):
        if self._is_playing and self._start_time is not None:
            elapsed = time.perf_counter() - self._start_time
            pos = self._position + elapsed
            if pos >= self.duration:
                self._is_playing = False
                self._start_time = None
                self._position = 0.0  # 重置播放位置
        return self._is_playing

    def get_duration(self):
        return self.duration

    def set_volume(self, track_id, volume):
        if track_id not in self._channel_indices:
            return

        volume = max(0.0, min(1.0, volume))
        last = self._last_volumes.get(track_id, -1.0)

        if volume == 0.0 or last == 0.0 or abs(volume - last) > 0.01:
            self._last_volumes[track_id] = volume
            idx = self._channel_indices[track_id]
            ch = pygame.mixer.Channel(idx)
            ch.set_volume(volume)

    def set_volume_by_distance(self, track_id, distance, max_distance=120):
        if track_id in self._channel_indices:
            if distance >= max_distance:
                volume = 0.0
            else:
                min_volume = 0.05
                volume = max(min_volume, 1.0 - (distance / max_distance))
            self.set_volume(track_id, volume)

    def set_pan(self, track_id, pan):
        """
        设置声道平衡 -1.0(左) ~ 1.0(右)
        pygame.mixer 单声道模式不支持真正的立体声分离，
        此方法仅作扩展接口保留，实际不执行任何操作
        """
        pass

    def add_footstep_tracks(self, walk_path, run_path):
        """加载脚步声音效轨道（走路/跑动）"""
        import os
        for movement_type, path in [('walk', walk_path), ('run', run_path)]:
            if path and os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    self._footstep_sounds[movement_type] = sound
                    ch = pygame.mixer.Channel(self._next_channel_index)
                    self._footstep_channels[movement_type] = ch
                    self._footstep_volumes[movement_type] = 0.0
                    self._next_channel_index += 1
                except Exception as e:
                    print(f"警告: 无法加载脚步声音效 {movement_type}: {e}")

    def set_footstep_volume(self, movement_type, volume):
        """设置脚步声音量并控制播放/停止"""
        if movement_type not in self._footstep_channels:
            return
        
        volume = max(0.0, min(1.0, volume))
        last_vol = self._footstep_volumes.get(movement_type, -1.0)
        
        # 只在音量变化足够大或从0/到0时操作
        if volume == 0.0 or last_vol == 0.0 or abs(volume - last_vol) > 0.02:
            self._footstep_volumes[movement_type] = volume
            ch = self._footstep_channels[movement_type]
            sound = self._footstep_sounds.get(movement_type)
            
            if volume > 0.01 and sound:
                if not ch.get_busy():
                    ch.play(sound, loops=-1)
                ch.set_volume(volume)
            else:
                if ch.get_busy():
                    ch.stop()

    def stop_footsteps(self):
        """停止所有脚步声"""
        for movement_type, ch in self._footstep_channels.items():
            if ch.get_busy():
                ch.stop()
            self._footstep_volumes[movement_type] = 0.0
