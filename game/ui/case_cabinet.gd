class_name CaseCabinet
extends Control
## 档案室：拉开的抽屉里竖着一排案卷。后面的只露出标签，最前面一份露出正面（名字和海报）；
## 滚轮 / 方向键翻阅，点击标签直接翻到那一份，点击最前面的档案把它取出、展开成卷宗。

signal case_chosen(path: String)
signal back_requested

const DESK := preload("res://art/title/desk.jpg")
const PHOTO_DIR := "res://art/title/photo_%s.png"
## 界面按这个尺寸排版，再整体缩放到窗口。
const STAGE := Vector2(1600, 1000)
const FILE_SIZE := Vector2(820, 600)
const FILE_X := (1600.0 - 820.0) * 0.5
const FRONT_Y := 400.0
## 每往后一份，档案上移这么多，露出标签。
const STEP := 50.0
const MAX_DEPTH := 6
const DRAWER_Y := 850.0
const TAB_SIZE := Vector2(236, 46)
const SLIDE := 0.28
const MANILA := Color(0.84, 0.72, 0.50)
const MANILA_DARK := Color(0.58, 0.46, 0.29)
const PAPER := Color(0.96, 0.93, 0.86)
const INK := Color(0.20, 0.13, 0.08)
const INK_SOFT := Color(0.36, 0.27, 0.18)
const STAMP := Color(0.64, 0.12, 0.10)
const CREAM := Color(0.95, 0.89, 0.76)
const STEEL := Color(0.21, 0.25, 0.23)

## 回到档案室时停在上次看的那一份。
static var _last_front := 0

var _stage: Control
var _shelf: Control
var _counter: Label
var _paths: PackedStringArray = []
var _cases: Array[CaseData] = []
var _files: Array[Control] = []
var _bodies: Array[Control] = []
var _tabs: Array[Control] = []
var _faces: Array[Control] = []
var _front := 0
var _lifted := false
var _dossier: Control


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := TextureRect.new()
	bg.texture = DESK
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.modulate = Color(0.32, 0.29, 0.27)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)
	var vignette := TextureRect.new()
	var gradient := GradientTexture2D.new()
	gradient.fill = GradientTexture2D.FILL_RADIAL
	gradient.fill_from = Vector2(0.5, 0.55)
	gradient.fill_to = Vector2(1.1, 1.1)
	gradient.gradient = Gradient.new()
	gradient.gradient.set_color(0, Color(0, 0, 0, 0))
	gradient.gradient.set_color(1, Color(0, 0, 0, 0.85))
	vignette.texture = gradient
	vignette.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(vignette)

	_stage = Control.new()
	_stage.size = STAGE
	_stage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_stage)
	_build_frame()
	_shelf = Control.new()
	_shelf.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stage.add_child(_shelf)
	for path in CaseLibrary.list_case_paths():
		var data := CaseLibrary.load_case(path)
		if data:
			_paths.append(path)
			_cases.append(data)
			_files.append(_make_file(_cases.size() - 1))
			_shelf.add_child(_files[-1])
	_build_drawer_front()
	if _files.is_empty():
		_stage.add_child(_text(tr("CASE_NONE"), Vector2(FILE_X, 420), FILE_SIZE.x, 22, CREAM, UiTheme.serif_font()))
	_front = clampi(_last_front, 0, maxi(_files.size() - 1, 0))
	_arrange(false)
	resized.connect(_fit)
	_fit()


func _fit() -> void:
	var s := minf(size.x / STAGE.x, size.y / STAGE.y)
	_stage.scale = Vector2(s, s)
	_stage.position = (size - STAGE * s) * 0.5


func _input(event: InputEvent) -> void:
	if _dossier:
		if event.is_action_pressed("ui_cancel"):
			_close()
		elif event.is_action_pressed("ui_accept"):
			case_chosen.emit(_paths[_front])
		else:
			return
		get_viewport().set_input_as_handled()
		return
	var step := 0
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			step = 1
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
			step = -1
	elif event.is_action_pressed("ui_right") or event.is_action_pressed("ui_down"):
		step = 1
	elif event.is_action_pressed("ui_left") or event.is_action_pressed("ui_up"):
		step = -1
	elif event.is_action_pressed("ui_accept"):
		_open(_front)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("ui_cancel"):
		back_requested.emit()
		get_viewport().set_input_as_handled()
	if step != 0:
		_flip_to(_front + step)
		get_viewport().set_input_as_handled()


func _build_frame() -> void:
	var serif := UiTheme.serif_font()
	_stage.add_child(_text(tr("CABINET_TITLE"), Vector2(64, 56), 300, 46, CREAM, serif))
	_stage.add_child(_text(tr("CABINET_HINT"), Vector2(66, 124), 250, 16, Color(CREAM, 0.55), serif, 4))
	var back := TitleScreen.menu_item(tr("BACK_MENU"), back_requested.emit, 26)
	back.position = Vector2(52, 900)
	_stage.add_child(back)
	_counter = _text("", Vector2(1330, 912), 220, 22, Color(CREAM, 0.7), UiTheme.mono_font())
	_counter.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_stage.add_child(_counter)
	var well := Panel.new()
	well.position = Vector2(FILE_X - 44, 24)
	well.size = Vector2(FILE_SIZE.x + 88, DRAWER_Y)
	var style := _box(Color(0.05, 0.05, 0.05, 0.8), STEEL.darkened(0.3), 6)
	style.border_width_left = 14
	style.border_width_right = 14
	style.border_width_top = 6
	style.corner_radius_bottom_left = 0
	style.corner_radius_bottom_right = 0
	well.add_theme_stylebox_override("panel", style)
	well.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stage.add_child(well)


func _build_drawer_front() -> void:
	var front := Panel.new()
	front.position = Vector2(FILE_X - 76, DRAWER_Y)
	front.size = Vector2(FILE_SIZE.x + 152, STAGE.y - DRAWER_Y + 80)
	var style := _box(STEEL, STEEL.lightened(0.25), 8)
	style.border_width_left = 0
	style.border_width_right = 0
	style.border_width_bottom = 0
	style.border_width_top = 4
	style.shadow_color = Color(0, 0, 0, 0.6)
	style.shadow_size = 18
	style.shadow_offset = Vector2(0, -6)
	front.add_theme_stylebox_override("panel", style)
	_stage.add_child(front)
	var holder := Panel.new()
	holder.size = Vector2(280, 54)
	holder.position = Vector2((front.size.x - holder.size.x) * 0.5, 22)
	holder.add_theme_stylebox_override("panel", _box(PAPER, Color(0.66, 0.55, 0.30), 3, 3))
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	front.add_child(holder)
	var label := _text(tr("CABINET_LABEL"), Vector2(0, 12), holder.size.x, 22, INK, UiTheme.serif_font())
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	holder.add_child(label)
	var handle := Panel.new()
	handle.size = Vector2(200, 22)
	handle.position = Vector2((front.size.x - handle.size.x) * 0.5, 96)
	var grip := _box(Color(0.10, 0.11, 0.10), STEEL.lightened(0.35), 11)
	grip.border_width_left = 0
	grip.border_width_right = 0
	grip.border_width_bottom = 0
	grip.border_width_top = 2
	handle.add_theme_stylebox_override("panel", grip)
	handle.mouse_filter = Control.MOUSE_FILTER_IGNORE
	front.add_child(handle)


func _make_file(index: int) -> Control:
	var data := _cases[index]
	var number := index + 1
	var root := Control.new()
	root.size = FILE_SIZE
	root.pivot_offset = Vector2(FILE_SIZE.x * 0.5, 0)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var save := SaveGame.load_for(data.id)
	var serif := UiTheme.serif_font()
	var mono := UiTheme.mono_font()

	var tab := Panel.new()
	tab.size = TAB_SIZE
	tab.position = Vector2(24 + (index % 3) * (FILE_SIZE.x - 48 - TAB_SIZE.x) * 0.5, 2 - TAB_SIZE.y)
	var tab_style := _box(MANILA, MANILA_DARK, 0, 1)
	tab_style.corner_radius_top_left = 10
	tab_style.corner_radius_top_right = 10
	tab_style.border_width_bottom = 0
	tab.add_theme_stylebox_override("panel", tab_style)
	tab.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	root.add_child(tab)
	var tab_label := _text("%02d  %s" % [number, data.title], Vector2(16, 9), TAB_SIZE.x - 32, 20, INK, serif, 1)
	tab.add_child(tab_label)
	if save.solved:
		tab_label.size.x -= 44
		var mark := _text(tr("CASE_STAMP"), Vector2(TAB_SIZE.x - 62, 13), 52, 14, STAMP, serif)
		mark.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		tab.add_child(mark)

	var body := Panel.new()
	body.size = FILE_SIZE
	var body_style := _box(MANILA, MANILA_DARK, 4, 1)
	body_style.shadow_color = Color(0, 0, 0, 0.45)
	body_style.shadow_size = 14
	body_style.shadow_offset = Vector2(0, -4)
	body.add_theme_stylebox_override("panel", body_style)
	body.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	root.add_child(body)
	# 正面内容只在最前面那份上显示，后面的档案只露出空白的封皮和标签。
	var face := Control.new()
	face.size = FILE_SIZE
	face.mouse_filter = Control.MOUSE_FILTER_IGNORE
	body.add_child(face)
	var frame := _photo(_poster(data), Vector2(316, 416), 8)
	frame.position = Vector2(40, 30)
	frame.rotation_degrees = -1.2
	face.add_child(frame)

	var x := 396.0
	face.add_child(_text(tr("CASE_FILE") % number, Vector2(x, 38), 380, 18, INK_SOFT, mono))
	face.add_child(_text(data.title, Vector2(x, 70), 390, 46, INK, serif, 2))
	var rule := ColorRect.new()
	rule.color = Color(INK, 0.35)
	rule.position = Vector2(x, 200)
	rule.size = Vector2(370, 2)
	rule.mouse_filter = Control.MOUSE_FILTER_IGNORE
	face.add_child(rule)
	var info := (
		"%s\n%s"
		% [tr("CASE_DURATION") % UiTheme.format_time(data.duration), tr("CASE_CHARACTERS") % data.characters.size()]
	)
	if save.best_score > 0.0:
		info += "\n" + tr("CASE_BEST") % int(round(save.best_score * 100.0))
	face.add_child(_text(info, Vector2(x, 218), 370, 17, INK_SOFT, mono))
	face.add_child(_text(tr("CABINET_OPEN"), Vector2(x, 396), 370, 22, Color(STAMP, 0.85), serif))
	if save.solved:
		var stamp := _stamp()
		stamp.position = Vector2(600, 300)
		face.add_child(stamp)

	tab.gui_input.connect(func(event: InputEvent) -> void: _on_click(event, index))
	body.gui_input.connect(func(event: InputEvent) -> void: _on_click(event, index))
	tab.mouse_entered.connect(func() -> void: tab.self_modulate = Color(1.12, 1.08, 1.0))
	tab.mouse_exited.connect(func() -> void: tab.self_modulate = Color.WHITE)
	body.mouse_entered.connect(func() -> void: _lift(index, true))
	body.mouse_exited.connect(func() -> void: _lift(index, false))
	_bodies.append(body)
	_tabs.append(tab)
	_faces.append(face)
	return root


func _on_click(event: InputEvent, index: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if index == _front:
			_open(index)
		else:
			_flip_to(index)


func _lift(index: int, on: bool) -> void:
	if index == _front and _dossier == null and _lifted != on:
		_lifted = on
		_arrange(true)


func _flip_to(index: int) -> void:
	index = clampi(index, 0, _files.size() - 1)
	if index == _front or _files.is_empty():
		return
	_front = index
	_lifted = false
	_arrange(true)


## 按与最前面那份的距离摆放每份档案；翻过去的落到抽屉面板后面。
func _arrange(animate: bool) -> void:
	for i in _files.size():
		var d := i - _front
		var pos := Vector2(FILE_X, FRONT_Y - d * STEP)
		var s := 1.0 - 0.022 * d
		var shade := 1.0 - 0.085 * d
		var alpha := 1.0
		if d < 0:
			pos.y = DRAWER_Y + 40
			s = 1.0
			shade = 1.0
			alpha = 0.0
		elif d > MAX_DEPTH:
			pos.y = FRONT_Y - (MAX_DEPTH + 1) * STEP
			s = 1.0 - 0.022 * (MAX_DEPTH + 1)
			shade = 0.4
			alpha = 0.0
		elif d == 0 and _lifted:
			pos.y -= 14
		_bodies[i].mouse_filter = Control.MOUSE_FILTER_STOP if d == 0 else Control.MOUSE_FILTER_IGNORE
		_tabs[i].mouse_filter = (
			Control.MOUSE_FILTER_STOP if d >= 0 and d <= MAX_DEPTH else Control.MOUSE_FILTER_IGNORE
		)
		_place(_files[i], pos, Vector2(s, s), Color(shade, shade, shade * 0.96, alpha), animate)
		var face_alpha := 1.0 if d <= 0 else 0.0
		if animate:
			_faces[i].create_tween().tween_property(_faces[i], "modulate:a", face_alpha, SLIDE)
		else:
			_faces[i].modulate.a = face_alpha
	var order := range(_files.size())
	order.sort_custom(func(a: int, b: int) -> bool: return _rank(a) < _rank(b))
	for k in order.size():
		_shelf.move_child(_files[order[k]], k)
	if not _files.is_empty():
		_counter.text = "%02d / %02d" % [_front + 1, _files.size()]
	_last_front = _front


## 绘制顺序：最深的先画，最前面的后画，翻过去的压在最上面（它们正往下落）。
func _rank(i: int) -> int:
	var d := i - _front
	return -d if d >= 0 else 100 - d


func _place(node: Control, pos: Vector2, s: Vector2, color: Color, animate: bool) -> void:
	if node.has_meta("tween"):
		(node.get_meta("tween") as Tween).kill()
	if not animate:
		node.position = pos
		node.scale = s
		node.modulate = color
		return
	var t := node.create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(node, "position", pos, SLIDE)
	t.tween_property(node, "scale", s, SLIDE)
	t.tween_property(node, "modulate", color, SLIDE)
	node.set_meta("tween", t)


func _open(index: int) -> void:
	if _dossier or index != _front or _files.is_empty():
		return
	var file := _files[index]
	_place(file, file.position - Vector2(0, 220), file.scale, Color(1, 1, 1, 0), true)
	_dossier = _make_dossier(index)
	_dossier.modulate.a = 0.0
	_dossier.scale = Vector2.ONE * 0.95
	_stage.add_child(_dossier)
	var t := _dossier.create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(_dossier, "modulate:a", 1.0, 0.25).set_delay(0.1)
	t.tween_property(_dossier, "scale", Vector2.ONE, 0.3).set_delay(0.1)


func _close() -> void:
	if _dossier == null:
		return
	var old := _dossier
	_dossier = null
	old.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var t := old.create_tween().set_parallel().set_trans(Tween.TRANS_CUBIC)
	t.tween_property(old, "modulate:a", 0.0, 0.18)
	t.tween_property(old, "scale", Vector2.ONE * 0.95, 0.18)
	t.chain().tween_callback(old.queue_free)
	_lifted = false
	_arrange(true)


## 取出的档案摊开：左页贴着海报，右页是案情说明、涉案人物和开始按钮。
func _make_dossier(index: int) -> Control:
	var data := _cases[index]
	var save := SaveGame.load_for(data.id)
	var serif := UiTheme.serif_font()
	var mono := UiTheme.mono_font()
	var root := Control.new()
	root.size = STAGE
	root.pivot_offset = STAGE * 0.5
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.62)
	dim.position = -STAGE
	dim.size = STAGE * 3.0
	dim.gui_input.connect(
		func(event: InputEvent) -> void:
			if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
				_close()
	)
	root.add_child(dim)

	var folder := Panel.new()
	folder.position = Vector2(110, 60)
	folder.size = Vector2(1380, 880)
	var folder_style := _box(MANILA, MANILA_DARK, 6, 2)
	folder_style.shadow_color = Color(0, 0, 0, 0.6)
	folder_style.shadow_size = 30
	folder_style.shadow_offset = Vector2(0, 10)
	folder.add_theme_stylebox_override("panel", folder_style)
	root.add_child(folder)
	var fold := ColorRect.new()
	fold.color = Color(MANILA_DARK, 0.7)
	fold.position = Vector2(folder.size.x * 0.5 - 1, 0)
	fold.size = Vector2(2, folder.size.y)
	fold.mouse_filter = Control.MOUSE_FILTER_IGNORE
	folder.add_child(fold)

	var poster := _photo(_poster(data), Vector2(468, 624), 12)
	poster.position = Vector2(110, 96)
	poster.rotation_degrees = -2.0
	folder.add_child(poster)
	var caption := _text(tr("CASE_FILE") % (index + 1), Vector2(110, 790), 468, 18, INK_SOFT, mono)
	caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	folder.add_child(caption)

	var sheet := Panel.new()
	sheet.position = Vector2(730, 34)
	sheet.size = Vector2(610, 812)
	var sheet_style := _box(PAPER, Color(0.80, 0.74, 0.62), 2, 1)
	sheet_style.shadow_color = Color(0, 0, 0, 0.3)
	sheet_style.shadow_size = 8
	sheet_style.shadow_offset = Vector2(3, 4)
	sheet.add_theme_stylebox_override("panel", sheet_style)
	sheet.mouse_filter = Control.MOUSE_FILTER_IGNORE
	folder.add_child(sheet)
	var col := VBoxContainer.new()
	col.position = Vector2(46, 40)
	col.size = sheet.size - Vector2(92, 76)
	col.add_theme_constant_override("separation", 12)
	sheet.add_child(col)
	col.add_child(_line(tr("CASE_FILE") % (index + 1), 16, INK_SOFT, mono))
	var title := _line(data.title, 46, INK, serif)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	col.add_child(title)
	var rule := ColorRect.new()
	rule.color = Color(INK, 0.35)
	rule.custom_minimum_size = Vector2(0, 2)
	col.add_child(rule)
	var meta := (
		"%s   ·   %s"
		% [tr("CASE_DURATION") % UiTheme.format_time(data.duration), tr("CASE_CHARACTERS") % data.characters.size()]
	)
	if save.best_score > 0.0:
		meta += "   ·   " + tr("CASE_BEST") % int(round(save.best_score * 100.0))
	col.add_child(_line(meta, 16, INK_SOFT, mono))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	var desc := _line(data.description.strip_edges(), 20, INK, serif)
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	desc.add_theme_constant_override("line_spacing", 8)
	scroll.add_child(desc)
	col.add_child(_line(tr("DOSSIER_CAST"), 15, INK_SOFT, mono))
	col.add_child(_cast(data))
	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 24)
	col.add_child(buttons)
	var start := _button(tr("DOSSIER_START"), STAMP, CREAM)
	start.pressed.connect(func() -> void: case_chosen.emit(_paths[index]))
	buttons.add_child(start)
	var put_back := _button(tr("DOSSIER_BACK"), Color(INK, 0.0), INK)
	put_back.pressed.connect(_close)
	buttons.add_child(put_back)
	if save.solved:
		var stamp := _stamp()
		stamp.position = Vector2(400, 54)
		sheet.add_child(stamp)
	return root


func _cast(data: CaseData) -> Control:
	var flow := HFlowContainer.new()
	flow.add_theme_constant_override("h_separation", 4)
	flow.add_theme_constant_override("v_separation", 6)
	for c in data.characters:
		var entry := VBoxContainer.new()
		entry.custom_minimum_size.x = 60.0
		entry.add_theme_constant_override("separation", 2)
		var medal := Medallion.new()
		medal.texture = CaseLibrary.portrait(data.id, c.id)
		medal.ring = c.color
		medal.custom_minimum_size = Vector2(46, 46)
		medal.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		entry.add_child(medal)
		var who := _line(c.display_name, 13, INK_SOFT, UiTheme.serif_font())
		who.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		entry.add_child(who)
		flow.add_child(entry)
	return flow


## 海报；还没有海报的案件用 cover 指定的小照片。
func _poster(data: CaseData) -> Texture2D:
	var tex := CaseLibrary.poster(data.id)
	if tex == null and data.cover != "" and ResourceLoader.exists(PHOTO_DIR % data.cover):
		tex = load(PHOTO_DIR % data.cover)
	return tex


## 带白边和阴影的照片，左上角压一条胶带。
func _photo(texture: Texture2D, photo_size: Vector2, border: float) -> Control:
	var frame := Panel.new()
	frame.size = photo_size + Vector2(border, border) * 2.0
	frame.pivot_offset = frame.size * 0.5
	var style := _box(Color(0.97, 0.95, 0.90), Color(0.97, 0.95, 0.90), 2, 0)
	style.shadow_color = Color(0, 0, 0, 0.4)
	style.shadow_size = 8
	style.shadow_offset = Vector2(3, 5)
	frame.add_theme_stylebox_override("panel", style)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if texture:
		var pic := TextureRect.new()
		pic.texture = texture
		pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		pic.position = Vector2(border, border)
		pic.size = photo_size
		pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		frame.add_child(pic)
	else:
		var blank := ColorRect.new()
		blank.color = Color(0.16, 0.14, 0.12)
		blank.position = Vector2(border, border)
		blank.size = photo_size
		blank.mouse_filter = Control.MOUSE_FILTER_IGNORE
		frame.add_child(blank)
	var tape := ColorRect.new()
	tape.color = Color(0.93, 0.90, 0.78, 0.6)
	tape.size = Vector2(photo_size.x * 0.3, 26)
	tape.position = Vector2(photo_size.x * 0.35, -12)
	tape.rotation_degrees = -3.0
	tape.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(tape)
	return frame


func _button(text: String, fill: Color, font_color: Color) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.add_theme_font_override("font", UiTheme.serif_font())
	b.add_theme_font_size_override("font_size", 24)
	for state in ["font_color", "font_hover_color", "font_pressed_color"]:
		b.add_theme_color_override(state, font_color)
	var states := {"normal": fill, "hover": fill.lightened(0.12), "pressed": fill.darkened(0.15)}
	if fill.a == 0.0:
		states = {"normal": fill, "hover": Color(INK, 0.08), "pressed": Color(INK, 0.15)}
	for state: String in states:
		var style := _box(states[state], Color(font_color, 0.6) if fill.a == 0.0 else states[state], 4, 2)
		style.content_margin_left = 30
		style.content_margin_right = 30
		style.content_margin_top = 8
		style.content_margin_bottom = 8
		b.add_theme_stylebox_override(state, style)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	return b


func _box(fill: Color, border: Color, radius: int, border_width: int = 0) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = border
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(radius)
	return style


func _text(text: String, at: Vector2, width: float, font_size: int, color: Color, font: Font, lines: int = 0) -> Label:
	var l := _line(text, font_size, color, font)
	if lines > 0:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.max_lines_visible = lines
		l.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	l.position = at
	l.size = Vector2(width, 0)
	return l


func _line(text: String, font_size: int, color: Color, font: Font) -> Label:
	var l := Label.new()
	l.text = text
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	return l


func _stamp() -> Control:
	var box := PanelContainer.new()
	var style := _box(Color(STAMP, 0.06), Color(STAMP, 0.85), 4, 3)
	style.content_margin_left = 14
	style.content_margin_right = 14
	style.content_margin_top = 2
	style.content_margin_bottom = 2
	box.add_theme_stylebox_override("panel", style)
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(_line(tr("CASE_STAMP"), 32, Color(STAMP, 0.9), UiTheme.serif_font()))
	box.rotation_degrees = -12.0
	return box


## 圆形头像：彩色外圈 + 裁成圆的肖像。
class Medallion:
	extends Control

	var texture: Texture2D
	var ring := Color.WHITE

	func _draw() -> void:
		var r := minf(size.x, size.y) * 0.5
		var c := size * 0.5
		draw_circle(c, r, ring)
		var points := PackedVector2Array()
		var uvs := PackedVector2Array()
		for i in 40:
			var v := Vector2.from_angle(TAU * i / 40.0)
			points.append(c + v * (r - 3.0))
			uvs.append(Vector2(0.5, 0.5) + v * 0.5)
		if texture:
			draw_colored_polygon(points, Color.WHITE, uvs, texture)
		else:
			draw_colored_polygon(points, ActorDot.PAWN_BG)
