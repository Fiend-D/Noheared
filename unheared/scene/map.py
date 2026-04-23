#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QRadialGradient

class SceneMap(QWidget):
    # 移动速度常量
    WALK_SPEED = 2.5
    RUN_SPEED = 5.0
    STAIR_SPEED_FACTOR = 0.5
    
    # 碰撞避免参数
    MIN_SEPARATION = 30
    MIN_SEPARATION_STAIRS = 18
    
    # 楼层区域（用于视觉区分和楼梯传送）
    UPPER_FLOOR_AREAS = {'露天甲板', '餐厅', '赌场', '音乐厅', '厨房', '医务室'}
    LOWER_FLOOR_AREAS = {'船长室', '豪华套房', '普通客房', '船员休息室'}
    FLOOR_DIVIDER_Y = 460  # 上下层分界线
    
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
        
        # 装饰物列表 [{type, x, y, w, h, color}, ...]
        self.decorations = []
        
        # 构建区域邻接图
        self.area_graph = {}
        for area in self.scene['areas']:
            self.area_graph[area['name']] = []
        for door in self.scene.get('doors', []):
            self.area_graph[door['area1']].append((door, door['area2']))
            self.area_graph[door['area2']].append((door, door['area1']))
        
        # 角色数据
        self.characters = {}
        
        # 监听点位置（主角）
        self.listener_pos = QPoint(self.width() // 2, self.height() // 2)
        self.listener_target_x = float(self.listener_pos.x())
        self.listener_target_y = float(self.listener_pos.y())
        self.listener_path = []
        self.listener_radius = 120  # 增大监听范围
        
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
    
    def _is_stair_area(self, area_name):
        """判断区域是否为楼梯"""
        return '楼梯' in area_name
    
    def _get_area_floor(self, area_name):
        """判断区域属于上层还是下层"""
        if area_name in self.UPPER_FLOOR_AREAS:
            return 'upper'
        elif area_name in self.LOWER_FLOOR_AREAS:
            return 'lower'
        return None
    
    def _is_stair_door(self, door):
        """判断门是否为楼梯门"""
        return '楼梯' in door['name']
    
    def _generate_decorations(self):
        """为场景区域生成装饰物（家具）"""
        self.decorations = []
        furniture_types = ['bed', 'sofa', 'sofa_l', 'round_table', 'table_rect',
                           'bookshelf', 'cabinet', 'rug', 'plant', 'desk', 'bathtub', 'tv_stand']
        # 冷蓝灰色调
        furniture_colors = [
            QColor(55, 65, 85), QColor(60, 70, 90), QColor(50, 60, 80),
            QColor(65, 75, 95), QColor(45, 55, 75), QColor(70, 80, 100)
        ]
        rug_colors = [
            QColor(80, 50, 50, 80), QColor(50, 70, 50, 80), QColor(50, 50, 80, 80),
            QColor(70, 60, 50, 80), QColor(60, 60, 60, 80)
        ]
        
        for area in self.scene.get('areas', []):
            # 楼梯区域不放家具
            if self._is_stair_area(area['name']):
                continue
            
            area_w = area['width']
            area_h = area['height']
            area_x = area['x']
            area_y = area['y']
            
            # 区域太小不放家具
            if area_w < 60 or area_h < 60:
                continue
            
            # 根据区域大小决定家具数量
            num_furniture = min(3, max(1, (area_w * area_h) // 15000))
            
            placed = []
            for _ in range(num_furniture):
                ftype = random.choice(furniture_types)
                
                # 家具尺寸
                if ftype == 'bed':
                    fw, fh = random.choice([(50, 70), (70, 50)])
                elif ftype in ('sofa', 'sofa_l'):
                    fw, fh = random.choice([(50, 30), (30, 50), (60, 30), (30, 60)])
                elif ftype == 'round_table':
                    fw = fh = random.choice([20, 25, 30])
                elif ftype == 'table_rect':
                    fw, fh = random.choice([(35, 25), (40, 30), (50, 30)])
                elif ftype == 'bookshelf':
                    fw, fh = random.choice([(40, 15), (15, 40)])
                elif ftype == 'cabinet':
                    fw, fh = random.choice([(35, 20), (40, 25)])
                elif ftype == 'rug':
                    fw, fh = random.choice([(50, 40), (60, 50), (40, 30)])
                elif ftype == 'plant':
                    fw = fh = random.choice([12, 15, 18])
                elif ftype == 'desk':
                    fw, fh = random.choice([(45, 25), (50, 30), (35, 25)])
                elif ftype == 'bathtub':
                    fw, fh = random.choice([(50, 25), (55, 30)])
                elif ftype == 'tv_stand':
                    fw, fh = random.choice([(40, 15), (45, 18)])
                else:
                    fw, fh = 30, 30
                
                # 尝试放置（简单碰撞避免）
                margin = 8
                max_attempts = 15
                for attempt in range(max_attempts):
                    fx = area_x + margin + random.randint(0, max(0, area_w - fw - margin * 2))
                    fy = area_y + margin + random.randint(0, max(0, area_h - fh - margin * 2))
                    
                    # 检查是否与其他家具重叠
                    overlap = False
                    for px, py, pw, ph in placed:
                        if not (fx + fw + 5 < px or fx > px + pw + 5 or fy + fh + 5 < py or fy > py + fh + 5):
                            overlap = True
                            break
                    
                    if not overlap:
                        placed.append((fx, fy, fw, fh))
                        color = random.choice(rug_colors) if ftype == 'rug' else random.choice(furniture_colors)
                        self.decorations.append({
                            'type': ftype,
                            'x': fx, 'y': fy,
                            'w': fw, 'h': fh,
                            'color': color
                        })
                        break
    
    def load_scene(self, scene_data):
        """从案例数据加载场景"""
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
        # 生成装饰物
        self._generate_decorations()
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
                'x': 0, 'y': 0,
                'target_x': 0, 'target_y': 0,
                'color': color,
                'marked': False,
                'assigned_name': '',
                'info': '',
                'path': [],
                'movement': 'walk',
                'is_moving': False,
                'move_direction': (0, 0)
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
        # 先检查门
        for door in self.scene.get('doors', []):
            if (door['x'] <= x <= door['x'] + door['width'] and
                door['y'] <= y <= door['y'] + door['height']):
                return door['area1']
        # 检查普通区域
        for area in self.scene['areas']:
            if (area['x'] <= x <= area['x'] + area['width'] and
                area['y'] <= y <= area['y'] + area['height']):
                return area['name']
        return None
    
    def can_hear_each_other(self, x1, y1, x2, y2):
        """判断两个位置是否能互相听到声音（必须在同一区域内）"""
        area1 = self.get_character_area(x1, y1)
        area2 = self.get_character_area(x2, y2)
        if area1 is None or area2 is None:
            return False
        return area1 == area2
    
    def constrain_to_walkable(self, x, y):
        """将坐标限制到最近的合法可行走区域内"""
        if self.get_character_area(x, y) is not None:
            return (x, y)
        
        best_x, best_y = x, y
        best_dist = float('inf')
        
        for area in self.scene.get('areas', []):
            cx = max(area['x'], min(x, area['x'] + area['width']))
            cy = max(area['y'], min(y, area['y'] + area['height']))
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_x, best_y = cx, cy
        
        best_x = max(0, min(best_x, self.width()))
        best_y = max(0, min(best_y, self.height()))
        return (best_x, best_y)
    
    def find_path_from(self, from_x, from_y, target_x, target_y):
        """寻找从指定位置到目标位置的路径（必须经门穿越）"""
        cur_area = self.get_character_area(from_x, from_y)
        tgt_area = self.get_character_area(target_x, target_y)
        
        if cur_area == tgt_area or cur_area is None or tgt_area is None:
            return [(target_x, target_y)]
        
        from collections import deque
        queue = deque([(cur_area, [])])
        visited = {cur_area}
        
        while queue:
            area, path = queue.popleft()
            if area == tgt_area:
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
        
        return [(target_x, target_y)]
    
    def find_path(self, char_id, target_x, target_y):
        """寻找角色从当前位置到目标位置的路径"""
        char = self.characters[char_id]
        return self.find_path_from(char['x'], char['y'], target_x, target_y)
    
    def _get_movement_speed(self, char_id):
        """获取角色的当前移动速度，考虑走路/跑动和楼梯"""
        char = self.characters[char_id]
        movement = char.get('movement', 'walk')
        base_speed = self.RUN_SPEED if movement == 'run' else self.WALK_SPEED
        
        # 检查是否在楼梯区域
        area = self.get_character_area(char['x'], char['y'])
        if area and self._is_stair_area(area):
            base_speed *= self.STAIR_SPEED_FACTOR
        
        return base_speed
    
    def _draw_decoration(self, painter, deco):
        """绘制单个装饰物"""
        x, y, w, h = deco['x'], deco['y'], deco['w'], deco['h']
        ftype = deco['type']
        color = deco['color']
        
        pen = QPen(color.darker(120))
        pen.setWidth(1)
        painter.setPen(pen)
        
        if ftype == 'bed':
            painter.setBrush(QBrush(color))
            painter.drawRect(x, y, w, h)
            # 头板
            if w > h:
                painter.setBrush(QBrush(color.darker(130)))
                painter.drawRect(x, y, 8, h)
            else:
                painter.setBrush(QBrush(color.darker(130)))
                painter.drawRect(x, y, w, 8)
        
        elif ftype in ('sofa', 'sofa_l'):
            painter.setBrush(QBrush(color))
            painter.drawRect(x, y, w, h)
            # 靠背
            painter.setBrush(QBrush(color.lighter(110)))
            if w > h:
                painter.drawRect(x, y, w, 8)
            else:
                painter.drawRect(x, y, 8, h)
        
        elif ftype == 'round_table':
            painter.setBrush(QBrush(color))
            painter.drawEllipse(x, y, w, h)
        
        elif ftype == 'table_rect':
            painter.setBrush(QBrush(color))
            painter.drawRect(x, y, w, h)
            # 桌面高光线
            painter.setPen(QPen(color.lighter(130), 1))
            painter.drawLine(x + 2, y + 3, x + w - 2, y + 3)
        
        elif ftype == 'bookshelf':
            painter.setBrush(QBrush(color))
            painter.drawRect(x, y, w, h)
            # 书架横线
            painter.setPen(QPen(color.darker(140), 1))
            for i in range(1, 4):
                by = y + int(h * i / 4)
                painter.drawLine(x + 2, by, x + w - 2, by)
        
        elif ftype == 'cabinet':
            painter.setBrush(QBrush(color))
            painter.drawRect(x, y, w, h)
            # 抽屉线
            painter.setPen(QPen(color.darker(130), 1))
            painter.drawLine(x + 2, y + h // 2, x + w - 2, y + h // 2)
            # 把手
            painter.setBrush(QBrush(color.lighter(150)))
            painter.drawEllipse(x + w // 2 - 2, y + h // 4 - 2, 4, 4)
            painter.drawEllipse(x + w // 2 - 2, y + 3 * h // 4 - 2, 4, 4)
        
        elif ftype == 'rug':
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(x, y, w, h)
        
        elif ftype == 'plant':
            # 花盆
            pot_color = QColor(100, 70, 50)
            painter.setBrush(QBrush(pot_color))
            painter.setPen(QPen(pot_color.darker(120), 1))
            painter.drawRect(x + w // 4, y + h // 2, w // 2, h // 2)
            # 叶子
            leaf_color = QColor(60, 100, 60)
            painter.setBrush(QBrush(leaf_color))
            painter.setPen(QPen(leaf_color.darker(120), 1))
            painter.drawEllipse(x + 2, y + 2, w - 4, h // 2 + 2)
        
        elif ftype == 'desk':
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(x, y, w, h)
            # 桌面
            painter.setPen(QPen(color.lighter(130), 1))
            painter.drawLine(x + 2, y + 3, x + w - 2, y + 3)
        
        elif ftype == 'bathtub':
            painter.setBrush(QBrush(color.lighter(110)))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRoundedRect(x, y, w, h, 6, 6)
        
        elif ftype == 'tv_stand':
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(x, y, w, h)
            # 电视
            tv_color = QColor(30, 30, 35)
            painter.setBrush(QBrush(tv_color))
            painter.drawRect(x + 4, y - h // 3, w - 8, h // 2)
    
    def _draw_door(self, painter, door):
        """绘制门：普通门画成开口，楼梯门画成楼梯图标+方向箭头"""
        x, y, w, h = door['x'], door['y'], door['width'], door['height']
        
        if self._is_stair_door(door):
            # === 楼梯门 ===
            # 画楼梯背景框
            painter.setPen(QPen(QColor(180, 160, 120), 2))
            painter.setBrush(QBrush(QColor(55, 50, 40, 120)))
            painter.drawRect(x, y, w, h)
            
            # 画台阶（横线）
            painter.setPen(QPen(QColor(170, 150, 110), 1))
            steps = 4
            for i in range(1, steps):
                sy = y + i * h / steps
                painter.drawLine(int(x), int(sy), int(x + w), int(sy))
            
            # 画竖线分隔（表示台阶竖面）
            step_w = w / 3
            for i in range(1, 3):
                sx = x + i * step_w
                painter.drawLine(int(sx), int(y), int(sx), int(y + h))
            
            # 方向箭头（判断 area1 是否在上层）
            area1_floor = self._get_area_floor(door['area1'])
            area2_floor = self._get_area_floor(door['area2'])
            if area1_floor == 'upper' and area2_floor == 'lower':
                arrow = '↓'
            elif area1_floor == 'lower' and area2_floor == 'upper':
                arrow = '↑'
            else:
                # 上层内部楼梯（甲板↔生活）
                arrow = '↓' if area1_floor == 'upper' else '↑'
            
            painter.setPen(QPen(QColor(220, 200, 160), 1))
            font = painter.font()
            old_size = font.pointSize()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            # 在门上方或下方标注箭头
            label_y = y - 14 if y > 30 else y + h + 14
            painter.drawText(int(x), int(label_y) - 10, int(w), 14,
                            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                            arrow)
            font.setPointSize(old_size)
            font.setBold(False)
            painter.setFont(font)
            
            # 标注去向
            painter.setPen(QPen(QColor(180, 170, 150), 1))
            painter.drawText(int(x), int(label_y) + 2, int(w), 12,
                            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                            door['name'])
        else:
            # === 普通门：画成开口样式 ===
            painter.setPen(QPen(QColor(140, 160, 200), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            if w > h:
                # 水平开口：上下两条线 + 左右短竖线
                painter.drawLine(int(x), int(y), int(x + w), int(y))
                painter.drawLine(int(x), int(y + h), int(x + w), int(y + h))
                mid_h = h / 2
                painter.drawLine(int(x), int(y), int(x), int(y + h))
                painter.drawLine(int(x + w), int(y), int(x + w), int(y + h))
            else:
                # 垂直开口：左右两条线 + 上下短横线
                painter.drawLine(int(x), int(y), int(x), int(y + h))
                painter.drawLine(int(x + w), int(y), int(x + w), int(y + h))
                painter.drawLine(int(x), int(y), int(x + w), int(y))
                painter.drawLine(int(x), int(y + h), int(x + w), int(y + h))
            
            # 门名称标签
            painter.setPen(QPen(QColor(160, 170, 190), 1))
            painter.drawText(int(x), int(y) - 4, door['name'])
    
    def _draw_floor_divider(self, painter):
        """绘制楼层分隔线"""
        if not self.scene.get('areas'):
            return
        # 检查场景是否包含 case5 的上下层区域
        has_upper = any(a['name'] in self.UPPER_FLOOR_AREAS for a in self.scene['areas'])
        has_lower = any(a['name'] in self.LOWER_FLOOR_AREAS for a in self.scene['areas'])
        if not (has_upper and has_lower):
            return
        
        divider_y = self.FLOOR_DIVIDER_Y
        w = self.width()
        
        # 画分隔带背景
        painter.fillRect(0, divider_y - 2, w, 4, QColor(40, 45, 60, 200))
        
        # 画虚线
        pen = QPen(QColor(100, 115, 150), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(0, divider_y, w, divider_y)
        
        # 标注
        painter.setPen(QPen(QColor(130, 145, 180), 1))
        font = painter.font()
        old_size = font.pointSize()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(15, divider_y - 8, "上层甲板")
        painter.drawText(15, divider_y + 18, "下层舱室")
        font.setPointSize(old_size)
        font.setBold(False)
        painter.setFont(font)
    
    def _teleport_character(self, char_id, door):
        """将角色通过楼梯门传送到目标区域"""
        char = self.characters[char_id]
        
        # 确定当前在哪个区域（通过坐标判断）
        current_area_name = None
        for area in self.scene.get('areas', []):
            if (area['x'] <= char['x'] <= area['x'] + area['width'] and
                area['y'] <= char['y'] <= area['y'] + area['height']):
                current_area_name = area['name']
                break
        
        # 确定目标区域
        if current_area_name == door['area1']:
            target_area_name = door['area2']
        elif current_area_name == door['area2']:
            target_area_name = door['area1']
        else:
            # 角色在门区域内，默认传送到 area2
            target_area_name = door['area2']
        
        # 找到目标区域
        target_area = None
        for area in self.scene.get('areas', []):
            if area['name'] == target_area_name:
                target_area = area
                break
        if not target_area:
            return
        
        # 计算目标位置：目标区域中心，偏向远离门的方向偏移 40px
        target_cx = target_area['x'] + target_area['width'] / 2
        target_cy = target_area['y'] + target_area['height'] / 2
        door_cx = door['x'] + door['width'] / 2
        door_cy = door['y'] + door['height'] / 2
        
        dx = target_cx - door_cx
        dy = target_cy - door_cy
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist > 0:
            offset_x = dx / dist * 40
            offset_y = dy / dist * 40
        else:
            offset_x = 0
            offset_y = 0
        
        char['x'] = door_cx + offset_x
        char['y'] = door_cy + offset_y
        
        # 确保在目标区域内
        char['x'] = max(target_area['x'] + 8, min(char['x'], target_area['x'] + target_area['width'] - 8))
        char['y'] = max(target_area['y'] + 8, min(char['y'], target_area['y'] + target_area['height'] - 8))
        
        # 如果 path 下一个节点是当前门的中心，移除它
        if char.get('path') and len(char['path']) > 0:
            next_x, next_y = char['path'][0]
            if abs(next_x - door_cx) < 10 and abs(next_y - door_cy) < 10:
                char['path'].pop(0)
    
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
        
        # 场景区域（上层/下层用不同色调区分）
        for area in self.scene.get('areas', []):
            floor = self._get_area_floor(area['name'])
            if floor == 'upper':
                pen_color = QColor(120, 150, 190)
                fill_color = QColor(42, 55, 78, 80)
            elif floor == 'lower':
                pen_color = QColor(120, 170, 150)
                fill_color = QColor(42, 65, 58, 80)
            else:
                pen_color = QColor(120, 140, 180)
                fill_color = QColor(40, 50, 70, 80)
            
            pen = QPen(pen_color)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QBrush(fill_color))
            painter.drawRect(area['x'], area['y'], area['width'], area['height'])
            painter.setPen(QPen(QColor(150, 160, 190), 1))
            painter.drawText(area['x'] + 10, area['y'] + 20, area['name'])
        
        # 楼层分隔线
        self._draw_floor_divider(painter)
        
        # 门（优化外观）
        for door in self.scene.get('doors', []):
            self._draw_door(painter, door)
        
        # 装饰物（家具）
        for deco in self.decorations:
            self._draw_decoration(painter, deco)
        
        # 监听范围（柔和光晕）
        listener_gradient = QRadialGradient(QPointF(self.listener_pos), self.listener_radius)
        listener_gradient.setColorAt(0.0, QColor(80, 160, 255, 30))
        listener_gradient.setColorAt(1.0, QColor(80, 160, 255, 0))
        painter.setBrush(QBrush(listener_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            self.listener_pos.x() - self.listener_radius,
            self.listener_pos.y() - self.listener_radius,
            self.listener_radius * 2, self.listener_radius * 2
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
            
            dist_to_listener = ((cx - self.listener_pos.x()) ** 2 + (cy - self.listener_pos.y()) ** 2) ** 0.5
            in_listener_range = dist_to_listener <= self.listener_radius
            
            if in_listener_range and char_id in self.speaking_animations and self.speaking_animations[char_id]['active']:
                anim = self.speaking_animations[char_id]
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
            
            # 移动方向指示器（小箭头）
            if char.get('is_moving'):
                dx, dy = char.get('move_direction', (0, 0))
                if abs(dx) > 0.01 or abs(dy) > 0.01:
                    dir_len = (dx**2 + dy**2)**0.5
                    if dir_len > 0:
                        ndx, ndy = dx / dir_len, dy / dir_len
                        arrow_len = 14
                        ax = cx + ndx * arrow_len
                        ay = cy + ndy * arrow_len
                        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
                        painter.drawLine(int(cx), int(cy), int(ax), int(ay))
            
            # 标记后显示名称
            if char['marked'] and char.get('assigned_name'):
                painter.setPen(QPen(QColor(220, 220, 240), 1))
                font = painter.font()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(int(cx - 30), int(cy - 22), char['assigned_name'])
                font.setBold(False)
                painter.setFont(font)
            
            # 标记状态
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
        
        # === 迷雾/光照效果 ===
        # 在监听点周围创建光照，其他地方变暗
        fog_gradient = QRadialGradient(QPointF(self.listener_pos), self.listener_radius * 1.8)
        fog_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        fog_gradient.setColorAt(0.4, QColor(0, 0, 0, 40))
        fog_gradient.setColorAt(0.7, QColor(0, 0, 0, 120))
        fog_gradient.setColorAt(1.0, QColor(0, 0, 0, 200))
        painter.setBrush(QBrush(fog_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
    
    def update_character_position(self, char_id, x, y, movement='walk'):
        """设置角色目标位置，并计算路径"""
        if char_id in self.characters:
            self.characters[char_id]['target_x'] = x
            self.characters[char_id]['target_y'] = y
            self.characters[char_id]['movement'] = movement
            path = self.find_path(char_id, x, y)
            self.characters[char_id]['path'] = path
    
    def resolve_collisions(self):
        """全局冲突解决：迭代推开重叠的角色"""
        chars = list(self.characters.items())
        for _ in range(4):
            for i in range(len(chars)):
                for j in range(i + 1, len(chars)):
                    id1, c1 = chars[i]
                    id2, c2 = chars[j]
                    dx = c1['x'] - c2['x']
                    dy = c1['y'] - c2['y']
                    dist = (dx ** 2 + dy ** 2) ** 0.5
                    
                    # 根据是否在楼梯区域使用不同的最小间距
                    area1 = self.get_character_area(c1['x'], c1['y'])
                    area2 = self.get_character_area(c2['x'], c2['y'])
                    in_stairs = (area1 and self._is_stair_area(area1)) or (area2 and self._is_stair_area(area2))
                    min_sep = self.MIN_SEPARATION_STAIRS if in_stairs else self.MIN_SEPARATION
                    
                    if dist < min_sep and dist > 0:
                        overlap = (min_sep - dist) / 2.0
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
                speed = self._get_movement_speed(char_id)
                # 距离目标很近时减速
                speed = min(speed, distance)
                ratio = speed / distance
                char['x'] += dx * ratio
                char['y'] += dy * ratio
                char['is_moving'] = True
                char['move_direction'] = (dx / distance, dy / distance)
                updated = True
            elif distance > 0.1:
                char['x'] = next_x
                char['y'] = next_y
                char['is_moving'] = True
                char['move_direction'] = (0, 0)
                updated = True
            else:
                if char.get('path') and len(char['path']) > 0:
                    char['path'].pop(0)
                char['is_moving'] = False
                char['move_direction'] = (0, 0)
            
            # === 楼梯传送检测 ===
            # 当角色靠近楼梯门中心时，直接传送到目标区域
            import time as pytime
            now = pytime.time()
            if char.get('teleport_cooldown', 0) < now:
                for door in self.scene.get('doors', []):
                    if not self._is_stair_door(door):
                        continue
                    door_cx = door['x'] + door['width'] / 2
                    door_cy = door['y'] + door['height'] / 2
                    dist_to_door = ((char['x'] - door_cx) ** 2 + (char['y'] - door_cy) ** 2) ** 0.5
                    if dist_to_door < 18:  # 靠近门中心 18px 内触发传送
                        self._teleport_character(char_id, door)
                        char['teleport_cooldown'] = now + 0.6  # 0.6秒冷却，防止死循环
                        updated = True
                        break
        
        # === 监听点（主角）平滑移动 ===
        if self.listener_path:
            next_lx, next_ly = self.listener_path[0]
        else:
            next_lx, next_ly = self.listener_target_x, self.listener_target_y
        
        ldx = next_lx - self.listener_pos.x()
        ldy = next_ly - self.listener_pos.y()
        ldist = (ldx ** 2 + ldy ** 2) ** 0.5
        
        if ldist > 1.0:
            speed = min(5.0, ldist * 0.12 + 0.8)
            speed = max(speed, 1.5)
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
            if self.listener_path:
                self.listener_path.pop(0)
        
        # === 全局碰撞避免 ===
        if self.characters:
            self.resolve_collisions()
            updated = True
        
        if updated:
            self.update()
    
    def get_footstep_state(self):
        """返回监听点周围需要播放脚步声的状态
        返回: {'walk': volume, 'run': volume}
        """
        state = {'walk': 0.0, 'run': 0.0}
        listener_x, listener_y = self.get_listener_position()
        
        for char_id, char in self.characters.items():
            if char.get('is_moving'):
                dx = char['x'] - listener_x
                dy = char['y'] - listener_y
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist < self.listener_radius:
                    vol = max(0.0, 1.0 - dist / self.listener_radius)
                    movement = char.get('movement', 'walk')
                    state[movement] = max(state[movement], vol)
        
        return state
    
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
            raw_x, raw_y = event.pos().x(), event.pos().y()
            new_x, new_y = self.constrain_to_walkable(raw_x, raw_y)
            self.listener_target_x = new_x
            self.listener_target_y = new_y
            self.listener_path = self.find_path_from(
                self.listener_pos.x(), self.listener_pos.y(), new_x, new_y
            )
            self.update()
    
    def mouseMoveEvent(self, event):
        self.hovered_character = None
        for char_id, char in self.characters.items():
            distance = ((event.pos().x() - char['x']) ** 2 + (event.pos().y() - char['y']) ** 2) ** 0.5
            if distance <= 18:
                self.hovered_character = char_id
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
        new_x, new_y = self.constrain_to_walkable(self.listener_pos.x(), self.listener_pos.y())
        self.listener_pos = QPoint(int(new_x), int(new_y))
        self.listener_target_x = new_x
        self.listener_target_y = new_y
        self.listener_path = []
