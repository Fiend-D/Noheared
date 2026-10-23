extends Node
## 在主界面、档案室和游戏界面之间切换。

var _theme: Theme
var _current: Node


func _ready() -> void:
	_theme = UiTheme.build()
	AudioBuses.setup()
	get_window().title = tr("APP_TITLE")
	show_title()


func show_title() -> void:
	var title := TitleScreen.new()
	title.theme = _theme
	title.start_requested.connect(show_cabinet)
	_swap(title)


func show_cabinet() -> void:
	var cabinet := CaseCabinet.new()
	cabinet.theme = _theme
	cabinet.case_chosen.connect(start_case)
	cabinet.back_requested.connect(show_title)
	_swap(cabinet)


func start_case(path: String) -> void:
	var data := CaseLibrary.load_case(path)
	if data == null:
		push_error("无法加载案件：%s" % path)
		return
	var game := Game.new()
	game.ui_theme = _theme
	game.case_data = data
	game.exit_requested.connect(show_cabinet)
	_swap(game)


func _swap(node: Node) -> void:
	if _current:
		_current.queue_free()
	_current = node
	add_child(node)
