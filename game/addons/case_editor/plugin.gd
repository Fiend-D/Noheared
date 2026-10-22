@tool
extends EditorPlugin

const TimelineDock := preload("res://addons/case_editor/timeline_dock.gd")
const MENU_IMPORT := "案件：从 case.json 导入…"
const MENU_EXPORT := "案件：导出当前案件为 case.json"
const MENU_VALIDATE := "案件：校验当前案件"

var _dock: TimelineDock
var _dialog: EditorFileDialog


func _enter_tree() -> void:
	_dock = TimelineDock.new()
	_dock.name = "CaseTimeline"
	_dock.preview_changed.connect(update_overlays)
	add_control_to_bottom_panel(_dock, "案件时间轴")
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


func _handles(object: Object) -> bool:
	return object is CaseData or object is CaseMap


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
