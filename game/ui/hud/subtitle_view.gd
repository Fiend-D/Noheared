class_name SubtitleView
extends PanelContainer
## 只显示监听者能听到的台词：听清的显示原文，隔墙的只显示“听不清”。

var _label: RichTextLabel
var _last: String = ""
var _names: Callable


## `names` 是 func(character_id) -> String，返回圆点编号加玩家指认的名字。
func setup(names: Callable) -> void:
	_names = names
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var box := StyleBoxFlat.new()
	box.bg_color = Color(0, 0, 0, 0.0)
	box.set_content_margin_all(8)
	add_theme_stylebox_override("panel", box)
	_label = RichTextLabel.new()
	_label.bbcode_enabled = true
	_label.fit_content = true
	_label.scroll_active = false
	_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.add_theme_font_size_override("normal_font_size", 22)
	_label.add_theme_font_size_override("bold_font_size", 22)
	_label.add_theme_constant_override("outline_size", 8)
	_label.add_theme_color_override("font_outline_color", Color(0.02, 0.03, 0.04, 0.92))
	_label.add_theme_constant_override("line_separation", 6)
	add_child(_label)
	visible = false


func show_lines(active: Array[CueScheduler.ActiveLine], case_data: CaseData) -> void:
	var parts: PackedStringArray = []
	for entry in active:
		if entry.clarity == Acoustics.Clarity.NONE:
			continue
		var c := case_data.get_character(entry.line.speaker)
		var color := c.color.lightened(0.25).to_html(false) if c else "ffffff"
		var who: String = _names.call(entry.line.speaker)
		if entry.clarity == Acoustics.Clarity.CLEAR:
			parts.append("[color=#%s][b]%s[/b][/color]  %s" % [color, who, _escape(entry.line.text)])
		else:
			parts.append("[color=#%s]%s[/color]  [color=#7c8794][i]%s[/i][/color]" % [color, who, tr("MUFFLED")])
	var text := "\n".join(parts)
	if text == _last:
		return
	_last = text
	_label.text = text
	visible = text != ""


func _escape(s: String) -> String:
	return s.replace("[", "[lb]")
