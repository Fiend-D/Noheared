extends GdUnitTestSuite
## 编辑器时间轴：拖动关键帧不能越过相邻关键帧，拖动台词按 0.1s 吸附。

const TimelineView := preload("res://addons/case_editor/timeline_view.gd")

var view: Control
var data: CaseData


func before_test() -> void:
	data = TestFixtures.make_case()
	view = auto_free(TimelineView.new())
	view.set_case(data)
	view.pixels_per_second = 10.0


func test_key_drag_is_clamped_between_neighbours() -> void:
	var key: TrackKey = data.characters[0].track[1]
	view._press(view._key_center(0, key))
	view._drag_to(view._key_center(0, key).x + 500.0)
	assert_float(key.time).is_equal(20.0)
	view._drag_to(view._key_center(0, key).x - 5000.0)
	assert_float(key.time).is_equal(0.0)


func test_line_drag_snaps_and_stays_in_case() -> void:
	var line: VoiceLine = data.voice_lines[0]
	var rect: Rect2 = view._line_rect(line)
	view._press(rect.get_center())
	view._drag_to(rect.get_center().x + 13.0)
	assert_float(line.start).is_equal_approx(3.3, 0.0001)
	view._drag_to(rect.get_center().x + 99999.0)
	assert_float(line.start).is_equal(data.duration - line.duration)


func test_click_on_empty_area_requests_preview() -> void:
	var requested := [-1.0]
	view.preview_requested.connect(func(t: float) -> void: requested[0] = t)
	view._press(Vector2(view.time_to_x(42.0), 2.0))
	assert_float(requested[0]).is_equal_approx(42.0, 0.001)
