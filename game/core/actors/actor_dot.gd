class_name ActorDot
extends Node2D
## 地图上代表一名角色的棋子。未指认时是灰色剪影，指认后换成所指认身份的头像徽章，下面挂名字缎带。

const RADIUS := 14.0
## 头像徽章比剪影大一圈，方便看清脸。
const PORTRAIT_RADIUS := 17.0
const RIPPLE_PERIOD := 1.2
const RIPPLE_REACH := 34.0
const PAWN_BG := Color(0.15, 0.16, 0.18)
const PAWN_FG := Color(0.56, 0.58, 0.61)
const CREAM := Color(0.96, 0.91, 0.80)
const SEGMENTS := 40

static var _silhouette: PackedVector2Array

var character: CharacterData
var assigned_name: String = "":
	set(value):
		assigned_name = value
		queue_redraw()
## 所指认身份的头像；为空时画剪影。
var portrait: Texture2D:
	set(value):
		portrait = value
		queue_redraw()
var selected: bool = false:
	set(value):
		selected = value
		queue_redraw()
## Acoustics.Clarity：NONE 表示没在说话（或完全听不到）。
var speaking: int = Acoustics.Clarity.NONE

var _phase: float = 0.0


func _ready() -> void:
	z_index = 5


func _process(delta: float) -> void:
	if speaking != Acoustics.Clarity.NONE or selected:
		_phase = fmod(_phase + delta, RIPPLE_PERIOD)
		queue_redraw()
	elif _phase != 0.0:
		_phase = 0.0
		queue_redraw()


func radius() -> float:
	return PORTRAIT_RADIUS if portrait else RADIUS


func _draw() -> void:
	var color := character.color if character else Color.WHITE
	var r := radius()
	if speaking != Acoustics.Clarity.NONE:
		var strength := 0.9 if speaking == Acoustics.Clarity.CLEAR else 0.35
		for k in 2:
			var p := fmod(_phase + k * RIPPLE_PERIOD * 0.5, RIPPLE_PERIOD) / RIPPLE_PERIOD
			draw_arc(
				Vector2.ZERO,
				r + p * RIPPLE_REACH,
				0,
				TAU,
				48,
				Color(color.lightened(0.3), strength * (1.0 - p)),
				2.0,
				true
			)
	draw_circle(Vector2(0, 2.5), r + 4.0, Color(0, 0, 0, 0.45))
	draw_circle(Vector2.ZERO, r + 3.0, MapStyle.INK)
	draw_circle(Vector2.ZERO, r + 2.0, color)
	if portrait:
		_draw_portrait(r)
	else:
		_draw_silhouette(r)
	draw_arc(Vector2.ZERO, r, 0, TAU, SEGMENTS, Color(MapStyle.INK, 0.8), 1.0, true)
	if selected:
		var spin := _phase / RIPPLE_PERIOD * TAU * 0.5
		for i in 4:
			var a := spin + i * TAU / 4.0
			draw_arc(Vector2.ZERO, r + 6.0, a, a + TAU / 8.0, 8, MapStyle.AMBER, 2.5, true)
	_draw_badge(r, color)
	if assigned_name != "":
		_draw_ribbon(r, color)


func _draw_silhouette(r: float) -> void:
	draw_circle(Vector2.ZERO, r, PAWN_BG)
	if _silhouette.is_empty():
		_silhouette = _make_silhouette(RADIUS)
	draw_colored_polygon(_silhouette, PAWN_FG)
	draw_circle(Vector2(0, -RADIUS * 0.12), RADIUS * 0.32, PAWN_FG)


func _draw_portrait(r: float) -> void:
	var points := PackedVector2Array()
	var uvs := PackedVector2Array()
	for i in SEGMENTS:
		var v := Vector2.from_angle(TAU * i / SEGMENTS)
		points.append(v * r)
		uvs.append(Vector2(0.5, 0.5) + v * 0.5)
	draw_colored_polygon(points, Color.WHITE, uvs, portrait)


## 编号小圆牌挂在右下，指认前后都在，方便和人物列表对照。
func _draw_badge(r: float, color: Color) -> void:
	var font := ThemeDB.fallback_font
	var label := character.label if character else "?"
	var at := Vector2(r, r) * 0.74
	var br := 7.5 if label.length() < 2 else 8.5
	draw_circle(at, br + 1.2, MapStyle.INK)
	draw_circle(at, br, color)
	var text_color := MapStyle.INK if color.get_luminance() > 0.6 else Color.WHITE
	draw_string(font, at + Vector2(-br, 4), label, HORIZONTAL_ALIGNMENT_CENTER, br * 2.0, 11, text_color)


func _draw_ribbon(r: float, color: Color) -> void:
	var font := ThemeDB.fallback_font
	var half := font.get_string_size(assigned_name, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x * 0.5 + 7.0
	var top := r + 6.0
	var h := 17.0
	var notch := 5.0
	var shape := PackedVector2Array(
		[
			Vector2(-half - notch, top),
			Vector2(half + notch, top),
			Vector2(half, top + h * 0.5),
			Vector2(half + notch, top + h),
			Vector2(-half - notch, top + h),
			Vector2(-half, top + h * 0.5),
		]
	)
	draw_colored_polygon(shape, Color(MapStyle.INK, 0.92))
	draw_line(Vector2(-half, top + 1.0), Vector2(half, top + 1.0), color, 2.0)
	draw_string(font, Vector2(-half, top + 13.5), assigned_name, HORIZONTAL_ALIGNMENT_CENTER, half * 2.0, 12, CREAM)


## 肩膀：圆盘下半部的半椭圆，裁到圆盘内。
static func _make_silhouette(r: float) -> PackedVector2Array:
	var shoulders := PackedVector2Array()
	var center := Vector2(0, r * 0.98)
	var steps := 20
	for i in steps + 1:
		var a := PI + PI * i / steps
		shoulders.append(center + Vector2(cos(a) * r * 0.66, sin(a) * r * 0.62))
	var disc := PackedVector2Array()
	for i in SEGMENTS:
		disc.append(Vector2.from_angle(TAU * i / SEGMENTS) * (r - 0.5))
	var clipped := Geometry2D.intersect_polygons(shoulders, disc)
	return clipped[0] if not clipped.is_empty() else shoulders
