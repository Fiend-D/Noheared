extends GdUnitTestSuite

var acoustics: Acoustics


func before_test() -> void:
	var map: CaseMap = auto_free(TestFixtures.make_map())
	acoustics = map.build_acoustics()


func test_same_room_is_clear_on_room_bus() -> void:
	var r := acoustics.resolve(&"A", &"A", 0.5)
	assert_int(r.clarity).is_equal(Acoustics.Clarity.CLEAR)
	assert_str(String(r.bus)).is_equal(String(Acoustics.BUS_ROOM))
	assert_float(r.gain_db).is_equal(0.0)


func test_adjacent_open_door_is_muffled() -> void:
	var r := acoustics.resolve(&"A", &"B", 0.5)
	assert_int(r.clarity).is_equal(Acoustics.Clarity.MUFFLED)
	assert_str(String(r.bus)).is_equal(String(Acoustics.BUS_MUFFLED))
	assert_float(r.gain_db).is_less(0.0)


func test_closed_door_blocks_normal_speech() -> void:
	assert_int(acoustics.cost_between(&"B", &"C")).is_equal(Acoustics.CLOSED_DOOR_COST)
	assert_int(acoustics.resolve(&"B", &"C", 0.5).clarity).is_equal(Acoustics.Clarity.NONE)


func test_loud_event_carries_through_several_rooms() -> void:
	var r := acoustics.resolve(&"A", &"C", 1.0)
	assert_int(r.cost).is_equal(3)
	assert_int(r.clarity).is_equal(Acoustics.Clarity.MUFFLED)
	assert_str(String(r.bus)).is_equal(String(Acoustics.BUS_FAR))
	var near := acoustics.resolve(&"A", &"B", 1.0)
	assert_float(r.gain_db).is_less(near.gain_db)


func test_unconnected_or_unknown_rooms_are_silent() -> void:
	assert_int(acoustics.resolve(&"A", &"D", 1.0).clarity).is_equal(Acoustics.Clarity.NONE)
	assert_int(acoustics.resolve(&"", &"A", 1.0).clarity).is_equal(Acoustics.Clarity.NONE)
	assert_int(acoustics.cost_between(&"A", &"Nowhere")).is_equal(-1)


func test_cost_is_symmetric() -> void:
	assert_int(acoustics.cost_between(&"C", &"A")).is_equal(acoustics.cost_between(&"A", &"C"))
