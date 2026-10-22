extends GdUnitTestSuite

var track: Array[TrackKey]


func before_test() -> void:
	track = [
		TrackKey.make(0.0, Vector2(0, 0)),
		TrackKey.make(10.0, Vector2(0, 0), TrackKey.Movement.RUN),
		TrackKey.make(20.0, Vector2(100, 0)),
	]


func test_holds_first_position_before_first_key() -> void:
	var pose := TrackMath.sample(track, -5.0)
	assert_vector(pose.position).is_equal(Vector2(0, 0))
	assert_int(pose.key_index).is_equal(-1)
	assert_bool(pose.moving).is_false()


func test_interpolates_between_keys() -> void:
	var pose := TrackMath.sample(track, 15.0)
	assert_vector(pose.position).is_equal_approx(Vector2(50, 0), Vector2(0.001, 0.001))
	assert_bool(pose.moving).is_true()
	assert_int(pose.movement).is_equal(TrackKey.Movement.RUN)


func test_idle_while_holding() -> void:
	var pose := TrackMath.sample(track, 5.0)
	assert_bool(pose.moving).is_false()
	assert_vector(pose.position).is_equal(Vector2(0, 0))


func test_holds_last_position_after_end() -> void:
	assert_vector(TrackMath.sample(track, 999.0).position).is_equal(Vector2(100, 0))


func test_sampling_is_independent_of_history() -> void:
	var forward := []
	for t in range(0, 25):
		forward.append(TrackMath.sample(track, t * 0.9).position)
	for t in range(24, -1, -1):
		assert_vector(TrackMath.sample(track, t * 0.9).position).is_equal(forward[t])


func test_key_index_binary_search() -> void:
	assert_int(TrackMath.key_index_at(track, 0.0)).is_equal(0)
	assert_int(TrackMath.key_index_at(track, 10.0)).is_equal(1)
	assert_int(TrackMath.key_index_at(track, 19.99)).is_equal(1)
	assert_int(TrackMath.key_index_at(track, 20.0)).is_equal(2)
