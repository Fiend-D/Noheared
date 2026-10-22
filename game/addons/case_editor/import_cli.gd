extends SceneTree
## 命令行导入：把 res://cases/<id>/case.json 转成 case.tres + map.tscn。
##
##   godot --headless --path game --import
##   godot --headless --path game --script res://addons/case_editor/import_cli.gd -- [case1 case5 ...]
##
## 不带参数时导入 res://cases 下所有含 case.json 的目录。


func _initialize() -> void:
	var ids := PackedStringArray(OS.get_cmdline_user_args())
	if ids.is_empty():
		var dir := DirAccess.open(CaseLibrary.ROOT)
		if dir:
			for d in dir.get_directories():
				if FileAccess.file_exists("%s/%s/case.json" % [CaseLibrary.ROOT, d]):
					ids.append(d)
	var failed := 0
	for id in ids:
		var case_dir := "%s/%s" % [CaseLibrary.ROOT, id]
		var data := CaseJson.import_dir(case_dir)
		if data == null:
			failed += 1
			continue
		var map := data.map_scene.instantiate() as CaseMap
		var issues := CaseValidator.validate(data, map)
		map.free()
		print(
			(
				"%s: %s，%d 名角色，%d 句台词，%d 条校验提示"
				% [id, data.title, data.characters.size(), data.voice_lines.size(), issues.size()]
			)
		)
		for issue in issues:
			print("  ", issue)
	quit(1 if failed > 0 else 0)
