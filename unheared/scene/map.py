#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QRadialGradient, QPainterPath

class SceneMap(QWidget):
    # 移动速度常量
    WALK_SPEED = 2.5
    RUN_SPEED = 5.0
    STAIR_SPEED_FACTOR = 0.5
    
    # 碰撞避免参数
    MIN_SEPARATION = 30
    MIN_SEPARATION_STAIRS = 18
    DOOR_SEPARATION = 8  # 门口区域使用更小的间距避免堵门
    
    # 楼层区域（用于视觉区分和楼梯传送）
    UPPER_FLOOR_AREAS = {'露天甲板', '餐厅', '赌场', '音乐厅', '厨房', '医务室',
                         '书房', '会客厅', '画室', '宴会厅', '酒窖', '大厅'}
    LOWER_FLOOR_AREAS = {'船长室', '豪华套房', '普通客房', '船员休息室',
                         '主人卧室', '客房A', '客房B', '客房C', '老板套房', '露台'}
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
        
        # 门口速度加速计数器
        self._door_speed_boost = {}
    
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
    
    def load_scene(self, scene_data, case_id=None):
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
        # 加载背景图
        self._load_background_image(case_id)
        self.update()
    
    def load_characters(self, characters_data):
        """从案例数据加载角色"""
        self.characters = {}
        self.speaking_animations = {}
        self.selected_character = None
        self.hovered_character = None
        self._character_labels = {}
        for i, (char_id, data) in enumerate(characters_data.items()):
            self._character_labels[char_id] = chr(ord('A') + i)
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
                # 门内区域归属不能固定为 area1，否则会导致跨门时路径反复重算卡住
                area1 = next((a for a in self.scene.get('areas', []) if a['name'] == door['area1']), None)
                area2 = next((a for a in self.scene.get('areas', []) if a['name'] == door['area2']), None)
                if area1 and area2:
                    c1x = area1['x'] + area1['width'] / 2
                    c1y = area1['y'] + area1['height'] / 2
                    c2x = area2['x'] + area2['width'] / 2
                    c2y = area2['y'] + area2['height'] / 2
                    d1 = ((x - c1x) ** 2 + (y - c1y) ** 2) ** 0.5
                    d2 = ((x - c2x) ** 2 + (y - c2y) ** 2) ** 0.5
                    return door['area1'] if d1 <= d2 else door['area2']
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

    def _constrain_to_area(self, x, y, area_name, margin=4):
        """将坐标限制在指定区域内，避免碰撞推挤导致穿墙"""
        area = next((a for a in self.scene.get('areas', []) if a['name'] == area_name), None)
        if not area:
            return self.constrain_to_walkable(x, y)
        cx = max(area['x'] + margin, min(x, area['x'] + area['width'] - margin))
        cy = max(area['y'] + margin, min(y, area['y'] + area['height'] - margin))
        return (cx, cy)
    
    def _is_near_door(self, x, y, margin=15):
        """检查坐标是否在某个门附近"""
        for door in self.scene.get('doors', []):
            door_cx = door['x'] + door['width'] / 2
            door_cy = door['y'] + door['height'] / 2
            if (abs(x - door_cx) < door['width'] / 2 + margin and
                abs(y - door_cy) < door['height'] / 2 + margin):
                return True
        return False
    
    def _areas_connected_by_door(self, area1, area2):
        """检查两个区域是否有门直接连接"""
        if area1 == area2:
            return True
        for door in self.scene.get('doors', []):
            if (door['area1'] == area1 and door['area2'] == area2) or \
               (door['area1'] == area2 and door['area2'] == area1):
                return True
        return False
    
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
                prev_area = cur_area
                for door, next_area in path:
                    entry_x, entry_y, exit_x, exit_y = self._get_door_transit_points(door, prev_area, next_area)
                    full_path.append((entry_x, entry_y))
                    full_path.append((exit_x, exit_y))
                    prev_area = next_area
                full_path.append((target_x, target_y))
                return full_path
            
            for door, neighbor in self.area_graph.get(area, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [(door, neighbor)]))
        
        return [(target_x, target_y)]
    
    def _get_door_transit_points(self, door, from_area_name, to_area_name):
        """根据两侧区域相对位置，生成穿门时的入口点和出口点"""
        door_cx = door['x'] + door['width'] / 2
        door_cy = door['y'] + door['height'] / 2
        from_area = next((a for a in self.scene.get('areas', []) if a['name'] == from_area_name), None)
        to_area = next((a for a in self.scene.get('areas', []) if a['name'] == to_area_name), None)

        if not from_area or not to_area:
            return (door_cx, door_cy, door_cx, door_cy)

        from_cx = from_area['x'] + from_area['width'] / 2
        from_cy = from_area['y'] + from_area['height'] / 2
        to_cx = to_area['x'] + to_area['width'] / 2
        to_cy = to_area['y'] + to_area['height'] / 2

        margin = 10
        pass_span = 14

        # 用y范围重叠判断：若两区域y不重叠（或微小重叠 <=20px），则为上下堆叠 → 垂直穿越
        fb = from_area['y'] + from_area['height']
        tb = to_area['y'] + to_area['height']
        y_overlap = min(fb, tb) - max(from_area['y'], to_area['y'])
        stacked = y_overlap <= 20

        if stacked:
            # 上下相邻 → 垂直穿越：从门上下侧出入
            edge_y = door['y'] if from_cy < door_cy else door['y'] + door['height']
            toward_y = door['y'] if to_cy < door_cy else door['y'] + door['height']
            entry_x = max(door['x'] + margin, min(from_cx, door['x'] + door['width'] - margin))
            exit_x = max(door['x'] + margin, min(to_cx, door['x'] + door['width'] - margin))
            entry_y = edge_y - pass_span if from_cy < door_cy else edge_y + pass_span
            exit_y = toward_y - pass_span if to_cy < door_cy else toward_y + pass_span
        else:
            # 左右相邻 → 水平穿越：从门左右侧出入
            edge_x = door['x'] if from_cx < door_cx else door['x'] + door['width']
            toward_x = door['x'] if to_cx < door_cx else door['x'] + door['width']
            entry_y = max(door['y'] + margin, min(from_cy, door['y'] + door['height'] - margin))
            exit_y = max(door['y'] + margin, min(to_cy, door['y'] + door['height'] - margin))
            entry_x = edge_x - pass_span if from_cx < door_cx else edge_x + pass_span
            exit_x = toward_x - pass_span if to_cx < door_cx else toward_x + pass_span
        return (entry_x, entry_y, exit_x, exit_y)
    
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
    
    def _draw_wall_gap(self, painter, door, bg_color=QColor(20, 28, 46)):
        """绘制门洞：缺口 + 垂直墙壁的两条线段"""
        x, y, w, h = door['x'], door['y'], door['width'], door['height']
        cx, cy = x + w / 2.0, y + h / 2.0
        arm = 8

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        opening_path = QPainterPath()
        opening_path.addRoundedRect(float(x - 2), float(y - 2), float(w + 4), float(h + 4), 3.0, 3.0)
        painter.drawPath(opening_path)

        painter.setPen(QPen(QColor(128, 158, 198, 210), 2))
        if w >= h:
            painter.drawLine(int(x), int(cy), int(x + arm), int(cy))
            painter.drawLine(int(x + w), int(cy), int(x + w - arm), int(cy))
        else:
            painter.drawLine(int(cx), int(y), int(cx), int(y + arm))
            painter.drawLine(int(cx), int(y + h), int(cx), int(y + h - arm))
    
    def _draw_stair_marker(self, painter, door):
        """绘制楼梯门：精致阶梯底板 + 内嵌标识（无外置标签）"""
        x, y, w, h = door['x'], door['y'], door['width'], door['height']
        cx, cy = x + w / 2, y + h / 2
        
        # 先画墙壁缺口
        self._draw_wall_gap(painter, door)
        
        # 方向判断 & 目标区域：以靠近楼梯的区域为入口，对侧为目的地
        a1d = next((a for a in self.scene['areas'] if a['name'] == door['area1']), None)
        a2d = next((a for a in self.scene['areas'] if a['name'] == door['area2']), None)
        a1_cx = a1d['x'] + a1d['width'] / 2; a1_cy = a1d['y'] + a1d['height'] / 2
        a2_cx = a2d['x'] + a2d['width'] / 2; a2_cy = a2d['y'] + a2d['height'] / 2
        d1 = (cx - a1_cx)**2 + (cy - a1_cy)**2
        d2 = (cx - a2_cx)**2 + (cy - a2_cy)**2
        if d2 < d1:
            target_name = door['area1']; closer_cy = a2_cy; target_cy = a1_cy
        else:
            target_name = door['area2']; closer_cy = a1_cy; target_cy = a2_cy
        arrow = '↑' if target_cy < closer_cy else '↓'
        
        # 阶梯底板渐变（更精致）
        if w >= h:
            plate_grad = QRadialGradient(QPointF(cx, cy), max(w, h))
        else:
            plate_grad = QRadialGradient(QPointF(cx, cy), max(w, h))
        plate_grad.setColorAt(0.0, QColor(80, 108, 146, 210))
        plate_grad.setColorAt(1.0, QColor(42, 58, 84, 210))
        painter.setPen(QPen(QColor(160, 195, 235, 180), 1))
        painter.setBrush(QBrush(plate_grad))
        painter.drawRoundedRect(int(x), int(y), int(w), int(h), 4, 4)

        # 阶梯台阶（真实楼梯感）
        painter.setBrush(Qt.BrushStyle.NoBrush)
        step_main = QColor(208, 228, 252, 140)
        step_shadow = QColor(20, 30, 46, 120)
        if w >= h:
            step_count = 5
            usable_w = max(10, w - 10)
            each = usable_w / step_count
            for i in range(step_count):
                sx = x + 5 + i * each
                painter.setPen(QPen(step_shadow, 1))
                painter.drawLine(int(sx), int(y + 4), int(sx), int(y + h - 4))
                painter.setPen(QPen(step_main, 1))
                painter.drawLine(int(sx + 1), int(y + 4), int(sx + 1), int(y + h - 4))
        else:
            step_count = 5
            usable_h = max(10, h - 10)
            each = usable_h / step_count
            for i in range(step_count):
                sy = y + 5 + i * each
                painter.setPen(QPen(step_shadow, 1))
                painter.drawLine(int(x + 4), int(sy), int(x + w - 4), int(sy))
                painter.setPen(QPen(step_main, 1))
                painter.drawLine(int(x + 4), int(sy + 1), int(x + w - 4), int(sy + 1))

        # 内嵌方向箭头 + 目的地简称（直接写在楼梯上）
        painter.setPen(QPen(QColor(236, 246, 255, 230), 2))
        if arrow == '↑':
            painter.drawLine(int(cx), int(cy + 4), int(cx), int(cy - 6))
            painter.drawLine(int(cx), int(cy - 6), int(cx - 4), int(cy - 2))
            painter.drawLine(int(cx), int(cy - 6), int(cx + 4), int(cy - 2))
        else:
            painter.drawLine(int(cx), int(cy - 4), int(cx), int(cy + 6))
            painter.drawLine(int(cx), int(cy + 6), int(cx - 4), int(cy + 2))
            painter.drawLine(int(cx), int(cy + 6), int(cx + 4), int(cy + 2))

        label_text = target_name[:4]
        font = painter.font()
        old_size = font.pointSize()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        bw, bh = 56, 16
        painter.setPen(QPen(QColor(22, 30, 42, 220), 1))
        painter.drawText(int(cx - bw // 2), int(cy + 12), bw, bh,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                        label_text)
        painter.setPen(QPen(QColor(220, 236, 255, 220), 1))
        painter.drawText(int(cx - bw // 2 + 1), int(cy + 11), bw, bh,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                        label_text)
        font.setPointSize(old_size)
        font.setBold(False)
        painter.setFont(font)
    
    def _draw_floor_labels(self, painter):
        """在区域最左边标注楼层名称"""
        if not self.scene.get('areas'):
            return
        
        has_upper = any(a['name'] in self.UPPER_FLOOR_AREAS for a in self.scene['areas'])
        has_lower = any(a['name'] in self.LOWER_FLOOR_AREAS for a in self.scene['areas'])
        if not (has_upper and has_lower):
            return
        
        # 收集上下层区域的 y 范围
        upper_y_min = float('inf')
        upper_y_max = 0
        lower_y_min = float('inf')
        lower_y_max = 0
        
        for area in self.scene['areas']:
            floor = self._get_area_floor(area['name'])
            ay = area['y']
            ah = area['height']
            if floor == 'upper':
                upper_y_min = min(upper_y_min, ay)
                upper_y_max = max(upper_y_max, ay + ah)
            elif floor == 'lower':
                lower_y_min = min(lower_y_min, ay)
                lower_y_max = max(lower_y_max, ay + ah)
        
        font = painter.font()
        old_size = font.pointSize()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        label_x = 6
        
        # 上层标注
        if upper_y_max > upper_y_min:
            mid_y = (upper_y_min + upper_y_max) / 2
            painter.setPen(QPen(QColor(120, 150, 190, 180), 1))
            painter.drawText(int(label_x), int(mid_y - 24), 36, 48,
                            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                            "上层")
        
        # 下层标注
        if lower_y_max > lower_y_min:
            mid_y = (lower_y_min + lower_y_max) / 2
            painter.setPen(QPen(QColor(120, 170, 150, 180), 1))
            painter.drawText(int(label_x), int(mid_y - 24), 36, 48,
                            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                            "下层")
        
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
        
        # 计算目标位置：目标区域中心，偏向远离门的方向偏移 60px
        target_cx = target_area['x'] + target_area['width'] / 2
        target_cy = target_area['y'] + target_area['height'] / 2
        door_cx = door['x'] + door['width'] / 2
        door_cy = door['y'] + door['height'] / 2
        
        dx = target_cx - door_cx
        dy = target_cy - door_cy
        dist = (dx ** 2 + dy ** 2) ** 0.5
        if dist > 0:
            offset_x = dx / dist * 60
            offset_y = dy / dist * 60
        else:
            offset_x = 0
            offset_y = 0
        
        char['x'] = door_cx + offset_x
        char['y'] = door_cy + offset_y
        
        # 确保在目标区域内，且远离其他门
        char['x'] = max(target_area['x'] + 15, min(char['x'], target_area['x'] + target_area['width'] - 15))
        char['y'] = max(target_area['y'] + 15, min(char['y'], target_area['y'] + target_area['height'] - 15))
        
        # 如果 path 下一个节点是当前门的中心，移除它
        if char.get('path') and len(char['path']) > 0:
            next_x, next_y = char['path'][0]
            if abs(next_x - door_cx) < 10 and abs(next_y - door_cy) < 10:
                char['path'].pop(0)
    
    def _load_background_image(self, case_id=None):
        """加载案件对应的背景图"""
        import os
        self._bg_pixmap = None
        if case_id:
            from PyQt6.QtGui import QPixmap
            bg_path = os.path.join('unheared', 'resources', 'backgrounds', f'{case_id}_bg.png')
            if os.path.exists(bg_path):
                self._bg_pixmap = QPixmap(bg_path)
                self.setMinimumSize(self._bg_pixmap.width(), self._bg_pixmap.height())
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # === 绘制背景图 ===
        if hasattr(self, '_bg_pixmap') and self._bg_pixmap:
            painter.drawPixmap(0, 0, self._bg_pixmap)
        else:
            # 备用：纯色背景
            painter.fillRect(self.rect(), QColor(20, 28, 46))
        
        # === 场景区域高亮（半透明叠加，用于楼层区分） ===
        for area in self.scene.get('areas', []):
            floor = self._get_area_floor(area['name'])
            if floor == 'upper':
                fill_color = QColor(60, 90, 140, 25)
            elif floor == 'lower':
                fill_color = QColor(60, 130, 110, 25)
            else:
                fill_color = QColor(50, 70, 100, 20)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(area['x'], area['y'], area['width'], area['height'])
        
        # 楼层分隔线
        self._draw_floor_labels(painter)
        
        # 绘制所有门：普通门画成墙壁缺口，楼梯门额外加标记和标注
        for door in self.scene.get('doors', []):
            if self._is_stair_door(door):
                self._draw_stair_marker(painter, door)
            else:
                self._draw_wall_gap(painter, door)
        
        # === 监听范围 ===
        listener_gradient = QRadialGradient(QPointF(self.listener_pos), self.listener_radius)
        listener_gradient.setColorAt(0.0, QColor(80, 160, 255, 25))
        listener_gradient.setColorAt(1.0, QColor(80, 160, 255, 0))
        painter.setBrush(QBrush(listener_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            self.listener_pos.x() - self.listener_radius,
            self.listener_pos.y() - self.listener_radius,
            self.listener_radius * 2, self.listener_radius * 2
        )
        
        # 监听点
        painter.setPen(QPen(QColor(100, 180, 255), 2))
        painter.setBrush(QBrush(QColor(100, 180, 255)))
        painter.drawEllipse(self.listener_pos.x() - 3, self.listener_pos.y() - 3, 6, 6)
        painter.setPen(QPen(QColor(100, 180, 255, 150), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.listener_pos.x() - 7, self.listener_pos.y() - 7, 14, 14)
        
        # === 绘制角色（更贴合原作） ===
        import time
        current_time = int(time.time() * 1000)
        
        for char_id, char in self.characters.items():
            cx, cy = char['x'], char['y']
            base_color = char['color']
            r, g, b = base_color.red(), base_color.green(), base_color.blue()
            
            dist_to_listener = ((cx - self.listener_pos.x()) ** 2 + (cy - self.listener_pos.y()) ** 2) ** 0.5
            in_listener_range = dist_to_listener <= self.listener_radius
            
            # === 声波纹（更精致） ===
            if in_listener_range and char_id in self.speaking_animations and self.speaking_animations[char_id]['active']:
                anim = self.speaking_animations[char_id]
                elapsed = (current_time - anim['start_time']) % 900
                for i in range(3):
                    wave_delay = i * 300
                    wave_elapsed = elapsed - wave_delay
                    if wave_elapsed > 0:
                        progress = min(wave_elapsed * self.wave_speed / self.wave_max_radius, 1.0)
                        radius = 10 + progress * self.wave_max_radius
                        alpha = int(160 * (1.0 - progress))
                        wave_color = QColor(r, g, b, alpha)
                        pen = QPen(wave_color)
                        pen.setWidth(1)
                        painter.setPen(pen)
                        painter.setBrush(Qt.BrushStyle.NoBrush)
                        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
            
            # === 外发光（更柔和、更小） ===
            glow_gradient = QRadialGradient(QPointF(cx, cy), 14)
            glow_gradient.setColorAt(0.0, QColor(r, g, b, 200))
            glow_gradient.setColorAt(0.5, QColor(r, g, b, 90))
            glow_gradient.setColorAt(1.0, QColor(r, g, b, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - 14), int(cy - 14), 28, 28)
            
            # === 核心圆点（更小、更精致） ===
            painter.setPen(QPen(QColor(r, g, b, 220), 2))
            painter.setBrush(QBrush(QColor(r, g, b, 160)))
            painter.drawEllipse(int(cx - 7), int(cy - 7), 14, 14)
            
            # === 中心亮点 ===
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 100)))
            painter.drawEllipse(int(cx - 3), int(cy - 3), 6, 6)
            
            # === 移动方向指示 ===
            if char.get('is_moving'):
                dx, dy = char.get('move_direction', (0, 0))
                if abs(dx) > 0.01 or abs(dy) > 0.01:
                    dir_len = (dx**2 + dy**2)**0.5
                    if dir_len > 0:
                        ndx, ndy = dx / dir_len, dy / dir_len
                        arrow_len = 10
                        ax = cx + ndx * arrow_len
                        ay = cy + ndy * arrow_len
                        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
                        painter.drawLine(int(cx), int(cy), int(ax), int(ay))
            
            # === 标签：字母标识 + 标记后显示名称 ===
            label = self._character_labels.get(char_id, '?')
            if char['marked'] and char.get('assigned_name'):
                label = f'{label}:{char["assigned_name"]}'
            font = painter.font()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            text_w = painter.fontMetrics().horizontalAdvance(label)
            # 半透明背景
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(20, 22, 30, 180)))
            painter.drawRoundedRect(int(cx - text_w // 2 - 4), int(cy - 22), text_w + 8, 18, 3, 3)
            # 文字阴影
            painter.setPen(QPen(QColor(20, 22, 30), 1))
            painter.drawText(int(cx - text_w // 2), int(cy - 10), label)
            # 文字
            painter.setPen(QPen(QColor(220, 220, 240), 1))
            painter.drawText(int(cx - text_w // 2 - 1), int(cy - 11), label)
            font.setBold(False)
            painter.setFont(font)
            
            # === 标记状态（金色外圈） ===
            if char['marked']:
                painter.setPen(QPen(QColor(255, 210, 70), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - 10), int(cy - 10), 20, 20)
            
            # === 选中状态（白色外圈+虚线） ===
            if char_id == self.selected_character:
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - 10), int(cy - 10), 20, 20)
                painter.setPen(QPen(QColor(255, 255, 255, 120), 1, Qt.PenStyle.DashLine))
                painter.drawEllipse(int(cx - 13), int(cy - 13), 26, 26)
            
            # === 悬停效果 ===
            if char_id == self.hovered_character:
                painter.setPen(QPen(QColor(200, 220, 255, 150), 1, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(int(cx - 13), int(cy - 13), 26, 26)
        
        # === 迷雾/光照效果 ===
        fog_gradient = QRadialGradient(QPointF(self.listener_pos), self.listener_radius * 1.8)
        fog_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        fog_gradient.setColorAt(0.4, QColor(0, 0, 0, 30))
        fog_gradient.setColorAt(0.7, QColor(0, 0, 0, 100))
        fog_gradient.setColorAt(1.0, QColor(0, 0, 0, 180))
        painter.setBrush(QBrush(fog_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
    
    def update_character_position(self, char_id, x, y, movement='walk'):
        """设置角色目标位置，并计算路径"""
        if char_id in self.characters:
            char = self.characters[char_id]
            if (char['target_x'] != x or char['target_y'] != y or
                    char.get('movement') != movement):
                char['target_x'] = x
                char['target_y'] = y
                char['movement'] = movement
                char['path'] = self.find_path(char_id, x, y)
    
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
                    
                    area1 = self.get_character_area(c1['x'], c1['y'])
                    area2 = self.get_character_area(c2['x'], c2['y'])
                    in_stairs = (area1 and self._is_stair_area(area1)) or (area2 and self._is_stair_area(area2))
                    
                    # 门口区域使用更小间距，避免两人堵门
                    near_door = self._is_near_door(c1['x'], c1['y']) or self._is_near_door(c2['x'], c2['y'])
                    if near_door:
                        min_sep = self.DOOR_SEPARATION
                    elif in_stairs:
                        min_sep = self.MIN_SEPARATION_STAIRS
                    else:
                        min_sep = self.MIN_SEPARATION
                    
                    if dist < min_sep and dist > 0:
                        overlap = (min_sep - dist) / 2.0
                        ratio = overlap / dist
                        c1['x'] += dx * ratio
                        c1['y'] += dy * ratio
                        c2['x'] -= dx * ratio
                        c2['y'] -= dy * ratio
                        
                        area1_after = self.get_character_area(c1['x'], c1['y'])
                        area2_after = self.get_character_area(c2['x'], c2['y'])
                        
                        # 如果有门连接两个区域，允许通过（不拉回原区域）
                        if area1 and area1_after != area1:
                            if not self._areas_connected_by_door(area1, area1_after):
                                c1['x'], c1['y'] = self._constrain_to_area(c1['x'], c1['y'], area1)
                        elif area1 is None and near_door:
                            c1['x'], c1['y'] = self.constrain_to_walkable(c1['x'], c1['y'])
                        
                        if area2 and area2_after != area2:
                            if not self._areas_connected_by_door(area2, area2_after):
                                c2['x'], c2['y'] = self._constrain_to_area(c2['x'], c2['y'], area2)
                        elif area2 is None and near_door:
                            c2['x'], c2['y'] = self.constrain_to_walkable(c2['x'], c2['y'])
    
    def update_positions(self):
        """平滑移动角色到目标位置，走路径点；平滑移动监听点；全局碰撞避免"""
        updated = False
        
        # === 角色移动 ===
        for char_id, char in self.characters.items():
            if char.get('path') and len(char['path']) > 0:
                next_x, next_y = char['path'][0]
            else:
                # 已到达最终目标，不产生移动
                char['is_moving'] = False
                char['move_direction'] = (0, 0)
                continue
            
            dx = next_x - char['x']
            dy = next_y - char['y']
            distance = (dx ** 2 + dy ** 2) ** 0.5
            
            if distance > 1.0:
                speed = self._get_movement_speed(char_id)
                # 门口速度提升，帮助快速通过
                boost = self._door_speed_boost.get(char_id, 0)
                if boost > 0:
                    speed *= (1.0 + boost * 0.05)
                    self._door_speed_boost[char_id] = boost - 1
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
                if char.get('path') and len(char['path']) > 0:
                    char['path'].pop(0)
                char['is_moving'] = bool(char.get('path') and len(char['path']) > 0)
                char['move_direction'] = (0, 0)
                updated = True
            else:
                if char.get('path') and len(char['path']) > 0:
                    char['path'].pop(0)
                char['is_moving'] = False
                char['move_direction'] = (0, 0)

            # 如果已经进入门洞区域，直接跳过当前路径点，减少门口来回抖动
            if char.get('path'):
                for door in self.scene.get('doors', []):
                    dx4, dy4 = 4, 4
                    in_door = (door['x'] - dx4 <= char['x'] <= door['x'] + door['width'] + dx4 and
                               door['y'] - dy4 <= char['y'] <= door['y'] + door['height'] + dy4)
                    if in_door:
                        # 跳过仍在门内的路径点
                        while char['path']:
                            px, py = char['path'][0]
                            if (door['x'] - dx4 <= px <= door['x'] + door['width'] + dx4 and
                                door['y'] - dy4 <= py <= door['y'] + door['height'] + dy4):
                                char['path'].pop(0)
                            else:
                                break
                        # 如果跳过后还有路径点，且角色已到达门对侧，跳过还在原侧的路径点
                        if char.get('path') and len(char['path']) >= 2:
                            current_area = self.get_character_area(char['x'], char['y'])
                            next_area = self.get_character_area(char['path'][0][0], char['path'][0][1])
                            if (current_area is not None and next_area is not None and
                                    current_area != next_area and
                                    self._areas_connected_by_door(current_area, next_area)):
                                char['path'].pop(0)
                        # 穿门时给个速度提升，快速通过
                        if char.get('path') and char.get('is_moving', False):
                            self._door_speed_boost.get(char_id, 0)
                            self._door_speed_boost[char_id] = min(10, self._door_speed_boost.get(char_id, 0) + 1)
                        break
            
            # === 楼梯传送检测 ===
            import time as pytime
            now = pytime.time()
            if char.get('teleport_cooldown', 0) < now:
                for door in self.scene.get('doors', []):
                    if not self._is_stair_door(door):
                        continue
                    current_area = self.get_character_area(char['x'], char['y'])
                    # 仅当角色在该楼梯连接的任一侧区域时触发，避免误传送
                    if current_area not in (door['area1'], door['area2']):
                        continue
                    if current_area == door['area1']:
                        entry_x, entry_y, _, _ = self._get_door_transit_points(door, door['area1'], door['area2'])
                    else:
                        entry_x, entry_y, _, _ = self._get_door_transit_points(door, door['area2'], door['area1'])

                    dist_to_entry = ((char['x'] - entry_x) ** 2 + (char['y'] - entry_y) ** 2) ** 0.5
                    # 只在楼梯入口附近触发，避免“全房间吸附传送”异常
                    if dist_to_entry < 24:
                        self._teleport_character(char_id, door)
                        char['teleport_cooldown'] = now + 1.0  # 1秒冷却，确保远离
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
                label = self._character_labels.get(char_id, '?')
                if char['marked'] and char.get('assigned_name'):
                    tooltip = f"{label} [{char['assigned_name']}]"
                else:
                    tooltip = label
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
