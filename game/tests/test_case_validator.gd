extends GdUnitTestSuite

var map: CaseMap
var data: CaseData


func before_test() -> void:
	map = auto_free(TestFixtures.make_map())
	data = TestFixtures.make_case()


func _errors(issues: PackedStringArray) -> Array:
	return Array(issues).filter(func(s: String) -> bool: return s.begins_with("ERROR"))


func test_fixture_has_no_errors() -> void:
	assert_array(_errors(CaseValidator.validate(data, map))).is_empty()


func test_detects_walking_through_walls() -> void:
	data.characters[0].track.append(TrackKey.make(30.0, Vector2(450, 50)))
	var errors := _errors(CaseValidator.validate(data, map))
	assert_int(errors.size()).is_equal(1)
	assert_str(errors[0]).contains("不相连")


func test_detects_bad_answer_and_unknown_speaker() -> void:
	data.questions[0].answer = "不存在的人"
	data.voice_lines[0].speaker = &"X"
	var errors := _errors(CaseValidator.validate(data, map))
	assert_int(errors.size()).is_equal(2)


func test_warns_on_overlapping_lines() -> void:
	data.voice_lines[2].start = 3.0
	data.sort_voice_lines()
	var issues := Array(CaseValidator.validate(data, map))
	assert_bool(issues.any(func(s: String) -> bool: return s.contains("重叠"))).is_true()


func test_warns_on_dead_air() -> void:
	var issues := Array(CaseValidator.validate(data, map))
	assert_bool(issues.any(func(s: String) -> bool: return s.contains("6.0s 起全图空窗 24.0s"))).is_true()
	assert_bool(issues.any(func(s: String) -> bool: return s.contains("留白"))).is_true()
	data.voice_lines[2].start = 20.0
	data.duration = 30.0
	issues = Array(CaseValidator.validate(data, map))
	assert_bool(issues.any(func(s: String) -> bool: return s.contains("空窗") or s.contains("留白"))).is_false()
