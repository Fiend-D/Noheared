#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为每个案件生成原作风格的蓝图背景图
用法: python generate_case_backgrounds.py
"""

import os
import json
import random
from PIL import Image, ImageDraw, ImageFont


def draw_wall_line(draw, x1, y1, x2, y2, color=(90, 115, 155), width=3):
    """绘制带厚度的墙壁线"""
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # 内发光效果：更亮的细线
    draw.line([(x1, y1), (x2, y2)], fill=(120, 150, 200), width=1)


def draw_door_gap(draw, door, wall_color=(90, 115, 155), wall_width=3):
    """在墙壁线上留出门的缺口"""
    x, y, w, h = door['x'], door['y'], door['width'], door['height']
    # 门区域画成背景色（擦除墙壁线）
    margin = wall_width + 1
    draw.rectangle(
        [x - margin, y - margin, x + w + margin, y + h + margin],
        fill=(20, 28, 46)  # 背景色
    )
    # 门框
    draw.rectangle([x, y, x + w, y + h], outline=(100, 125, 165), width=1)


def draw_room_interior(draw, area, seed=0):
    """在房间内部绘制简单的家具/隔断线条"""
    rng = random.Random(seed)
    x, y, w, h = area['x'], area['y'], area['width'], area['height']
    margin = 15
    
    # 根据房间大小决定内部元素
    if w < 80 or h < 80:
        return
    
    num_elements = min(3, max(1, (w * h) // 20000))
    
    for _ in range(num_elements):
        etype = rng.choice(['table', 'desk', 'sofa', 'shelf', 'divider'])
        
        if etype == 'table':
            tw, th = rng.randint(30, 60), rng.randint(20, 40)
            tx = x + margin + rng.randint(0, max(0, w - tw - margin * 2))
            ty = y + margin + rng.randint(0, max(0, h - th - margin * 2))
            draw.rectangle([tx, ty, tx + tw, ty + th], outline=(60, 80, 110), width=1)
        
        elif etype == 'desk':
            dw, dh = rng.randint(40, 70), rng.randint(20, 30)
            dx = x + margin + rng.randint(0, max(0, w - dw - margin * 2))
            dy = y + margin + rng.randint(0, max(0, h - dh - margin * 2))
            draw.rectangle([dx, dy, dx + dw, dy + dh], outline=(60, 80, 110), width=1)
            # 椅子
            draw.ellipse([dx + dw - 10, dy - 8, dx + dw + 2, dy + 4], outline=(60, 80, 110), width=1)
        
        elif etype == 'sofa':
            sw, sh = rng.randint(40, 70), rng.randint(15, 25)
            sx = x + margin + rng.randint(0, max(0, w - sw - margin * 2))
            sy = y + margin + rng.randint(0, max(0, h - sh - margin * 2))
            draw.rectangle([sx, sy, sx + sw, sy + sh], outline=(60, 80, 110), width=1)
            # 靠背
            if sw > sh:
                draw.line([(sx, sy), (sx + sw, sy)], fill=(60, 80, 110), width=1)
            else:
                draw.line([(sx, sy), (sx, sy + sh)], fill=(60, 80, 110), width=1)
        
        elif etype == 'shelf':
            shelf_w, shelf_h = rng.randint(30, 50), rng.randint(40, 70)
            sx = x + margin + rng.randint(0, max(0, w - shelf_w - margin * 2))
            sy = y + margin + rng.randint(0, max(0, h - shelf_h - margin * 2))
            draw.rectangle([sx, sy, sx + shelf_w, sy + shelf_h], outline=(60, 80, 110), width=1)
            # 横线
            for ly in range(sy + 15, sy + shelf_h, 15):
                draw.line([(sx, ly), (sx + shelf_w, ly)], fill=(55, 75, 105), width=1)
        
        elif etype == 'divider':
            if rng.random() > 0.5:
                # 水平隔断
                div_x = x + margin + rng.randint(0, max(0, w - margin * 2))
                div_y = y + margin + rng.randint(0, max(0, h - margin * 2))
                div_w = rng.randint(40, min(100, w - margin * 2))
                draw.line([(div_x, div_y), (div_x + div_w, div_y)], fill=(65, 85, 120), width=2)
            else:
                # 垂直隔断
                div_x = x + margin + rng.randint(0, max(0, w - margin * 2))
                div_y = y + margin + rng.randint(0, max(0, h - margin * 2))
                div_h = rng.randint(40, min(100, h - margin * 2))
                draw.line([(div_x, div_y), (div_x, div_y + div_h)], fill=(65, 85, 120), width=2)


def generate_case_background(case_file, output_dir):
    """为单个案件生成背景图"""
    with open(case_file, 'r', encoding='utf-8') as f:
        case_data = json.load(f)
    
    scene = case_data.get('scene', {})
    areas = scene.get('areas', [])
    doors = scene.get('doors', [])
    
    # 计算画布尺寸
    max_x = max((a['x'] + a['width'] for a in areas), default=800)
    max_y = max((a['y'] + a['height'] for a in areas), default=400)
    padding = 30
    canvas_w = int(max_x + padding * 2)
    canvas_h = int(max_y + padding * 2)
    
    # 创建画布
    bg_color = (20, 28, 46)  # 深蓝背景
    img = Image.new('RGB', (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(img)
    
    # 绘制网格
    grid_color = (28, 38, 56)
    grid_size = 40
    for gx in range(0, canvas_w, grid_size):
        draw.line([(gx, 0), (gx, canvas_h)], fill=grid_color, width=1)
    for gy in range(0, canvas_h, grid_size):
        draw.line([(0, gy), (canvas_w, gy)], fill=grid_color, width=1)
    
    # 绘制房间
    room_fill = (28, 40, 62)  # 房间填充色
    room_border = (90, 115, 155)  # 房间边框
    
    for i, area in enumerate(areas):
        ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
        
        # 房间填充
        draw.rectangle([ax, ay, ax + aw, ay + ah], fill=room_fill)
        
        # 房间内部元素
        if not any(s in area['name'] for s in ['楼梯', '走廊', '甲板']):
            draw_room_interior(draw, area, seed=i * 100 + hash(area['name']) % 1000)
    
    # 绘制墙壁线（房间边框，留出门口）
    wall_width = 3
    wall_color = (90, 115, 155)
    
    # 先收集每个区域边上的门
    door_edges = {}  # (area_name, edge) -> door
    for door in doors:
        # 简单判断门在哪个区域的哪条边上
        dx, dy, dw, dh = door['x'], door['y'], door['width'], door['height']
        dcx, dcy = dx + dw / 2, dy + dh / 2
        
        for area in areas:
            ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
            # 门中心靠近区域的哪条边
            edges = []
            if abs(dcy - ay) < 10 and ax <= dcx <= ax + aw:
                edges.append(('top', area['name']))
            if abs(dcy - (ay + ah)) < 10 and ax <= dcx <= ax + aw:
                edges.append(('bottom', area['name']))
            if abs(dcx - ax) < 10 and ay <= dcy <= ay + ah:
                edges.append(('left', area['name']))
            if abs(dcx - (ax + aw)) < 10 and ay <= dcy <= ay + ah:
                edges.append(('right', area['name']))
            
            for edge, name in edges:
                door_edges.setdefault((name, edge), []).append((dx, dy, dw, dh))
    
    # 绘制每个区域的墙壁线，在门的位置留缺口
    for area in areas:
        ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
        
        # 收集四条边上的门
        top_doors = door_edges.get((area['name'], 'top'), [])
        bottom_doors = door_edges.get((area['name'], 'bottom'), [])
        left_doors = door_edges.get((area['name'], 'left'), [])
        right_doors = door_edges.get((area['name'], 'right'), [])
        
        def draw_edge_with_gaps(y_or_x, is_horizontal, doors_on_edge, start, end):
            """在一条边上绘制墙壁线，留出门口"""
            segments = []
            current = start
            
            # 按坐标排序门
            if is_horizontal:
                doors_sorted = sorted(doors_on_edge, key=lambda d: d[0])
            else:
                doors_sorted = sorted(doors_on_edge, key=lambda d: d[1])
            
            for door in doors_sorted:
                if is_horizontal:
                    d_start = door[0]
                    d_end = door[0] + door[2]
                    if current < d_start:
                        segments.append((current, d_start))
                    current = max(current, d_end)
                else:
                    d_start = door[1]
                    d_end = door[1] + door[3]
                    if current < d_start:
                        segments.append((current, d_start))
                    current = max(current, d_end)
            
            if current < end:
                segments.append((current, end))
            
            for seg_start, seg_end in segments:
                if is_horizontal:
                    draw_wall_line(draw, seg_start, y_or_x, seg_end, y_or_x, wall_color, wall_width)
                else:
                    draw_wall_line(draw, y_or_x, seg_start, y_or_x, seg_end, wall_color, wall_width)
        
        # 上边缘
        draw_edge_with_gaps(ay, True, top_doors, ax, ax + aw)
        # 下边缘
        draw_edge_with_gaps(ay + ah, True, bottom_doors, ax, ax + aw)
        # 左边缘
        draw_edge_with_gaps(ax, False, left_doors, ay, ay + ah)
        # 右边缘
        draw_edge_with_gaps(ax + aw, False, right_doors, ay, ay + ah)
    
    # 绘制门区域（如果门不在任何区域边缘上，单独绘制）
    for door in doors:
        dx, dy, dw, dh = door['x'], door['y'], door['width'], door['height']
        # 门的小标记
        draw.rectangle([dx, dy, dx + dw, dy + dh], outline=(100, 125, 165), width=1)
    
    # 绘制区域名称
    font = None
    for font_path in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
    ]:
        try:
            font = ImageFont.truetype(font_path, 15)
            break
        except:
            continue
    if font is None:
        font = ImageFont.load_default()
    
    for area in areas:
        ax, ay, aw, ah = area['x'], area['y'], area['width'], area['height']
        name = area['name']
        # 计算文字居中位置
        bbox = draw.textbbox((0, 0), name, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        tx = ax + (aw - text_w) / 2
        ty = ay + (ah - text_h) / 2
        
        # 文字阴影
        draw.text((tx + 1, ty + 1), name, fill=(15, 22, 38), font=font)
        draw.text((tx, ty), name, fill=(130, 155, 195), font=font)
    
    # 保存
    case_id = os.path.splitext(os.path.basename(case_file))[0]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'{case_id}_bg.png')
    img.save(output_path)
    print(f"  已生成: {output_path} ({canvas_w}x{canvas_h})")
    return output_path


def main():
    cases_dir = 'unheared/cases'
    output_dir = 'unheared/resources/backgrounds'
    
    print("=== 生成案件背景图 ===")
    case_files = sorted([f for f in os.listdir(cases_dir) if f.endswith('.json')])
    
    for case_file in case_files:
        case_path = os.path.join(cases_dir, case_file)
        generate_case_background(case_path, output_dir)
    
    print(f"\n=== 完成！背景图保存在 {output_dir}/ ===")


if __name__ == '__main__':
    main()
