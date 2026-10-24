extends GdUnitTestSuite
## 监听者走动：墙挡路，只能经门洞进出，踩楼梯口换楼层，点击房间沿门洞寻路。

const DT := 1.0 / 60.0

var map: CaseMap
var listener: Listener


func before_test() -> void:
	map = auto_free(TestFixtures.make_map())
	var upstairs := Room.new()
	upstairs.room_name = "E"
	upstairs.floor_index = 1
	upstairs.polygon = TestFixtures.rect(0, 300, 100, 100)
	map.add_child(upstairs)
	var stair := Stair.new()
	stair.room_a = "A"
	stair.room_b = "E"
	stair.position = Vector2(50, 80)
	stair.end_b = Vector2(50, 320)
	map.add_child(stair)
	map.refresh()
	listener = auto_free(Listener.new())
	listener.setup(map)
	listener.place(Vector2(50, 50), map.get_room("A"))


func _walk(direction: Vector2, seconds: float) -> void:
	for i in int(seconds / DT):
		listener.step(direction, false, DT)


func test_shared_wall_door_passage() -> void:
	var door := map.get_doors()[0]
	assert_vector(door.end_a).is_equal(Vector2(100, 50))
	assert_vector(door.end_b).is_equal(Vector2(100, 50))
	assert_vector(door.axis).is_equal(Vector2.RIGHT)


func test_walkable_areas() -> void:
	assert_bool(map.is_walkable(Vector2(50, 50), 0)).is_true()
	assert_bool(map.is_walkable(Vector2(100, 50), 0)).is_true()
	assert_bool(map.is_walkable(Vector2(100, 20), 0)).is_false()
	assert_bool(map.is_walkable(Vector2(350, 50), 0)).is_false()
	assert_bool(map.is_walkable(Vector2(50, 350), 0)).is_false()


func test_walks_through_door_into_next_room() -> void:
	_walk(Vector2.RIGHT, 0.6)
	assert_str(listener.room.room_name).is_equal("B")


func test_door_assist_lines_up_with_doorway() -> void:
	listener.place(Vector2(50, 38), map.get_room("A"))
	_walk(Vector2.RIGHT, 0.7)
	assert_str(listener.room.room_name).is_equal("B")


func test_wall_blocks_walking() -> void:
	listener.place(Vector2(50, 15), map.get_room("A"))
	_walk(Vector2.RIGHT, 2.0)
	assert_str(listener.room.room_name).is_equal("A")
	assert_float(listener.position.x).is_less_equal(100.0 - CaseMap.WALK_MARGIN)


func test_stair_switches_floor() -> void:
	var floors: Array[int] = []
	listener.floor_changed.connect(func(f: int) -> void: floors.append(f))
	_walk(Vector2.DOWN, 1.0)
	assert_str(listener.room.room_name).is_equal("E")
	assert_int(listener.floor_index).is_equal(1)
	assert_array(floors).contains_exactly([1])


func test_same_floor_stair_works_both_ways() -> void:
	var stair: Stair = auto_free(Stair.new())
	stair.room_a = "A"
	stair.room_b = "D"
	stair.position = Vector2(20, 50)
	stair.end_b = Vector2(480, 50)
	map.add_child(stair)
	map.refresh()
	listener.place(Vector2(60, 50), map.get_room("A"))
	_walk(Vector2.LEFT, 0.5)
	assert_str(listener.room.room_name).is_equal("D")
	_walk(Vector2.LEFT, 0.3)
	_walk(Vector2.RIGHT, 0.6)
	assert_str(listener.room.room_name).is_equal("A")
	assert_int(listener.floor_index).is_equal(0)


func test_click_route_goes_through_doors() -> void:
	var target := Vector2(250, 60)
	listener.walk_to(target, map.get_room("C"))
	assert_bool(listener.has_path()).is_true()
	_walk(Vector2.ZERO, 5.0)
	assert_bool(listener.has_path()).is_false()
	assert_vector(listener.position).is_equal(target)
	assert_str(listener.room.room_name).is_equal("C")


func test_unreachable_room_keeps_position() -> void:
	listener.walk_to(Vector2(450, 50), map.get_room("D"))
	_walk(Vector2.ZERO, 1.0)
	assert_str(listener.room.room_name).is_equal("A")
	assert_vector(listener.position).is_equal(Vector2(50, 50))


func test_every_door_in_cases_is_walkable() -> void:
	for path in CaseLibrary.list_case_paths():
		var data := CaseLibrary.load_case(path)
		var case_map: CaseMap = auto_free(data.map_scene.instantiate())
		case_map.refresh()
		var walker: Listener = auto_free(Listener.new())
		walker.setup(case_map)
		for door in case_map.get_doors():
			for from in [door.room_a, door.room_b]:
				var to: String = door.room_b if from == door.room_a else door.room_a
				var dir: Vector2 = door.axis if from == door.room_a else -door.axis
				var start: Vector2 = door.mouth(from, 20.0) + dir.orthogonal() * door.half_width * 0.8
				walker.place(start, case_map.get_room(from))
				var reached := false
				for i in 120:
					walker.step(dir, false, DT)
					if walker.room and walker.room.room_name == to:
						reached = true
						break
				assert_bool(reached).override_failure_message("%s: %s -> %s" % [data.id, from, to]).is_true()


func test_furniture_blocks_and_click_route_goes_around() -> void:
	var prop: Prop = auto_free(Prop.new())
	prop.size = Vector2(20, 60)
	prop.position = Vector2(60, 50)
	prop.room_name = "A"
	map.add_child(prop)
	map.refresh()
	assert_bool(map.is_walkable(Vector2(60, 50), 0)).is_false()
	listener.place(Vector2(25, 50), map.get_room("A"))
	_walk(Vector2.RIGHT, 1.0)
	assert_str(listener.room.room_name).is_equal("A")
	var target := Vector2(150, 50)
	listener.walk_to(target, map.get_room("B"))
	_walk(Vector2.ZERO, 3.0)
	assert_vector(listener.position).is_equal(target)
	assert_str(listener.room.room_name).is_equal("B")


func test_furniture_never_cuts_off_doors_or_stairs() -> void:
	for path in CaseLibrary.list_case_paths():
		var data := CaseLibrary.load_case(path)
		var case_map: CaseMap = auto_free(data.map_scene.instantiate())
		case_map.refresh()
		for room in case_map.get_rooms():
			var exits: Array[Vector2] = []
			for d in case_map.get_doors():
				if room.room_name in [d.room_a, d.room_b]:
					exits.append(d.mouth(room.room_name, CaseMap.ROUTE_DOOR_DEPTH))
			for s in case_map.get_stairs():
				if room.room_name in [s.room_a, s.room_b]:
					exits.append(s.end_in(room.room_name))
			for i in range(1, exits.size()):
				var legs := case_map.route(room, exits[i], room, exits[0])
				var msg := "%s %s: %s -> %s" % [data.id, room.room_name, exits[0], exits[i]]
				assert_bool(legs.is_empty()).override_failure_message(msg).is_false()


func test_route_across_floors_uses_stairs() -> void:
	listener.walk_to(Vector2(50, 360), map.get_room("E"))
	_walk(Vector2.ZERO, 3.0)
	assert_str(listener.room.room_name).is_equal("E")
	assert_int(listener.floor_index).is_equal(1)


func test_click_stair_walks_there_and_changes_floor() -> void:
	listener.place(Vector2(150, 50), map.get_room("B"))
	var stair: Stair = map.get_stairs()[0]
	assert_int(stair.end_at(Vector2(54, 78), 0)).is_equal(0)
	assert_int(stair.end_at(Vector2(50, 320), 0)).is_equal(-1)
	assert_int(stair.end_at(Vector2(50, 320), 1)).is_equal(1)
	var floors: Array[int] = []
	listener.floor_changed.connect(func(f: int) -> void: floors.append(f))
	listener.take_stair(stair, 0)
	_walk(Vector2.ZERO, 3.0)
	assert_bool(listener.has_path()).is_false()
	assert_str(listener.room.room_name).is_equal("E")
	assert_vector(listener.position).is_equal(Vector2(50, 320))
	assert_array(floors).contains_exactly([1])
	listener.take_stair(stair, 1)
	_walk(Vector2.ZERO, 1.0)
	assert_str(listener.room.room_name).is_equal("A")
	assert_int(listener.floor_index).is_equal(0)
