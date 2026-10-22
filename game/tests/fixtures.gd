class_name TestFixtures
extends RefCounted
## 测试用的小地图和小案件：A —门— B —关着的门— C，D 与其他房间不相连。


static func rect(x: float, y: float, w: float, h: float) -> PackedVector2Array:
	return PackedVector2Array([Vector2(x, y), Vector2(x + w, y), Vector2(x + w, y + h), Vector2(x, y + h)])


static func make_map() -> CaseMap:
	var map := CaseMap.new()
	for spec: Array in [["A", 0, 0], ["B", 100, 0], ["C", 200, 0], ["D", 400, 0]]:
		var room := Room.new()
		room.room_name = spec[0]
		room.polygon = rect(spec[1], spec[2], 100, 100)
		map.add_child(room)
	map.add_child(_door("A", "B", Vector2(100, 50), true))
	map.add_child(_door("B", "C", Vector2(200, 50), false))
	return map


static func _door(a: String, b: String, pos: Vector2, is_open: bool) -> Door:
	var d := Door.new()
	d.room_a = a
	d.room_b = b
	d.position = pos
	d.open = is_open
	return d


static func make_case() -> CaseData:
	var c := CaseData.new()
	c.id = &"fixture"
	c.duration = 60.0
	var walker := CharacterData.new()
	walker.id = &"W"
	walker.display_name = "行人"
	walker.label = "1"
	walker.track = [
		TrackKey.make(0.0, Vector2(50, 50)),
		TrackKey.make(10.0, Vector2(50, 50), TrackKey.Movement.WALK),
		TrackKey.make(20.0, Vector2(150, 50)),
	]
	var sitter := CharacterData.new()
	sitter.id = &"S"
	sitter.display_name = "坐着的人"
	sitter.label = "2"
	sitter.track = [TrackKey.make(0.0, Vector2(250, 50))]
	c.characters = [walker, sitter]
	c.voice_lines = [_line(&"W", 2.0, 3.0, "你好"), _line(&"S", 4.0, 2.0, "嗯"), _line(&"W", 30.0, 2.0, "再见")]
	var q := Question.new()
	q.id = &"q1"
	q.kind = Question.Kind.CHARACTER
	q.prompt = "谁在走路？"
	q.answer = "行人"
	c.questions = [q]
	return c


static func _line(speaker: StringName, start: float, duration: float, text: String) -> VoiceLine:
	var l := VoiceLine.new()
	l.speaker = speaker
	l.start = start
	l.duration = duration
	l.text = text
	return l
