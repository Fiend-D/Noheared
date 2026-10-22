extends GdUnitTestSuite
## 拖动、倒退后的状态必须与顺序播放到同一时刻完全一致。

const CASE_PATH := "res://cases/case5/case.tres"


func test_active_line_indices() -> void:
	var data := TestFixtures.make_case()
	data.sort_voice_lines()
	assert_array(Array(CueScheduler.active_line_indices(data.voice_lines, 1.0))).is_empty()
	assert_array(Array(CueScheduler.active_line_indices(data.voice_lines, 4.5))).is_equal([0, 1])
	assert_array(Array(CueScheduler.active_line_indices(data.voice_lines, 5.0))).is_equal([1])
	assert_array(Array(CueScheduler.active_line_indices(data.voice_lines, 31.0))).is_equal([2])


func test_game_state_after_seek_matches_sequential_playback() -> void:
	var data: CaseData = load(CASE_PATH)
	var game := Game.new()
	game.case_data = data
	game.persist = false
	game.ui_theme = UiTheme.build()
	add_child(game)
	auto_free(game)
	await await_idle_frame()

	var checkpoints := [125.0, 640.0, 1250.0]
	var sequential := {}
	for t: float in checkpoints:
		game.clock.seek(t)
		await await_idle_frame()
		sequential[t] = _snapshot(game)

	for t: float in [1250.0, 125.0, 640.0]:
		game.clock.seek(1799.0)
		await await_idle_frame()
		game.clock.seek(t)
		await await_idle_frame()
		assert_dict(_snapshot(game)).is_equal(sequential[t])


func _snapshot(game: Game) -> Dictionary:
	var positions := {}
	for c in game.case_data.characters:
		positions[String(c.id)] = [game.actors.get_pose(c.id).position, game.actors.get_room_name(c.id)]
	var lines := []
	for a in game.scheduler.active_lines:
		lines.append([a.index, a.clarity])
	return {"positions": positions, "lines": lines}
