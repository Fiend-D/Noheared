@tool
class_name Door
extends Node2D
## 连接两个房间的门洞。节点位置即门的中心。
## 通道几何（`end_a` / `end_b` / `axis` / `half_width`）由 CaseMap.refresh() 根据两侧房间算出：
## 相邻房间共用一面墙时两端重合，房间之间有空隙时是一段走道。

const THRESHOLD := preload("res://art/floors/parquet.jpg")
const LEAF := preload("res://art/floors/wood.jpg")
const TEXTURE_TILE := 64.0
const LEAF_THICKNESS := 5.0
## 开着的门扇与墙的夹角。
const OPEN_ANGLE := deg_to_rad(80.0)
## 门洞比这个宽时画成双扇门。
const DOUBLE_DOOR_WIDTH := 34.0

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
## room_a 一侧墙上的门口（地图坐标）。
var end_a: Vector2 = Vector2.ZERO
## room_b 一侧墙上的门口（地图坐标）。
var end_b: Vector2 = Vector2.ZERO
## 从 room_a 指向 room_b 的单位向量（水平或竖直）。
var axis: Vector2 = Vector2.DOWN
var half_width: float = 10.0


func _ready() -> void:
	z_index = 1
	texture_repeat = CanvasItem.TEXTURE_REPEAT_MIRROR
	var mat := ShaderMaterial.new()
	mat.shader = Prop.LIT_SHADER
	material = mat


func set_light(light: float, warm: float) -> void:
	var mat := material as ShaderMaterial
	if mat:
		mat.set_shader_parameter("light", light)
		mat.set_shader_parameter("warm", warm)


func set_passage(a: Vector2, b: Vector2, direction: Vector2, half: float) -> void:
	end_a = a
	end_b = b
	axis = direction
	half_width = half
	queue_redraw()


func passage_length() -> float:
	return maxf((end_b - end_a).dot(axis), 0.0)


## 点在门洞通道内（含伸进两侧房间的 `reach`），且离门框至少 `margin`。
func passage_contains(map_point: Vector2, margin: float, reach: float) -> bool:
	var rel := map_point - end_a
	var s := rel.dot(axis)
	var perp := absf(rel.dot(axis.orthogonal()))
	return s >= -reach and s <= passage_length() + reach and perp <= maxf(half_width - margin, 3.0)


## 门在 `room` 一侧、往房间里退 `depth` 的点。
func mouth(room: String, depth: float) -> Vector2:
	if room == room_a:
		return end_a - axis * depth
	return end_b + axis * depth


## 相对门洞中线的横向偏移（正负表示在哪一侧）与沿通道的位置。
func lateral(map_point: Vector2) -> Vector2:
	var rel := map_point - end_a
	return Vector2(rel.dot(axis), rel.dot(axis.orthogonal()))


func _draw() -> void:
	var a := end_a - position
	var b := end_b - position
	var n := axis.orthogonal()
	var hw := half_width
	var cover := MapStyle.WALL_WIDTH * 0.5 + 1.0
	var floor_poly := PackedVector2Array(
		[a - axis * cover + n * hw, b + axis * cover + n * hw, b + axis * cover - n * hw, a - axis * cover - n * hw]
	)
	var uvs := PackedVector2Array()
	for p in floor_poly:
		uvs.append((p + position) / TEXTURE_TILE)
	draw_colored_polygon(floor_poly, MapStyle.DOOR_FLOOR_TINT, uvs, THRESHOLD)
	if passage_length() > 1.0:
		for side in [-1.0, 1.0]:
			draw_line(a + n * hw * side, b + n * hw * side, MapStyle.WALL, 4.0, true)
	for end in [a, b]:
		for side in [-1.0, 1.0]:
			var jamb: Vector2 = end + n * hw * side
			draw_rect(Rect2(jamb - Vector2(2.5, 2.5) - axis * (cover - 2.5), Vector2(5, 5)), MapStyle.WALL)
			draw_rect(Rect2(jamb - Vector2(2.5, 2.5) + axis * (cover - 2.5), Vector2(5, 5)), MapStyle.WALL)
	# 宽门洞是对开的双扇门，窄的是单扇；开着的门扇转进 room_a 一侧
	var sides := PackedFloat32Array([1.0, -1.0] if hw * 2.0 > DOUBLE_DOOR_WIDTH else [1.0])
	var length := hw * 2.0 / sides.size()
	for side in sides:
		var hinge := a + n * hw * side
		var closed := -n * side
		var dir := closed if not open else (closed * cos(OPEN_ANGLE) - axis * sin(OPEN_ANGLE))
		_draw_leaf(hinge, dir, length)


func _draw_leaf(hinge: Vector2, dir: Vector2, length: float) -> void:
	var across := dir.orthogonal() * LEAF_THICKNESS * 0.5
	var tip := hinge + dir * length
	var poly := PackedVector2Array([hinge + across, tip + across, tip - across, hinge - across])
	var uvs := PackedVector2Array()
	for p in poly:
		uvs.append(Vector2(p.dot(dir), p.dot(dir.orthogonal()) * 4.0) / TEXTURE_TILE)
	draw_colored_polygon(poly, MapStyle.DOOR_LEAF, uvs, LEAF)
	var ring := poly.duplicate()
	ring.append(poly[0])
	draw_polyline(ring, MapStyle.WALL, 1.2, true)
	draw_circle(hinge, 2.2, MapStyle.WALL)
	draw_circle(tip - dir * 4.0 + across * 1.6, 1.6, MapStyle.DOOR_KNOB)
