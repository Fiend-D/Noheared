class_name SidePanel
extends TabContainer
## 右侧面板：笔记（可回跳）、人物指认、案件问题。

signal seek_requested(t: float)
signal identity_changed(character_id: StringName, assigned: String)
signal answers_submitted

var case_data: CaseData
var transcript: Transcript
var save: SaveGame

var _notes: ItemList
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
	_notes = ItemList.new()
	_notes.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_notes.auto_height = false
	_notes.max_columns = 1
	_notes.fixed_column_width = int(Game.SIDE_WIDTH) - 48
	_notes.max_text_lines = 4
	_notes.text_overrun_behavior = TextServer.OVERRUN_NO_TRIMMING
	_notes.item_clicked.connect(
		func(i: int, _pos: Vector2, _button: int) -> void:
			if i < _note_times.size() and _note_times[i] >= 0.0:
				seek_requested.emit(_note_times[i])
	)
	col.add_child(_notes)
	return col


func refresh_notes() -> void:
	if _notes == null:
		return
	var scroll_to_end := _notes.get_v_scroll_bar().value >= _notes.get_v_scroll_bar().max_value - _notes.size.y - 4
	_notes.clear()
	_note_times.clear()
	var entries := transcript.entries(case_data)
	if entries.is_empty():
		_notes.add_item(tr("NOTES_EMPTY"), null, false)
		_note_times.append(-1.0)
		return
	for e in entries:
		var stamp := "[%s] " % UiTheme.format_time(e.time)
		if e.kind == "line":
			var line := case_data.voice_lines[e.index]
			var idx := _notes.add_item("%s%s：%s" % [stamp, _names.call(line.speaker), line.text])
			var c := case_data.get_character(line.speaker)
			if c:
				_notes.set_item_custom_fg_color(idx, c.color.lightened(0.45))
		else:
			var ev := case_data.sfx_events[e.index]
			var idx := _notes.add_item("%s%s%s" % [stamp, tr("SFX_PREFIX"), ev.label])
			_notes.set_item_custom_fg_color(idx, Color(0.95, 0.8, 0.5))
		_note_times.append(e.time)
	if scroll_to_end:
		var bar := _notes.get_v_scroll_bar()
		bar.set_deferred("value", bar.max_value)


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
