class_name AudioBuses
extends RefCounted
## 运行时创建并维护混音总线：Room（同房间）、Muffled（隔一道门）、Far（穿透多个房间）。

const MASTER := &"Master"


static func setup() -> void:
	if AudioServer.get_bus_index(Acoustics.BUS_ROOM) == -1:
		_add_bus(Acoustics.BUS_ROOM, [_reverb(0.25, 0.10)])
	if AudioServer.get_bus_index(Acoustics.BUS_MUFFLED) == -1:
		_add_bus(Acoustics.BUS_MUFFLED, [_low_pass(750.0), _reverb(0.45, 0.22)])
	if AudioServer.get_bus_index(Acoustics.BUS_FAR) == -1:
		_add_bus(Acoustics.BUS_FAR, [_low_pass(380.0), _reverb(0.65, 0.30)])
	if _pitch_effect_index() == -1:
		var pitch := AudioEffectPitchShift.new()
		var master := AudioServer.get_bus_index(MASTER)
		AudioServer.add_bus_effect(master, pitch, 0)
		AudioServer.set_bus_effect_enabled(master, 0, false)


## 变速播放时播放器会设置 pitch_scale = speed，这里在 Master 上反向补偿，保持音高不变。
static func set_speed(speed: float) -> void:
	var idx := _pitch_effect_index()
	if idx == -1:
		return
	var master := AudioServer.get_bus_index(MASTER)
	var effect := AudioServer.get_bus_effect(master, idx) as AudioEffectPitchShift
	effect.pitch_scale = 1.0 / speed
	AudioServer.set_bus_effect_enabled(master, idx, not is_equal_approx(speed, 1.0))


## 监听者所在房间越大，同房间混响越明显。`area` 是地图像素面积。
static func set_room_size(area: float) -> void:
	var bus := AudioServer.get_bus_index(Acoustics.BUS_ROOM)
	if bus == -1:
		return
	for i in AudioServer.get_bus_effect_count(bus):
		var reverb := AudioServer.get_bus_effect(bus, i) as AudioEffectReverb
		if reverb:
			reverb.room_size = clampf(sqrt(area) / 900.0, 0.1, 0.8)
			reverb.wet = clampf(0.06 + sqrt(area) / 6000.0, 0.06, 0.18)


static func _pitch_effect_index() -> int:
	var master := AudioServer.get_bus_index(MASTER)
	for i in AudioServer.get_bus_effect_count(master):
		if AudioServer.get_bus_effect(master, i) is AudioEffectPitchShift:
			return i
	return -1


static func _add_bus(bus_name: StringName, effects: Array[AudioEffect]) -> void:
	AudioServer.add_bus()
	var idx := AudioServer.bus_count - 1
	AudioServer.set_bus_name(idx, bus_name)
	AudioServer.set_bus_send(idx, MASTER)
	for e in effects:
		AudioServer.add_bus_effect(idx, e)


static func _low_pass(cutoff: float) -> AudioEffectLowPassFilter:
	var e := AudioEffectLowPassFilter.new()
	e.cutoff_hz = cutoff
	e.resonance = 0.5
	return e


static func _reverb(size: float, wet: float) -> AudioEffectReverb:
	var e := AudioEffectReverb.new()
	e.room_size = size
	e.wet = wet
	e.dry = 1.0
	e.damping = 0.6
	return e
