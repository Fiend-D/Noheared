# unheared

复刻《疑案追声》玩法的声音推理游戏（Godot 4 重写版）。

你是一个看不见的“耳朵”：案件是一段固定时长的录音，角色在多房间的蓝图地图上走动、交谈。你只能听清自己所在房间的对话，隔壁只有闷声，尖叫枪声能穿墙。反复倒带、换房间跟人，最后指认每个圆点的身份并回答问题。

## 文档

| 文档 | 内容 |
| --- | --- |
| [docs/setup.md](docs/setup.md) | 环境搭建：Godot、代码检查、ffmpeg / Python 库、配音环境（edge-tts、CosyVoice2） |
| [docs/case-authoring.md](docs/case-authoring.md) | 自制剧本：case.json 全部字段、地图与走位规则、配音脚本用法、导入校验、编辑器插件 |
| [docs/packaging.md](docs/packaging.md) | 打包发布：导出模板、导出命令、打包内容、CI 产物、图标与版本号 |
| [docs/unheard-analysis.md](docs/unheard-analysis.md) | 玩法拆解与设计说明 |

## 运行

需要 [Godot 4.7](https://godotengine.org/download)（标准版，非 .NET）。

```bash
godot --path game            # 直接运行
godot -e --path game         # 打开编辑器
```

首次打开会自动导入资源。命令行环境可先执行 `godot --headless --path game --import`。

主界面只有“开始调查 / 设置 / 退出”。开始调查进入档案室：抽屉里竖着一排案卷，后面的只露出标签，最前面一份露出案件名和海报；滚轮或方向键翻阅，点标签直接翻到那一份，点最前面的档案把它取出、摊开成卷宗（海报、案情、涉案人物、最佳成绩），点“开始查案”进入游戏。

地图上的角色是棋子：还没指认时是带编号的灰色剪影，指认身份后换成该身份的头像徽章，下面挂名字缎带。

操作：

| 按键 | 作用 |
| --- | --- |
| WASD / 方向键 | 监听者走动（墙会挡住，只能从门洞进出房间；走到楼梯口自动上下楼） |
| Shift | 快走 |
| 鼠标左键点房间 | 监听者沿门洞、楼梯自动走过去 |
| 鼠标左键点角色 | 选中角色，右侧切到“人物”指认 |
| 空格 | 播放 / 暂停 |
| Q / E | 倒退 / 快进 5 秒 |
| R | 切换倍速（×0.5 / ×1 / ×2 / ×4） |
| 滚轮 | 缩放地图，放大后镜头跟随监听者 |

监听者按真实时间走动，暂停和倒带时也可以移动。右侧“笔记”点击条目可跳回该时刻。

## 目录

```
game/                    Godot 项目
  core/                  时间轴、轨迹采样、声学、调度、存档、JSON 导入导出、校验
  map/                   Room / Door / Stair / Prop / CaseMap 节点，聚光着色器，监听者
  ui/                    主界面（书桌）、档案室（选案件）、游戏控制器、HUD
  art/                   地板材质、家具贴图 + catalog.json、主界面素材、案件海报、角色头像
  cases/<id>/            case.json（源数据）、case.tres + map.tscn（导入结果）、audio/*.ogg
  addons/case_editor/    编辑器插件：时间轴面板、地图预览、试听、校验、导入导出
  addons/gdUnit4/        测试框架
  tests/                 gdUnit4 测试
tools/                   Python 内容流水线（迁移、配音、美术切图、自动摆家具）
  art_sources/           AI 生成的原始素材表（家具、地板、书桌、照片、肖像表、海报）
docs/                    设计文档
legacy/                  旧版 PyQt 实现（只保留代码和案件 JSON 作参考）
```

### 仓库里提交什么

提交代码、文档、案件源数据（`case.json`）以及运行游戏必需的资源：`game/cases/*/audio/*.ogg`、`game/audio/`、`game/art/`（以及它的原始素材表 `tools/art_sources/`）、导入生成的 `case.tres` / `map.tscn` 和 `*.import`。这样 clone 下来就能直接运行，CI 导出的版本也带声音。

以下内容只留在本地，已写进 `.gitignore`：

- `legacy/release/`（旧版打包产物）、`legacy/unheared/audio/` 及旧版的 WAV / MP3 录音：已迁移成 `game/cases/*/audio` 下的逐句 OGG。
- `tools/voice_prompts/`：配音时的参考音频，缺失时 `tts_lines.py` 会自动从现有语音里重新挑。
- Godot 缓存和产物：`game/.godot/`、`game/export/`、`game/reports/`、`*.translation`（导入时由 `i18n/strings.csv` 生成）。

## 核心设计

- **确定性时间轴**：`TimelineClock` 是唯一时间源；角色位置是关键帧插值的纯函数 `TrackMath.sample(track, t)`，任意 seek、倒退结果都与顺序播放一致。
- **逐句语音**：每句台词一个音频片段，`CueScheduler` 按当前时间决定播放哪些片段、从哪个偏移量开始，并做漂移校正。变速时在 Master 总线上做音高补偿。
- **声学**：`Acoustics` 用房间连通图（门、楼梯；关着的门代价更高）决定可听性。同房间走 `Room` 总线（定位声像 + 按房间大小的混响），隔一道门走 `Muffled`（低通），大音量事件按跳数衰减走 `Far`。切换总线时淡入淡出。
- **只记录听到的内容**：字幕只显示能听到的台词，隔墙的只显示“听不清”；听清的台词进入笔记。
- **监听聚光**：地图是插画式室内（地板材质 + 可复用家具贴图，墙由房间多边形画出，和数据精确对齐）。监听者所在房间是暖色原色，其余房间按声学距离逐级变暗、变成青色单色（`map/lit.gdshader`，`MapStyle.LIGHT_LEVELS`）。
- **家具挡路**：挡路的家具监听者走不过去，点击寻路会在房间内绕开（`CaseMap.route`）。角色仍严格按关键帧移动，所以家具必须避开角色轨迹——自动摆放脚本和校验器都会检查。

## 案件数据

`game/cases/<id>/case.json` 是源数据，`case.tres` / `map.tscn` 由它导入生成：

```bash
godot --headless --path game --import
godot --headless --path game --script res://addons/case_editor/import_cli.gd -- case1 case5   # 不带参数则全部导入
```

完整字段说明、设计规则和编辑器插件用法见 [docs/case-authoring.md](docs/case-authoring.md)。

## 内容流水线（tools/）

### 迁移旧案件

```bash
python3 tools/migrate_legacy_case.py            # 全部；或指定 case1 case5
```

读取 `legacy/unheared/cases/*.json` 和整段角色录音，输出新格式 `case.json`、逐句 OGG 和脚步声。旧版的“时间段 + 目标点”会按旧版速度沿门洞路线展开成确定性关键帧。只依赖标准库和 ffmpeg。

迁移已经做完，结果都在 `game/cases/` 里。旧版录音（`legacy/unheared/audio/`）不在仓库中，只有本地有这些文件时才能重新跑迁移。

### 剧本编译

```bash
python3 tools/compose_case.py case8 --check   # 检查剧本，打印每场的起止时间
python3 tools/compose_case.py case8           # case.play → case.json
```

把纯文本剧本 `game/cases/<id>/case.play`（房间矩形、角色、台词、“谁走到哪”）编译成 `case.json`：自动放门、规划走位、让说话的人先走到位、绕开家具，配音后按真实时长重新排时间。case8、case9 用它编写。格式和流程见 [docs/case-authoring.md](docs/case-authoring.md#12-用剧本文件编写)。

### 美术素材

家具、地板、主界面、角色头像和案件海报都是 AI 生成的素材，原图在 `tools/art_sources/`：家具和肖像为洋红底的 3×3 表（每格一件 / 一人），地板为 3×3 材质表，海报为单张竖图。切图并生成目录：

```bash
python3 tools/art_sheets.py   # 需要 Pillow + numpy + scipy
```

脚本按到背景色的距离和洋红色相去底、裁边，输出 `game/art/props/*.png` + `catalog.json`（地图尺寸、是否挡路、是否地毯）、`game/art/floors/*.jpg`、`game/art/exterior/*.jpg`、`game/art/title/`、`game/art/portraits/<案件>/<角色 ID>.jpg`（每格去边框、取头肩部分）和 `game/art/posters/<案件>.jpg`（裁成 3:4）。新增家具：在素材表里加一格，把名字写进 `PROP_SHEETS`、尺寸写进 `CATALOG`。家具尺寸改了以后要重新导入案件（尺寸在导入时写进 `map.tscn`）。

### 自动摆家具

```bash
python3 tools/furnish.py                # 给还没有家具的案件铺地板、摆家具
python3 tools/furnish.py case4 --force  # 重摆
python3 tools/furnish.py case8 --force --ignore-tracks  # 不避让轨迹（之后用 compose_case.py 让角色绕开家具）
```

按房间名套模板（书房 → 书架、书桌、地毯……），家具贴图不压任何角色的轨迹和站位，门口、楼梯口、房间名附近留空；每放一件挡路家具都检查监听者仍能在门口、楼梯口之间走通。结果是确定的，可以在编辑器里继续手调。改完重新导入。

### 配音

```bash
~/.local/share/unheard-tts/venv/bin/python tools/tts_lines.py case8 case9      # CosyVoice2，生成缺失的台词，可中断续跑
.venv/bin/python tools/tts_lines.py case8 --engine edge                        # edge-tts
python3 tools/fix_speech_timing.py case8                                       # 配音后让角色先走到位再开口
```

括号里的表演提示不会被念出来，而是作为 CosyVoice 的语气指令。安装见 [docs/setup.md](docs/setup.md#4-配音环境)，参数、音色、返工方法见 [docs/case-authoring.md](docs/case-authoring.md#6-配音)。

## 测试与检查

```bash
pip install "gdtoolkit==4.*"
cd game
gdformat --check --line-length=120 core map ui addons/case_editor tests
gdlint core map ui addons/case_editor tests
godot --headless -s -d res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://tests
```

CI（`.github/workflows/ci.yml`）会跑格式检查、lint、重新导入全部案件、gdUnit4 测试，并导出 Linux / Windows 版本。

## 导出

```bash
cd game && mkdir -p export/linux && godot --headless --export-release Linux
```

需要先安装 4.7.2 导出模板，详见 [docs/packaging.md](docs/packaging.md)。
