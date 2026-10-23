class_name Listener
extends Node2D
## 玩家扮演的“耳朵”。在房间里走动，只能经门洞进出房间，踩上楼梯口换楼层。持有当前的 AudioListener2D。
## 监听者按真实时间移动，不属于时间轴：暂停、倒带时也能走动。

signal moved(room: Room)
signal floor_changed(floor_index: int)

const SPEED := 170.0
const RUN_FACTOR := 1.8
const STAIR_RADIUS := 13.0
## 走下楼梯后要先离开楼梯口这么远，才会再次触发楼梯。
const STAIR_REARM := 26.0
## 朝门洞走时自动往门洞中线靠的速度（每秒）。
const DOOR_ASSIST := 140.0
const DOOR_ASSIST_RANGE := 34.0
const ARRIVE_EPSILON := 1.5
const COLOR := Color(0.96, 0.94, 0.88)

var map: CaseMap
var room: Room
var floor_index: int = 0
var walking: bool = false

var _ear: AudioListener2D
var _path: Array[Dictionary] = []
var _stair_block: Vector2 = Vector2.INF
var _phase: float = 0.0
var _stride: float = 0.0


func _ready() -> void:
	z_index = 10
	_ear = AudioListener2D.new()
	add_child(_ear)
	_ear.make_current()


func setup(case_map: CaseMap) -> void:
	map = case_map


func place(map_point: Vector2, new_room: Room) -> void:
	position = map_point
	_path.clear()
	_stair_block = map_point
	_set_room(new_room)


## 沿门洞、楼梯走到 `new_room` 里的 `map_point`。走不通时原地不动。
func walk_to(map_point: Vector2, new_room: Room) -> void:
	if map == null or room == null:
		place(map_point, new_room)
		return
	_path = map.route(room, map_point, new_room, position)


func stop() -> void:
	_path.clear()


func has_path() -> bool:
	return not _path.is_empty()


func room_name() -> StringName:
	return StringName(room.room_name) if room else &""


## 每帧由游戏调用。`direction` 来自键盘（长度 0~1），有输入时打断自动寻路。
func step(direction: Vector2, running: bool, delta: float) -> void:
	var speed := SPEED * (RUN_FACTOR if running else 1.0)
	var before := position
	if direction != Vector2.ZERO:
		_path.clear()
		_move_free(direction.limit_length(1.0) * speed * delta, direction, delta)
		_check_stairs()
	elif not _path.is_empty():
		_follow(speed * delta)
	walking = position.distance_to(before) > 0.01
	if walking:
		_stride += position.distance_to(before)


func _move_free(motion: Vector2, direction: Vector2, delta: float) -> void:
	if map == null:
		position += motion
		return
	motion += _door_assist(direction, delta)
	for candidate in [position + motion, position + Vector2(motion.x, 0), position + Vector2(0, motion.y)]:
		if map.is_walkable(candidate, floor_index):
			position = candidate
			break
	_update_room()


## 朝门洞方向走时把监听者往门洞中线推，免得卡在门框上。
func _door_assist(direction: Vector2, delta: float) -> Vector2:
	for d in map.get_doors():
		if d.floor_index != floor_index or absf(direction.dot(d.axis)) < 0.5:
			continue
		var l := d.lateral(position)
		var along_ok := l.x > -DOOR_ASSIST_RANGE and l.x < d.passage_length() + DOOR_ASSIST_RANGE
		if along_ok and absf(l.y) < d.half_width + DOOR_ASSIST_RANGE * 0.5 and absf(l.y) > 0.5:
			var push := minf(DOOR_ASSIST * delta, absf(l.y))
			return -d.axis.orthogonal() * signf(l.y) * push
	return Vector2.ZERO


func _follow(budget: float) -> void:
	while budget > 0.0 and not _path.is_empty():
		var target: Dictionary = _path[0]
		if target.jump:
			_jump_to(target.pos)
			_path.pop_front()
			continue
		var to: Vector2 = target.pos
		var dist := position.distance_to(to)
		if dist <= budget + ARRIVE_EPSILON:
			position = to
			budget -= dist
			_path.pop_front()
		else:
			position += (to - position) / dist * budget
			budget = 0.0
		_update_room()


func _check_stairs() -> void:
	if map == null:
		return
	if _stair_block != Vector2.INF:
		if position.distance_to(_stair_block) < STAIR_REARM:
			return
		_stair_block = Vector2.INF
	for s in map.get_stairs():
		for e in [[s.end_a(), s.floor_a, s.end_b, s.room_b], [s.end_b, s.floor_b, s.end_a(), s.room_a]]:
			if e[1] == floor_index and position.distance_to(e[0]) <= STAIR_RADIUS:
				_jump_to(e[2], map.get_room(e[3]))
				return


func _jump_to(map_point: Vector2, new_room: Room = null) -> void:
	position = map_point
	_stair_block = map_point
	if new_room == null and map:
		new_room = map.room_at(map_point, &"", -1 if room == null else _other_floor_hint(map_point))
	_set_room(new_room)


func _other_floor_hint(map_point: Vector2) -> int:
	for r in map.get_rooms():
		if r.floor_index != floor_index and r.contains_point(map_point):
			return r.floor_index
	return -1


func _update_room() -> void:
	if map == null:
		return
	var r := map.room_at(position, &"", floor_index)
	if r != null:
		_set_room(r)


func _set_room(new_room: Room) -> void:
	if room == new_room:
		return
	if room:
		room.highlighted = false
	room = new_room
	if room:
		room.highlighted = true
		AudioBuses.set_room_size(room.get_area())
		if room.floor_index != floor_index:
			floor_index = room.floor_index
			floor_changed.emit(floor_index)
	moved.emit(room)


func _process(delta: float) -> void:
	_phase = fmod(_phase + delta, 2.4)
	queue_redraw()


func _draw() -> void:
	var k := _phase / 2.4
	draw_circle(Vector2.ZERO, 26.0, Color(MapStyle.AMBER, 0.07))
	draw_arc(Vector2.ZERO, 12.0 + k * 34.0, 0, TAU, 48, Color(MapStyle.AMBER, 0.5 * (1.0 - k)), 1.5, true)
	var bob := sin(_stride * 0.25) * 1.2 if walking else 0.0
	var o := Vector2(0, bob)
	draw_circle(o, 9.5, Color(0, 0, 0, 0.55))
	draw_circle(o, 8.0, COLOR)
	# 耳机：头梁 + 两侧耳罩
	draw_arc(o, 12.5, PI * 1.12, PI * 1.88, 20, COLOR, 2.5, true)
	for side in [-1.0, 1.0]:
		var cup: Vector2 = o + Vector2(side * 11.5, 1.0)
		draw_circle(cup, 4.0, MapStyle.INK)
		draw_circle(cup, 3.2, MapStyle.AMBER)
	draw_circle(o, 2.6, MapStyle.INK)
