@tool
extends EditorPlugin

const TimelineDock := preload("res://addons/case_editor/timeline_dock.gd")
const PropPalette := preload("res://addons/case_editor/prop_palette.gd")
const MENU_IMPORT := "案件：从 case.json 导入…"
const MENU_EXPORT := "案件：导出当前案件为 case.json"
const MENU_VALIDATE := "案件：校验当前案件"

var _dock: TimelineDock
var _palette: PropPalette
var _dialog: EditorFileDialog
var _drag: Prop
var _drag_from: Vector2
var _drag_offset: Vector2


func _enter_tree() -> void:
	_dock = TimelineDock.new()
	_dock.name = "CaseTimeline"
	_dock.preview_changed.connect(update_overlays)
	add_control_to_bottom_panel(_dock, "案件时间轴")
	_palette = PropPalette.new()
	_palette.name = "家具"
	_palette.flip_requested.connect(_flip_selected)
	add_control_to_dock(DOCK_SLOT_RIGHT_UL, _palette)
	add_tool_menu_item(MENU_IMPORT, _ask_import)
	add_tool_menu_item(MENU_EXPORT, _export)
	add_tool_menu_item(MENU_VALIDATE, func() -> void: _dock.validate())


func _exit_tree() -> void:
	remove_tool_menu_item(MENU_IMPORT)
	remove_tool_menu_item(MENU_EXPORT)
	remove_tool_menu_item(MENU_VALIDATE)
	if _dialog:
		_dialog.queue_free()
	remove_control_from_bottom_panel(_dock)
	_dock.queue_free()
	remove_control_from_docks(_palette)
	_palette.queue_free()


func _handles(object: Object) -> bool:
	return object is CaseData or object is CaseMap or object is Prop


func _forward_canvas_gui_input(event: InputEvent) -> bool:
	var root := EditorInterface.get_edited_scene_root() as CaseMap
	if root == null:
		return false
	var to_map := (root.get_viewport().global_canvas_transform * root.get_global_transform()).affine_inverse()
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE and _palette.selected_type() != "":
		_palette.clear_selection()
		return true
	if event is InputEventMouseMotion and _drag:
		_drag.position = (to_map * event.position + _drag_offset).round()
		return true
	if event is InputEventMouseButton:
		return _mouse_button(root, event, to_map * event.position)
	return false


func _mouse_button(root: CaseMap, mb: InputEventMouseButton, p: Vector2) -> bool:
	if mb.button_index == MOUSE_BUTTON_RIGHT and mb.pressed and _palette.selected_type() != "":
		_palette.clear_selection()
		return true
	if mb.button_index != MOUSE_BUTTON_LEFT:
		return false
	if not mb.pressed:
		return _commit_drag(root)
	if _palette.selected_type() != "":
		_place(root, _palette.selected_type(), p.round())
		if not mb.shift_pressed:
			_palette.clear_selection()
		return true
	return _start_drag(root, p)


func _start_drag(root: CaseMap, p: Vector2) -> bool:
	var hit := _prop_at(root, p)
	if hit == null:
		return false
	EditorInterface.get_selection().clear()
	EditorInterface.get_selection().add_node(hit)
	_drag = hit
	_drag_from = hit.position
	_drag_offset = hit.position - p
	return true


func _prop_at(root: CaseMap, p: Vector2) -> Prop:
	var props := root.get_props()
	for i in range(props.size() - 1, -1, -1):
		if props[i].visible and props[i].rect().has_point(p):
			return props[i]
	return null


func _place(root: CaseMap, type: String, p: Vector2) -> void:
	var room := root.room_at(p, &"", root.current_floor)
	if room == null:
		push_warning("家具要放在房间里")
		return
	var group := root.get_node_or_null("Props")
	if group == null:
		group = Node2D.new()
		group.name = "Props"
		root.add_child(group)
		group.owner = root
	var prop := Prop.new()
	PropCatalog.apply(prop, type)
	prop.name = type
	prop.position = p
	prop.room_name = room.room_name
	var ur := get_undo_redo()
	ur.create_action("放置家具 %s" % type)
	ur.add_do_method(group, "add_child", prop, true)
	ur.add_do_property(prop, "owner", root)
	ur.add_do_method(root, "refresh")
	ur.add_do_reference(prop)
	ur.add_undo_method(group, "remove_child", prop)
	ur.add_undo_method(root, "refresh")
	ur.commit_action()


## 松开鼠标时提交拖动。没有在拖动时返回 false，让编辑器照常处理。
func _commit_drag(root: CaseMap) -> bool:
	var prop := _drag
	if prop == null:
		return false
	_drag = null
	var to := prop.position
	if to == _drag_from:
		return true
	var room := root.room_at(to, &"", prop.floor_index)
	var new_room := room.room_name if room else prop.room_name
	var ur := get_undo_redo()
	ur.create_action("移动家具")
	ur.add_do_property(prop, "position", to)
	ur.add_do_property(prop, "room_name", new_room)
	ur.add_do_method(root, "refresh")
	ur.add_undo_property(prop, "position", _drag_from)
	ur.add_undo_property(prop, "room_name", prop.room_name)
	ur.add_undo_method(root, "refresh")
	ur.commit_action()
	return true


func _flip_selected() -> void:
	var ur := get_undo_redo()
	ur.create_action("翻转家具")
	for node in EditorInterface.get_selection().get_selected_nodes():
		if node is Prop:
			ur.add_do_property(node, "flip_h", not node.flip_h)
			ur.add_undo_property(node, "flip_h", node.flip_h)
	ur.commit_action()


func _edit(object: Object) -> void:
	if object is CaseData:
		_dock.load_case(object)
		make_bottom_panel_item_visible(_dock)
	update_overlays()


## 编辑地图场景时，在视口上画出预览时刻的人物位置。
func _forward_canvas_draw_over_viewport(overlay: Control) -> void:
	var root := EditorInterface.get_edited_scene_root() as CaseMap
	if root == null or _dock.case_data == null:
		return
	var xform := root.get_viewport().global_canvas_transform * root.get_global_transform()
	var font := overlay.get_theme_default_font()
	for c in _dock.case_data.characters:
		var pose := TrackMath.sample(c.track, _dock.preview_time)
		var p := xform * pose.position
		overlay.draw_circle(p, 10.0, c.color)
		overlay.draw_arc(p, 11.0, 0, TAU, 24, Color.WHITE, 1.5, true)
		overlay.draw_string(
			font,
			p + Vector2(-20, -14),
			"%s %s" % [c.label, c.display_name],
			HORIZONTAL_ALIGNMENT_CENTER,
			40,
			12,
			Color.WHITE
		)


func _ask_import() -> void:
	if _dialog == null:
		_dialog = EditorFileDialog.new()
		_dialog.file_mode = EditorFileDialog.FILE_MODE_OPEN_DIR
		_dialog.access = EditorFileDialog.ACCESS_RESOURCES
		_dialog.title = "选择含 case.json 的案件目录"
		_dialog.dir_selected.connect(_import)
		EditorInterface.get_base_control().add_child(_dialog)
	_dialog.popup_file_dialog()


func _import(dir: String) -> void:
	var data := CaseJson.import_dir(dir)
	EditorInterface.get_resource_filesystem().scan()
	if data:
		_dock.load_case(load(dir.path_join("case.tres")))
		make_bottom_panel_item_visible(_dock)


func _export() -> void:
	var data := _dock.case_data
	if data == null or data.resource_path == "":
		push_warning("先在时间轴面板中打开一个已保存的案件")
		return
	var dir := data.resource_path.get_base_dir()
	var err := CaseJson.write_json(dir.path_join("case.json"), CaseJson.export_case(data, dir))
	if err == OK:
		print("已导出 ", dir.path_join("case.json"))
	else:
		push_error("导出失败：%s" % error_string(err))
