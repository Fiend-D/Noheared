class_name Transcript
extends RefCounted
## 玩家听清过的台词和听到过的音效，按时间排序。

signal changed

var heard_lines: Dictionary = {}
var heard_sfx: Dictionary = {}


func add_line(index: int) -> void:
	if not heard_lines.has(index):
		heard_lines[index] = true
		changed.emit()


func add_sfx(index: int) -> void:
	if not heard_sfx.has(index):
		heard_sfx[index] = true
		changed.emit()


## 返回 [{time, kind: "line"/"sfx", index}]，按时间排序。
func entries(case_data: CaseData) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for i: int in heard_lines:
		if i < case_data.voice_lines.size():
			out.append({"time": case_data.voice_lines[i].start, "kind": "line", "index": i})
	for i: int in heard_sfx:
		if i < case_data.sfx_events.size():
			out.append({"time": case_data.sfx_events[i].time, "kind": "sfx", "index": i})
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a.time < b.time)
	return out


func to_dict() -> Dictionary:
	return {"lines": heard_lines.keys(), "sfx": heard_sfx.keys()}


func load_dict(data: Dictionary) -> void:
	heard_lines.clear()
	heard_sfx.clear()
	for i: Variant in data.get("lines", []):
		heard_lines[int(i)] = true
	for i: Variant in data.get("sfx", []):
		heard_sfx[int(i)] = true
	changed.emit()
