class_name TimelineBar
extends PanelContainer
## 底部播放控制条。

const SKIP_SECONDS := 10.0

var clock: TimelineClock
var scrubber: Scrubber

var _play: Button
var _speed: Button
var _time_label: Label


func setup(timeline: TimelineClock) -> void:
	clock = timeline
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	add_child(row)

	row.add_child(_button("⏪ 10", func() -> void: clock.skip(-SKIP_SECONDS)))
	_play = _button("", func() -> void: clock.toggle())
	_play.custom_minimum_size.x = 110
	row.add_child(_play)
	row.add_child(_button("10 ⏩", func() -> void: clock.skip(SKIP_SECONDS)))
	_speed = _button("", func() -> void: clock.cycle_speed())
	_speed.custom_minimum_size.x = 110
	row.add_child(_speed)

	_time_label = Label.new()
	_time_label.custom_minimum_size.x = 130
	_time_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	row.add_child(_time_label)

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


func _button(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.pressed.connect(cb)
	return b


func _on_time(t: float) -> void:
	scrubber.time = t
	_time_label.text = "%s / %s" % [UiTheme.format_time(t), UiTheme.format_time(clock.duration)]


func _on_playing(is_playing: bool) -> void:
	_play.text = tr("PAUSE") if is_playing else tr("PLAY")


func _on_speed(s: float) -> void:
	_speed.text = tr("SPEED") % String.num(s, 2).trim_suffix(".0")
