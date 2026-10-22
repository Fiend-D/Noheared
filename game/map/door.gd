@tool
class_name Door
extends Node2D
## 连接两个房间的门洞。节点位置即门的中心。

const GAP_COLOR := Color(0.10, 0.18, 0.32, 1.0)
const JAMB_COLOR := Color(0.62, 0.80, 1.0, 0.95)
const CLOSED_COLOR := Color(0.95, 0.70, 0.30, 0.95)

@export var room_a: String = ""
@export var room_b: String = ""
@export var size: Vector2 = Vector2(24, 10):
	set(value):
		size = value
		queue_redraw()
## 关着的门让声音更难穿过。
@export var open: bool = true:
	set(value):
		open = value
		queue_redraw()

var floor_index: int = 0


func _draw() -> void:
	var rect := Rect2(-size * 0.5, size)
	draw_rect(rect.grow(1.5), GAP_COLOR)
	var horizontal := size.x >= size.y
	if horizontal:
		draw_line(rect.position, rect.position + Vector2(0, size.y), JAMB_COLOR, 2.0)
		draw_line(rect.end - Vector2(0, size.y), rect.end, JAMB_COLOR, 2.0)
	else:
		draw_line(rect.position, rect.position + Vector2(size.x, 0), JAMB_COLOR, 2.0)
		draw_line(rect.end - Vector2(size.x, 0), rect.end, JAMB_COLOR, 2.0)
	if not open:
		var a := Vector2(rect.position.x, 0) if horizontal else Vector2(0, rect.position.y)
		draw_line(a, -a, CLOSED_COLOR, 3.0)
