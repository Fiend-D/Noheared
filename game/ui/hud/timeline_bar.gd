class_name TimelineBar
extends PanelContainer
## 底部播放控制条：倒退 / 播放 / 快进 / 倍速、时间码和进度条。

const SKIP_SECONDS := 10.0

var clock: TimelineClock
var scrubber: Scrubber

var _play: Button
var _speed: Button
var _time_label: Label
var _total_label: Label


func setup(timeline: TimelineClock) -> void:
	clock = timeline
	var style := UiTheme.box(UiTheme.BG, Color(0, 0, 0, 0), 14)
	style.border_color = UiTheme.LINE
	style.border_width_top = 1
	style.set_corner_radius_all(0)
	add_theme_stylebox_override("panel", style)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	add_child(row)

	row.add_child(_button("⟲ %d" % int(SKIP_SECONDS), func() -> void: clock.skip(-SKIP_SECONDS), 64))
	_play = _button("", func() -> void: clock.toggle(), 48)
	_play.custom_minimum_size.y = 48
	_play.add_theme_font_size_override("font_size", 20)
	for state in ["normal", "hover", "pressed"]:
		var sb := UiTheme.box(
			UiTheme.ACCENT if state == "pressed" else Color(UiTheme.ACCENT, 0.12 if state == "normal" else 0.25),
			UiTheme.ACCENT
		)
		sb.set_corner_radius_all(24)
		_play.add_theme_stylebox_override(state, sb)
	_play.add_theme_color_override("font_color", UiTheme.ACCENT)
	row.add_child(_play)
	row.add_child(_button("%d ⟳" % int(SKIP_SECONDS), func() -> void: clock.skip(SKIP_SECONDS), 64))
	_speed = _button("", func() -> void: clock.cycle_speed(), 64)
	_speed.add_theme_font_override("font", UiTheme.mono_font())
	row.add_child(_speed)

	var times := VBoxContainer.new()
	times.alignment = BoxContainer.ALIGNMENT_CENTER
	times.add_theme_constant_override("separation", -4)
	times.custom_minimum_size.x = 110
	row.add_child(times)
	_time_label = Label.new()
	_time_label.add_theme_font_override("font", UiTheme.mono_font())
	_time_label.add_theme_font_size_override("font_size", 28)
	_time_label.add_theme_color_override("font_color", UiTheme.TEXT)
	times.add_child(_time_label)
	_total_label = Label.new()
	_total_label.add_theme_font_override("font", UiTheme.mono_font())
	_total_label.add_theme_font_size_override("font_size", 12)
	_total_label.add_theme_color_override("font_color", UiTheme.TEXT_DIM)
	_total_label.text = "/ " + UiTheme.format_time(clock.duration)
	times.add_child(_total_label)

	scrubber = Scrubber.new()
	scrubber.duration = clock.duration
	scrubber.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scrubber.seek_requested.connect(clock.seek)
	row.add_child(scrubber)

	clock.time_changed.connect(_on_time)
	clock.playing_changed.connect(_on_playing)
	clock.speed_changed.connect(_on_speed)
	_on_time(clock.time)
	_on_playing(clock.playing)
	_on_speed(clock.speed)


func _button(text: String, cb: Callable, width: float) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = Vector2(width, 36)
	b.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	b.pressed.connect(cb)
	return b


func _on_time(t: float) -> void:
	scrubber.time = t
	_time_label.text = UiTheme.format_time(t)


func _on_playing(is_playing: bool) -> void:
	_play.text = "❚❚" if is_playing else "▶"
	_play.tooltip_text = tr("PAUSE") if is_playing else tr("PLAY")


func _on_speed(s: float) -> void:
	_speed.text = "×" + String.num(s, 2).trim_suffix(".0")
	_speed.tooltip_text = tr("SPEED") % String.num(s, 2).trim_suffix(".0")
