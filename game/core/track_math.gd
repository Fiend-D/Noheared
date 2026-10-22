@tool
class_name TrackMath
extends RefCounted
## 角色轨迹的纯函数采样：同一个 t 永远得到同一个结果。


class Pose:
	extends RefCounted
	var position: Vector2 = Vector2.ZERO
	var moving: bool = false
	var movement: TrackKey.Movement = TrackKey.Movement.IDLE
	## 当前所在区间的起始关键帧下标；t 早于第一帧时为 -1。
	var key_index: int = -1


## 返回最后一个 time <= t 的关键帧下标，t 早于第一帧时返回 -1。要求 track 按时间升序。
static func key_index_at(track: Array[TrackKey], t: float) -> int:
	var lo := 0
	var hi := track.size() - 1
	var found := -1
	while lo <= hi:
		var mid := (lo + hi) >> 1
		if track[mid].time <= t:
			found = mid
			lo = mid + 1
		else:
			hi = mid - 1
	return found


static func sample(track: Array[TrackKey], t: float) -> Pose:
	var pose := Pose.new()
	if track.is_empty():
		return pose
	var i := key_index_at(track, t)
	pose.key_index = i
	if i < 0:
		pose.position = track[0].position
		return pose
	var a := track[i]
	if i >= track.size() - 1:
		pose.position = a.position
		return pose
	var b := track[i + 1]
	var span := b.time - a.time
	var w := 1.0 if span <= 0.0 else clampf((t - a.time) / span, 0.0, 1.0)
	pose.position = a.position.lerp(b.position, w)
	pose.moving = not a.position.is_equal_approx(b.position)
	if pose.moving:
		pose.movement = TrackKey.Movement.WALK if a.movement == TrackKey.Movement.IDLE else a.movement
	return pose


## 所在关键帧区间的房间提示：优先使用前后关键帧上写明的 room。
static func room_hint(track: Array[TrackKey], key_index: int) -> StringName:
	if track.is_empty():
		return &""
	var i := clampi(key_index, 0, track.size() - 1)
	return track[i].room


static func sort_track(track: Array[TrackKey]) -> void:
	track.sort_custom(func(a: TrackKey, b: TrackKey) -> bool: return a.time < b.time)
