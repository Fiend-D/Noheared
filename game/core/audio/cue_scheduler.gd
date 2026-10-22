@tool
class_name CueScheduler
extends Node
## 按时间轴调度台词、音效和脚步声。每帧根据当前时间 t 决定哪些声音应在播放、从哪个偏移量播放，
## 再用 Acoustics 决定总线和音量。seek 之后只需丢掉现有播放器，下一帧会按新偏移量重建。

## 台词被清楚听到时每帧都会发出；接收方自行去重。
signal line_heard(index: int)
signal sfx_heard(index: int)

const DRIFT_TOLERANCE := 0.12
const FOOTSTEP_LOUDNESS := 0.3
const FOOTSTEP_GAIN_DB := -10.0
const WALK_STREAM_PATH := "res://audio/footsteps/walk.ogg"
const RUN_STREAM_PATH := "res://audio/footsteps/run.ogg"


class ActiveLine:
	extends RefCounted
	var index: int
	var line: VoiceLine
	var clarity: Acoustics.Clarity


var case_data: CaseData
var clock: TimelineClock
var actors: ActorSystem
var listener: Listener
var acoustics: Acoustics
## 发声器的父节点，必须位于 2D 世界中，定位音频才会生效。
var emitter_parent: Node2D

var active_lines: Array[ActiveLine] = []

var _voice: Dictionary = {}
var _sfx: Dictionary = {}
var _footsteps: Dictionary = {}
var _pool: Array[SoundEmitter] = []
var _walk_stream: AudioStream
var _run_stream: AudioStream


func setup(
	data: CaseData,
	timeline: TimelineClock,
	actor_system: ActorSystem,
	ear: Listener,
	room_graph: Acoustics,
	parent: Node2D
) -> void:
	case_data = data
	clock = timeline
	actors = actor_system
	listener = ear
	acoustics = room_graph
	emitter_parent = parent
	case_data.sort_voice_lines()
	process_priority = 10
	_walk_stream = _load_loop(WALK_STREAM_PATH)
	_run_stream = _load_loop(RUN_STREAM_PATH)
	clock.seeked.connect(_on_seeked)
	clock.playing_changed.connect(_on_playing_changed)
	clock.speed_changed.connect(_on_speed_changed)


## 给定时刻正在说的台词下标。`lines` 必须按 start 升序。
static func active_line_indices(lines: Array[VoiceLine], t: float) -> PackedInt32Array:
	var out := PackedInt32Array()
	for i in lines.size():
		var line := lines[i]
		if line.start > t:
			break
		if line.is_active_at(t):
			out.append(i)
	return out


static func active_sfx_indices(events: Array[SfxEvent], t: float) -> PackedInt32Array:
	var out := PackedInt32Array()
	for i in events.size():
		if events[i].is_active_at(t):
			out.append(i)
	return out


func _process(_delta: float) -> void:
	if case_data == null:
		return
	var t := clock.time
	var listener_room := listener.room_name()
	_update_voices(t, listener_room)
	_update_sfx(t, listener_room)
	_update_footsteps(listener_room)


func _update_voices(t: float, listener_room: StringName) -> void:
	active_lines.clear()
	var speaking := {}
	var keep := {}
	for i in active_line_indices(case_data.voice_lines, t):
		var line := case_data.voice_lines[i]
		var result := acoustics.resolve(listener_room, actors.get_room_name(line.speaker), line.loudness)
		var entry := ActiveLine.new()
		entry.index = i
		entry.line = line
		entry.clarity = result.clarity
		active_lines.append(entry)
		speaking[line.speaker] = maxi(speaking.get(line.speaker, 0), result.clarity)
		if result.clarity == Acoustics.Clarity.CLEAR:
			line_heard.emit(i)
		if line.stream == null:
			continue
		keep[i] = true
		var pose := actors.get_pose(line.speaker)
		var pos := pose.position if pose else Vector2.ZERO
		_drive(_voice, i, line.stream, t - line.start, pos, result, line.volume_db)
	_release_missing(_voice, keep)
	actors.set_speaking(speaking)


func _update_sfx(t: float, listener_room: StringName) -> void:
	var keep := {}
	for i in active_sfx_indices(case_data.sfx_events, t):
		var ev := case_data.sfx_events[i]
		var pos := ev.position
		var room_name: StringName
		if ev.attach_to != &"":
			var pose := actors.get_pose(ev.attach_to)
			if pose:
				pos = pose.position
			room_name = actors.get_room_name(ev.attach_to)
		else:
			var room := actors.map.room_at(pos)
			room_name = StringName(room.room_name) if room else &""
		var result := acoustics.resolve(listener_room, room_name, ev.loudness)
		if result.audible():
			sfx_heard.emit(i)
		if ev.stream == null:
			continue
		keep[i] = true
		_drive(_sfx, i, ev.stream, t - ev.time, pos, result, ev.volume_db)
	_release_missing(_sfx, keep)


func _update_footsteps(listener_room: StringName) -> void:
	for c in case_data.characters:
		var pose := actors.get_pose(c.id)
		var em: SoundEmitter = _footsteps.get(c.id)
		var moving := pose != null and pose.moving and clock.playing
		if not moving:
			if em and em.playing:
				em.halt()
			continue
		var stream := _run_stream if pose.movement == TrackKey.Movement.RUN else _walk_stream
		if stream == null:
			continue
		if em == null:
			em = _acquire()
			_footsteps[c.id] = em
		var result := acoustics.resolve(listener_room, actors.get_room_name(c.id), FOOTSTEP_LOUDNESS)
		em.global_position = pose.position
		em.set_target(result.bus, result.gain_db + FOOTSTEP_GAIN_DB, result.audible())
		if not em.playing or em.stream != stream:
			em.start(stream, randf() * 0.4, false, clock.speed)


func _drive(
	table: Dictionary,
	key: int,
	stream: AudioStream,
	offset: float,
	pos: Vector2,
	result: Acoustics.Result,
	volume_db: float
) -> void:
	var em: SoundEmitter = table.get(key)
	if em == null:
		em = _acquire()
		table[key] = em
		em.global_position = pos
		em.set_target(result.bus, result.gain_db + volume_db, result.audible())
		em.start(stream, offset, not clock.playing, clock.speed)
		return
	em.global_position = pos
	em.set_target(result.bus, result.gain_db + volume_db, result.audible())
	if clock.playing and em.playing and not em.completed:
		var actual := em.get_playback_position() + AudioServer.get_time_since_last_mix() * clock.speed
		if absf(actual - offset) > DRIFT_TOLERANCE * maxf(1.0, clock.speed):
			em.seek(maxf(offset, 0.0))


func _release_missing(table: Dictionary, keep: Dictionary) -> void:
	for key: int in table.keys():
		if not keep.has(key):
			_release(table[key])
			table.erase(key)


func _acquire() -> SoundEmitter:
	if not _pool.is_empty():
		return _pool.pop_back()
	var em := SoundEmitter.new()
	emitter_parent.add_child(em)
	return em


func _release(em: SoundEmitter) -> void:
	em.halt()
	_pool.append(em)


func release_all() -> void:
	for table: Dictionary in [_voice, _sfx, _footsteps]:
		for em: SoundEmitter in table.values():
			_release(em)
		table.clear()


func _on_seeked(_t: float) -> void:
	for table: Dictionary in [_voice, _sfx]:
		for em: SoundEmitter in table.values():
			_release(em)
		table.clear()


func _on_playing_changed(is_playing: bool) -> void:
	for table: Dictionary in [_voice, _sfx]:
		for em: SoundEmitter in table.values():
			em.pitch_scale = clock.speed
			em.stream_paused = not is_playing


func _on_speed_changed(speed: float) -> void:
	AudioBuses.set_speed(speed)
	for table: Dictionary in [_voice, _sfx, _footsteps]:
		for em: SoundEmitter in table.values():
			em.pitch_scale = speed


func _load_loop(path: String) -> AudioStream:
	if not ResourceLoader.exists(path):
		return null
	var stream := load(path) as AudioStream
	if stream is AudioStreamOggVorbis:
		(stream as AudioStreamOggVorbis).loop = true
	return stream
