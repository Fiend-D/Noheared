@tool
class_name CharacterData
extends Resource

@export var id: StringName = &""
## 真实身份，玩家需要推理出来。
@export var display_name: String = ""
## 圆点上显示的编号。
@export var label: String = ""
@export var color: Color = Color.WHITE
@export var track: Array[TrackKey] = []
