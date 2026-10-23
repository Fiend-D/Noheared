@tool
class_name Prop
extends Node2D
## 一件家具。节点位置是贴图中心（地图坐标）。`blocks` 为 true 时监听者不能穿过它的占地范围。

const LIT_SHADER := preload("res://map/lit.gdshader")
## 占地范围相对贴图的比例：贴图是略带俯角的画法，边缘的腿和阴影不算占地。
const FOOTPRINT := 0.82

@export var prop_type: String = ""
@export var texture: Texture2D:
	set(value):
		texture = value
		queue_redraw()
@export var size: Vector2 = Vector2(32, 32):
	set(value):
		size = value
		queue_redraw()
@export var flip_h: bool = false:
	set(value):
		flip_h = value
		queue_redraw()
@export var blocks: bool = true
## 地毯：不阻挡、不画阴影。导入时排在其它家具前面，所以画在它们下面。
@export var rug: bool = false
@export var room_name: String = ""

var floor_index: int = 0


func _ready() -> void:
	var mat := ShaderMaterial.new()
	mat.shader = LIT_SHADER
	material = mat


func set_light(light: float, warm: float) -> void:
	var mat := material as ShaderMaterial
	if mat:
		mat.set_shader_parameter("light", light)
		mat.set_shader_parameter("warm", warm)


## 阻挡监听者的范围（地图坐标）。
func footprint() -> Rect2:
	var s := size * FOOTPRINT
	return Rect2(position - s * 0.5, s)


func rect() -> Rect2:
	return Rect2(position - size * 0.5, size)


func blocks_point(map_point: Vector2, margin: float) -> bool:
	return blocks and footprint().grow(margin).has_point(map_point)


func _draw() -> void:
	if texture == null:
		draw_rect(Rect2(-size * 0.5, size), Color(0.5, 0.4, 0.3, 0.6))
		return
	var r := Rect2(-size * 0.5, size)
	if not rug:
		var shadow := Vector2(2, 3)
		draw_set_transform(shadow, 0.0, Vector2(-1, 1) if flip_h else Vector2.ONE)
		draw_texture_rect(texture, r, false, Color(0, 0, 0, 0.45))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2(-1, 1) if flip_h else Vector2.ONE)
	draw_texture_rect(texture, r, false)
	draw_set_transform(Vector2.ZERO)
