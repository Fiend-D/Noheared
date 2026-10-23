class_name Game
extends Node
## 一局游戏：组装地图、时间轴、人物、声音调度和 HUD，并处理输入与存档。

signal exit_requested

const SIDE_WIDTH := 400.0
const TOP_HEIGHT := 56.0
const BOTTOM_HEIGHT := 76.0
const FIT_PADDING := 0.9
const AUTOSAVE_INTERVAL := 10.0
const ZOOM_STEP := 1.15
const ZOOM_MAX := 3.0
const CAMERA_FOLLOW := 8.0

var case_data: CaseData
var ui_theme: Theme
## 为 false 时不读写存档（测试用）。
var persist: bool = true

var clock: TimelineClock
var map: CaseMap
var actors: ActorSystem
var listener: Listener
var scheduler: CueScheduler
var transcript: Transcript
var save: SaveGame

var _world: Node2D
var _camera: Camera2D
var _floor_tabs: TabBar
var _side: SidePanel
var _bar: TimelineBar
var _subtitles: SubtitleView
var _location: Label
var _selected: ActorDot
var _autosave_left: float = AUTOSAVE_INTERVAL
var _fit_zoom: float = 1.0
var _zoom_factor: float = 1.0


func _ready() -> void:
	if persist:
		save = SaveGame.load_for(case_data.id)
	else:
		save = SaveGame.new()
		save.case_id = case_data.id
	transcript = Transcript.new()
	transcript.load_dict(save.transcript)

	clock = TimelineClock.new(case_data.duration)
	add_child(clock)

	_world = Node2D.new()
	add_child(_world)
	map = case_data.map_scene.instantiate() as CaseMap
	_world.add_child(map)
	actors = ActorSystem.new()
	_world.add_child(actors)
	actors.setup(case_data, map, clock)
	listener = Listener.new()
	_world.add_child(listener)
	listener.setup(map)
	_camera = Camera2D.new()
	_world.add_child(_camera)
	_camera.make_current()

	scheduler = CueScheduler.new()
	add_child(scheduler)
	scheduler.setup(case_data, clock, actors, listener, map.build_acoustics(), _world)
	scheduler.line_heard.connect(transcript.add_line)
	scheduler.sfx_heard.connect(transcript.add_sfx)

	_build_hud()
	listener.moved.connect(_on_listener_moved)
	listener.floor_changed.connect(_select_floor)
	_restore()
	get_viewport().size_changed.connect(_fit_camera)
	_fit_camera()


func _restore() -> void:
	for id: String in save.identities:
		_mark(StringName(id), save.identities[id])
	var floor_index := clampi(save.floor_index, 0, map.floor_count() - 1)
	_select_floor(floor_index)
	var start_room: Room = null
	var start_pos := Vector2.ZERO
	if save.has_listener_position:
		start_room = map.room_at(save.listener_position)
		start_pos = save.listener_position
	if start_room == null or not map.is_walkable(start_pos, start_room.floor_index):
		start_room = _default_room(floor_index)
		start_pos = map.nearest_walkable(start_room, start_room.get_center()) if start_room else Vector2.ZERO
	listener.place(start_pos, start_room)
	_select_floor(listener.floor_index)
	clock.seek(minf(save.time, case_data.duration))
	_update_markers()


func _default_room(floor_index: int) -> Room:
	var first_speaker: StringName = case_data.voice_lines[0].speaker if not case_data.voice_lines.is_empty() else &""
	if first_speaker != &"":
		actors.update_at(case_data.voice_lines[0].start)
		var r := actors.get_room(first_speaker)
		actors.update_at(clock.time)
		if r and r.floor_index == floor_index:
			return r
	for r in map.get_rooms():
		if r.floor_index == floor_index:
			return r
	return null


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.theme = ui_theme
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	layer.add_child(root)

	var top := PanelContainer.new()
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.offset_bottom = TOP_HEIGHT
	top.offset_right = -SIDE_WIDTH
	var top_style := UiTheme.box(UiTheme.BG, Color(0, 0, 0, 0), 12)
	top_style.set_corner_radius_all(0)
	top_style.border_color = UiTheme.LINE
	top_style.border_width_bottom = 1
	top.add_theme_stylebox_override("panel", top_style)
	root.add_child(top)
	var top_row := HBoxContainer.new()
	top_row.add_theme_constant_override("separation", 14)
	top.add_child(top_row)
	var back := Button.new()
	back.text = tr("BACK")
	back.focus_mode = Control.FOCUS_NONE
	back.pressed.connect(_exit)
	top_row.add_child(back)
	var titles := VBoxContainer.new()
	titles.add_theme_constant_override("separation", -2)
	titles.alignment = BoxContainer.ALIGNMENT_CENTER
	top_row.add_child(titles)
	var case_no := Label.new()
	case_no.text = String(case_data.id).to_upper()
	case_no.add_theme_font_override("font", UiTheme.mono_font())
	case_no.add_theme_font_size_override("font_size", 10)
	case_no.add_theme_color_override("font_color", UiTheme.ACCENT)
	titles.add_child(case_no)
	var title := Label.new()
	title.text = case_data.title
	title.add_theme_font_size_override("font_size", 19)
	titles.add_child(title)
	_floor_tabs = TabBar.new()
	_floor_tabs.focus_mode = Control.FOCUS_NONE
	_floor_tabs.clip_tabs = false
	for i in map.floor_count():
		_floor_tabs.add_tab(map.floor_name(i))
	_floor_tabs.visible = map.floor_count() > 1
	_floor_tabs.tab_changed.connect(_select_floor)
	top_row.add_child(_floor_tabs)
	var help := Label.new()
	help.text = tr("HELP_HINT")
	help.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	help.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	help.add_theme_color_override("font_color", UiTheme.TEXT_DIM)
	help.add_theme_font_size_override("font_size", 12)
	help.clip_text = true
	top_row.add_child(help)
	_location = Label.new()
	_location.add_theme_color_override("font_color", UiTheme.ACCENT)
	_location.add_theme_font_size_override("font_size", 15)
	top_row.add_child(_location)

	var side_bg := ColorRect.new()
	side_bg.color = Color(UiTheme.BG, 1.0)
	side_bg.set_anchors_and_offsets_preset(Control.PRESET_RIGHT_WIDE)
	side_bg.offset_left = -SIDE_WIDTH
	root.add_child(side_bg)

	_side = SidePanel.new()
	_side.set_anchors_and_offsets_preset(Control.PRESET_RIGHT_WIDE)
	_side.offset_left = -SIDE_WIDTH
	root.add_child(_side)
	_side.setup(case_data, transcript, save, _display_name)
	_side.seek_requested.connect(clock.seek)
	_side.identity_changed.connect(_on_identity_changed)
	_side.answers_submitted.connect(_on_submit)

	_bar = TimelineBar.new()
	_bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	_bar.offset_top = -BOTTOM_HEIGHT
	_bar.offset_right = -SIDE_WIDTH
	root.add_child(_bar)
	_bar.setup(clock)

	_subtitles = SubtitleView.new()
	_subtitles.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_subtitles.anchor_left = 0.0
	_subtitles.anchor_right = 1.0
	_subtitles.offset_left = 80
	_subtitles.offset_right = -SIDE_WIDTH - 80
	_subtitles.offset_bottom = -BOTTOM_HEIGHT - 20
	_subtitles.grow_vertical = Control.GROW_DIRECTION_BEGIN
	root.add_child(_subtitles)
	_subtitles.setup(_display_name)

	transcript.changed.connect(_update_markers)


func _display_name(character_id: StringName) -> String:
	var c := case_data.get_character(character_id)
	if c == null:
		return String(character_id)
	var base := tr("DOT_LABEL") % c.label
	var assigned := String(save.identities.get(String(character_id), ""))
	return base if assigned == "" else "%s·%s" % [base, assigned]


func _process(delta: float) -> void:
	var direction := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	listener.step(direction, Input.is_action_pressed("move_run"), delta)
	listener.modulate.a = 1.0 if listener.floor_index == map.current_floor else 0.0
	_update_camera(minf(delta * CAMERA_FOLLOW, 1.0))
	_subtitles.show_lines(scheduler.active_lines, case_data)
	_autosave_left -= delta
	if _autosave_left <= 0.0:
		_autosave_left = AUTOSAVE_INTERVAL
		_save()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_play"):
		clock.toggle()
	elif event.is_action_pressed("seek_back"):
		clock.skip(-5.0)
	elif event.is_action_pressed("seek_forward"):
		clock.skip(5.0)
	elif event.is_action_pressed("cycle_speed"):
		clock.cycle_speed()
	elif event is InputEventMouseButton and event.pressed:
		match event.button_index:
			MOUSE_BUTTON_LEFT:
				_on_map_click(_world.get_global_mouse_position())
			MOUSE_BUTTON_WHEEL_UP:
				_zoom_factor = minf(_zoom_factor * ZOOM_STEP, ZOOM_MAX)
			MOUSE_BUTTON_WHEEL_DOWN:
				_zoom_factor = maxf(_zoom_factor / ZOOM_STEP, 1.0)
			_:
				return
	else:
		return
	get_viewport().set_input_as_handled()


func _on_map_click(point: Vector2) -> void:
	var dot := actors.dot_at(point)
	if dot:
		if _selected:
			_selected.selected = false
		_selected = dot
		dot.selected = true
		_side.highlight_person(dot.character.id)
		return
	var room := map.room_at(point, &"", map.current_floor)
	if room:
		listener.walk_to(map.nearest_walkable(room, room.clamp_point(point, CaseMap.WALK_MARGIN + 4.0)), room)


func _on_listener_moved(room: Room) -> void:
	_location.text = "◉ %s" % (room.room_name if room else "—")
	map.light_from(room.room_name if room else "")


func _select_floor(index: int) -> void:
	map.show_floor(index)
	if _floor_tabs and _floor_tabs.current_tab != index:
		_floor_tabs.current_tab = index
	save.floor_index = index
	actors.update_at(clock.time)
	_fit_camera()


func _fit_camera() -> void:
	if _camera == null:
		return
	var bounds := map.get_bounds(map.current_floor)
	if bounds.size.x <= 0.0 or bounds.size.y <= 0.0:
		return
	var area := _map_area()
	_fit_zoom = minf(area.size.x / bounds.size.x, area.size.y / bounds.size.y) * FIT_PADDING
	_update_camera(1.0)


func _map_area() -> Rect2:
	var vp := get_viewport().get_visible_rect().size
	return Rect2(0, TOP_HEIGHT, vp.x - SIDE_WIDTH, vp.y - TOP_HEIGHT - BOTTOM_HEIGHT)


## 不缩放时显示整层；放大后镜头跟着监听者。`blend` 为 1 时直接到位。
func _update_camera(blend: float) -> void:
	if _camera == null:
		return
	var bounds := map.get_bounds(map.current_floor)
	var z := _fit_zoom * _zoom_factor
	var focus := bounds.get_center()
	if _zoom_factor > 1.001 and listener.floor_index == map.current_floor:
		var t := clampf((_zoom_factor - 1.0) / 0.5, 0.0, 1.0)
		focus = focus.lerp(listener.position, t)
	var vp := get_viewport().get_visible_rect().size
	var target := focus - (_map_area().get_center() - vp * 0.5) / z
	_camera.zoom = _camera.zoom.lerp(Vector2(z, z), blend)
	_camera.position = _camera.position.lerp(target, blend)


func _update_markers() -> void:
	var markers: Array[Dictionary] = []
	for i: int in transcript.heard_lines:
		var line := case_data.voice_lines[i]
		var c := case_data.get_character(line.speaker)
		markers.append({"time": line.start, "color": c.color if c else Color.WHITE})
	for i: int in transcript.heard_sfx:
		markers.append({"time": case_data.sfx_events[i].time, "color": Color(0.95, 0.8, 0.5)})
	_bar.scrubber.markers = markers


func _on_identity_changed(character_id: StringName, assigned: String) -> void:
	save.identities[String(character_id)] = assigned
	_mark(character_id, assigned)
	transcript.changed.emit()


func _mark(character_id: StringName, assigned: String) -> void:
	var dot: ActorDot = actors.dots.get(character_id)
	if dot:
		dot.assigned_name = assigned
		dot.portrait = CaseLibrary.portrait_for_name(case_data, assigned) if assigned != "" else null


func _on_submit() -> void:
	var result := Scoring.evaluate(case_data, save.identities, save.answers)
	save.best_score = maxf(save.best_score, result.score())
	_side.show_result(result)
	if result.solved() and not save.solved:
		save.solved = true
		var dialog := AcceptDialog.new()
		dialog.theme = ui_theme
		dialog.title = tr("SOLVED_TITLE")
		dialog.dialog_text = case_data.truth if case_data.truth != "" else tr("SOLVED_DEFAULT")
		dialog.dialog_autowrap = true
		dialog.min_size = Vector2i(560, 240)
		add_child(dialog)
		dialog.popup_centered()
	_save()


func _save() -> void:
	if not persist:
		return
	save.time = clock.time
	save.listener_position = listener.position
	save.has_listener_position = true
	save.transcript = transcript.to_dict()
	save.write()


func _exit() -> void:
	clock.pause()
	scheduler.release_all()
	_save()
	exit_requested.emit()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST and save != null:
		_save()
