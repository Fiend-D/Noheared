@tool
class_name UiTheme
extends RefCounted

const BG := Color(0.05, 0.08, 0.14, 0.94)
const BG_LIGHT := Color(0.10, 0.15, 0.25, 1.0)
const ACCENT := Color(0.45, 0.70, 1.0)
const TEXT := Color(0.88, 0.93, 1.0)
const TEXT_DIM := Color(0.60, 0.68, 0.80)
const FONT_NAMES := [
	"Noto Sans CJK SC",
	"Noto Sans SC",
	"Source Han Sans SC",
	"Microsoft YaHei",
	"PingFang SC",
	"WenQuanYi Micro Hei",
	"sans-serif",
]


static func build() -> Theme:
	var theme := Theme.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(FONT_NAMES)
	theme.default_font = font
	theme.default_font_size = 16
	ThemeDB.fallback_font = font

	theme.set_stylebox("panel", "PanelContainer", _box(BG, 0))
	theme.set_stylebox("panel", "Panel", _box(BG, 0))
	theme.set_stylebox("normal", "Button", _box(BG_LIGHT, 6))
	theme.set_stylebox("hover", "Button", _box(BG_LIGHT.lightened(0.12), 6))
	theme.set_stylebox("pressed", "Button", _box(ACCENT.darkened(0.45), 6))
	theme.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	theme.set_stylebox("normal", "OptionButton", _box(BG_LIGHT, 6))
	theme.set_stylebox("hover", "OptionButton", _box(BG_LIGHT.lightened(0.12), 6))
	theme.set_stylebox("panel", "ItemList", _box(Color(0, 0, 0, 0.25), 4))
	theme.set_stylebox("panel", "TabContainer", _box(BG, 0))
	for type in ["Label", "Button", "OptionButton", "ItemList", "RichTextLabel", "TabBar"]:
		theme.set_color("font_color", type, TEXT)
	theme.set_color("default_color", "RichTextLabel", TEXT)
	theme.set_color("font_hover_color", "Button", Color.WHITE)
	return theme


static func _box(color: Color, radius: int) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	sb.set_corner_radius_all(radius)
	sb.content_margin_left = 10
	sb.content_margin_right = 10
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	return sb


static func format_time(seconds: float) -> String:
	var s := int(seconds)
	return "%02d:%02d" % [floori(s / 60.0), s % 60]
