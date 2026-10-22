extends GdUnitTestSuite

var clock: TimelineClock


func before_test() -> void:
	clock = auto_free(TimelineClock.new(30.0))


func test_advances_only_by_speed() -> void:
	clock.play()
	clock.set_speed(2.0)
	clock.advance(1.5)
	assert_float(clock.time).is_equal_approx(3.0, 0.0001)


func test_stops_at_end_and_emits_finished() -> void:
	var finished := [false]
	clock.finished.connect(func() -> void: finished[0] = true)
	clock.play()
	clock.advance(100.0)
	assert_float(clock.time).is_equal(30.0)
	assert_bool(clock.playing).is_false()
	assert_bool(finished[0]).is_true()


func test_seek_clamps_and_emits() -> void:
	var seen := []
	clock.seeked.connect(func(t: float) -> void: seen.append(t))
	clock.seek(-4.0)
	clock.seek(12.5)
	clock.seek(99.0)
	assert_array(seen).is_equal([0.0, 12.5, 30.0])


func test_play_at_end_restarts() -> void:
	clock.seek(30.0)
	clock.play()
	assert_float(clock.time).is_equal(0.0)


func test_cycle_speed_wraps() -> void:
	var speeds := []
	for i in TimelineClock.SPEEDS.size():
		speeds.append(clock.cycle_speed())
	assert_array(speeds).is_equal([2.0, 4.0, 0.5, 1.0])
