@tool
class_name CaseLibrary
extends RefCounted
## 扫描 res://cases/<id>/case.tres。

const ROOT := "res://cases"


static func list_case_paths() -> PackedStringArray:
	var out := PackedStringArray()
	var dir := DirAccess.open(ROOT)
	if dir == null:
		return out
	var names := Array(dir.get_directories())
	names.sort_custom(func(a: String, b: String) -> bool: return a.naturalnocasecmp_to(b) < 0)
	for n: String in names:
		var path := "%s/%s/case.tres" % [ROOT, n]
		if ResourceLoader.exists(path):
			out.append(path)
	return out


static func load_case(path: String) -> CaseData:
	return load(path) as CaseData


## 案件海报（res://art/posters/<案件>.jpg），没有则返回 null。
static func poster(case_id: StringName) -> Texture2D:
	return _texture("res://art/posters/%s.jpg" % case_id)


## 角色头像（res://art/portraits/<案件>/<角色 ID>.jpg），没有则返回 null。
static func portrait(case_id: StringName, character_id: StringName) -> Texture2D:
	return _texture("res://art/portraits/%s/%s.jpg" % [case_id, character_id])


## 按身份名（display_name）找该身份角色的头像。
static func portrait_for_name(data: CaseData, display_name: String) -> Texture2D:
	for c in data.characters:
		if c.display_name == display_name:
			return portrait(data.id, c.id)
	return null


static func _texture(path: String) -> Texture2D:
	return load(path) as Texture2D if ResourceLoader.exists(path) else null
