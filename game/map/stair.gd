@tool
class_name Stair
extends Node2D
## 连接两个楼层的楼梯。节点位置是 `room_a` 一侧的楼梯口，`end_b` 是 `room_b` 一侧（地图坐标）。

const ICON_SIZE := Vector2(34, 22)
const TREADS := 5
## 鼠标落在楼梯口图标外扩这么多像素内也算指着它。
const PICK_MARGIN := 8.0

@export var room_a: String = ""
@export var room_b: String = ""
@export var end_b: Vector2 = Vector2.ZERO:
	set(value):
		end_b = value
		queue_redraw()

var floor_a: int = 0
var floor_b: int = 0
## 楼梯口靠近房间上墙时标签画在下方，避免压到墙。由 CaseMap.refresh() 设置。
var label_below_a: bool = false
var label_below_b: bool = false
## -1 表示两端都画。
var visible_floor: int = -1:
	set(value):
		visible_floor = value
		queue_redraw()
## 鼠标指着的楼梯口：0 是 room_a 一侧，1 是 room_b 一侧，-1 表示没有。
var hovered_end: int = -1:
	set(value):
		if hovered_end != value:
			hovered_end = value
			queue_redraw()


func _ready() -> void:
	z_index = 1


func end_a() -> Vector2:
	return position


## 楼梯在 `room_name` 那一侧的楼梯口。
func end_in(room_name: String) -> Vector2:
	return position if room_name == room_a else end_b


## `floor_index` 层上 `map_point` 指着的楼梯口（0 / 1），没有返回 -1。
func end_at(map_point: Vector2, floor_index: int) -> int:
	for i in 2:
		var at := position if i == 0 else end_b
		var on_floor := floor_a if i == 0 else floor_b
		if on_floor == floor_index and Rect2(at - ICON_SIZE * 0.5, ICON_SIZE).grow(PICK_MARGIN).has_point(map_point):
			return i
	return -1


## 从 `end` 一侧上楼梯，到达的那个房间。
func far_room(end: int) -> String:
	return room_b if end == 0 else room_a


func near_room(end: int) -> String:
	return room_a if end == 0 else room_b


func _draw() -> void:
	if visible_floor < 0 or visible_floor == floor_a:
		_draw_end(Vector2.ZERO, room_b, floor_b - floor_a, label_below_a, hovered_end == 0)
	if visible_floor < 0 or visible_floor == floor_b:
		_draw_end(end_b - position, room_a, floor_a - floor_b, label_below_b, hovered_end == 1)


## `rise` > 0 表示往上走（楼层下标变大）。`hot` 为 true 时描出高亮轮廓。
func _draw_end(at: Vector2, destination: String, rise: int, label_below: bool, hot: bool) -> void:
	var going_up := rise > 0
	var rect := Rect2(at - ICON_SIZE * 0.5, ICON_SIZE)
	if hot:
		draw_rect(rect.grow(7.0), Color(MapStyle.AMBER, 0.18))
		draw_rect(rect.grow(4.0), Color(MapStyle.AMBER, 0.95), false, 2.0)
	draw_rect(Rect2(rect.position + Vector2(2, 3), rect.size), Color(0, 0, 0, 0.45))
	draw_rect(rect, MapStyle.DOOR_FLOOR)
	for i in range(TREADS):
		var x := rect.position.x + rect.size.x * i / TREADS
		var shade := 0.10 + 0.08 * i
		draw_rect(Rect2(x, rect.position.y, rect.size.x / TREADS, rect.size.y), Color(1, 0.9, 0.75, shade))
		draw_line(Vector2(x, rect.position.y), Vector2(x, rect.end.y), MapStyle.WALL, 1.5)
	draw_rect(rect, MapStyle.AMBER if hot else MapStyle.WALL, false, 2.5)
	var y := at.y
	var tip := Vector2(rect.end.x - 5, y) if going_up else Vector2(rect.position.x + 5, y)
	var tail := Vector2(rect.position.x + 5, y) if going_up else Vector2(rect.end.x - 5, y)
	var back := (tail - tip).normalized()
	draw_line(tail, tip, MapStyle.AMBER, 2.0, true)
	draw_line(tip, tip + back.rotated(0.6) * 6.0, MapStyle.AMBER, 2.0, true)
	draw_line(tip, tip + back.rotated(-0.6) * 6.0, MapStyle.AMBER, 2.0, true)
	var font := ThemeDB.fallback_font
	var arrow := "⇅ " if rise == 0 else ("▲ " if going_up else "▼ ")
	var label_pos := Vector2(rect.position.x - 40, rect.end.y + 14 if label_below else rect.position.y - 5)
	var text := arrow + destination
	var width := ICON_SIZE.x + 80
	var label_color := Color.WHITE if hot else MapStyle.AMBER
	draw_string_outline(font, label_pos, text, HORIZONTAL_ALIGNMENT_CENTER, width, 11, 4, MapStyle.LABEL_OUTLINE)
	draw_string(font, label_pos, text, HORIZONTAL_ALIGNMENT_CENTER, width, 11, label_color)
