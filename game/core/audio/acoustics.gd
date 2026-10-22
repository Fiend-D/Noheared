@tool
class_name Acoustics
extends RefCounted
## 根据房间连通图判断某个声源对监听者是否可听、走哪条总线、衰减多少。

enum Clarity { NONE, MUFFLED, CLEAR }

const BUS_ROOM := &"Room"
const BUS_MUFFLED := &"Muffled"
const BUS_FAR := &"Far"

const CLOSED_DOOR_COST := 2
const LOUD_THRESHOLD := 0.75
const ADJACENT_GAIN_DB := -8.0
const PER_HOP_GAIN_DB := -9.0
const LOUDNESS_GAIN_DB := 8.0


class Result:
	extends RefCounted
	var clarity: Clarity = Clarity.NONE
	var bus: StringName = BUS_ROOM
	var gain_db: float = -80.0
	## 两房间之间的声学距离；-1 表示不连通。
	var cost: int = -1

	func audible() -> bool:
		return clarity != Clarity.NONE


var _edges: Dictionary = {}
var _cost_cache: Dictionary = {}


func add_room(room: StringName) -> void:
	if not _edges.has(room):
		_edges[room] = {}


func connect_rooms(a: StringName, b: StringName, cost: int = 1) -> void:
	add_room(a)
	add_room(b)
	var current: int = _edges[a].get(b, cost)
	_edges[a][b] = mini(current, cost)
	_edges[b][a] = mini(current, cost)
	_cost_cache.clear()


func has_room(room: StringName) -> bool:
	return _edges.has(room)


## 正常音量能传多远；大音量事件按 loudness 逐级传得更远。
static func max_cost_for(loudness: float) -> int:
	if loudness < LOUD_THRESHOLD:
		return 1
	return 2 + int((loudness - LOUD_THRESHOLD) * 12.0)


func cost_between(a: StringName, b: StringName) -> int:
	if a == b:
		return 0 if _edges.has(a) else -1
	if not _edges.has(a) or not _edges.has(b):
		return -1
	var key := "%s|%s" % [a, b]
	if _cost_cache.has(key):
		return _cost_cache[key]
	var dist := {a: 0}
	var frontier: Array[StringName] = [a]
	while not frontier.is_empty():
		var best_i := 0
		for i in frontier.size():
			if dist[frontier[i]] < dist[frontier[best_i]]:
				best_i = i
		var node: StringName = frontier[best_i]
		frontier.remove_at(best_i)
		var edges: Dictionary = _edges[node]
		for next: StringName in edges:
			var d: int = dist[node] + edges[next]
			if not dist.has(next) or d < dist[next]:
				dist[next] = d
				frontier.append(next)
	var result: int = dist.get(b, -1)
	_cost_cache[key] = result
	return result


func resolve(listener_room: StringName, source_room: StringName, loudness: float) -> Result:
	var r := Result.new()
	if listener_room == &"" or source_room == &"":
		return r
	r.cost = cost_between(listener_room, source_room)
	if r.cost < 0 or r.cost > max_cost_for(loudness):
		return r
	var loud_bonus := (loudness - 0.5) * LOUDNESS_GAIN_DB
	if r.cost == 0:
		r.clarity = Clarity.CLEAR
		r.bus = BUS_ROOM
		r.gain_db = 0.0
	elif r.cost == 1:
		r.clarity = Clarity.MUFFLED
		r.bus = BUS_MUFFLED
		r.gain_db = ADJACENT_GAIN_DB + loud_bonus
	else:
		r.clarity = Clarity.MUFFLED
		r.bus = BUS_FAR
		r.gain_db = ADJACENT_GAIN_DB + PER_HOP_GAIN_DB * (r.cost - 1) + loud_bonus
	return r
