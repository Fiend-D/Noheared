@tool
class_name CaseJson
extends RefCounted
## case.json <-> CaseData + 地图场景 的互相转换。
## JSON 便于脚本批量生成内容；运行时只读 case.tres 和 map.tscn。

const FORMAT := 1
const MOVEMENT_NAMES := {"idle": TrackKey.Movement.IDLE, "walk": TrackKey.Movement.WALK, "run": TrackKey.Movement.RUN}
const KIND_NAMES := {"choice": Question.Kind.CHOICE, "character": Question.Kind.CHARACTER}


## 读取 `<case_dir>/case.json`，生成并保存 `map.tscn` 和 `case.tres`。返回生成的 CaseData。
static func import_dir(case_dir: String) -> CaseData:
	var json_path := case_dir.path_join("case.json")
	var text := FileAccess.get_file_as_string(json_path)
	if text == "":
		push_error("读不到 %s" % json_path)
		return null
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		push_error("%s 不是合法的 JSON 对象" % json_path)
		return null
	var data: Dictionary = parsed

	var map_path := case_dir.path_join("map.tscn")
	var map := build_map(data.get("map", {}))
	var packed := PackedScene.new()
	var err := packed.pack(map)
	map.free()
	if err != OK:
		push_error("打包地图失败：%s" % error_string(err))
		return null
	ResourceSaver.save(packed, map_path)

	var case_data := build_case(data, case_dir)
	case_data.map_scene = ResourceLoader.load(map_path, "", ResourceLoader.CACHE_MODE_REPLACE)
	err = ResourceSaver.save(case_data, case_dir.path_join("case.tres"))
	if err != OK:
		push_error("保存 case.tres 失败：%s" % error_string(err))
		return null
	return case_data


static func build_map(m: Dictionary) -> CaseMap:
	var map := CaseMap.new()
	map.name = "CaseMap"
	map.floor_names = PackedStringArray(m.get("floors", ["一层"]))
	var rooms := _group(map, "Rooms")
	var doors := _group(map, "Doors")
	var stairs := _group(map, "Stairs")
	for r: Dictionary in m.get("rooms", []):
		var room := Room.new()
		room.name = _node_name(r.name)
		room.room_name = r.name
		room.floor_index = int(r.get("floor", 0))
		var poly := PackedVector2Array()
		for p: Array in r.polygon:
			poly.append(_vec(p))
		room.polygon = poly
		_attach(rooms, room, map)
	for d: Dictionary in m.get("doors", []):
		var door := Door.new()
		door.name = _node_name(d.get("name", "Door"))
		door.room_a = d.room_a
		door.room_b = d.room_b
		door.position = _vec(d.position)
		door.size = _vec(d.get("size", [24, 10]))
		door.open = bool(d.get("open", true))
		_attach(doors, door, map)
	for s: Dictionary in m.get("stairs", []):
		var stair := Stair.new()
		stair.name = _node_name(s.get("name", "Stair"))
		stair.room_a = s.room_a
		stair.room_b = s.room_b
		stair.position = _vec(s.end_a)
		stair.end_b = _vec(s.end_b)
		_attach(stairs, stair, map)
	return map


static func build_case(data: Dictionary, case_dir: String) -> CaseData:
	var c := CaseData.new()
	c.id = StringName(data.get("id", case_dir.get_file()))
	c.title = data.get("title", "")
	c.description = data.get("description", "")
	c.duration = float(data.get("duration", 60.0))
	c.truth = data.get("truth", "")

	for ch: Dictionary in data.get("characters", []):
		var cd := CharacterData.new()
		cd.id = StringName(ch.id)
		cd.display_name = ch.get("name", "")
		cd.label = ch.get("label", String(ch.id))
		cd.color = Color.from_string(ch.get("color", "#ffffff"), Color.WHITE)
		for k: Dictionary in ch.get("track", []):
			var key := TrackKey.make(
				float(k.t), _vec(k.p), MOVEMENT_NAMES.get(k.get("m", "idle"), TrackKey.Movement.IDLE)
			)
			key.room = StringName(k.get("room", ""))
			cd.track.append(key)
		TrackMath.sort_track(cd.track)
		c.characters.append(cd)

	for l: Dictionary in data.get("voice_lines", []):
		var line := VoiceLine.new()
		line.speaker = StringName(l.speaker)
		line.start = float(l.start)
		line.duration = float(l.get("duration", 1.0))
		line.text = l.get("text", "")
		line.volume_db = float(l.get("volume_db", 0.0))
		line.loudness = float(l.get("loudness", 0.5))
		line.stream = _load_stream(case_dir, l.get("audio", ""))
		c.voice_lines.append(line)
	c.sort_voice_lines()

	for s: Dictionary in data.get("sfx", []):
		var ev := SfxEvent.new()
		ev.time = float(s.time)
		ev.duration = float(s.get("duration", 1.0))
		ev.position = _vec(s.get("position", [0, 0]))
		ev.attach_to = StringName(s.get("attach_to", ""))
		ev.loudness = float(s.get("loudness", 0.5))
		ev.volume_db = float(s.get("volume_db", 0.0))
		ev.label = s.get("label", "")
		ev.stream = _load_stream(case_dir, s.get("audio", ""))
		c.sfx_events.append(ev)

	for q: Dictionary in data.get("questions", []):
		var question := Question.new()
		question.id = StringName(q.id)
		question.kind = KIND_NAMES.get(q.get("kind", "choice"), Question.Kind.CHOICE)
		question.prompt = q.get("prompt", "")
		question.options = PackedStringArray(q.get("options", []))
		question.answer = q.get("answer", "")
		c.questions.append(question)
	return c


## CaseData（+ 可选地图）导出为 JSON 字典。音频路径相对于 `case_dir`。
static func export_case(c: CaseData, case_dir: String) -> Dictionary:
	var out := {
		"format": FORMAT,
		"id": String(c.id),
		"title": c.title,
		"description": c.description,
		"duration": c.duration,
		"truth": c.truth,
		"characters": [],
		"voice_lines": [],
		"sfx": [],
		"questions": [],
	}
	if c.map_scene:
		var map := c.map_scene.instantiate() as CaseMap
		out["map"] = export_map(map)
		map.free()
	var movement_keys := _invert(MOVEMENT_NAMES)
	for ch in c.characters:
		var track := []
		for k in ch.track:
			var kd := {"t": k.time, "p": [k.position.x, k.position.y], "m": movement_keys[k.movement]}
			if k.room != &"":
				kd["room"] = String(k.room)
			track.append(kd)
		out.characters.append(
			{
				"id": String(ch.id),
				"name": ch.display_name,
				"label": ch.label,
				"color": "#" + ch.color.to_html(false),
				"track": track
			}
		)
	for l in c.voice_lines:
		var ld := {"speaker": String(l.speaker), "start": l.start, "duration": l.duration, "text": l.text}
		if l.loudness != 0.5:
			ld["loudness"] = l.loudness
		if l.volume_db != 0.0:
			ld["volume_db"] = l.volume_db
		if l.stream:
			ld["audio"] = _relative(case_dir, l.stream.resource_path)
		out.voice_lines.append(ld)
	for s in c.sfx_events:
		var sd := {
			"time": s.time,
			"duration": s.duration,
			"position": [s.position.x, s.position.y],
			"loudness": s.loudness,
			"label": s.label,
		}
		if s.attach_to != &"":
			sd["attach_to"] = String(s.attach_to)
		if s.stream:
			sd["audio"] = _relative(case_dir, s.stream.resource_path)
		out.sfx.append(sd)
	var kind_keys := _invert(KIND_NAMES)
	for q in c.questions:
		out.questions.append(
			{
				"id": String(q.id),
				"kind": kind_keys[q.kind],
				"prompt": q.prompt,
				"options": Array(q.options),
				"answer": q.answer
			}
		)
	return out


static func export_map(map: CaseMap) -> Dictionary:
	var m := {"floors": Array(map.floor_names), "rooms": [], "doors": [], "stairs": []}
	for r in map.get_rooms():
		var poly := []
		for p in r.polygon:
			var g := p + r.position
			poly.append([g.x, g.y])
		m.rooms.append({"name": r.room_name, "floor": r.floor_index, "polygon": poly})
	for d in map.get_doors():
		(
			m
			. doors
			. append(
				{
					"name": String(d.name),
					"room_a": d.room_a,
					"room_b": d.room_b,
					"position": [d.position.x, d.position.y],
					"size": [d.size.x, d.size.y],
					"open": d.open,
				}
			)
		)
	for s in map.get_stairs():
		(
			m
			. stairs
			. append(
				{
					"name": String(s.name),
					"room_a": s.room_a,
					"room_b": s.room_b,
					"end_a": [s.position.x, s.position.y],
					"end_b": [s.end_b.x, s.end_b.y],
				}
			)
		)
	return m


static func write_json(path: String, data: Dictionary) -> Error:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(data, " ", false))
	return OK


static func _load_stream(case_dir: String, rel: String) -> AudioStream:
	if rel == "":
		return null
	var path := case_dir.path_join(rel)
	if not ResourceLoader.exists(path):
		push_warning("音频不存在或尚未导入：%s" % path)
		return null
	return load(path) as AudioStream


static func _group(map: CaseMap, group_name: String) -> Node2D:
	var g := Node2D.new()
	g.name = group_name
	map.add_child(g)
	g.owner = map
	return g


static func _attach(parent: Node, child: Node, owner_node: Node) -> void:
	parent.add_child(child, true)
	child.owner = owner_node


static func _vec(a: Variant) -> Vector2:
	if a is Array and a.size() >= 2:
		return Vector2(float(a[0]), float(a[1]))
	return Vector2.ZERO


static func _node_name(s: String) -> String:
	return s.validate_node_name() if s != "" else "Node"


static func _relative(case_dir: String, path: String) -> String:
	var prefix := case_dir.trim_suffix("/") + "/"
	return path.trim_prefix(prefix)


static func _invert(d: Dictionary) -> Dictionary:
	var out := {}
	for k: Variant in d:
		out[d[k]] = k
	return out
