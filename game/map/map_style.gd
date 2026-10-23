@tool
class_name MapStyle
extends RefCounted
## 地图配色：插画式室内，粗黑墙；监听者所在房间暖光，其余房间按声学距离变暗、变青。

const INK := Color(0.039, 0.055, 0.078)
const BACKDROP := Color(0.050, 0.068, 0.078)
const ROOM_FILL := Color(0.36, 0.33, 0.29)
const WALL := Color(0.025, 0.030, 0.035)
const MASS_EDGE := Color(0.55, 0.66, 0.66, 0.22)
const DOOR_LEAF := Color(0.78, 0.62, 0.46)
const DOOR_KNOB := Color(0.85, 0.68, 0.32)
const WALL_SHADE := Color(0, 0, 0, 0.32)
const RAILING := Color(0.32, 0.25, 0.18)
const LABEL := Color(0.94, 0.91, 0.83)
const LABEL_OUTLINE := Color(0, 0, 0, 0.65)
const DOOR_FLOOR := Color(0.30, 0.22, 0.15)
const DOOR_FLOOR_TINT := Color(0.85, 0.80, 0.75)
const AMBER := Color(0.96, 0.68, 0.26)
const ALERT := Color(0.90, 0.32, 0.25)
const WALL_WIDTH := 8.0
const WALL_SHADE_WIDTH := 22.0
const RAILING_WIDTH := 3.0
## 地板贴图一格对应的地图尺寸。
const FLOOR_TILE := 96.0

## 按与监听者所在房间的声学距离（0 = 同一房间）取 [亮度, 暖色]，超出数组的用最后一项。
const LIGHT_LEVELS: Array[Vector2] = [Vector2(1.0, 1.0), Vector2(0.8, 0.0), Vector2(0.5, 0.0), Vector2(0.3, 0.0)]
## 灯光过渡速度（每秒）。
const LIGHT_FADE := 4.0
