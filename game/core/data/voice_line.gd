@tool
class_name VoiceLine
extends Resource

@export var speaker: StringName = &""
@export var start: float = 0.0
@export var duration: float = 1.0
@export var stream: AudioStream
@export_multiline var text: String = ""
@export var volume_db: float = 0.0
## 0..1，越大越能穿透房间。喊叫、尖叫用高值。
@export_range(0.0, 1.0) var loudness: float = 0.5


func end_time() -> float:
	return start + duration


func is_active_at(t: float) -> bool:
	return t >= start and t < start + duration
