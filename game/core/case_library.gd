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
