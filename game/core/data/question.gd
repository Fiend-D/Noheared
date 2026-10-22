@tool
class_name Question
extends Resource

enum Kind { CHOICE, CHARACTER }

@export var id: StringName = &""
@export var kind: Kind = Kind.CHOICE
@export_multiline var prompt: String = ""
## `CHARACTER` 类题目的选项为空时，使用案件中所有角色的真实姓名。
@export var options: PackedStringArray = PackedStringArray()
@export var answer: String = ""
