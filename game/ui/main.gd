extends Node
## 在案件选择界面和游戏界面之间切换。

var _theme: Theme
var _current: Node


func _ready() -> void:
	_theme = UiTheme.build()
	AudioBuses.setup()
	get_window().title = tr("APP_TITLE")
	show_case_select()


func show_case_select() -> void:
	var select := CaseSelect.new()
	select.theme = _theme
	select.case_chosen.connect(start_case)
	_swap(select)


func start_case(path: String) -> void:
	var data := CaseLibrary.load_case(path)
	if data == null:
		push_error("无法加载案件：%s" % path)
		return
	var game := Game.new()
	game.ui_theme = _theme
	game.case_data = data
	game.exit_requested.connect(show_case_select)
	_swap(game)


func _swap(node: Node) -> void:
	if _current:
		_current.queue_free()
	_current = node
	add_child(node)
