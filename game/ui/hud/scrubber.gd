class_name Scrubber
extends Control
## 进度条：分钟刻度、已听清台词的位置标记，拖动即 seek。

signal seek_requested(t: float)

const TRACK_HEIGHT := 3.0
const MINOR_TICK := 60.0
const MAJOR_TICK := 300.0

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
	custom_minimum_size = Vector2(200, 44)
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
	var y := size.y * 0.55
	var font := UiTheme.mono_font()
	var t := 0.0
	while t <= duration:
		var x := _time_to_x(t)
		var major := fmod(t, MAJOR_TICK) < 0.01
		draw_line(Vector2(x, y - (9.0 if major else 5.0)), Vector2(x, y - 2.0), UiTheme.LINE, 1.0)
		if major and t > 0.0:
			draw_string(
				font, Vector2(x + 3, y - 8), UiTheme.format_time(t), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, UiTheme.TEXT_DIM
			)
		t += MINOR_TICK
	draw_rect(Rect2(0, y - TRACK_HEIGHT * 0.5, size.x, TRACK_HEIGHT), Color(1, 1, 1, 0.10))
	var px := _time_to_x(time)
	draw_rect(Rect2(0, y - TRACK_HEIGHT * 0.5, px, TRACK_HEIGHT), Color(UiTheme.ACCENT, 0.85))
	for m in markers:
		var mx := _time_to_x(m.time)
		draw_rect(Rect2(mx - 1.0, y + 5.0, 2.0, 7.0), Color(m.color, 0.9))
	draw_line(Vector2(px, 2), Vector2(px, size.y - 2), UiTheme.ACCENT, 2.0)
	draw_colored_polygon(PackedVector2Array([Vector2(px - 5, 0), Vector2(px + 5, 0), Vector2(px, 6)]), UiTheme.ACCENT)
	if _hover_x >= 0.0:
		var label := UiTheme.format_time(_x_to_time(_hover_x))
		draw_line(Vector2(_hover_x, y - 8), Vector2(_hover_x, y + 8), Color(1, 1, 1, 0.4), 1.0)
		draw_string(font, Vector2(_hover_x - 30, size.y), label, HORIZONTAL_ALIGNMENT_CENTER, 60, 11, UiTheme.TEXT)
