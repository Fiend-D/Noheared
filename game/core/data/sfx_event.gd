@tool
class_name SfxEvent
extends Resource

@export var time: float = 0.0
@export var duration: float = 1.0
@export var stream: AudioStream
## 固定位置；`attach_to` 非空时改为跟随该角色。
@export var position: Vector2 = Vector2.ZERO
@export var attach_to: StringName = &""
@export_range(0.0, 1.0) var loudness: float = 0.5
@export var volume_db: float = 0.0
## 写入笔记时显示的描述，例如“枪声”。
@export var label: String = ""


func end_time() -> float:
	return time + duration


func is_active_at(t: float) -> bool:
	return t >= time and t < time + duration
