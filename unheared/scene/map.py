#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QRadialGradient

class SceneMap(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 400)
        self.setMouseTracking(True)
        
        # 蓝图风格场景
        self.scene = {
            'name': '默认场景',
            'areas': [
                {'name': '房间1', 'x': 100, 'y': 100, 'width': 200, 'height': 150},
                {'name': '房间2', 'x': 400, 'y': 100, 'width': 200, 'height': 150},
                {'name': '走廊', 'x': 100, 'y': 250, 'width': 500, 'height': 100}
            ],
            'doors': [
                {'name': '房间1门', 'area1': '房间1', 'area2': '走廊', 'x': 190, 'y': 250, 'width': 20, 'height': 10},
                {'name': '房间2门', 'area1': '房间2', 'area2': '走廊', 'x': 490, 'y': 250, 'width': 20, 'height': 10}
            ]
        }
        
        # 构建区域邻接图: {area_name: [(door_info, neighbor_area), ...]}
        self.area_graph = {}
        for area in self.scene['areas']:
            self.area_graph[area['name']] = []
        for door in self.scene.get('doors', []):
            self.area_graph[door['area1']].append((door, door['area2']))
            self.area_graph[door['area2']].append((door, door['area1']))
        
        # 角色数据 - 将由案例数据加载
        self.characters = {}
        
        # 监听点位置（主角）
        self.listener_pos = QPoint(self.width() // 2, self.height() // 2)
        self.listener_target_x = float(self.listener_pos.x())
        self.listener_target_y = float(self.listener_pos.y())
        self.listener_path = []  # 监听点路径点
        self.listener_radius = 100
        
        # 选中状态
        self.selected_character = None
        self.hovered_character = None
        
        # 声波纹动画
        self.speaking_animations = {}
        self.wave_speed = 0.08
        self.wave_max_radius = 60
        
        # 标记回调
        self.mark_callback = None
        
        # 移动动画定时器
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.update_positions)
        self.move_timer.start(16)
    
    def load_scene(self, scene_data):
        """从案例数据加载场景（地图、区域、门）"""
        if not scene_data:
            return
        self.scene = scene_data
        # 重建区域邻接图
        self.area_graph = {}
        for area in self.scene.get('areas', []):
            self.area_graph[area['name']] = []
        for door in self.scene.get('doors', []):
            self.area_graph[door['area1']].append((door, door['area2']))
            self.area_graph[door['area2']].append((door, door['area1']))
        # 窗口大小适配场景
        w = self.scene.get('width', 800)
        h = self.scene.get('height', 400)
        self.setMinimumSize(w, h)
        # 重置监听点到场景中心
        self.listener_pos = QPoint(w // 2, h // 2)
        self.listener_target_x = float(w // 2)
        self.listener_target_y = float(h // 2)
        self.update()
    
    def load_characters(self, characters_data):
        """从案例数据加载角色"""
        self.characters = {}
        self.speaking_animations = {}
        self.selected_character = None
        self.hovered_character = None
        for char_id, data in characters_data.items():
            color_hex = data.get('color', '#FFFFFF')
            color = QColor(color_hex)
            self.characters[char_id] = {
                'name': data.get('name', char_id),
                'x': 0,
                'y': 0,
                'target_x': 0,
                'target_y': 0,
                'color': color,
                'marked': False,
                'assigned_name': '',
                'info': '',
                'path': []  # 路径点列表 [(x,y), ...]
            }
        self.update()
    
    def set_speaking(self, char_id, speaking):
        import time
        if speaking:
            self.speaking_animations[char_id] = {
                'start_time': int(time.time() * 1000),
                'active': True
            }
        else:
            if char_id in self.speaking_animations:
                self.speaking_animations[char_id]['active'] = False
    
    def get_character_area(self, x, y):
        """判断坐标在哪个区域内（含门区域）"""
        # 先检查门（门的优先级更高）
        for door in self.scene.get('doors', []):
            if (door['x'] <= x <= door['x'] + door['width'] and
                door['y'] <= y <= door['y'] + door['height']):
                return door['area1']  # 门算在 area1 一侧
        # 检查普通区域
        for area in self.scene['areas']:
            if (area['x'] <= x <= area['x'] + area['width'] and
                area['y'] <= y <= area['y'] + area['height']):
                return area['name']
        return None
    
    def can_hear_each_other(self, x1, y1, x2, y2):
        """
        判断两个位置是否能互相听到声音。
        规则：必须在同一区域内。
        门/走廊等区域边界不允许声音传播。
        """
        area1 = self.get_character_area(x1, y1)
        area2 = self.get_character_area(x2, y2)

        if area1 is None or area2 is None:
            return False

        return area1 == area2
    
    def constrain_to_walkable(self, x, y):
        """将坐标限制到最近的合法可行走区域内"""
        # 如果已经在某个区域内，直接返回
        if self.get_character_area(x, y) is not None:
            return (x, y)
        
        # 找到所有区域中距离最近的内部点
        best_x, best_y = x, y
        best_dist = float('inf')
        
        for area in self.scene.get('areas', []):
            # 点到矩形内部的最近点
            cx = max(area['x'], min(x, area['x'] + area['width']))
            cy = max(area['y'], min(y, area['y'] + area['height']))
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_x, best_y = cx, cy
        
        # 限制在 widget 边界内
        best_x = max(0, min(best_x, self.width()))
        best_y = max(0, min(best_y, self.height()))
        
        return (best_x, best_y)
    
    def find_path_from(self, from_x, from_y, target_x, target_y):
        """寻找从指定位置到目标位置的路径（必须经门穿越）"""
        cur_area = self.get_character_area(from_x, from_y)
        tgt_area = self.get_character_area(target_x, target_y)
        
        if cur_area == tgt_area or cur_area is None or tgt_area is None:
            return [(target_x, target_y)]
        
        # BFS 找区域路径
        from collections import deque
        queue = deque([(cur_area, [])])
        visited = {cur_area}
        
        while queue:
            area, path = queue.popleft()
            if area == tgt_area:
                # 构建完整路径点
                full_path = []
                for door, _ in path:
                    door_cx = door['x'] + door['width'] / 2
                    door_cy = door['y'] + door['height'] / 2
                    full_path.append((door_cx, door_cy))
                full_path.append((target_x, target_y))
                return full_path
            
            for door, neighbor in self.area_graph.get(area, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [(door, neighbor)]))
        
        # 未找到路径，直接走（fallback）
        return [(target_x, target_y)]
    
    def find_path(self, char_id, target_x, target_y):
        """寻找角色从当前位置到目标位置的路径"""
        char = self.characters[char_id]
        return self.find_path_from(char['x'], char['y'], target_x, target_y)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 深色背景
        painter.fillRect(self.rect(), QColor(30, 32, 40))
        
        # 网格
        pen = QPen(QColor(45, 50, 65))
        pen.setWidth(1)
        painter.setPen(pen)
        grid_size = 40
        for x in range(0, self.width(), grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_size):
            painter.drawLine(0, y, self.width(), y)
        
        # 场景区域
        for area in self.scene.get('areas', []):
            pen = QPen(QColor(120, 140, 180))
            pen.setWidth(2)
            painter.setPen(pen)
            brush = QBrush(QColor(40, 50, 70, 80))
            painter.setBrush(brush)
            painter.drawRect(area['x'], area['y'], area['width'], area['height'])
            painter.setPen(QPen(QColor(150, 160, 190), 1))
            painter.drawText(area['x'] + 10, area['y'] + 20, area['name'])
        
        # 门（绘制为开口，表示通道）
        for door in self.scene.get('doors', []):
            pen = QPen(QColor(160, 170, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(50, 60, 85)))
            painter.drawRect(door['x'], door['y'], door['width'], door['height'])
            # 门的标签
            painter.setPen(QPen(QColor(180, 190, 210), 1))
            painter.drawText(door['x'], door['y'] - 4, door['name'])
        
        # 监听范围
        listener_gradient = QRadialGradient(QPointF(self.listener_pos), self.listener_radius)
        listener_gradient.setColorAt(0.0, QColor(80, 160, 255, 30))
        listener_gradient.setColorAt(1.0, QColor(80, 160, 255, 0))
        painter.setBrush(QBrush(listener_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            self.listener_pos.x() - self.listener_radius,
            self.listener_pos.y() - self.listener_radius,
            self.listener_radius * 2,
            self.listener_radius * 2
        )
        
        # 监听点中心
        painter.setPen(QPen(QColor(100, 180, 255), 2))
        painter.setBrush(QBrush(QColor(100, 180, 255)))
        painter.drawEllipse(self.listener_pos.x() - 4, self.listener_pos.y() - 4, 8, 8)
        painter.setPen(QPen(QColor(100, 180, 255), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.listener_pos.x() - 8, self.listener_pos.y() - 8, 16, 16)
        
        # 绘制角色
        import time
        current_time = int(time.time() * 1000)
        
        for char_id, char in self.characters.items():
            cx, cy = char['x'], char['y']
            base_color = char['color']
            
            # 声波纹（只在监听范围内显示）
            dist_to_listener = ((cx - self.listener_pos.x()) ** 2 + (cy - self.listener_pos.y()) ** 2) ** 0.5
            in_listener_range = dist_to_listener <= self.listener_radius
            
            if in_listener_range and char_id in self.speaking_animations and self.speaking_animations[char_id]['active']:
                anim = self.speaking_animations[char_id]
                # 循环周期 900ms，让波纹持续产生，角色说话期间一直扩散
                elapsed = (current_time - anim['start_time']) % 900
                for i in range(3):
                    wave_delay = i * 300
                    wave_elapsed = elapsed - wave_delay
                    if wave_elapsed > 0:
                        progress = min(wave_elapsed * self.wave_speed / self.wave_max_radius, 1.0)
                        radius = 15 + progress * self.wave_max_radius
                        alpha = int(180 * (1.0 - progress))
                        wave_color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha)
                        pen = QPen(wave_color)
                        pen.setWidth(2)
                        painter.setPen(pen)
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
            
            # 发光效果
            glow_gradient = QRadialGradient(QPointF(cx, cy), 18)
            glow_gradient.setColorAt(0.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 180))
            glow_gradient.setColorAt(0.6, QColor(base_color.red(), base_color.green(), base_color.blue(), 80))
            glow_gradient.setColorAt(1.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - 18), int(cy - 18), 36, 36)
            
            # 核心圆圈
            painter.setPen(QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 200), 2))
            painter.setBrush(QBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), 120)))
            painter.drawEllipse(int(cx - 10), int(cy - 10), 20, 20)
            
            # 内部高亮
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 60)))
            painter.drawEllipse(int(cx - 6), int(cy - 6), 12, 12)
            
            # 标记后显示名称（已分配的名称，不是真实身份）
            if char['marked'] and char.get('assigned_name'):
                painter.setPen(QPen(QColor(220, 220, 240), 1))
                font = painter.font()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(int(cx - 30), int(cy - 22), char['assigned_name'])
                font.setBold(False)
                painter.setFont(font)
            
            # 标记状态（黄色边框）
            if char['marked']:
                painter.setPen(QPen(QColor(255, 220, 80), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - 14), int(cy - 14), 28, 28)
            
            # 选中状态
            if char_id == self.selected_character:
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - 12), int(cy - 12), 24, 24)
            
            # 悬停效果
            if char_id == self.hovered_character:
                painter.setPen(QPen(QColor(200, 220, 255), 1, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - 16), int(cy - 16), 32, 32)
    
    def update_character_position(self, char_id, x, y):
        """设置角色目标位置，并计算路径"""
        if char_id in self.characters:
            self.characters[char_id]['target_x'] = x
            self.characters[char_id]['target_y'] = y
            # 重新计算路径
            path = self.find_path(char_id, x, y)
            self.characters[char_id]['path'] = path
    
    def resolve_collisions(self):
        """全局冲突解决：迭代推开重叠的角色"""
        min_separation = 30  # 两个角色圆心最小距离
        chars = list(self.characters.items())
        for _ in range(4):  # 迭代4次确保收敛
            for i in range(len(chars)):
                for j in range(i + 1, len(chars)):
                    id1, c1 = chars[i]
                    id2, c2 = chars[j]
                    dx = c1['x'] - c2['x']
                    dy = c1['y'] - c2['y']
                    dist = (dx ** 2 + dy ** 2) ** 0.5
                    if dist < min_separation and dist > 0:
                        overlap = (min_separation - dist) / 2.0
                        ratio = overlap / dist
                        c1['x'] += dx * ratio
                        c1['y'] += dy * ratio
                        c2['x'] -= dx * ratio
                        c2['y'] -= dy * ratio
    
    def update_positions(self):
        """平滑移动角色到目标位置，走路径点；平滑移动监听点；全局碰撞避免"""
        updated = False
        
        # === 角色移动 ===
        for char_id, char in self.characters.items():
            if char.get('path') and len(char['path']) > 0:
                next_x, next_y = char['path'][0]
            else:
                next_x, next_y = char['target_x'], char['target_y']
            
            dx = next_x - char['x']
            dy = next_y - char['y']
            distance = (dx ** 2 + dy ** 2) ** 0.5
            
            if distance > 1.0:
                speed = min(5.0, distance * 0.12 + 0.8)
                ratio = speed / distance
                char['x'] += dx * ratio
                char['y'] += dy * ratio
                updated = True
            elif distance > 0.1:
                char['x'] = next_x
                char['y'] = next_y
                updated = True
            else:
                if char.get('path') and len(char['path']) > 0:
                    char['path'].pop(0)
                continue
        
        # === 监听点（主角）平滑移动，走路径点，速度和角色一致 ===
        if self.listener_path:
            next_lx, next_ly = self.listener_path[0]
        else:
            next_lx, next_ly = self.listener_target_x, self.listener_target_y
        
        ldx = next_lx - self.listener_pos.x()
        ldy = next_ly - self.listener_pos.y()
        ldist = (ldx ** 2 + ldy ** 2) ** 0.5
        
        if ldist > 1.0:
            speed = min(5.0, ldist * 0.12 + 0.8)
            speed = max(speed, 1.5)  # 监听点用 QPoint(int)，确保至少移动 1 像素不卡住
            new_lx = self.listener_pos.x() + ldx * (speed / ldist)
            new_ly = self.listener_pos.y() + ldy * (speed / ldist)
            self.listener_pos = QPoint(int(new_lx), int(new_ly))
            updated = True
            if hasattr(self, 'listener_move_callback') and callable(self.listener_move_callback):
                self.listener_move_callback(new_lx, new_ly)
        elif ldist > 0.1:
            self.listener_pos = QPoint(int(next_lx), int(next_ly))
            updated = True
            if hasattr(self, 'listener_move_callback') and callable(self.listener_move_callback):
                self.listener_move_callback(next_lx, next_ly)
        else:
            # 到达当前路径点，切换到下一个
            if self.listener_path:
                self.listener_path.pop(0)
        
        # === 全局碰撞避免 ===
        if self.characters:
            self.resolve_collisions()
            updated = True
        
        if updated:
            self.update()
    
    def get_character_position(self, char_id):
        if char_id in self.characters:
            return (self.characters[char_id]['x'], self.characters[char_id]['y'])
        return None
    
    def get_listener_position(self):
        return (self.listener_pos.x(), self.listener_pos.y())
    
    def mousePressEvent(self, event):
        clicked_char = None
        for char_id, char in self.characters.items():
            distance = ((event.pos().x() - char['x']) ** 2 + (event.pos().y() - char['y']) ** 2) ** 0.5
            if distance <= 18:
                clicked_char = char_id
                break
        
        if clicked_char:
            self.selected_character = clicked_char
            self.toggle_character_mark(clicked_char)
            self.update()
            if hasattr(self, 'mark_callback') and callable(self.mark_callback):
                self.mark_callback(clicked_char, self.characters[clicked_char]['marked'])
        else:
            # 点击空白处：设置监听点目标位置（限制在合法区域内），计算路径后平滑移动过去
            raw_x, raw_y = event.pos().x(), event.pos().y()
            new_x, new_y = self.constrain_to_walkable(raw_x, raw_y)
            self.listener_target_x = new_x
            self.listener_target_y = new_y
            # 主角也要走门，计算路径
            self.listener_path = self.find_path_from(
                self.listener_pos.x(), self.listener_pos.y(), new_x, new_y
            )
            self.update()
    
    def mouseMoveEvent(self, event):
        # 鼠标移动只用于检测悬停角色，不移动监听点
        self.hovered_character = None
        for char_id, char in self.characters.items():
            distance = ((event.pos().x() - char['x']) ** 2 + (event.pos().y() - char['y']) ** 2) ** 0.5
            if distance <= 18:
                self.hovered_character = char_id
                # 未标记时不暴露真实身份！
                if char['marked'] and char.get('assigned_name'):
                    tooltip = f"? [{char['assigned_name']}]"
                else:
                    tooltip = "?"
                if char['info']:
                    tooltip += f"\n{char['info']}"
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                self.update()
                return
        
        QToolTip.hideText()
        self.update()
    
    def toggle_character_mark(self, char_id):
        if char_id in self.characters:
            self.characters[char_id]['marked'] = not self.characters[char_id]['marked']
            if not self.characters[char_id]['marked']:
                self.characters[char_id]['assigned_name'] = ''
            self.update()
    
    def set_character_mark(self, char_id, marked, assigned_name=''):
        if char_id in self.characters:
            self.characters[char_id]['marked'] = marked
            self.characters[char_id]['assigned_name'] = assigned_name
            self.update()
    
    def set_character_info(self, char_id, info):
        if char_id in self.characters:
            self.characters[char_id]['info'] = info
    
    def get_marked_characters(self):
        return {
            char_id: char.get('assigned_name', '')
            for char_id, char in self.characters.items()
            if char['marked']
        }
    
    def clear_all_marks(self):
        for char_id in self.characters:
            self.characters[char_id]['marked'] = False
            self.characters[char_id]['assigned_name'] = ''
        self.selected_character = None
        self.update()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口变化时，将监听点限制到最近的合法位置
        new_x, new_y = self.constrain_to_walkable(self.listener_pos.x(), self.listener_pos.y())
        self.listener_pos = QPoint(int(new_x), int(new_y))
        self.listener_target_x = new_x
        self.listener_target_y = new_y
        self.listener_path = []
