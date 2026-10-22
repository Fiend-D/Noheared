@tool
class_name Stair
extends Node2D
## 连接两个楼层的楼梯。节点位置是 `room_a` 一侧的楼梯口，`end_b` 是 `room_b` 一侧（地图坐标）。

const BODY := Color(0.20, 0.32, 0.52, 0.95)
const STEP := Color(0.62, 0.80, 1.0, 0.85)
const TEXT := Color(0.95, 0.85, 0.55, 1.0)
const ICON_SIZE := Vector2(40, 24)

@export var room_a: String = ""
@export var room_b: String = ""
@export var end_b: Vector2 = Vector2.ZERO:
	set(value):
		end_b = value
		queue_redraw()

var floor_a: int = 0
var floor_b: int = 0
## -1 表示两端都画。
var visible_floor: int = -1:
	set(value):
		visible_floor = value
		queue_redraw()


func end_a() -> Vector2:
	return position


func _draw() -> void:
	if visible_floor < 0 or visible_floor == floor_a:
		_draw_end(Vector2.ZERO, room_b)
	if visible_floor < 0 or visible_floor == floor_b:
		_draw_end(end_b - position, room_a)


func _draw_end(at: Vector2, destination: String) -> void:
	var rect := Rect2(at - ICON_SIZE * 0.5, ICON_SIZE)
	draw_rect(rect, BODY)
	draw_rect(rect, STEP, false, 1.5)
	var steps := 5
	for i in range(1, steps):
		var x := rect.position.x + rect.size.x * i / steps
		draw_line(Vector2(x, rect.position.y + 3), Vector2(x, rect.end.y - 3), STEP, 1.0)
	var font := ThemeDB.fallback_font
	draw_string(
		font,
		Vector2(rect.position.x - 30, rect.end.y + 15),
		"⇅ " + destination,
		HORIZONTAL_ALIGNMENT_CENTER,
		ICON_SIZE.x + 60,
		12,
		TEXT
	)
