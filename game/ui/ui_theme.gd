@tool
class_name UiTheme
extends RefCounted
## 界面主题：深色监听台风格。细边框、直角、琥珀色强调，时间等数字用等宽字体。

const BG := Color(0.047, 0.063, 0.086, 0.97)
const BG_LIGHT := Color(0.086, 0.110, 0.145, 1.0)
const LINE := Color(0.80, 0.85, 0.90, 0.16)
const ACCENT := Color(0.96, 0.68, 0.26)
const ALERT := Color(0.90, 0.32, 0.25)
const TEXT := Color(0.90, 0.92, 0.94)
const TEXT_DIM := Color(0.55, 0.61, 0.68)
const FONT_NAMES := [
	"Noto Sans CJK SC",
	"Noto Sans SC",
	"Source Han Sans SC",
	"Microsoft YaHei",
	"PingFang SC",
	"WenQuanYi Micro Hei",
	"sans-serif",
]
const MONO_NAMES := [
	"JetBrains Mono",
	"Cascadia Mono",
	"Consolas",
	"Menlo",
	"DejaVu Sans Mono",
	"Noto Sans Mono",
	"monospace",
]
const SERIF_NAMES := [
	"Noto Serif CJK SC",
	"Noto Serif SC",
	"Source Han Serif SC",
	"Songti SC",
	"SimSun",
	"serif",
]

static var _mono: SystemFont
static var _serif: SystemFont


static func build() -> Theme:
	var theme := Theme.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(FONT_NAMES)
	theme.default_font = font
	theme.default_font_size = 16
	ThemeDB.fallback_font = font

	theme.set_stylebox("panel", "PanelContainer", box(BG))
	theme.set_stylebox("panel", "Panel", box(BG))
	for type in ["Button", "OptionButton"]:
		theme.set_stylebox("normal", type, box(Color(BG_LIGHT, 0.6), LINE))
		theme.set_stylebox("hover", type, box(BG_LIGHT, ACCENT))
		theme.set_stylebox("pressed", type, box(ACCENT.darkened(0.55), ACCENT))
		theme.set_stylebox("disabled", type, box(Color(BG_LIGHT, 0.3), Color(LINE, 0.08)))
		theme.set_stylebox("focus", type, StyleBoxEmpty.new())
		theme.set_color("font_color", type, TEXT)
		theme.set_color("font_hover_color", type, ACCENT)
		theme.set_color("font_pressed_color", type, Color.WHITE)
		theme.set_color("font_focus_color", type, TEXT)
	theme.set_stylebox("panel", "PopupMenu", box(BG_LIGHT, LINE))
	theme.set_stylebox("hover", "PopupMenu", box(Color(ACCENT, 0.2)))
	theme.set_color("font_color", "PopupMenu", TEXT)
	theme.set_color("font_hover_color", "PopupMenu", ACCENT)
	theme.set_stylebox("panel", "ItemList", box(Color(0, 0, 0, 0.2)))
	theme.set_stylebox("panel", "TabContainer", box(BG))
	theme.set_stylebox("tabbar_background", "TabContainer", _underline(Color(0, 0, 0, 0), LINE, 1))
	for type in ["TabBar", "TabContainer"]:
		theme.set_stylebox("tab_selected", type, _underline(Color(ACCENT, 0.08), ACCENT, 2))
		theme.set_stylebox("tab_unselected", type, _underline(Color(0, 0, 0, 0), Color(0, 0, 0, 0), 2))
		theme.set_stylebox("tab_hovered", type, _underline(Color(1, 1, 1, 0.04), Color(ACCENT, 0.4), 2))
		theme.set_stylebox("tab_focus", type, StyleBoxEmpty.new())
		theme.set_color("font_selected_color", type, ACCENT)
		theme.set_color("font_unselected_color", type, TEXT_DIM)
		theme.set_color("font_hovered_color", type, TEXT)
	theme.set_stylebox("scroll", "VScrollBar", _bar(Color(1, 1, 1, 0.03)))
	theme.set_stylebox("grabber", "VScrollBar", _bar(Color(1, 1, 1, 0.18)))
	theme.set_stylebox("grabber_highlight", "VScrollBar", _bar(Color(ACCENT, 0.6)))
	theme.set_stylebox("grabber_pressed", "VScrollBar", _bar(ACCENT))
	theme.set_stylebox("embedded_border", "Window", box(BG_LIGHT, ACCENT))
	theme.set_stylebox("panel", "AcceptDialog", box(BG_LIGHT))
	for type in ["Label", "ItemList", "RichTextLabel", "AcceptDialog"]:
		theme.set_color("font_color", type, TEXT)
	theme.set_color("default_color", "RichTextLabel", TEXT)
	theme.set_color("title_color", "Window", ACCENT)
	return theme


## 平面底色，可选 1px 边框。
static func box(color: Color, border: Color = Color(0, 0, 0, 0), margin: int = 10) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(2)
	if border.a > 0.0:
		sb.border_color = border
		sb.set_border_width_all(1)
	sb.content_margin_left = margin
	sb.content_margin_right = margin
	sb.content_margin_top = margin * 0.6
	sb.content_margin_bottom = margin * 0.6
	return sb


static func _underline(color: Color, line: Color, width: int) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.border_color = line
	sb.border_width_bottom = width
	sb.content_margin_left = 16
	sb.content_margin_right = 16
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	return sb


static func _bar(color: Color) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(3)
	sb.content_margin_left = 3
	sb.content_margin_right = 3
	return sb


## 等宽字体，用于时间码。
static func mono_font() -> Font:
	if _mono == null:
		_mono = SystemFont.new()
		_mono.font_names = PackedStringArray(MONO_NAMES)
	return _mono


static func serif_font() -> Font:
	if _serif == null:
		_serif = SystemFont.new()
		_serif.font_names = PackedStringArray(SERIF_NAMES)
	return _serif


static func format_time(seconds: float) -> String:
	var s := int(seconds)
	return "%02d:%02d" % [floori(s / 60.0), s % 60]
