@tool
class_name CaseMap
extends Node2D
## 案件地图的根节点。子节点中的 Room / Door / Stair 描述空间结构。

signal floor_changed(floor_index: int)

const BLUEPRINT_SHADER := preload("res://map/blueprint.gdshader")
const BACKGROUND_MARGIN := 3000.0

@export var floor_names: PackedStringArray = PackedStringArray(["一层"])

var current_floor: int = -1

var _background: ColorRect


func _ready() -> void:
	_background = ColorRect.new()
	_background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_background.show_behind_parent = true
	var mat := ShaderMaterial.new()
	mat.shader = BLUEPRINT_SHADER
	_background.material = mat
	add_child(_background, false, Node.INTERNAL_MODE_FRONT)
	refresh()


## 重新计算门和楼梯所在的楼层，并更新背景范围。编辑地图后调用。
func refresh() -> void:
	for door in get_doors():
		var ra := get_room(door.room_a)
		door.floor_index = ra.floor_index if ra else 0
	for stair in get_stairs():
		var ra := get_room(stair.room_a)
		var rb := get_room(stair.room_b)
		stair.floor_a = ra.floor_index if ra else 0
		stair.floor_b = rb.floor_index if rb else 0
	if _background:
		var b := get_bounds().grow(BACKGROUND_MARGIN)
		_background.position = b.position
		_background.size = b.size


func get_rooms() -> Array[Room]:
	var out: Array[Room] = []
	_collect(self, out, Room)
	return out


func get_doors() -> Array[Door]:
	var out: Array[Door] = []
	_collect(self, out, Door)
	return out


func get_stairs() -> Array[Stair]:
	var out: Array[Stair] = []
	_collect(self, out, Stair)
	return out


func _collect(node: Node, out: Array, type: Variant) -> void:
	for child in node.get_children():
		if is_instance_of(child, type):
			out.append(child)
		_collect(child, out, type)


func get_room(room_name: String) -> Room:
	for r in get_rooms():
		if r.room_name == room_name:
			return r
	return null


## 返回包含该点的房间。`hint` 用于楼层重叠时消歧，`floor_filter` >= 0 时只看该楼层。
func room_at(map_point: Vector2, hint: StringName = &"", floor_filter: int = -1) -> Room:
	var found: Room = null
	for r in get_rooms():
		if floor_filter >= 0 and r.floor_index != floor_filter:
			continue
		if not r.contains_point(map_point):
			continue
		if hint != &"" and r.room_name == String(hint):
			return r
		if found == null:
			found = r
	return found


## 角色当前所在房间。在门洞里时不在任何房间内，此时沿关键帧往回找最近一个落在房间里的位置。
func room_for_pose(c: CharacterData, pose: TrackMath.Pose) -> Room:
	var room := room_at(pose.position, TrackMath.room_hint(c.track, pose.key_index))
	if room:
		return room
	var i := mini(pose.key_index, c.track.size() - 1)
	while i >= 0:
		var key := c.track[i]
		room = room_at(key.position, key.room)
		if room:
			return room
		i -= 1
	if not c.track.is_empty():
		return room_at(c.track[0].position, c.track[0].room)
	return null


func floor_count() -> int:
	var n := floor_names.size()
	for r in get_rooms():
		n = maxi(n, r.floor_index + 1)
	return maxi(n, 1)


func floor_name(index: int) -> String:
	if index >= 0 and index < floor_names.size():
		return floor_names[index]
	return "%d F" % (index + 1)


func get_bounds(floor_filter: int = -1) -> Rect2:
	var result := Rect2()
	var first := true
	for r in get_rooms():
		if floor_filter >= 0 and r.floor_index != floor_filter:
			continue
		var b := r.get_bounds()
		result = b if first else result.merge(b)
		first = false
	return result


func show_floor(index: int) -> void:
	current_floor = index
	for r in get_rooms():
		r.visible = index < 0 or r.floor_index == index
	for d in get_doors():
		d.visible = index < 0 or d.floor_index == index
	for s in get_stairs():
		s.visible_floor = index
	floor_changed.emit(index)


func build_acoustics() -> Acoustics:
	var acoustics := Acoustics.new()
	for r in get_rooms():
		acoustics.add_room(StringName(r.room_name))
	for d in get_doors():
		acoustics.connect_rooms(StringName(d.room_a), StringName(d.room_b), 1 if d.open else Acoustics.CLOSED_DOOR_COST)
	for s in get_stairs():
		acoustics.connect_rooms(StringName(s.room_a), StringName(s.room_b), 1)
	return acoustics


## 两个房间是否通过门或楼梯直接相连。
func rooms_adjacent(a: String, b: String) -> bool:
	for d in get_doors():
		if (d.room_a == a and d.room_b == b) or (d.room_a == b and d.room_b == a):
			return true
	for s in get_stairs():
		if (s.room_a == a and s.room_b == b) or (s.room_a == b and s.room_b == a):
			return true
	return false
