class_name SidePanel
extends TabContainer
## 右侧面板：笔记（可回跳）、人物指认、案件问题。

signal seek_requested(t: float)
signal identity_changed(character_id: StringName, assigned: String)
signal answers_submitted

var case_data: CaseData
var transcript: Transcript
var save: SaveGame

var _notes: VBoxContainer
var _notes_scroll: ScrollContainer
var _note_times: Array[float] = []
var _people_rows: Dictionary = {}
var _question_inputs: Dictionary = {}
var _result: Label
var _names: Callable


func setup(data: CaseData, notes: Transcript, save_game: SaveGame, names: Callable) -> void:
	case_data = data
	transcript = notes
	save = save_game
	_names = names
	add_child(_build_notes())
	add_child(_build_people())
	add_child(_build_questions())
	set_tab_title(0, tr("TAB_NOTES"))
	set_tab_title(1, tr("TAB_PEOPLE"))
	set_tab_title(2, tr("TAB_QUESTIONS"))
	transcript.changed.connect(refresh_notes)
	refresh_notes()


func _build_notes() -> Control:
	var col := VBoxContainer.new()
	col.add_child(_hint(tr("NOTES_HINT")))
	_notes_scroll = ScrollContainer.new()
	_notes_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_notes_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	col.add_child(_notes_scroll)
	_notes = VBoxContainer.new()
	_notes.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_notes.add_theme_constant_override("separation", 2)
	_notes_scroll.add_child(_notes)
	return col


func refresh_notes() -> void:
	if _notes == null:
		return
	var bar := _notes_scroll.get_v_scroll_bar()
	var scroll_to_end := bar.value >= bar.max_value - _notes_scroll.size.y - 4
	for child in _notes.get_children():
		child.queue_free()
	_note_times.clear()
	var entries := transcript.entries(case_data)
	if entries.is_empty():
		_notes.add_child(_hint(tr("NOTES_EMPTY")))
		return
	for e in entries:
		var stamp := (
			"[font_size=12][color=#%s]%s[/color][/font_size]  "
			% [UiTheme.ACCENT.to_html(false), UiTheme.format_time(e.time)]
		)
		var accent := UiTheme.ACCENT
		var body: String
		if e.kind == "line":
			var line := case_data.voice_lines[e.index]
			var c := case_data.get_character(line.speaker)
			accent = c.color if c else UiTheme.TEXT
			body = (
				"[color=#%s][b]%s[/b][/color]\n%s"
				% [accent.lightened(0.3).to_html(false), _names.call(line.speaker), line.text.replace("[", "[lb]")]
			)
		else:
			var ev := case_data.sfx_events[e.index]
			body = "[color=#%s]%s%s[/color]" % [UiTheme.ACCENT.to_html(false), tr("SFX_PREFIX"), ev.label]
		_notes.add_child(_note_entry(stamp + body, accent, e.time))
		_note_times.append(e.time)
	if scroll_to_end:
		bar.set_deferred("value", bar.max_value)


func _note_entry(bbcode: String, accent: Color, t: float) -> Control:
	var panel := PanelContainer.new()
	var normal := UiTheme.box(Color(1, 1, 1, 0.02), Color(0, 0, 0, 0), 10)
	normal.border_color = Color(accent, 0.8)
	normal.border_width_left = 3
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = Color(UiTheme.ACCENT, 0.1)
	panel.add_theme_stylebox_override("panel", normal)
	panel.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	panel.tooltip_text = tr("NOTES_HINT")
	panel.mouse_entered.connect(func() -> void: panel.add_theme_stylebox_override("panel", hover))
	panel.mouse_exited.connect(func() -> void: panel.add_theme_stylebox_override("panel", normal))
	panel.gui_input.connect(
		func(event: InputEvent) -> void:
			if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
				seek_requested.emit(t)
	)
	var label := RichTextLabel.new()
	label.bbcode_enabled = true
	label.fit_content = true
	label.scroll_active = false
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("normal_font_size", 15)
	label.add_theme_font_size_override("bold_font_size", 14)
	label.add_theme_font_override("mono_font", UiTheme.mono_font())
	label.text = bbcode
	panel.add_child(label)
	return panel


func _build_people() -> Control:
	var col := VBoxContainer.new()
	col.add_child(_hint(tr("PEOPLE_HINT")))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	col.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)

	var names := Array(case_data.character_names())
	names.sort()
	for c in case_data.characters:
		var row := HBoxContainer.new()
		var swatch := ColorRect.new()
		swatch.color = c.color
		swatch.custom_minimum_size = Vector2(22, 22)
		row.add_child(swatch)
		var label := Label.new()
		label.text = tr("DOT_LABEL") % c.label
		label.custom_minimum_size.x = 70
		row.add_child(label)
		var pick := OptionButton.new()
		pick.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		pick.add_item(tr("UNASSIGNED"))
		for n: String in names:
			pick.add_item(n)
		var current := String(save.identities.get(String(c.id), ""))
		var current_idx := names.find(current)
		pick.select(current_idx + 1 if current_idx >= 0 else 0)
		var cid := c.id
		pick.item_selected.connect(
			func(i: int) -> void:
				var value := "" if i == 0 else pick.get_item_text(i)
				identity_changed.emit(cid, value)
		)
		row.add_child(pick)
		list.add_child(row)
		_people_rows[c.id] = row
	return col


func highlight_person(character_id: StringName) -> void:
	current_tab = 1
	for id: StringName in _people_rows:
		var row: HBoxContainer = _people_rows[id]
		row.modulate = Color(1.3, 1.3, 1.3) if id == character_id else Color.WHITE


func _build_questions() -> Control:
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_theme_constant_override("separation", 10)
	scroll.add_child(col)
	for i in case_data.questions.size():
		var q := case_data.questions[i]
		var prompt := Label.new()
		prompt.text = "%d. %s" % [i + 1, q.prompt]
		prompt.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		col.add_child(prompt)
		var pick := OptionButton.new()
		pick.add_item(tr("CHOOSE"))
		var options := case_data.options_for(q)
		for o in options:
			pick.add_item(o)
		var saved := String(save.answers.get(String(q.id), ""))
		var saved_idx := Array(options).find(saved)
		pick.select(saved_idx + 1 if saved_idx >= 0 else 0)
		col.add_child(pick)
		_question_inputs[q.id] = pick
	var submit := Button.new()
	submit.text = tr("SUBMIT")
	submit.pressed.connect(_on_submit)
	col.add_child(submit)
	_result = Label.new()
	_result.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	col.add_child(_result)
	return scroll


func _on_submit() -> void:
	for id: StringName in _question_inputs:
		var pick: OptionButton = _question_inputs[id]
		save.answers[String(id)] = "" if pick.selected <= 0 else pick.get_item_text(pick.selected)
	answers_submitted.emit()


func show_result(r: Scoring.Result) -> void:
	_result.text = tr("RESULT") % [r.questions_correct, r.questions_total, r.identities_correct, r.identities_total]
	for id: StringName in _question_inputs:
		var pick: OptionButton = _question_inputs[id]
		pick.modulate = Color(1.0, 0.6, 0.6) if r.wrong_questions.has(id) else Color(0.7, 1.0, 0.75)


func _hint(text: String) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color", UiTheme.TEXT_DIM)
	l.add_theme_font_size_override("font_size", 13)
	return l
