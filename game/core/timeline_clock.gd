class_name TimelineClock
extends Node
## 全局唯一的时间源。其他系统只读取 `time`，自己不保存帧间状态。

signal time_changed(t: float)
signal seeked(t: float)
signal playing_changed(is_playing: bool)
signal speed_changed(new_speed: float)
signal finished

const SPEEDS: Array[float] = [0.5, 1.0, 2.0, 4.0]

var duration: float = 0.0
var time: float = 0.0
var playing: bool = false
var speed: float = 1.0


func _init(case_duration: float = 0.0) -> void:
	duration = case_duration
	process_priority = -100


func _process(delta: float) -> void:
	if playing:
		advance(delta)


## 单独暴露出来，便于测试和编辑器预览在没有场景树的情况下推进时间。
func advance(delta: float) -> void:
	time = minf(time + delta * speed, duration)
	time_changed.emit(time)
	if time >= duration:
		pause()
		finished.emit()


func play() -> void:
	if playing:
		return
	if time >= duration:
		seek(0.0)
	playing = true
	playing_changed.emit(true)


func pause() -> void:
	if not playing:
		return
	playing = false
	playing_changed.emit(false)


func toggle() -> void:
	if playing:
		pause()
	else:
		play()


func seek(t: float) -> void:
	time = clampf(t, 0.0, duration)
	seeked.emit(time)
	time_changed.emit(time)


func skip(seconds: float) -> void:
	seek(time + seconds)


func set_speed(new_speed: float) -> void:
	speed = clampf(new_speed, 0.25, 8.0)
	speed_changed.emit(speed)


func cycle_speed() -> float:
	var idx := SPEEDS.find(speed)
	set_speed(SPEEDS[(idx + 1) % SPEEDS.size()])
	return speed
