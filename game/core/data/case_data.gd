@tool
class_name CaseData
extends Resource

@export var id: StringName = &""
@export var title: String = ""
@export_multiline var description: String = ""
@export var duration: float = 60.0
@export var map_scene: PackedScene
@export var characters: Array[CharacterData] = []
@export var voice_lines: Array[VoiceLine] = []
@export var sfx_events: Array[SfxEvent] = []
@export var questions: Array[Question] = []
## 全部答对后展示的真相。
@export_multiline var truth: String = ""
## 案件选择界面档案袋上的照片（`art/title/photo_<cover>.png`）。
@export var cover: String = ""


func get_character(character_id: StringName) -> CharacterData:
	for c in characters:
		if c.id == character_id:
			return c
	return null


func character_names() -> PackedStringArray:
	var names := PackedStringArray()
	for c in characters:
		names.append(c.display_name)
	return names


func options_for(question: Question) -> PackedStringArray:
	if question.kind == Question.Kind.CHARACTER and question.options.is_empty():
		return character_names()
	return question.options


func sort_voice_lines() -> void:
	voice_lines.sort_custom(func(a: VoiceLine, b: VoiceLine) -> bool: return a.start < b.start)
