@tool
class_name TrackKey
extends Resource
## 角色轨迹上的一个关键帧。`movement` 描述从本帧到下一帧之间的移动方式。

enum Movement { IDLE, WALK, RUN }

@export var time: float = 0.0
@export var position: Vector2 = Vector2.ZERO
@export var movement: Movement = Movement.IDLE
## 可选：当多个楼层的房间在坐标上重叠时，用来消除歧义。
@export var room: StringName = &""


static func make(t: float, pos: Vector2, move: Movement = Movement.IDLE) -> TrackKey:
	var key := TrackKey.new()
	key.time = t
	key.position = pos
	key.movement = move
	return key
