class_name SaveGame
extends RefCounted
## 每个案件一个存档文件：user://saves/<case_id>.json

const DIR := "user://saves"

var case_id: StringName
var time: float = 0.0
var floor_index: int = 0
var listener_position: Vector2 = Vector2.ZERO
var has_listener_position: bool = false
## 角色 id -> 玩家指认的名字
var identities: Dictionary = {}
## 问题 id -> 玩家选择的答案
var answers: Dictionary = {}
var transcript: Dictionary = {}
var best_score: float = 0.0
var solved: bool = false


static func path_for(id: StringName) -> String:
	return "%s/%s.json" % [DIR, id]


static func load_for(id: StringName) -> SaveGame:
	var save := SaveGame.new()
	save.case_id = id
	var path := path_for(id)
	if not FileAccess.file_exists(path):
		return save
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if parsed is Dictionary:
		save.from_dict(parsed)
	return save


func write() -> Error:
	DirAccess.make_dir_recursive_absolute(DIR)
	var f := FileAccess.open(path_for(case_id), FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(to_dict(), "\t"))
	return OK


func to_dict() -> Dictionary:
	var d := {
		"time": time,
		"floor": floor_index,
		"identities": identities,
		"answers": answers,
		"transcript": transcript,
		"best_score": best_score,
		"solved": solved,
	}
	if has_listener_position:
		d["listener"] = [listener_position.x, listener_position.y]
	return d


func from_dict(d: Dictionary) -> void:
	time = float(d.get("time", 0.0))
	floor_index = int(d.get("floor", 0))
	identities = d.get("identities", {})
	answers = d.get("answers", {})
	transcript = d.get("transcript", {})
	best_score = float(d.get("best_score", 0.0))
	solved = bool(d.get("solved", false))
	var l: Variant = d.get("listener")
	if l is Array and l.size() == 2:
		listener_position = Vector2(l[0], l[1])
		has_listener_position = true
