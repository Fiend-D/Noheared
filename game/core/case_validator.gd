@tool
class_name CaseValidator
extends RefCounted
## 案件数据校验。返回 "ERROR: ..." / "WARN: ..." 形式的提示列表。

const MAX_DOOR_GAP := 80.0
const FURNITURE_SAMPLE := 4.0
## 与 tools/pacing.py 保持一致：全图无声的上限（秒）。
const MAX_GAP := 20.0
const MAX_OPENING := 10.0
const MAX_TAIL := 15.0


static func validate(c: CaseData, map: CaseMap) -> PackedStringArray:
	var issues := PackedStringArray()
	if c.duration <= 0.0:
		issues.append("ERROR: 案件时长必须大于 0")
	if c.map_scene == null and map == null:
		issues.append("ERROR: 缺少地图")

	if map:
		_check_map(map, issues)

	var ids := {}
	for ch in c.characters:
		if ids.has(ch.id):
			issues.append("ERROR: 角色 id 重复：%s" % ch.id)
		ids[ch.id] = true
		if ch.track.is_empty():
			issues.append("ERROR: 角色 %s 没有任何关键帧" % ch.id)
			continue
		if map:
			_check_track(ch, map, issues)
			_check_furniture(ch, map, issues)

	_check_lines(c, ids, issues)
	_check_pacing(c, issues)
	if map:
		_check_speech_positions(c, map, issues)

	for ev in c.sfx_events:
		if ev.attach_to != &"" and not ids.has(ev.attach_to):
			issues.append("ERROR: 音效 %s 绑定了不存在的角色 %s" % [ev.label, ev.attach_to])
		if ev.time < 0.0 or ev.time > c.duration:
			issues.append("ERROR: 音效 %s 的时间 %.1f 超出案件范围" % [ev.label, ev.time])

	for q in c.questions:
		var options := c.options_for(q)
		if options.is_empty():
			issues.append("ERROR: 问题 %s 没有选项" % q.id)
		elif not options.has(q.answer):
			issues.append("ERROR: 问题 %s 的答案“%s”不在选项中" % [q.id, q.answer])
	return issues


## 同层房间不能重叠；门必须贴着它连接的两个房间，否则监听者走不过去；家具必须在所属房间内。
static func _check_map(map: CaseMap, issues: PackedStringArray) -> void:
	var rooms := map.get_rooms()
	for i in rooms.size():
		for j in range(i + 1, rooms.size()):
			var a := rooms[i]
			var b := rooms[j]
			if a.floor_index != b.floor_index:
				continue
			for overlap in Geometry2D.intersect_polygons(a.polygon, b.polygon):
				if _area(overlap) > 1.0:
					issues.append("ERROR: 房间 %s 与 %s 重叠" % [a.room_name, b.room_name])
					break
	map.refresh()
	for d in map.get_doors():
		for side in [[d.room_a, d.end_a], [d.room_b, d.end_b]]:
			var room := map.get_room(side[0])
			if room == null:
				issues.append("ERROR: 门 %s 连接了不存在的房间 %s" % [d.name, side[0]])
			elif room.closest_wall_point(side[1]).distance_to(side[1]) > 1.0:
				issues.append("ERROR: 门 %s 没有对着房间 %s 的墙" % [d.name, side[0]])
		if d.passage_length() > MAX_DOOR_GAP:
			issues.append("ERROR: 门 %s 两侧房间相距 %.0f，超过 %.0f" % [d.name, d.passage_length(), MAX_DOOR_GAP])
	for p in map.get_props():
		var room := map.get_room(p.room_name)
		if room == null or not room.contains_point(p.position):
			issues.append("ERROR: 家具 %s 不在房间 %s 里" % [p.name, p.room_name])
		if p.texture == null:
			issues.append("WARN: 家具 %s 的类型 %s 不在家具目录里" % [p.name, p.prop_type])


## 角色应当先走到位再开口、说完再离开：开口时还在走，或说话途中换了房间，都提示出来。
static func _check_speech_positions(c: CaseData, map: CaseMap, issues: PackedStringArray) -> void:
	for line in c.voice_lines:
		var ch := c.get_character(line.speaker)
		if ch == null or ch.track.is_empty():
			continue
		var at_start := TrackMath.sample(ch.track, line.start + 0.05)
		var at_end := TrackMath.sample(ch.track, line.end_time())
		if at_start.moving:
			issues.append("WARN: 角色 %s 在 %.1fs 开口时还在走：%s" % [ch.id, line.start, line.text.left(16)])
		elif map.room_for_pose(ch, at_start) != map.room_for_pose(ch, at_end):
			issues.append("WARN: 角色 %s 在 %.1fs 的台词说到一半换了房间：%s" % [ch.id, line.start, line.text.left(16)])


static func _area(poly: PackedVector2Array) -> float:
	var s := 0.0
	for i in poly.size():
		s += poly[i].cross(poly[(i + 1) % poly.size()])
	return absf(s) * 0.5


## 相邻关键帧所在房间必须相同或通过门/楼梯直接相连（门洞中的帧跳过），否则就是穿墙。
static func _check_track(ch: CharacterData, map: CaseMap, issues: PackedStringArray) -> void:
	var prev_time := -INF
	var prev_room: Room = null
	for k in ch.track:
		if k.time < prev_time:
			issues.append("ERROR: 角色 %s 的关键帧没有按时间排序（%.2f）" % [ch.id, k.time])
		prev_time = k.time
		var room := map.room_at(k.position, k.room)
		if room == null:
			continue
		if k.room != &"" and room.room_name != String(k.room):
			issues.append("WARN: 角色 %s 在 %.1fs 的关键帧标注为 %s，但坐标在 %s" % [ch.id, k.time, k.room, room.room_name])
		if prev_room and prev_room != room and not map.rooms_adjacent(prev_room.room_name, room.room_name):
			issues.append(
				"ERROR: 角色 %s 在 %.1fs 从 %s 直接到了 %s（两房间不相连）" % [ch.id, k.time, prev_room.room_name, room.room_name]
			)
		prev_room = room


## 角色轨迹不能穿过挡路的家具（角色按关键帧直线移动，不会绕开家具）。
static func _check_furniture(ch: CharacterData, map: CaseMap, issues: PackedStringArray) -> void:
	var props := map.get_props().filter(func(p: Prop) -> bool: return p.blocks)
	if props.is_empty():
		return
	var reported := {}
	for i in ch.track.size():
		var a := ch.track[i].position
		var b := ch.track[mini(i + 1, ch.track.size() - 1)].position
		# 楼梯两端不在同一层，地图上两点间的连线不是实际路线
		if _floor_of(map, ch.track[i].room) != _floor_of(map, ch.track[mini(i + 1, ch.track.size() - 1)].room):
			continue
		var steps := maxi(int(a.distance_to(b) / FURNITURE_SAMPLE), 1)
		for s in steps + 1:
			var p := a.lerp(b, float(s) / steps)
			for prop: Prop in props:
				if not reported.has(prop) and prop.footprint().has_point(p) and prop.room_name == _room_name(map, p):
					reported[prop] = true
					issues.append("WARN: 角色 %s 在 %.1fs 穿过家具 %s" % [ch.id, ch.track[i].time, prop.name])


static func _floor_of(map: CaseMap, room_name: String) -> int:
	var r := map.get_room(room_name)
	return r.floor_index if r else -1


static func _room_name(map: CaseMap, p: Vector2) -> String:
	var r := map.room_at(p)
	return r.room_name if r else ""


## 空窗期：全图任何地方都没有台词和音效的时间段。
static func _check_pacing(c: CaseData, issues: PackedStringArray) -> void:
	var spans: Array[Vector2] = []
	for line in c.voice_lines:
		spans.append(Vector2(line.start, line.end_time()))
	for ev in c.sfx_events:
		spans.append(Vector2(ev.time, ev.time + ev.duration))
	if spans.is_empty():
		return
	spans.sort_custom(func(a: Vector2, b: Vector2) -> bool: return a.x < b.x)
	if spans[0].x > MAX_OPENING:
		issues.append("WARN: 开场 %.1fs 才有第一声（上限 %.0fs）" % [spans[0].x, MAX_OPENING])
	var t := spans[0].y
	for s in spans:
		if s.x - t > MAX_GAP:
			issues.append("WARN: %.1fs 起全图空窗 %.1fs（上限 %.0fs）" % [t, s.x - t, MAX_GAP])
		t = maxf(t, s.y)
	if c.duration - t > MAX_TAIL:
		issues.append("WARN: 最后一声之后还有 %.1fs 留白（上限 %.0fs）" % [c.duration - t, MAX_TAIL])


static func _check_lines(c: CaseData, ids: Dictionary, issues: PackedStringArray) -> void:
	var last_end := {}
	var sorted := c.voice_lines.duplicate()
	sorted.sort_custom(func(a: VoiceLine, b: VoiceLine) -> bool: return a.start < b.start)
	var missing_audio := 0
	for line: VoiceLine in sorted:
		if not ids.has(line.speaker):
			issues.append("ERROR: 台词“%s”的说话人 %s 不存在" % [line.text.left(16), line.speaker])
		if line.start < 0.0 or line.end_time() > c.duration + 0.01:
			issues.append("ERROR: 台词“%s”超出案件时间范围" % line.text.left(16))
		if line.duration <= 0.0:
			issues.append("ERROR: 台词“%s”的时长必须大于 0" % line.text.left(16))
		if last_end.get(line.speaker, -INF) > line.start + 0.01:
			issues.append("WARN: 角色 %s 在 %.1fs 的台词与上一句重叠" % [line.speaker, line.start])
		last_end[line.speaker] = maxf(last_end.get(line.speaker, -INF), line.end_time())
		if line.stream == null:
			missing_audio += 1
	if missing_audio > 0:
		issues.append("WARN: %d 句台词没有语音（只显示字幕）" % missing_audio)
