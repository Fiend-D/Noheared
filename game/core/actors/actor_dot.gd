class_name ActorDot
extends Node2D
## 地图上代表一名角色的圆点。

const RADIUS := 13.0
const RIPPLE_PERIOD := 1.2
const RIPPLE_REACH := 34.0

var character: CharacterData
var assigned_name: String = "":
	set(value):
		assigned_name = value
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
	if speaking != Acoustics.Clarity.NONE:
		_phase = fmod(_phase + delta, RIPPLE_PERIOD)
		queue_redraw()
	elif _phase != 0.0:
		_phase = 0.0
		queue_redraw()


func _draw() -> void:
	var color := character.color if character else Color.WHITE
	if speaking != Acoustics.Clarity.NONE:
		var strength := 0.9 if speaking == Acoustics.Clarity.CLEAR else 0.35
		for k in 2:
			var p := fmod(_phase + k * RIPPLE_PERIOD * 0.5, RIPPLE_PERIOD) / RIPPLE_PERIOD
			draw_arc(
				Vector2.ZERO,
				RADIUS + p * RIPPLE_REACH,
				0,
				TAU,
				48,
				Color(color.lightened(0.3), strength * (1.0 - p)),
				2.0,
				true
			)
	draw_circle(Vector2.ZERO, RADIUS + 2.0, Color(0, 0, 0, 0.5))
	draw_circle(Vector2.ZERO, RADIUS, color)
	if selected:
		draw_arc(Vector2.ZERO, RADIUS + 4.0, 0, TAU, 40, Color.WHITE, 2.5, true)
	var font := ThemeDB.fallback_font
	var label := character.label if character else "?"
	var text_color := Color.BLACK if color.get_luminance() > 0.6 else Color.WHITE
	draw_string(font, Vector2(-RADIUS, 5), label, HORIZONTAL_ALIGNMENT_CENTER, RADIUS * 2, 14, text_color)
	if assigned_name != "":
		draw_string(
			font, Vector2(-60, RADIUS + 17), assigned_name, HORIZONTAL_ALIGNMENT_CENTER, 120, 13, Color(1, 1, 1, 0.9)
		)
