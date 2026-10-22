@tool
extends VBoxContainer
## 编辑器底部的“案件时间轴”面板。

signal preview_changed

const TimelineView := preload("res://addons/case_editor/timeline_view.gd")
const AUDITION_VOICES := 4
const MUFFLED_DB := -14.0

var case_data: CaseData
var preview_time: float = 0.0

var _map: CaseMap
var _acoustics: Acoustics
var _title: Label
var _time_label: Label
var _room_pick: OptionButton
var _audition: Button
var _view: TimelineView
var _issues: ItemList
var _open_dialog: EditorFileDialog
var _players: Array[AudioStreamPlayer] = []
var _playing_lines: Dictionary = {}
var _dirty: bool = false


func _ready() -> void:
	custom_minimum_size = Vector2(0, 260)
	var bar := HBoxContainer.new()
	add_child(bar)
	bar.add_child(_button("打开案件…", _ask_open))
	bar.add_child(_button("保存", save))
	bar.add_child(_button("校验", validate))
	_title = Label.new()
	_title.text = "未打开案件（在文件系统中选中 case.tres 即可）"
	bar.add_child(_title)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.add_child(spacer)
	bar.add_child(_label("监听房间"))
	_room_pick = OptionButton.new()
	_room_pick.custom_minimum_size.x = 140
	bar.add_child(_room_pick)
	_audition = _button("▶ 试听", _toggle_audition)
	_audition.toggle_mode = true
	bar.add_child(_audition)
	_time_label = _label("00:00")
	_time_label.custom_minimum_size.x = 60
	bar.add_child(_time_label)
	bar.add_child(_label("Ctrl+滚轮缩放"))

	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(split)
	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	split.add_child(scroll)
	_view = TimelineView.new()
	_view.preview_requested.connect(set_preview_time)
	_view.item_selected.connect(func(r: Resource) -> void: EditorInterface.inspect_object(r, "", true))
	_view.data_changed.connect(_on_data_changed)
	scroll.add_child(_view)
	_issues = ItemList.new()
	_issues.custom_minimum_size.x = 340
	split.add_child(_issues)

	for i in AUDITION_VOICES:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_players.append(p)
	set_process(false)


func load_case(data: CaseData) -> void:
	_stop_audition()
	case_data = data
	if _map:
		_map.free()
	_map = data.map_scene.instantiate() as CaseMap if data.map_scene else null
	_acoustics = _map.build_acoustics() if _map else null
	_room_pick.clear()
	if _map:
		for r in _map.get_rooms():
			_room_pick.add_item(r.room_name)
	_title.text = "%s（%s）" % [data.title, data.resource_path]
	_view.set_case(data)
	_dirty = false
	set_preview_time(0.0)
	validate()


func set_preview_time(t: float) -> void:
	preview_time = clampf(t, 0.0, case_data.duration if case_data else 0.0)
	_view.preview_time = preview_time
	_time_label.text = UiTheme.format_time(preview_time)
	if _audition.button_pressed:
		_stop_voices()
	preview_changed.emit()


func save() -> void:
	if case_data == null or case_data.resource_path == "":
		return
	for c in case_data.characters:
		TrackMath.sort_track(c.track)
	case_data.sort_voice_lines()
	var err := ResourceSaver.save(case_data)
	if err == OK:
		_dirty = false
		_title.text = "%s（%s）" % [case_data.title, case_data.resource_path]
	else:
		push_error("保存失败：%s" % error_string(err))


func validate() -> void:
	_issues.clear()
	if case_data == null:
		return
	var issues := CaseValidator.validate(case_data, _map)
	if issues.is_empty():
		_issues.add_item("✓ 没有发现问题")
	for issue in issues:
		var idx := _issues.add_item(issue)
		_issues.set_item_custom_fg_color(idx, Color(1, 0.5, 0.5) if issue.begins_with("ERROR") else Color(1, 0.85, 0.4))


func _on_data_changed() -> void:
	_dirty = true
	_title.text = "%s（%s）*" % [case_data.title, case_data.resource_path]
	preview_changed.emit()


## 试听：从预览时刻开始推进时间，按所选监听房间判断每句台词是清楚、发闷还是听不到。
func _toggle_audition() -> void:
	if _audition.button_pressed and case_data and _map:
		set_process(true)
	else:
		_stop_audition()


func _stop_audition() -> void:
	set_process(false)
	if _audition:
		_audition.button_pressed = false
	_stop_voices()


func _stop_voices() -> void:
	for p in _players:
		p.stop()
	_playing_lines.clear()


func _process(delta: float) -> void:
	preview_time = minf(preview_time + delta, case_data.duration)
	_view.preview_time = preview_time
	_time_label.text = UiTheme.format_time(preview_time)
	preview_changed.emit()
	var listener_room := StringName(_room_pick.get_item_text(_room_pick.selected)) if _room_pick.selected >= 0 else &""
	var active := CueScheduler.active_line_indices(case_data.voice_lines, preview_time)
	for i: int in _playing_lines.keys():
		if not active.has(i):
			(_playing_lines[i] as AudioStreamPlayer).stop()
			_playing_lines.erase(i)
	for i in active:
		var line := case_data.voice_lines[i]
		if line.stream == null or _playing_lines.has(i):
			continue
		var c := case_data.get_character(line.speaker)
		if c == null:
			continue
		var room := _map.room_for_pose(c, TrackMath.sample(c.track, preview_time))
		var result := _acoustics.resolve(listener_room, StringName(room.room_name) if room else &"", line.loudness)
		if not result.audible():
			continue
		var player := _free_player()
		if player == null:
			continue
		player.stream = line.stream
		player.volume_db = (
			line.volume_db + (0.0 if result.clarity == Acoustics.Clarity.CLEAR else MUFFLED_DB + result.gain_db)
		)
		player.play(preview_time - line.start)
		_playing_lines[i] = player
	if preview_time >= case_data.duration:
		_stop_audition()


func _free_player() -> AudioStreamPlayer:
	for p in _players:
		if not p.playing:
			return p
	return null


func _ask_open() -> void:
	if _open_dialog == null:
		_open_dialog = EditorFileDialog.new()
		_open_dialog.file_mode = EditorFileDialog.FILE_MODE_OPEN_FILE
		_open_dialog.access = EditorFileDialog.ACCESS_RESOURCES
		_open_dialog.filters = PackedStringArray(["*.tres ; 案件资源"])
		_open_dialog.file_selected.connect(func(path: String) -> void: load_case(load(path)))
		add_child(_open_dialog)
	_open_dialog.popup_file_dialog()


func _button(text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.pressed.connect(cb)
	return b


func _label(text: String) -> Label:
	var l := Label.new()
	l.text = text
	return l


func _exit_tree() -> void:
	if _map:
		_map.free()
		_map = null
