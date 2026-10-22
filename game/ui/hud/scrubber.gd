class_name Scrubber
extends Control
## 进度条：显示已听清台词的位置标记，拖动即 seek。

signal seek_requested(t: float)

const TRACK_HEIGHT := 8.0

var duration: float = 1.0
var time: float = 0.0:
	set(value):
		time = value
		queue_redraw()
## [{time, color}]
var markers: Array[Dictionary] = []:
	set(value):
		markers = value
		queue_redraw()

var _dragging: bool = false
var _hover_x: float = -1.0


func _ready() -> void:
	custom_minimum_size = Vector2(200, 36)
	mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	mouse_exited.connect(
		func() -> void:
			_hover_x = -1.0
			queue_redraw()
	)


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		_dragging = event.pressed
		if event.pressed:
			_emit_seek(event.position.x)
		accept_event()
	elif event is InputEventMouseMotion:
		_hover_x = event.position.x
		if _dragging:
			_emit_seek(event.position.x)
		queue_redraw()


func _emit_seek(x: float) -> void:
	seek_requested.emit(_x_to_time(x))


func _x_to_time(x: float) -> float:
	return clampf(x / maxf(size.x, 1.0), 0.0, 1.0) * duration


func _time_to_x(t: float) -> float:
	return t / maxf(duration, 0.001) * size.x


func _draw() -> void:
	var y := size.y * 0.5
	var track := Rect2(0, y - TRACK_HEIGHT * 0.5, size.x, TRACK_HEIGHT)
	draw_rect(track, Color(1, 1, 1, 0.12))
	draw_rect(Rect2(track.position, Vector2(_time_to_x(time), TRACK_HEIGHT)), Color(UiTheme.ACCENT, 0.7))
	for m in markers:
		var x := _time_to_x(m.time)
		draw_line(Vector2(x, y - 11), Vector2(x, y + 11), Color(m.color, 0.85), 2.0)
	var px := _time_to_x(time)
	draw_circle(Vector2(px, y), 8.0, Color.WHITE)
	if _hover_x >= 0.0:
		var font := get_theme_default_font()
		var label := UiTheme.format_time(_x_to_time(_hover_x))
		draw_string(font, Vector2(_hover_x - 30, 10), label, HORIZONTAL_ALIGNMENT_CENTER, 60, 12, UiTheme.TEXT_DIM)
