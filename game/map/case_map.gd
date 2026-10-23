@tool
class_name CaseMap
extends Node2D
## 案件地图的根节点。子节点中的 Room / Door / Stair 描述空间结构。

signal floor_changed(floor_index: int)

const BACKDROP_SHADER := preload("res://map/backdrop.gdshader")
const BACKGROUND_MARGIN := 3000.0
## 房间向外扩这么多合并成建筑轮廓，房间之间的窄缝就成了厚墙。
const MASS_GROW := 28.0
const MASS_SHADOW := Vector2(8, 11)
## 监听者离墙的最小距离。
const WALK_MARGIN := 6.0
## 门洞通道向两侧房间里延伸的距离，保证和房间的可走区域相接。
const DOOR_REACH := 6.0
const ROUTE_DOOR_DEPTH := 14.0
const MIN_DOOR_HALF_WIDTH := 10.0
## 房间内绕开家具寻路的网格边长。
const ROUTE_CELL := 6.0
const ROUTE_SAMPLE := 3.0

@export var floor_names: PackedStringArray = PackedStringArray(["一层"])
## 建筑外的地面材质（`art/exterior/`），为空时是纯色。
@export var backdrop: Texture2D:
	set(value):
		backdrop = value
		_update_backdrop()

var current_floor: int = -1

var _background: ColorRect
var _acoustics: Acoustics
## 房间名 -> 当前灯光 Vector2(亮度, 暖色)；目标值在 `_light_target`。
var _light: Dictionary = {}
var _light_target: Dictionary = {}
var _grids: Dictionary = {}
var _blocking: Array[Prop] = []
var _mass: Array[PackedVector2Array] = []


func _ready() -> void:
	_background = ColorRect.new()
	_background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_background.show_behind_parent = true
	var mat := ShaderMaterial.new()
	mat.shader = BACKDROP_SHADER
	_background.material = mat
	add_child(_background, false, Node.INTERNAL_MODE_FRONT)
	_update_backdrop()
	refresh()


func _update_backdrop() -> void:
	if _background == null:
		return
	var mat := _background.material as ShaderMaterial
	mat.set_shader_parameter("ground", backdrop)
	mat.set_shader_parameter("has_ground", backdrop != null)


## 建筑轮廓：每层的房间外扩后合并，先画投影再画成墙色。
func _draw() -> void:
	for outline in _mass:
		var shadow := outline.duplicate()
		for i in shadow.size():
			shadow[i] += MASS_SHADOW
		draw_colored_polygon(shadow, Color(0, 0, 0, 0.5))
	for outline in _mass:
		draw_colored_polygon(outline, MapStyle.WALL)
		var ring := outline.duplicate()
		ring.append(outline[0])
		draw_polyline(ring, MapStyle.MASS_EDGE, 1.5, true)


func _rebuild_mass() -> void:
	_mass.clear()
	for r in get_rooms():
		if current_floor >= 0 and r.floor_index != current_floor:
			continue
		var local := PackedVector2Array()
		for p in r.polygon:
			local.append(p + r.position)
		for grown in Geometry2D.offset_polygon(local, MASS_GROW, Geometry2D.JOIN_MITER):
			_add_mass(grown)
	queue_redraw()


func _add_mass(poly: PackedVector2Array) -> void:
	var merged := poly
	var i := 0
	while i < _mass.size():
		var parts := Geometry2D.merge_polygons(merged, _mass[i])
		var outers := parts.filter(func(p: PackedVector2Array) -> bool: return not Geometry2D.is_polygon_clockwise(p))
		if outers.size() == 1:
			merged = outers[0]
			_mass.remove_at(i)
			i = 0
		else:
			i += 1
	_mass.append(merged)


## 重新计算门和楼梯所在的楼层，并更新背景范围。编辑地图后调用。
func refresh() -> void:
	for door in get_doors():
		var ra := get_room(door.room_a)
		door.floor_index = ra.floor_index if ra else 0
		_compute_passage(door, ra, get_room(door.room_b))
	for stair in get_stairs():
		var ra := get_room(stair.room_a)
		var rb := get_room(stair.room_b)
		stair.floor_a = ra.floor_index if ra else 0
		stair.floor_b = rb.floor_index if rb else 0
		stair.label_below_a = _near_top_wall(ra, stair.end_a())
		stair.label_below_b = _near_top_wall(rb, stair.end_b)
		stair.queue_redraw()
	_blocking.clear()
	for prop in get_props():
		var room := get_room(prop.room_name) if prop.room_name != "" else null
		if room == null:
			room = room_at(prop.position)
			prop.room_name = room.room_name if room else ""
		prop.floor_index = room.floor_index if room else 0
		if prop.blocks:
			_blocking.append(prop)
	_acoustics = build_acoustics()
	_grids.clear()
	_rebuild_mass()
	if _background:
		var b := get_bounds().grow(BACKGROUND_MARGIN)
		_background.position = b.position
		_background.size = b.size


## 门洞通道：两端各取门中心在两侧墙上的投影，方向取水平或竖直。
func _compute_passage(door: Door, ra: Room, rb: Room) -> void:
	var c := door.position
	if ra == null or rb == null:
		var horizontal := door.size.x >= door.size.y
		var dir := Vector2.DOWN if horizontal else Vector2.RIGHT
		door.set_passage(c, c, dir, maxf((door.size.x if horizontal else door.size.y) * 0.5, MIN_DOOR_HALF_WIDTH))
		return
	var pa := ra.closest_wall_point(c)
	var pb := rb.closest_wall_point(c)
	var d := pb - pa
	if d.length() < 1.0:
		# 共用一面墙：通道垂直于这面墙，朝 room_b 一侧。
		d = ra.closest_wall_direction(c).orthogonal()
		if d.dot(rb.get_center() - pa) < 0.0:
			d = -d
	var axis := Vector2(signf(d.x), 0.0) if absf(d.x) > absf(d.y) else Vector2(0.0, signf(d.y))
	if axis == Vector2.ZERO:
		axis = Vector2.DOWN
	if axis.x != 0.0:
		pa.y = c.y
		pb.y = c.y
	else:
		pa.x = c.x
		pb.x = c.x
	if (pb - pa).dot(axis) < 0.0:
		pb = pa
	var across := door.size.y if axis.x != 0.0 else door.size.x
	door.set_passage(pa, pb, axis, maxf(across * 0.5, MIN_DOOR_HALF_WIDTH))


func _near_top_wall(room: Room, point: Vector2) -> bool:
	if room == null:
		return false
	var b := room.get_bounds()
	return point.y - b.position.y < b.end.y - point.y


## 监听者能否站在这里：在房间内离墙足够远，或在门洞通道里，且不压在挡路的家具上。
func is_walkable(map_point: Vector2, floor_index: int, margin: float = WALK_MARGIN) -> bool:
	for p in _blocking:
		if p.floor_index == floor_index and p.blocks_point(map_point, margin):
			return false
	for r in get_rooms():
		if r.floor_index == floor_index and r.is_walkable(map_point, margin):
			return true
	for d in get_doors():
		if d.floor_index == floor_index and d.passage_contains(map_point, margin, margin + DOOR_REACH):
			return true
	return false


## 从 `from_room` 走到 `to_room` 的路线点：[{pos, jump}]。jump 为 true 表示经楼梯直接换到该点。
## 给出 `from_point` 时，房间里的每一段都会绕开家具。走不通时返回空数组。
func route(from_room: Room, to_point: Vector2, to_room: Room, from_point: Vector2 = Vector2.INF) -> Array[Dictionary]:
	var legs := _room_route(from_room, to_point, to_room)
	if legs.is_empty() or from_point == Vector2.INF:
		return legs
	var out: Array[Dictionary] = []
	var at := from_point
	for leg in legs:
		if not leg.jump and leg.room != "":
			var room := get_room(leg.room)
			var detour := _path_in_room(room, at, leg.pos)
			if detour.is_empty():
				return [] as Array[Dictionary]
			for i in detour.size() - 1:
				out.append({"pos": detour[i], "jump": false})
		out.append({"pos": leg.pos, "jump": leg.jump})
		at = leg.pos
	return out


## 只按门和楼梯连通关系求路线。每个点带 `room`：走到这个点的这段路在哪个房间里（穿门洞时为空）。
func _room_route(from_room: Room, to_point: Vector2, to_room: Room) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	if from_room == null or to_room == null:
		return out
	var start := from_room.room_name
	var goal := to_room.room_name
	var came: Dictionary = {start: null}
	var queue: Array[String] = [start]
	while not queue.is_empty() and not came.has(goal):
		var cur: String = queue.pop_front()
		for link in _links(cur):
			var other: String = link.other
			if not came.has(other):
				came[other] = {"from": cur, "via": link.via}
				queue.append(other)
	if not came.has(goal):
		return out
	var hops: Array[Dictionary] = []
	var at := goal
	while came[at] != null:
		hops.push_front({"from": came[at].from, "to": at, "via": came[at].via})
		at = came[at].from
	for hop in hops:
		var via: Node2D = hop.via
		if via is Door:
			var door := via as Door
			out.append({"pos": door.mouth(hop.from, ROUTE_DOOR_DEPTH), "jump": false, "room": hop.from})
			out.append({"pos": door.mouth(hop.to, ROUTE_DOOR_DEPTH), "jump": false, "room": ""})
		else:
			var stair := via as Stair
			out.append({"pos": stair.end_in(hop.from), "jump": false, "room": hop.from})
			out.append({"pos": stair.end_in(hop.to), "jump": true, "room": ""})
	out.append({"pos": to_point, "jump": false, "room": goal})
	return out


## 房间里从 `a` 走到 `b` 的折线（含 `b`，不含 `a`）。直线走得通就直接走，否则在网格上绕开家具。
func _path_in_room(room: Room, a: Vector2, b: Vector2) -> PackedVector2Array:
	if room == null or segment_clear(a, b, room.floor_index):
		return PackedVector2Array([b])
	var grid := _grid_for(room)
	var from := _cell(grid, a)
	var to := _cell(grid, b)
	if not grid.is_in_boundsv(from) or not grid.is_in_boundsv(to):
		return PackedVector2Array()
	var keep := [grid.is_point_solid(from), grid.is_point_solid(to)]
	grid.set_point_solid(from, false)
	grid.set_point_solid(to, false)
	var cells := grid.get_point_path(from, to)
	grid.set_point_solid(from, keep[0])
	grid.set_point_solid(to, keep[1])
	if cells.is_empty():
		return PackedVector2Array()
	var points := PackedVector2Array([a])
	points.append_array(cells.slice(1, cells.size() - 1))
	points.append(b)
	return _shortcut(points, room.floor_index)


## 去掉折线上能直接跳过的点。
func _shortcut(points: PackedVector2Array, floor_index: int) -> PackedVector2Array:
	var out := PackedVector2Array()
	var i := 0
	while i < points.size() - 1:
		var j := points.size() - 1
		while j > i + 1 and not segment_clear(points[i], points[j], floor_index):
			j -= 1
		out.append(points[j])
		i = j
	return out


## `room` 里离 `map_point` 最近的可站立点（按网格找）；找不到时返回房间中心。
func nearest_walkable(room: Room, map_point: Vector2) -> Vector2:
	if is_walkable(map_point, room.floor_index) and room.contains_point(map_point):
		return map_point
	var grid := _grid_for(room)
	var best := room.get_center()
	var best_d := INF
	for x in grid.region.size.x:
		for y in grid.region.size.y:
			var c := Vector2i(x, y)
			var p := grid.get_point_position(c)
			var d := p.distance_squared_to(map_point)
			if d < best_d and not grid.is_point_solid(c) and room.contains_point(p):
				best_d = d
				best = p
	return best


## 线段上每隔几个像素都能站人。
func segment_clear(a: Vector2, b: Vector2, floor_index: int) -> bool:
	var steps := maxi(int(a.distance_to(b) / ROUTE_SAMPLE), 1)
	for i in range(1, steps + 1):
		if not is_walkable(a.lerp(b, float(i) / steps), floor_index):
			return false
	return true


func _grid_for(room: Room) -> AStarGrid2D:
	if _grids.has(room.room_name):
		return _grids[room.room_name]
	var grid := AStarGrid2D.new()
	var b := room.get_bounds().grow(DOOR_REACH + WALK_MARGIN)
	grid.region = Rect2i(Vector2i.ZERO, Vector2i((b.size / ROUTE_CELL).ceil()))
	grid.cell_size = Vector2(ROUTE_CELL, ROUTE_CELL)
	grid.offset = b.position + grid.cell_size * 0.5
	grid.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	grid.update()
	for x in grid.region.size.x:
		for y in grid.region.size.y:
			var c := Vector2i(x, y)
			grid.set_point_solid(c, not is_walkable(grid.get_point_position(c), room.floor_index))
	_grids[room.room_name] = grid
	return grid


func _cell(grid: AStarGrid2D, p: Vector2) -> Vector2i:
	return Vector2i(((p - grid.offset) / grid.cell_size).round())


## 监听者在 `room_name` 时各房间的灯光：同一房间暖光，按声学距离逐级变暗变青。空字符串表示全亮。
func light_from(room_name: String, instant: bool = false) -> void:
	for r in get_rooms():
		var level := Vector2.ONE
		if room_name != "" and _acoustics:
			var cost := _acoustics.cost_between(StringName(room_name), StringName(r.room_name))
			if cost < 0:
				cost = MapStyle.LIGHT_LEVELS.size()
			level = MapStyle.LIGHT_LEVELS[mini(cost, MapStyle.LIGHT_LEVELS.size() - 1)]
		_light_target[r.room_name] = level
		if instant or not _light.has(r.room_name):
			_light[r.room_name] = level
	_apply_light()


func _process(delta: float) -> void:
	if _light_target.is_empty():
		return
	var changed := false
	for room_name: String in _light_target:
		var now: Vector2 = _light.get(room_name, Vector2.ONE)
		var target: Vector2 = _light_target[room_name]
		if now != target:
			_light[room_name] = now.move_toward(target, MapStyle.LIGHT_FADE * delta)
			changed = true
	if changed:
		_apply_light()


func _apply_light() -> void:
	for r in get_rooms():
		var l: Vector2 = _light.get(r.room_name, Vector2.ONE)
		r.set_light(l.x, l.y)
	for p in get_props():
		var l: Vector2 = _light.get(p.room_name, Vector2.ONE)
		p.set_light(l.x, l.y)
	for d in get_doors():
		var la: Vector2 = _light.get(d.room_a, Vector2.ONE)
		var lb: Vector2 = _light.get(d.room_b, Vector2.ONE)
		d.set_light(maxf(la.x, lb.x), maxf(la.y, lb.y))


func room_light(room_name: String) -> Vector2:
	return _light.get(room_name, Vector2.ONE)


func _links(room_name: String) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for d in get_doors():
		if d.room_a == room_name:
			out.append({"other": d.room_b, "via": d})
		elif d.room_b == room_name:
			out.append({"other": d.room_a, "via": d})
	for s in get_stairs():
		if s.room_a == room_name:
			out.append({"other": s.room_b, "via": s})
		elif s.room_b == room_name:
			out.append({"other": s.room_a, "via": s})
	return out


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


func get_props() -> Array[Prop]:
	var out: Array[Prop] = []
	_collect(self, out, Prop)
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
	for p in get_props():
		p.visible = index < 0 or p.floor_index == index
	for s in get_stairs():
		s.visible_floor = index
	_rebuild_mass()
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
