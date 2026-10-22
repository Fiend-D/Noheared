@tool
class_name CaseValidator
extends RefCounted
## 案件数据校验。返回 "ERROR: ..." / "WARN: ..." 形式的提示列表。


static func validate(c: CaseData, map: CaseMap) -> PackedStringArray:
	var issues := PackedStringArray()
	if c.duration <= 0.0:
		issues.append("ERROR: 案件时长必须大于 0")
	if c.map_scene == null and map == null:
		issues.append("ERROR: 缺少地图")

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

	_check_lines(c, ids, issues)

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
