@tool
class_name Room
extends Node2D
## 一个房间。`polygon` 使用地图坐标（Room 节点本身应放在原点）。

const FILL := Color(0.10, 0.18, 0.32, 0.55)
const FILL_ACTIVE := Color(0.16, 0.28, 0.48, 0.75)
const WALL := Color(0.62, 0.80, 1.0, 0.95)
const LABEL := Color(0.75, 0.88, 1.0, 0.9)
const WALL_WIDTH := 3.0

@export var room_name: String = "":
	set(value):
		room_name = value
		queue_redraw()
@export var floor_index: int = 0
@export var polygon: PackedVector2Array = PackedVector2Array():
	set(value):
		polygon = value
		queue_redraw()

var highlighted: bool = false:
	set(value):
		if highlighted != value:
			highlighted = value
			queue_redraw()


func contains_point(map_point: Vector2) -> bool:
	return polygon.size() >= 3 and Geometry2D.is_point_in_polygon(map_point - position, polygon)


func get_bounds() -> Rect2:
	if polygon.is_empty():
		return Rect2(position, Vector2.ZERO)
	var r := Rect2(polygon[0], Vector2.ZERO)
	for p in polygon:
		r = r.expand(p)
	r.position += position
	return r


func get_area() -> float:
	var s := 0.0
	for i in polygon.size():
		var a := polygon[i]
		var b := polygon[(i + 1) % polygon.size()]
		s += a.x * b.y - b.x * a.y
	return absf(s) * 0.5


func get_center() -> Vector2:
	return get_bounds().get_center()


## 房间内离 `map_point` 最近、且离墙至少 `margin` 的点（矩形房间精确，其他形状近似）。
func clamp_point(map_point: Vector2, margin: float = 10.0) -> Vector2:
	var b := get_bounds().grow(-margin)
	if b.size.x <= 0.0 or b.size.y <= 0.0:
		return get_center()
	return Vector2(clampf(map_point.x, b.position.x, b.end.x), clampf(map_point.y, b.position.y, b.end.y))


func _draw() -> void:
	if polygon.size() < 3:
		return
	draw_colored_polygon(polygon, FILL_ACTIVE if highlighted else FILL)
	var outline := polygon.duplicate()
	outline.append(polygon[0])
	draw_polyline(outline, WALL, WALL_WIDTH, true)
	var b := get_bounds()
	b.position -= position
	var font := ThemeDB.fallback_font
	draw_string(font, b.position + Vector2(10, 22), room_name, HORIZONTAL_ALIGNMENT_LEFT, b.size.x - 20, 15, LABEL)
