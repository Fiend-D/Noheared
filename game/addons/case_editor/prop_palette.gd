@tool
extends VBoxContainer
## 家具面板：选中一件家具后在地图上单击放置（按住 Shift 连续放置，右键或 Esc 取消）。

signal flip_requested

const THUMB := 56

var _list: ItemList
var _ids: PackedStringArray = []


func _ready() -> void:
	var hint := Label.new()
	hint.text = "选中后在地图上单击放置\nShift 连续放置，右键 / Esc 取消\n拖动已有家具可移动"
	hint.add_theme_font_size_override("font_size", 12)
	add_child(hint)
	var flip := Button.new()
	flip.text = "水平翻转选中的家具"
	flip.pressed.connect(func() -> void: flip_requested.emit())
	add_child(flip)
	_list = ItemList.new()
	_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_list.max_columns = 0
	_list.icon_mode = ItemList.ICON_MODE_TOP
	_list.fixed_icon_size = Vector2i(THUMB, THUMB)
	_list.fixed_column_width = THUMB + 16
	_list.same_column_width = true
	add_child(_list)
	reload()


func reload() -> void:
	_list.clear()
	_ids = PropCatalog.ids()
	for id in _ids:
		var tex: Texture2D = load(PropCatalog.PROPS_DIR + id + ".png")
		var i := _list.add_item(id, tex)
		_list.set_item_tooltip(i, id)


## 当前要放置的家具类型，没选时为空。
func selected_type() -> String:
	var sel := _list.get_selected_items()
	return _ids[sel[0]] if not sel.is_empty() else ""


func clear_selection() -> void:
	_list.deselect_all()
