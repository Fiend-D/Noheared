@tool
class_name Room
extends Node2D
## 一个房间。`polygon` 使用地图坐标（Room 节点本身应放在原点）。

@export var room_name: String = "":
	set(value):
		room_name = value
		queue_redraw()
@export var floor_index: int = 0
@export var polygon: PackedVector2Array = PackedVector2Array():
	set(value):
		polygon = value
		queue_redraw()
## 地板材质（`art/floors/` 下的贴图），为空时用纯色。
@export var floor_texture: Texture2D:
	set(value):
		floor_texture = value
		queue_redraw()
## 户外区域（花园、甲板、露台）：围栏代替墙。
@export var outdoor: bool = false:
	set(value):
		outdoor = value
		queue_redraw()

var highlighted: bool = false:
	set(value):
		if highlighted != value:
			highlighted = value
			queue_redraw()

var _label: Node2D


func _ready() -> void:
	texture_repeat = CanvasItem.TEXTURE_REPEAT_MIRROR
	var mat := ShaderMaterial.new()
	mat.shader = Prop.LIT_SHADER
	material = mat
	_label = RoomLabel.new()
	_label.z_index = 2
	add_child(_label, false, Node.INTERNAL_MODE_BACK)


func set_light(light: float, warm: float) -> void:
	var mat := material as ShaderMaterial
	if mat:
		mat.set_shader_parameter("light", light)
		mat.set_shader_parameter("warm", warm)


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


## 墙上离 `map_point` 最近的点（地图坐标）。
func closest_wall_point(map_point: Vector2) -> Vector2:
	var i := _closest_wall(map_point)
	var a := polygon[i]
	var b := polygon[(i + 1) % polygon.size()]
	return position + Geometry2D.get_closest_point_to_segment(map_point - position, a, b)


## 离 `map_point` 最近那面墙的方向（单位向量）。
func closest_wall_direction(map_point: Vector2) -> Vector2:
	var i := _closest_wall(map_point)
	return (polygon[(i + 1) % polygon.size()] - polygon[i]).normalized()


func _closest_wall(map_point: Vector2) -> int:
	var local := map_point - position
	var best := 0
	var best_d := INF
	for i in polygon.size():
		var q := Geometry2D.get_closest_point_to_segment(local, polygon[i], polygon[(i + 1) % polygon.size()])
		var d := q.distance_squared_to(local)
		if d < best_d:
			best_d = d
			best = i
	return best


## 点在房间内且离墙至少 `margin`。
func is_walkable(map_point: Vector2, margin: float) -> bool:
	return contains_point(map_point) and closest_wall_point(map_point).distance_to(map_point) >= margin


## 房间内离 `map_point` 最近、且离墙至少 `margin` 的点（矩形房间精确，其他形状近似）。
func clamp_point(map_point: Vector2, margin: float = 10.0) -> Vector2:
	var b := get_bounds().grow(-margin)
	if b.size.x <= 0.0 or b.size.y <= 0.0:
		return get_center()
	return Vector2(clampf(map_point.x, b.position.x, b.end.x), clampf(map_point.y, b.position.y, b.end.y))


func _draw() -> void:
	if polygon.size() < 3:
		return
	if floor_texture:
		var uvs := PackedVector2Array()
		for p in polygon:
			uvs.append(p / MapStyle.FLOOR_TILE)
		draw_colored_polygon(polygon, Color.WHITE, uvs, floor_texture)
	else:
		draw_colored_polygon(polygon, MapStyle.ROOM_FILL)
	var outline := polygon.duplicate()
	outline.append(polygon[0])
	if outdoor:
		draw_polyline(outline, MapStyle.RAILING, MapStyle.RAILING_WIDTH, true)
	else:
		draw_polyline(outline, MapStyle.WALL_SHADE, MapStyle.WALL_SHADE_WIDTH, true)
		draw_polyline(outline, MapStyle.WALL, MapStyle.WALL_WIDTH, true)
	if _label:
		_label.queue_redraw()


## 房间名不受灯光影响，画在家具上面。
class RoomLabel:
	extends Node2D

	func _draw() -> void:
		var room := get_parent() as Room
		var b := room.get_bounds()
		b.position -= room.position
		var font := UiTheme.serif_font()
		var color := MapStyle.AMBER if room.highlighted else MapStyle.LABEL
		var at := b.position + Vector2(10, 22)
		var width := b.size.x - 20
		draw_string_outline(font, at, room.room_name, HORIZONTAL_ALIGNMENT_LEFT, width, 14, 5, MapStyle.LABEL_OUTLINE)
		draw_string(font, at, room.room_name, HORIZONTAL_ALIGNMENT_LEFT, width, 14, color)
