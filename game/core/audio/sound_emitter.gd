class_name SoundEmitter
extends AudioStreamPlayer2D
## 带音量渐变的定位播放器。切换总线时先淡出再切换，避免爆音。

const SILENT_DB := -60.0
const FADE_TIME := 0.08

var target_db: float = SILENT_DB
## 播放到结尾后置为 true，防止调度器在台词区间内反复重启它。
var completed: bool = false

var _pending_bus: StringName = &""


func _init() -> void:
	max_distance = 1600.0
	attenuation = 0.7
	panning_strength = 1.0
	volume_db = SILENT_DB
	bus = Acoustics.BUS_ROOM
	finished.connect(func() -> void: completed = true)


func set_target(bus_name: StringName, gain_db: float, audible: bool) -> void:
	target_db = gain_db if audible else SILENT_DB
	if not audible or bus_name == bus:
		_pending_bus = &""
		return
	if volume_db <= SILENT_DB + 1.0:
		bus = bus_name
		_pending_bus = &""
	else:
		_pending_bus = bus_name


## 立即应用目标状态（新开始播放或 seek 之后用）。
func snap() -> void:
	if _pending_bus != &"":
		bus = _pending_bus
		_pending_bus = &""
	volume_db = target_db


func start(stream_to_play: AudioStream, offset: float, paused: bool, speed: float) -> void:
	stream = stream_to_play
	completed = false
	pitch_scale = speed
	snap()
	play(maxf(offset, 0.0))
	stream_paused = paused


func halt() -> void:
	stop()
	stream = null
	completed = false
	volume_db = SILENT_DB
	_pending_bus = &""


func _process(delta: float) -> void:
	var goal := SILENT_DB if _pending_bus != &"" else target_db
	var step := (absf(SILENT_DB) / FADE_TIME) * delta
	volume_db = move_toward(volume_db, goal, step)
	if _pending_bus != &"" and volume_db <= SILENT_DB + 0.5:
		bus = _pending_bus
		_pending_bus = &""
