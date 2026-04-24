#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QMessageBox, QFrame, QSplitter, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from unheared.audio.player import AudioPlayer
from unheared.scene.map import SceneMap
from unheared.case.case import CaseManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('疑案追声')
        self.setGeometry(100, 100, 1400, 800)

        self.audio_player = AudioPlayer()
        self.scene_map = SceneMap()
        # 设置回调函数
        self.scene_map.mark_callback = self.on_character_marked
        self.scene_map.listener_move_callback = self.on_listener_moved
        self.case_manager = CaseManager()

        # 进度条拖动标志
        self.is_slider_dragging = False

        # 当前说话的角色（用于声波纹）
        self.current_speaking = set()

        # 字幕历史记录
        self._subtitle_history = []
        self._seen_dialogue_ids = set()

        # 选中的角色（用于标记）
        self.selected_char_id = None
        self.selected_char_name = None
        self.was_playing = False  # 跟踪之前的播放状态

        self.init_ui()
        self.load_cases()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        central_widget.setStyleSheet('''
            QWidget {
                background-color: #14161f;
                color: #c8cdd5;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
                font-size: 13px;
            }
            QFrame#card {
                background-color: #1a1c26;
                border: 1px solid #252a38;
                border-radius: 10px;
            }
            QLabel#title {
                color: #d4a843;
                font-size: 20px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QLabel#section {
                color: #8a94a8;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QLabel {
                color: #a0a8b8;
            }
            QComboBox {
                background-color: #1e212c;
                border: 1px solid #2f3548;
                border-radius: 6px;
                color: #c8cdd5;
                padding: 5px 10px;
                min-width: 180px;
            }
            QComboBox:hover {
                border-color: #d4a843;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e212c;
                color: #c8cdd5;
                border: 1px solid #2f3548;
                selection-background-color: #d4a843;
                selection-color: #14161f;
                padding: 4px;
            }
            QListWidget {
                background-color: #161822;
                border: 1px solid #252a38;
                border-radius: 6px;
                color: #c8cdd5;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #d4a843;
                color: #14161f;
            }
            QListWidget::item:hover {
                background-color: #252a38;
            }
            QTextEdit {
                background-color: #161822;
                border: 1px solid #252a38;
                border-radius: 6px;
                color: #c8cdd5;
                padding: 10px;
                font-size: 13px;
                line-height: 1.6;
            }
            QPushButton {
                background-color: #252a38;
                border: 1px solid #353d52;
                border-radius: 6px;
                color: #c8cdd5;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2f3548;
                border-color: #4a5270;
            }
            QPushButton:pressed {
                background-color: #353d52;
            }
            QPushButton#primary {
                background-color: #2e6db4;
                border-color: #3a7ac8;
                color: #ffffff;
            }
            QPushButton#primary:hover {
                background-color: #3a7ac8;
            }
            QPushButton#play {
                background-color: #2e6db4;
                border-color: #3a7ac8;
                color: #ffffff;
                font-weight: bold;
                min-width: 90px;
            }
            QPushButton#play:hover {
                background-color: #3a7ac8;
            }
            QSlider {
                background-color: transparent;
            }
            QSlider::groove:horizontal {
                background: #252a38;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2e6db4, stop:1 #5a9ad8);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #7aa8d8;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #9ac8f8;
            }
        ''')

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # === 顶部栏：游戏标题 + 案例选择 + 提交按钮 ===
        top_bar = QFrame()
        top_bar.setObjectName('card')
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 10, 16, 10)
        top_layout.setSpacing(12)

        title_label = QLabel('疑案追声')
        title_label.setObjectName('title')
        top_layout.addWidget(title_label)

        top_layout.addSpacing(24)

        case_label = QLabel('案例选择')
        case_label.setObjectName('section')
        top_layout.addWidget(case_label)

        self.case_combo = QComboBox()
        self.case_combo.setMinimumWidth(220)
        self.case_combo.currentIndexChanged.connect(self.on_case_selected)
        top_layout.addWidget(self.case_combo)

        top_layout.addStretch()

        self.submit_button = QPushButton('提交答案')
        self.submit_button.setObjectName('primary')
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self.submit_answer)
        top_layout.addWidget(self.submit_button)

        main_layout.addWidget(top_bar)

        # === 中间：分割器 - 左侧字幕+人员列表，右侧地图+问题 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet('QSplitter::handle { background-color: #252a38; }')

        # 左侧面板
        left_card = QFrame()
        left_card.setObjectName('card')
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        subtitle_label = QLabel('对话字幕')
        subtitle_label.setObjectName('section')
        left_layout.addWidget(subtitle_label)

        self.dialogue_display = QTextEdit()
        self.dialogue_display.setReadOnly(True)
        self.dialogue_display.setMinimumHeight(200)
        left_layout.addWidget(self.dialogue_display, 3)

        char_label = QLabel('人员列表')
        char_label.setObjectName('section')
        left_layout.addWidget(char_label)

        self.character_list = QListWidget()
        self.character_list.setMaximumHeight(180)
        self.character_list.itemClicked.connect(self.select_character)
        left_layout.addWidget(self.character_list, 1)

        self.mark_status_label = QLabel('标记状态: 未开始')
        self.mark_status_label.setStyleSheet('color: #8a9ab8; font-size: 12px;')
        left_layout.addWidget(self.mark_status_label)

        splitter.addWidget(left_card)

        # 右侧面板
        right_card = QFrame()
        right_card.setObjectName('card')
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        # 问题卡片
        questions_card = QFrame()
        questions_card.setObjectName('card')
        questions_card.setStyleSheet('''
            QFrame#card {
                background-color: #161822;
                border: 1px solid #252a38;
                border-radius: 8px;
            }
        ''')
        questions_card_layout = QVBoxLayout(questions_card)
        questions_card_layout.setContentsMargins(12, 10, 12, 10)
        questions_card_layout.setSpacing(8)

        questions_label = QLabel('案件问题')
        questions_label.setObjectName('section')
        questions_card_layout.addWidget(questions_label)

        self.questions_container = QWidget()
        self.questions_layout = QHBoxLayout(self.questions_container)
        self.questions_layout.setContentsMargins(0, 0, 0, 0)
        self.questions_layout.setSpacing(12)
        questions_card_layout.addWidget(self.questions_container)

        right_layout.addWidget(questions_card)

        map_label = QLabel('场景地图')
        map_label.setObjectName('section')
        right_layout.addWidget(map_label)

        right_layout.addWidget(self.scene_map, 1)

        splitter.addWidget(right_card)
        splitter.setSizes([380, 1020])

        main_layout.addWidget(splitter, 1)

        # === 底部：播放控制 ===
        bottom_card = QFrame()
        bottom_card.setObjectName('card')
        bottom_layout = QHBoxLayout(bottom_card)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.setSpacing(14)

        self.play_button = QPushButton('▶ 播放')
        self.play_button.setObjectName('play')
        self.play_button.clicked.connect(self.toggle_play)
        bottom_layout.addWidget(self.play_button)

        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setRange(0, 1000)
        self.time_slider.sliderPressed.connect(self.on_slider_pressed)
        self.time_slider.sliderReleased.connect(self.on_slider_released)
        self.time_slider.valueChanged.connect(self.seek)
        bottom_layout.addWidget(self.time_slider, 1)

        self.time_label = QLabel('00:00 / 00:00')
        self.time_label.setStyleSheet('color: #8a94a8; font-family: monospace; font-size: 13px;')
        bottom_layout.addWidget(self.time_label)

        self.clear_marks_button = QPushButton('清除标记')
        self.clear_marks_button.clicked.connect(self.clear_all_marks)
        bottom_layout.addWidget(self.clear_marks_button)

        main_layout.addWidget(bottom_card)

        # 定时器更新时间和对话
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(100)

    def load_cases(self):
        # 加载案例列表，显示脚本名称
        import os, json
        cases_dir = 'unheared/cases'
        if os.path.exists(cases_dir):
            for f in sorted(os.listdir(cases_dir)):
                if f.endswith('.json'):
                    case_id = f[:-5]
                    case_path = os.path.join(cases_dir, f)
                    try:
                        with open(case_path, 'r', encoding='utf-8') as cf:
                            case_data = json.load(cf)
                        case_title = case_data.get('name', case_id)
                    except Exception:
                        case_title = case_id
                    self.case_combo.addItem(case_title, case_id)

    def on_case_selected(self, index):
        if index >= 0:
            case_id = self.case_combo.itemData(index)
            self.select_case(case_id)

    def select_case(self, case_id):
        if self.case_manager.load_case(case_id):
            case_info = self.case_manager.get_case_info()
            self.setWindowTitle(f'疑案追声 - {case_info["name"]}')

            # 清除之前的音频
            self.audio_player.stop()
            self.audio_player = AudioPlayer()

            # 加载音频轨道
            audio_tracks = self.case_manager.get_audio_tracks()
            for track_id, file_path in audio_tracks.items():
                self.audio_player.add_track(track_id, file_path)

            # 加载脚步声音效
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            walk_path = os.path.join(project_root, 'unheared', 'audio', 'footsteps', 'walk.wav')
            run_path = os.path.join(project_root, 'unheared', 'audio', 'footsteps', 'run.wav')
            self.audio_player.add_footstep_tracks(walk_path, run_path)

            # 加载场景
            scene_data = self.case_manager.get_scene()
            self.scene_map.load_scene(scene_data, case_id=case_id)

            # 初始化场景
            self.init_scene()

            # 重置时间戳状态
            self.last_timestamp = None
            self.current_speaking = set()

            # 更新人员列表
            self.update_character_list()

            # 加载问题
            self.setup_questions()

            # 启用提交按钮
            self.submit_button.setEnabled(True)

            # 重置播放状态
            self.play_button.setText('▶ 播放')

    def init_scene(self):
        # 从案例数据加载角色到场景地图
        characters = self.case_manager.get_characters()
        self.scene_map.load_characters(characters)

        # 初始化角色位置（从时间轴第一个位置）
        for char_id, char_data in characters.items():
            if 'positions' in char_data and char_data['positions']:
                first_pos = char_data['positions'][0]
                x, y = first_pos['position']
                self.scene_map.update_character_position(char_id, x, y)
                # 直接设置当前位置
                if char_id in self.scene_map.characters:
                    self.scene_map.characters[char_id]['x'] = x
                    self.scene_map.characters[char_id]['y'] = y

        self.scene_map.update()

    def toggle_play(self):
        if self.audio_player.is_playing():
            self.audio_player.pause()
            self.play_button.setText('▶ 播放')
        else:
            if self.audio_player.get_duration() > 0:
                self.audio_player.play()
                self.play_button.setText('⏸ 暂停')

    def on_slider_pressed(self):
        self.is_slider_dragging = True

    def on_slider_released(self):
        self.is_slider_dragging = False

    def seek(self, value):
        duration = self.audio_player.get_duration()
        if duration > 0:
            position = (value / 1000) * duration
            self.audio_player.set_position(position)
            self.update_character_positions(position)
            self.update_dialogues(position)

    def update_ui(self):
        position = self.audio_player.get_position()
        duration = self.audio_player.get_duration()
        self.update_time()
        self.update_dialogues(position)
        self.update_character_positions(position)
        self.update_speaking_animations(position)
        self.update_footstep_sounds()

        # 检查播放状态变化
        is_playing = self.audio_player.is_playing()
        if self.was_playing != is_playing:
            if is_playing:
                self.play_button.setText('⏸ 暂停')
            else:
                self.play_button.setText('▶ 播放')
                # 仅在自然播放结束时重置，暂停时保留当前进度
                if duration > 0 and position >= duration - 0.2:
                    self.time_slider.setValue(0)
                    self.dialogue_display.clear()
        self.was_playing = is_playing

    def update_time(self):
        if not self.is_slider_dragging:
            position = self.audio_player.get_position()
            duration = self.audio_player.get_duration()
            if duration > 0:
                pos_str = self.format_time(position)
                dur_str = self.format_time(duration)
                self.time_label.setText(f'{pos_str} / {dur_str}')
                progress = min(1.0, max(0.0, position / duration))
                slider_value = int(progress * 1000)
                if abs(slider_value - self.time_slider.value()) > 2:
                    self.time_slider.setValue(slider_value)

    def update_dialogues(self, timestamp):
        # 检测时间回退（seek），清空历史重新构建
        if getattr(self, 'last_timestamp', None) is not None and timestamp < self.last_timestamp - 0.5:
            self._subtitle_history.clear()
            self._seen_dialogue_ids.clear()

        dialogues = self.case_manager.get_dialogues(timestamp)
        if dialogues:
            for d in dialogues:
                dialogue_key = (d['character'], d['text'], d['start'])
                if dialogue_key not in self._seen_dialogue_ids:
                    self._seen_dialogue_ids.add(dialogue_key)
                    self._subtitle_history.append({
                        'time': d['start'],
                        'character': d['character'],
                        'text': d['text']
                    })
                    if len(self._subtitle_history) > 100:
                        self._subtitle_history.pop(0)
            self._refresh_dialogue_display()

        # 播放结束或重置时清空
        if not self.audio_player.is_playing() and self.audio_player.get_position() <= 0.1:
            if self._subtitle_history:
                self._subtitle_history.clear()
                self._seen_dialogue_ids.clear()
                self.dialogue_display.clear()

    def _refresh_dialogue_display(self):
        """刷新字幕显示区域"""
        if not self._subtitle_history:
            return
        lines = []
        for entry in self._subtitle_history[-25:]:
            time_str = f"{int(entry['time'] // 60):02d}:{int(entry['time'] % 60):02d}"
            lines.append(
                f'<span style="color:#5a7a9a;font-size:11px;">[{time_str}]</span> '
                f'<span style="color:#7aa8d8;">{entry["character"]}</span>: '
                f'<span style="color:#e0e4ec;">{entry["text"]}</span>'
            )
        self.dialogue_display.setHtml('<br>'.join(lines))

    def update_speaking_animations(self, timestamp):
        """更新角色说话状态，控制声波纹"""
        dialogues = self.case_manager.get_dialogues(timestamp)
        current_speaking_chars = set()

        for d in dialogues:
            char_id = d['character']
            current_speaking_chars.add(char_id)
            if char_id not in self.current_speaking:
                self.scene_map.set_speaking(char_id, True)

        # 停止不再说话的角色的声波纹
        for char_id in self.current_speaking - current_speaking_chars:
            self.scene_map.set_speaking(char_id, False)

        self.current_speaking = current_speaking_chars

    def update_footstep_sounds(self):
        """更新脚步声效：根据监听点周围角色的移动状态播放走路/跑动声"""
        if not hasattr(self.audio_player, '_footstep_channels') or not self.audio_player._footstep_channels:
            return
        state = self.scene_map.get_footstep_state()
        for movement_type, volume in state.items():
            self.audio_player.set_footstep_volume(movement_type, volume)

    def _update_character_audio(self, char_id, char_x, char_y, listener_x, listener_y):
        """根据角色和监听点的位置关系更新音量和声像"""
        can_hear = self.scene_map.can_hear_each_other(listener_x, listener_y, char_x, char_y)

        if not can_hear:
            self.audio_player.set_volume(char_id, 0.0)
            return

        distance = ((char_x - listener_x) ** 2 + (char_y - listener_y) ** 2) ** 0.5
        self.audio_player.set_volume_by_distance(char_id, distance, self.scene_map.listener_radius)
        pan = (char_x - listener_x) / 400.0
        self.audio_player.set_pan(char_id, pan)

    def update_character_positions(self, timestamp):
        positions = self.case_manager.get_character_positions(timestamp)

        is_seeking = False
        if getattr(self, 'last_timestamp', None) is not None:
            time_diff = abs(timestamp - self.last_timestamp)
            if time_diff > 1.0:
                is_seeking = True

        listener_x, listener_y = self.scene_map.get_listener_position()

        for char_id, data in positions.items():
            pos = data['position']
            movement = data.get('movement', 'walk')
            x, y = pos
            if is_seeking:
                if char_id in self.scene_map.characters:
                    self.scene_map.characters[char_id]['x'] = x
                    self.scene_map.characters[char_id]['y'] = y

            self.scene_map.update_character_position(char_id, x, y, movement)

            if char_id in self.scene_map.characters:
                actual_x = self.scene_map.characters[char_id]['x']
                actual_y = self.scene_map.characters[char_id]['y']
            else:
                actual_x, actual_y = x, y

            self._update_character_audio(char_id, actual_x, actual_y, listener_x, listener_y)

        self.last_timestamp = timestamp

    def on_listener_moved(self, x, y):
        """监听点移动时更新音量"""
        if not self.case_manager.current_case:
            return

        listener_x, listener_y = self.scene_map.get_listener_position()
        position = self.audio_player.get_position()

        audio_tracks = self.case_manager.get_audio_tracks()
        all_char_ids = list(audio_tracks.keys())

        for char_id in all_char_ids:
            char_data = self.case_manager.get_character_position_at_time(char_id, position)
            if char_data:
                char_x, char_y = char_data['position']
            else:
                char_x, char_y = 0, 0

            if char_id in self.scene_map.characters:
                char_x = self.scene_map.characters[char_id]['x']
                char_y = self.scene_map.characters[char_id]['y']

            self._update_character_audio(char_id, char_x, char_y, listener_x, listener_y)

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f'{minutes:02d}:{secs:02d}'

    def clear_all_marks(self):
        self.scene_map.clear_all_marks()
        self.update_character_list()
        self.mark_status_label.setText('标记状态: 未开始')
        self.mark_status_label.setStyleSheet('color: #8a9ab8;')

    def update_character_list(self):
        self.character_list.clear()
        characters = self.case_manager.get_characters()
        marked = self.scene_map.get_marked_characters()

        for char_id, char_info in characters.items():
            # 只显示角色名称，不暴露标记结果（避免剧透）
            item = QListWidgetItem(char_info['name'])
            item.setData(Qt.ItemDataRole.UserRole, char_id)
            self.character_list.addItem(item)

        # 更新标记状态（只显示数量，不显示具体标记了谁）
        total = len(characters)
        marked_count = len(marked)
        if marked_count == total and total > 0:
            self.mark_status_label.setText(f'标记状态: 已完成 ({marked_count}/{total})')
            self.mark_status_label.setStyleSheet('color: #6ab88a;')
        else:
            self.mark_status_label.setText(f'标记状态: {marked_count}/{total}')
            self.mark_status_label.setStyleSheet('color: #c8a85c;')

    def select_character(self, item):
        char_id = item.data(Qt.ItemDataRole.UserRole)
        char_name = self.case_manager.get_characters().get(char_id, {}).get('name', char_id)
        self.selected_char_id = char_id
        self.selected_char_name = char_name
        self.dialogue_display.setHtml(
            f'<span style="color:#7aa8d8;">已选择: {char_name}</span><br>'
            f'<span style="color:#8a9ab8;">请点击地图中的角色圆圈进行标记</span>'
        )

    def on_character_marked(self, circle_id, marked):
        if self.selected_char_id and self.selected_char_name:
            if marked:
                # 检查该人员是否已被标记到其他圆圈上，如果是则取消旧标记（一人一源）
                for other_id, other_char in self.scene_map.characters.items():
                    if other_id != circle_id and other_char['marked'] and other_char.get('assigned_name') == self.selected_char_name:
                        self.scene_map.set_character_mark(other_id, False, '')
                        break
                self.scene_map.set_character_mark(circle_id, True, self.selected_char_name)
            else:
                self.scene_map.set_character_mark(circle_id, False, '')

            self.update_character_list()
            self.selected_char_id = None
            self.selected_char_name = None
        else:
            self.dialogue_display.setHtml(
                '<span style="color:#d87878;">请先从人员列表中选择一个角色</span>'
            )

    def setup_questions(self):
        """根据当前案例动态加载问题"""
        # 清空现有问题控件
        while self.questions_layout.count():
            item = self.questions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.question_combos = {}
        questions = self.case_manager.get_questions()

        for q in questions:
            q_widget = QWidget()
            q_layout = QVBoxLayout(q_widget)
            q_layout.setContentsMargins(4, 4, 4, 4)
            q_layout.setSpacing(4)

            # 问题文字
            q_label = QLabel(q['question'])
            q_label.setStyleSheet('color: #b0b8c8; font-size: 12px;')
            q_label.setWordWrap(True)
            q_layout.addWidget(q_label)

            # 选项下拉框
            combo = QComboBox()
            combo.setStyleSheet('''
                QComboBox {
                    background-color: #2a2d38;
                    border: 1px solid #404858;
                    border-radius: 3px;
                    color: #c8cdd5;
                    padding: 4px;
                }
                QComboBox::drop-down { border: none; }
                QComboBox QAbstractItemView {
                    background-color: #2a2d38;
                    color: #c8cdd5;
                    selection-background-color: #3a5a8a;
                }
            ''')
            combo.addItem('-- 请选择 --')
            for opt in q['options']:
                combo.addItem(opt)
            q_layout.addWidget(combo)

            self.questions_layout.addWidget(q_widget)
            self.question_combos[q['id']] = {
                'combo': combo,
                'answer': q['answer'],
                'question': q['question']
            }

    def submit_answer(self):
        """提交答案验证（标记 + 问题）"""
        if not self.case_manager.current_case:
            return

        marked = self.scene_map.get_marked_characters()
        characters = self.case_manager.get_characters()

        # === 验证标记 ===
        if len(marked) != len(characters):
            QMessageBox.warning(
                self, '标记不完整',
                f'请完成所有标记后再提交。\n当前标记: {len(marked)}/{len(characters)}'
            )
            return

        mark_correct = 0
        mark_wrong = 0
        mark_results = []

        for char_id, assigned_name in marked.items():
            correct_name = characters.get(char_id, {}).get('name', '')
            if assigned_name == correct_name:
                mark_correct += 1
                mark_results.append(f'✓ {char_id} → {assigned_name}')
            else:
                mark_wrong += 1
                mark_results.append(f'✗ {char_id} → {assigned_name} （正确: {correct_name}）')

        # === 验证问题 ===
        question_results = []
        question_correct = 0
        question_wrong = 0
        unanswered = 0

        for qid, data in self.question_combos.items():
            combo = data['combo']
            selected = combo.currentText()
            if selected == '-- 请选择 --':
                unanswered += 1
                question_results.append(f'? {data["question"]}')
            elif selected == data['answer']:
                question_correct += 1
                question_results.append(f'✓ {data["question"]}: {selected}')
            else:
                question_wrong += 1
                question_results.append(f'✗ {data["question"]}: {selected} （正确: {data["answer"]}）')

        # === 汇总结果 ===
        lines = []
        lines.append('【人员标记】')
        lines.extend(mark_results)
        lines.append(f'标记得分: {mark_correct}/{len(characters)}')

        if self.question_combos:
            lines.append('')
            lines.append('【案件问题】')
            lines.extend(question_results)
            if unanswered > 0:
                lines.append(f'问题得分: {question_correct}/{len(self.question_combos)} （{unanswered}题未答）')
            else:
                lines.append(f'问题得分: {question_correct}/{len(self.question_combos)}')

        result_text = '\n'.join(lines)

        total_correct = mark_correct + question_correct
        total_items = len(characters) + len(self.question_combos)

        if mark_wrong == 0 and question_wrong == 0 and unanswered == 0:
            QMessageBox.information(self, '完美通关!', result_text)
        else:
            QMessageBox.information(self, f'得分: {total_correct}/{total_items}', result_text)
