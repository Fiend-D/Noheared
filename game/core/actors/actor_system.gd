class_name ActorSystem
extends Node2D
## 每帧按时间轴采样所有角色的位置。位置只取决于 t，倒退、拖动都与剧本一致。

const PICK_RADIUS := 18.0

var case_data: CaseData
var map: CaseMap
var clock: TimelineClock

var dots: Dictionary = {}

var _poses: Dictionary = {}
var _rooms: Dictionary = {}


func setup(data: CaseData, case_map: CaseMap, timeline: TimelineClock) -> void:
	case_data = data
	map = case_map
	clock = timeline
	process_priority = -50
	for c in case_data.characters:
		TrackMath.sort_track(c.track)
		var dot := ActorDot.new()
		dot.character = c
		dot.name = "Actor_%s" % c.id
		add_child(dot)
		dots[c.id] = dot
	update_at(clock.time)


func _process(_delta: float) -> void:
	if clock:
		update_at(clock.time)


func update_at(t: float) -> void:
	for c in case_data.characters:
		var pose := TrackMath.sample(c.track, t)
		var room := map.room_for_pose(c, pose)
		_poses[c.id] = pose
		_rooms[c.id] = room
		var dot: ActorDot = dots[c.id]
		dot.position = pose.position
		dot.visible = map.current_floor < 0 or room == null or room.floor_index == map.current_floor


func get_pose(character_id: StringName) -> TrackMath.Pose:
	return _poses.get(character_id)


func get_room(character_id: StringName) -> Room:
	return _rooms.get(character_id)


func get_room_name(character_id: StringName) -> StringName:
	var room: Room = _rooms.get(character_id)
	return StringName(room.room_name) if room else &""


func dot_at(map_point: Vector2) -> ActorDot:
	var best: ActorDot = null
	var best_d := PICK_RADIUS
	for dot: ActorDot in dots.values():
		if not dot.visible:
			continue
		var d := dot.position.distance_to(map_point)
		if d <= best_d:
			best = dot
			best_d = d
	return best


func set_speaking(states: Dictionary) -> void:
	for id: StringName in dots:
		var dot: ActorDot = dots[id]
		dot.speaking = states.get(id, Acoustics.Clarity.NONE)
