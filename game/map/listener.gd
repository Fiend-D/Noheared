class_name Listener
extends Node2D
## 玩家扮演的“耳朵”。持有当前的 AudioListener2D。

signal moved(room: Room)

const MOVE_TIME := 0.2
const COLOR := Color(1.0, 0.95, 0.75)

var room: Room

var _ear: AudioListener2D
var _tween: Tween
var _phase: float = 0.0


func _ready() -> void:
	z_index = 10
	_ear = AudioListener2D.new()
	add_child(_ear)
	_ear.make_current()


func place(map_point: Vector2, new_room: Room) -> void:
	position = map_point
	_set_room(new_room)


func move_to(map_point: Vector2, new_room: Room) -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_tween.tween_property(self, "position", map_point, MOVE_TIME)
	_set_room(new_room)


func room_name() -> StringName:
	return StringName(room.room_name) if room else &""


func _set_room(new_room: Room) -> void:
	if room == new_room:
		return
	if room:
		room.highlighted = false
	room = new_room
	if room:
		room.highlighted = true
		AudioBuses.set_room_size(room.get_area())
	moved.emit(room)


func _process(delta: float) -> void:
	_phase = fmod(_phase + delta, 2.0)
	queue_redraw()


func _draw() -> void:
	draw_circle(Vector2.ZERO, 7.0, COLOR)
	draw_arc(Vector2.ZERO, 11.0, 0, TAU, 32, Color(COLOR, 0.8), 2.0, true)
	var k := _phase / 2.0
	draw_arc(Vector2.ZERO, 14.0 + k * 26.0, 0, TAU, 48, Color(COLOR, 0.45 * (1.0 - k)), 1.5, true)
