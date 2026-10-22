class_name CaseSelect
extends Control

signal case_chosen(path: String)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.035, 0.06, 0.11)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 48)
	add_child(margin)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 16)
	margin.add_child(col)

	var title := Label.new()
	title.text = tr("APP_TITLE")
	title.add_theme_font_size_override("font_size", 40)
	col.add_child(title)
	var hint := Label.new()
	hint.text = tr("CASE_SELECT_HINT")
	hint.add_theme_color_override("font_color", UiTheme.TEXT_DIM)
	col.add_child(hint)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(scroll)
	var grid := GridContainer.new()
	grid.columns = 3
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	grid.add_theme_constant_override("h_separation", 16)
	grid.add_theme_constant_override("v_separation", 16)
	scroll.add_child(grid)

	var paths := CaseLibrary.list_case_paths()
	if paths.is_empty():
		var none := Label.new()
		none.text = tr("CASE_NONE")
		col.add_child(none)
	for path in paths:
		var data := CaseLibrary.load_case(path)
		if data:
			grid.add_child(_card(path, data))


func _card(path: String, data: CaseData) -> Control:
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.custom_minimum_size = Vector2(0, 190)
	var box := StyleBoxFlat.new()
	box.bg_color = UiTheme.BG_LIGHT
	box.set_corner_radius_all(10)
	box.set_content_margin_all(16)
	panel.add_theme_stylebox_override("panel", box)

	var col := VBoxContainer.new()
	panel.add_child(col)
	var title := Label.new()
	title.text = data.title
	title.add_theme_font_size_override("font_size", 22)
	col.add_child(title)

	var save := SaveGame.load_for(data.id)
	var meta := Label.new()
	var bits := [tr("CASE_DURATION") % UiTheme.format_time(data.duration)]
	if save.best_score > 0.0:
		bits.append(tr("CASE_BEST") % int(round(save.best_score * 100.0)))
	if save.solved:
		bits.append(tr("CASE_SOLVED"))
	meta.text = " · ".join(bits)
	meta.add_theme_color_override("font_color", UiTheme.ACCENT)
	col.add_child(meta)

	var desc := Label.new()
	desc.text = data.description
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	desc.add_theme_color_override("font_color", UiTheme.TEXT_DIM)
	col.add_child(desc)

	var start := Button.new()
	start.text = tr("CASE_START")
	start.pressed.connect(func() -> void: case_chosen.emit(path))
	col.add_child(start)
	return panel
