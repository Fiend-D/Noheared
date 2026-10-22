#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from unheared.paths import get_base_dir

class CaseManager:
    def __init__(self):
        self.current_case = None
        self.case_directory = 'unheared/cases'

    def load_case(self, case_id):
        case_file = os.path.join(self.case_directory, f'{case_id}.json')
        if os.path.exists(case_file):
            with open(case_file, 'r', encoding='utf-8') as f:
                self.current_case = json.load(f)
            # 修复音频文件路径
            if 'audio_tracks' in self.current_case:
                base_dir = get_base_dir()

                for track_id, file_path in self.current_case['audio_tracks'].items():
                    if not os.path.isabs(file_path):
                        full_path = os.path.join(base_dir, 'unheared', file_path)
                    else:
                        full_path = file_path

                    if os.path.exists(full_path):
                        self.current_case['audio_tracks'][track_id] = full_path
                        print(f"找到音频文件: {full_path}")
                    else:
                        print(f"警告: 音频文件不存在: {full_path}")
            return True
        return False

    def get_case_info(self):
        if self.current_case:
            return {
                'name': self.current_case.get('name', ''),
                'description': self.current_case.get('description', ''),
                'duration': self.current_case.get('duration', 0)
            }
        return None

    def get_characters(self):
        if self.current_case:
            return self.current_case.get('characters', {})
        return {}

    def get_audio_tracks(self):
        if self.current_case:
            return self.current_case.get('audio_tracks', {})
        return {}

    def get_character_positions(self, timestamp):
        """获取所有角色在指定时间戳的位置和移动状态"""
        if self.current_case:
            positions = {}
            for char_id, char_data in self.current_case.get('characters', {}).items():
                if 'positions' in char_data:
                    for pos in char_data['positions']:
                        if pos['start'] <= timestamp <= pos['end']:
                            positions[char_id] = {
                                'position': pos['position'],
                                'movement': pos.get('movement', 'walk')
                            }
                            break
            return positions
        return {}

    def get_character_position_at_time(self, char_id, timestamp):
        """根据时间戳获取指定角色的位置和移动状态"""
        if self.current_case:
            char_data = self.current_case.get('characters', {}).get(char_id)
            if char_data and 'positions' in char_data:
                for pos in char_data['positions']:
                    if pos['start'] <= timestamp <= pos['end']:
                        return {
                            'position': pos['position'],
                            'movement': pos.get('movement', 'walk')
                        }
        return None

    def get_scene(self):
        """获取场景数据（地图、区域、门）"""
        if self.current_case:
            return self.current_case.get('scene', None)
        return None

    def get_questions(self):
        """获取案件问题列表"""
        if self.current_case:
            return self.current_case.get('questions', [])
        return []

    def get_dialogues(self, timestamp):
        if self.current_case:
            dialogues = []
            for dialogue in self.current_case.get('dialogues', []):
                if dialogue['start'] <= timestamp <= dialogue['end']:
                    dialogues.append(dialogue)
            return dialogues
        return []
