@tool
extends Control
## 时间轴绘制与交互：每个角色一行，上半行是台词块，下半行是关键帧。
## 拖动台词块修改开始时间，拖动关键帧修改时间（限制在相邻关键帧之间），点击空白处设置预览时刻。

signal preview_requested(t: float)
signal item_selected(resource: Resource)
signal data_changed

const RULER_HEIGHT := 24.0
const ROW_HEIGHT := 40.0
const LABEL_WIDTH := 110.0
const KEY_SIZE := 6.0
const SNAP := 0.1

var case_data: CaseData
var pixels_per_second: float = 8.0:
	set(value):
		pixels_per_second = clampf(value, 0.5, 200.0)
		_update_size()
var preview_time: float = 0.0:
	set(value):
		preview_time = value
		queue_redraw()

var _selected: Resource
var _drag: Resource
var _drag_origin_x: float = 0.0
var _drag_origin_time: float = 0.0
var _drag_min: float = 0.0
var _drag_max: float = 0.0


func set_case(data: CaseData) -> void:
	case_data = data
	_selected = null
	_update_size()


func _update_size() -> void:
	var rows := case_data.characters.size() if case_data else 0
	var duration := case_data.duration if case_data else 0.0
	custom_minimum_size = Vector2(LABEL_WIDTH + duration * pixels_per_second + 40, RULER_HEIGHT + rows * ROW_HEIGHT + 8)
	queue_redraw()


func time_to_x(t: float) -> float:
	return LABEL_WIDTH + t * pixels_per_second


func x_to_time(x: float) -> float:
	return maxf((x - LABEL_WIDTH) / pixels_per_second, 0.0)


func _row_y(index: int) -> float:
	return RULER_HEIGHT + index * ROW_HEIGHT


func _row_of(speaker: StringName) -> int:
	for i in case_data.characters.size():
		if case_data.characters[i].id == speaker:
			return i
	return -1


func _line_rect(line: VoiceLine) -> Rect2:
	var row := _row_of(line.speaker)
	return Rect2(
		time_to_x(line.start), _row_y(row) + 3, maxf(line.duration * pixels_per_second, 3.0), ROW_HEIGHT * 0.5 - 4
	)


func _key_center(row: int, key: TrackKey) -> Vector2:
	return Vector2(time_to_x(key.time), _row_y(row) + ROW_HEIGHT * 0.75)


func _hit(pos: Vector2) -> Resource:
	for i in case_data.characters.size():
		for key in case_data.characters[i].track:
			if _key_center(i, key).distance_to(pos) <= KEY_SIZE + 2:
				return key
	for line in case_data.voice_lines:
		if _line_rect(line).has_point(pos):
			return line
	return null


func _gui_input(event: InputEvent) -> void:
	if case_data == null:
		return
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.ctrl_pressed:
			pixels_per_second *= 1.2
			accept_event()
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.ctrl_pressed:
			pixels_per_second /= 1.2
			accept_event()
		elif mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_press(mb.position)
			elif _drag:
				_drag = null
				data_changed.emit()
			accept_event()
	elif event is InputEventMouseMotion and _drag:
		_drag_to((event as InputEventMouseMotion).position.x)
		accept_event()


func _press(pos: Vector2) -> void:
	var hit := _hit(pos)
	if hit == null:
		preview_requested.emit(x_to_time(pos.x))
		return
	_selected = hit
	item_selected.emit(hit)
	_drag = hit
	_drag_origin_x = pos.x
	if hit is VoiceLine:
		_drag_origin_time = hit.start
		_drag_min = 0.0
		_drag_max = maxf(case_data.duration - hit.duration, 0.0)
	else:
		var key := hit as TrackKey
		_drag_origin_time = key.time
		_drag_min = 0.0
		_drag_max = case_data.duration
		for c in case_data.characters:
			var i := c.track.find(key)
			if i >= 0:
				if i > 0:
					_drag_min = c.track[i - 1].time
				if i < c.track.size() - 1:
					_drag_max = c.track[i + 1].time
	queue_redraw()


func _drag_to(x: float) -> void:
	var t := _drag_origin_time + (x - _drag_origin_x) / pixels_per_second
	t = clampf(snappedf(t, SNAP), _drag_min, _drag_max)
	if _drag is VoiceLine:
		_drag.start = t
	elif _drag is TrackKey:
		_drag.time = t
	queue_redraw()


func _draw() -> void:
	if case_data == null:
		return
	var font := get_theme_default_font()
	var dim := Color(1, 1, 1, 0.45)
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.08, 0.10, 0.14))
	var step := _ruler_step()
	var t := 0.0
	while t <= case_data.duration:
		var x := time_to_x(t)
		draw_line(Vector2(x, RULER_HEIGHT - 8), Vector2(x, size.y), Color(1, 1, 1, 0.07))
		draw_string(font, Vector2(x + 3, 15), UiTheme.format_time(t), HORIZONTAL_ALIGNMENT_LEFT, -1, 11, dim)
		t += step

	for i in case_data.characters.size():
		var c := case_data.characters[i]
		var y := _row_y(i)
		draw_line(Vector2(0, y), Vector2(size.x, y), Color(1, 1, 1, 0.08))
		draw_rect(Rect2(0, y, LABEL_WIDTH - 4, ROW_HEIGHT), Color(c.color, 0.25))
		draw_string(
			font,
			Vector2(6, y + 24),
			"%s %s" % [c.label, c.display_name],
			HORIZONTAL_ALIGNMENT_LEFT,
			LABEL_WIDTH - 10,
			13,
			Color.WHITE
		)
		for k in c.track.size():
			var key := c.track[k]
			var center := _key_center(i, key)
			if k < c.track.size() - 1 and not key.position.is_equal_approx(c.track[k + 1].position):
				var next_x := time_to_x(c.track[k + 1].time)
				var move_color := (
					Color(1.0, 0.6, 0.3, 0.5) if key.movement == TrackKey.Movement.RUN else Color(c.color, 0.5)
				)
				draw_line(center, Vector2(next_x, center.y), move_color, 3.0)
			var diamond := PackedVector2Array(
				[
					center + Vector2(0, -KEY_SIZE),
					center + Vector2(KEY_SIZE, 0),
					center + Vector2(0, KEY_SIZE),
					center + Vector2(-KEY_SIZE, 0)
				]
			)
			draw_colored_polygon(diamond, Color.WHITE if key == _selected else c.color.lightened(0.3))

	for line in case_data.voice_lines:
		var row := _row_of(line.speaker)
		if row < 0:
			continue
		var c := case_data.characters[row]
		var rect := _line_rect(line)
		var fill := Color(c.color, 0.85) if line.stream else Color(c.color, 0.35)
		draw_rect(rect, fill)
		if line == _selected:
			draw_rect(rect, Color.WHITE, false, 2.0)
		if rect.size.x > 30:
			draw_string(
				font,
				rect.position + Vector2(3, 12),
				line.text,
				HORIZONTAL_ALIGNMENT_LEFT,
				rect.size.x - 6,
				11,
				Color.WHITE
			)

	var px := time_to_x(preview_time)
	draw_line(Vector2(px, 0), Vector2(px, size.y), Color(1.0, 0.85, 0.3), 2.0)


func _ruler_step() -> float:
	for s in [1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]:
		if s * pixels_per_second >= 70.0:
			return s
	return 600.0
