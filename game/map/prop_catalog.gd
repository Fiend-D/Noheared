@tool
class_name PropCatalog
extends RefCounted
## 家具目录（`art/props/catalog.json`，由 tools/art_sheets.py 生成）。只在导入和编辑器里用；
## 导入时把尺寸、阻挡等写进 Prop 节点，运行时不读这个文件。

const PROPS_DIR := "res://art/props/"
const FLOORS_DIR := "res://art/floors/"
const EXTERIOR_DIR := "res://art/exterior/"

static var _entries: Dictionary = {}


static func entries() -> Dictionary:
	if _entries.is_empty():
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(PROPS_DIR + "catalog.json"))
		if parsed is Dictionary:
			_entries = parsed
	return _entries


static func ids() -> PackedStringArray:
	return PackedStringArray(entries().keys())


static func has(id: String) -> bool:
	return entries().has(id)


## 按目录设置 Prop 的贴图、尺寸和阻挡属性。
static func apply(prop: Prop, id: String) -> void:
	prop.prop_type = id
	var e: Dictionary = entries().get(id, {})
	if e.is_empty():
		push_warning("家具目录里没有 %s" % id)
		return
	prop.texture = load(PROPS_DIR + id + ".png")
	prop.size = Vector2(e.size[0], e.size[1])
	prop.blocks = bool(e.get("block", true))
	prop.rug = bool(e.get("rug", false))


static func floor_texture(material_id: String) -> Texture2D:
	if material_id == "":
		return null
	var path := FLOORS_DIR + material_id + ".jpg"
	return load(path) if ResourceLoader.exists(path) else null


static func exterior_texture(id: String) -> Texture2D:
	if id == "":
		return null
	var path := EXTERIOR_DIR + id + ".jpg"
	return load(path) if ResourceLoader.exists(path) else null


## 材质贴图的名字（文件名去掉扩展名），地板和外景通用。
static func floor_id(texture: Texture2D) -> String:
	return texture.resource_path.get_file().get_basename() if texture else ""
