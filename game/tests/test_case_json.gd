extends GdUnitTestSuite

const CASE_DIR := "res://cases/case1"


func _source() -> Dictionary:
	return JSON.parse_string(FileAccess.get_file_as_string(CASE_DIR.path_join("case.json")))


func test_build_map_from_json() -> void:
	var src := _source()
	var map: CaseMap = auto_free(CaseJson.build_map(src.map))
	assert_int(map.get_rooms().size()).is_equal(src.map.rooms.size())
	assert_int(map.get_doors().size()).is_equal(src.map.doors.size())
	var first: Dictionary = src.map.rooms[0]
	var room := map.get_room(first.name)
	assert_object(room).is_not_null()
	var p: Array = first.polygon[0]
	assert_object(map.room_at(Vector2(p[0], p[1]) + Vector2(5, 5))).is_same(room)


func test_export_round_trip_preserves_content() -> void:
	var src := _source()
	var data := CaseJson.build_case(src, CASE_DIR)
	var map: CaseMap = auto_free(CaseJson.build_map(src.map))
	var exported := CaseJson.export_case(data, CASE_DIR)
	exported["map"] = CaseJson.export_map(map)
	var again := CaseJson.build_case(exported, CASE_DIR)
	assert_str(again.title).is_equal(data.title)
	assert_int(again.characters.size()).is_equal(data.characters.size())
	assert_int(again.voice_lines.size()).is_equal(data.voice_lines.size())
	for i in data.voice_lines.size():
		assert_float(again.voice_lines[i].start).is_equal(data.voice_lines[i].start)
		assert_str(again.voice_lines[i].text).is_equal(data.voice_lines[i].text)
		assert_bool(again.voice_lines[i].stream != null).is_equal(data.voice_lines[i].stream != null)
	for i in data.characters.size():
		assert_int(again.characters[i].track.size()).is_equal(data.characters[i].track.size())
		assert_str(again.characters[i].color.to_html(false)).is_equal(data.characters[i].color.to_html(false))
	assert_int(again.questions[0].kind).is_equal(data.questions[0].kind)


func test_imported_cases_validate_without_errors() -> void:
	for path in CaseLibrary.list_case_paths():
		var data: CaseData = load(path)
		var map: CaseMap = auto_free(data.map_scene.instantiate())
		var errors := Array(CaseValidator.validate(data, map)).filter(
			func(s: String) -> bool: return s.begins_with("ERROR")
		)
		assert_array(errors).override_failure_message("%s: %s" % [path, errors]).is_empty()
