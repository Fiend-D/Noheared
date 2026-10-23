class_name TitleScreen
extends Control
## 主界面：夜晚的书桌，左侧只有标题和菜单。

signal start_requested

const DESK := preload("res://art/title/desk.jpg")
const CREAM := Color(0.95, 0.89, 0.76)
const MENU_WIDTH := 0.3

var _settings: AcceptDialog


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := TextureRect.new()
	bg.texture = DESK
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)
	var shade := TextureRect.new()
	var gradient := GradientTexture2D.new()
	gradient.gradient = Gradient.new()
	gradient.gradient.set_color(0, Color(0, 0, 0, 0.8))
	gradient.gradient.set_color(1, Color(0, 0, 0, 0))
	shade.texture = gradient
	shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	shade.stretch_mode = TextureRect.STRETCH_SCALE
	shade.anchor_right = MENU_WIDTH + 0.12
	shade.anchor_bottom = 1.0
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)
	_build_menu()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		accept_event()
		start_requested.emit()


func _build_menu() -> void:
	var col := VBoxContainer.new()
	col.anchor_right = MENU_WIDTH
	col.anchor_bottom = 1.0
	col.offset_left = 72
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 10)
	add_child(col)
	var ear := Label.new()
	ear.text = "))) "
	ear.add_theme_font_override("font", UiTheme.serif_font())
	ear.add_theme_font_size_override("font_size", 24)
	ear.add_theme_color_override("font_color", Color(UiTheme.ACCENT, 0.7))
	col.add_child(ear)
	var title := Label.new()
	title.text = tr("APP_TITLE")
	title.add_theme_font_override("font", UiTheme.serif_font())
	title.add_theme_font_size_override("font_size", 84)
	title.add_theme_color_override("font_color", CREAM)
	title.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.75))
	title.add_theme_constant_override("shadow_offset_x", 3)
	title.add_theme_constant_override("shadow_offset_y", 4)
	col.add_child(title)
	var rule := ColorRect.new()
	rule.color = Color(CREAM, 0.45)
	rule.custom_minimum_size = Vector2(280, 1)
	rule.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	col.add_child(rule)
	var tagline := Label.new()
	tagline.text = tr("TITLE_TAGLINE")
	tagline.add_theme_font_override("font", UiTheme.serif_font())
	tagline.add_theme_font_size_override("font_size", 16)
	tagline.add_theme_color_override("font_color", Color(CREAM, 0.6))
	col.add_child(tagline)
	var gap := Control.new()
	gap.custom_minimum_size.y = 48
	col.add_child(gap)
	col.add_child(menu_item(tr("MENU_START"), start_requested.emit))
	col.add_child(menu_item(tr("MENU_SETTINGS"), _show_settings))
	col.add_child(menu_item(tr("MENU_QUIT"), func() -> void: get_tree().quit()))
	var tail := Control.new()
	tail.custom_minimum_size.y = 80
	col.add_child(tail)


## 菜单项：衬线大字，悬停时前面出现 ›。档案室的返回按钮也用它。
static func menu_item(text: String, action: Callable, font_size: int = 30) -> Button:
	var b := Button.new()
	b.text = "  " + text
	b.flat = true
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.focus_mode = Control.FOCUS_NONE
	b.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.add_theme_font_override("font", UiTheme.serif_font())
	b.add_theme_font_size_override("font_size", font_size)
	b.add_theme_color_override("font_color", CREAM)
	b.add_theme_color_override("font_hover_color", UiTheme.ACCENT)
	b.add_theme_color_override("font_pressed_color", UiTheme.ACCENT)
	b.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.7))
	b.add_theme_constant_override("shadow_offset_y", 2)
	for state in ["normal", "hover", "pressed", "focus"]:
		b.add_theme_stylebox_override(state, StyleBoxEmpty.new())
	b.mouse_entered.connect(func() -> void: b.text = "› " + text)
	b.mouse_exited.connect(func() -> void: b.text = "  " + text)
	b.pressed.connect(action)
	return b


func _show_settings() -> void:
	if _settings == null:
		_settings = AcceptDialog.new()
		_settings.title = tr("MENU_SETTINGS")
		var grid := GridContainer.new()
		grid.columns = 2
		grid.add_theme_constant_override("h_separation", 16)
		var vol_label := Label.new()
		vol_label.text = tr("SETTINGS_VOLUME")
		grid.add_child(vol_label)
		var vol := HSlider.new()
		vol.custom_minimum_size.x = 220
		vol.min_value = 0.0
		vol.max_value = 1.0
		vol.step = 0.05
		vol.value = db_to_linear(AudioServer.get_bus_volume_db(0))
		vol.value_changed.connect(func(v: float) -> void: AudioServer.set_bus_volume_db(0, linear_to_db(v)))
		grid.add_child(vol)
		var fs_label := Label.new()
		fs_label.text = tr("SETTINGS_FULLSCREEN")
		grid.add_child(fs_label)
		var fs := CheckBox.new()
		fs.button_pressed = get_window().mode == Window.MODE_FULLSCREEN
		fs.toggled.connect(
			func(on: bool) -> void: get_window().mode = Window.MODE_FULLSCREEN if on else Window.MODE_WINDOWED
		)
		grid.add_child(fs)
		_settings.add_child(grid)
		add_child(_settings)
	_settings.popup_centered()
