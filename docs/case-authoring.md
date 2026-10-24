# 自制剧本

一个案件 = 一段固定时长的“录音”：几名角色按时间表在多房间地图里走动、说话，玩家扮演看不见的监听者，只能听清自己所在房间的对话。本文从零做一个案件，按顺序走一遍即可。环境准备见 [setup.md](setup.md)。

## 0. 流程总览

```
写 case.json（地图 / 角色走位 / 台词 / 问题）
  → 生成配音        tools/tts_lines.py
  → 修正走位时间    tools/fix_speech_timing.py
  → 铺地板摆家具    tools/furnish.py
  → 导入 + 校验      import_cli.gd
  → 编辑器里微调、试玩
  → 提交
```

源数据只有 `game/cases/<id>/case.json` 和 `audio/` 下的音频；`case.tres`、`map.tscn` 都是导入生成的，不要手改。

手写关键帧很累。更省事的做法是写一个剧本文件 `case.play`，用 `tools/compose_case.py` 自动生成走位和台词时间，见[第 12 节](#12-用剧本文件编写)（case1、case2、case3、case8、case9 就是这样写的）。

## 1. 新建案件

```bash
mkdir -p game/cases/case8/audio
```

案件按目录名自然排序（`case2` 在 `case10` 前），选择界面的“档案 0N”就是这个顺序。最小骨架：

```json
{
 "format": 1,
 "id": "case8",
 "title": "雨夜书店",
 "description": "打烊后的书店里传出争吵声……",
 "duration": 300,
 "truth": "全部答对后展示的真相文字。",
 "cover": "street",
 "map": {
  "floors": ["一层"],
  "backdrop": "cobblestone",
  "rooms": [],
  "doors": [],
  "stairs": [],
  "props": []
 },
 "characters": [],
 "voice_lines": [],
 "sfx": [],
 "questions": []
}
```

| 字段 | 说明 |
| --- | --- |
| `id` | 与目录名一致，存档按它区分 |
| `duration` | 录音总长（秒） |
| `truth` | 全部问题答对后弹出的真相 |
| `cover` | 备用封面：案件还没有海报时，档案室用这张小照片代替：`office` `theatre` `gallery` `study` `liner` `manor` `hotel` `tape` `street`（`game/art/title/photo_*.png`） |

也可以复制一个现有案件（如 `case1`）再改，记得把 `audio/` 清空、`id` 改掉。

### 1.1 海报与角色头像

档案室里每份案卷正面贴一张海报，地图上角色被指认身份后显示该身份的头像。两者都按案件 `id` 和角色 `id` 找文件，缺了也能玩（海报退回 `cover` 照片，头像退回灰色剪影）：

| 文件 | 来源 | 要求 |
| --- | --- | --- |
| `game/art/posters/<id>.jpg` | `tools/art_sources/poster_<id>.jpg` | 竖版电影海报风插画，不要文字；脚本居中裁成 3:4、缩到 600×800 |
| `game/art/portraits/<id>/<角色 ID>.jpg` | `tools/art_sources/portraits_<n>.jpg` | 洋红底 3×3 肖像表，每格一人：米色细边框、深色背景、头肩像、脸居中，不要文字。在 `tools/art_sheets.py` 的 `PORTRAITS` 里按格子顺序写上 `"<案件>/<角色 ID>"` |

生成肖像时把性别、年龄、职业和年代写清楚，并和配音音色对上（音高 200 Hz 以上一般是女声）。放好原图后运行 `python3 tools/art_sheets.py`，再 `godot --headless --path game --import`。头像按身份名（`name`）匹配：玩家给某个棋子指认了“宋院长”，棋子上就显示 `name` 为“宋院长”的那个角色的头像。case1、case2、case3 重写后旧头像已删掉，新头像还没切，指认后仍是灰色剪影。

## 2. 剧本设计要点

玩法核心是“只能听见一部分”，好剧本要逼玩家反复倒带、换房间：

- **线索分散在不同房间、同一时刻**。两场关键对话同时发生在相隔两道门的房间，玩家第一遍只能跟一边。
- **身份要靠听来推断**。地图上的人在指认前只显示带编号的灰色剪影；玩家要根据对话内容（称呼、口头禅、谈到的事）把名字对应到圆点上，这是计分的一半。台词里适当互相称呼。
- **大音量事件做节点**。尖叫、枪声、摔门能穿墙，适合标记“出事了”，引导玩家赶过去。
- **说谎和不在场证明**。角色私下说的和公开说的不一样，玩家需要两边都听到。
- **时长**：入门 2–5 分钟、3–4 人；完整案件 20–30 分钟、8–10 人（参考 case6 / case7）。
- **不要冷场**：玩家能去任何房间，所以“空窗期”指全图都没人说话、也没有音效的时间。规则见下面 2.1。

### 2.1 节奏规则

`tools/pacing.py` 检查已生成的 `case.json`；`compose_case.py` 编译时自动跑同样的检查，有**错误**就不写 `case.json`。

```bash
python3 tools/pacing.py case8 case9   # 有错误时退出码为 1
```

| 规则 | 级别 |
| --- | --- |
| 开场 10 秒内必须有第一声 | 错误 |
| 任何一段全图空窗不超过 20 秒 | 错误 |
| 10 秒以上的空窗每 5 分钟最多 1 段（不足 5 分钟按 1 段算） | 错误 |
| 最后一声之后留白不超过 15 秒（剧本里写 `时长: 自动` 就不会超） | 错误 |
| 单句台词不超过 12 秒 / 60 字，太长就拆开 | 提示 |
| 同一房间两个人同时说话（重叠超过 0.3 秒），听不清 | 提示 |
| 同一时刻最多 3 个房间在说话，再多玩家顾不过来 | 提示 |
| 每个角色至少 5 句台词，否则很难认出 | 提示 |
| 每个身份至少被别人叫到 2 次（全名；三个字以上的去掉首字，如“宋院长”→“院长”；两个字的人名加姓氏称呼，如“林小姐”“林姐”） | 提示 |

补空窗的办法是**加一场戏**（让闲着的角色在别的房间聊几句、顺带埋一条线索），而不是把后面的场景硬往前挪。游戏里的校验（第 7 节）也会对开场、空窗、留白给出 WARN，旧案件的录音里还有几处超标的空窗。

建议先写一张时间表（时间 × 房间 × 谁在场 × 说什么），再落到 JSON。

## 3. 地图

坐标单位是像素，y 轴向下。比例感：角色棋子直径约 30，单人床约 50×85，一般房间 200–400 见方。

### 3.1 房间 `rooms`

```json
{"name": "店堂", "floor": 0, "polygon": [[50,50],[400,50],[400,300],[50,300]], "floor_material": "wood"}
```

- `name` 在整个案件中唯一，地图上显示在房间左上角。
- `polygon` 按顺序给出顶点，推荐矩形。同一层的房间**不能重叠**（校验报错）；可以共用一面墙，也可以留 20–50 的缝（缝会画成厚墙）。
- `floor` 是 `map.floors` 的下标。多层建筑的各层放在不同的 y 区间，不要重叠。
- `floor_material`：`wood` `parquet` `checker` `carpet` `marble` `deck` `flagstone` `grass` `concrete`（不写则由 `furnish.py` 按房间名里的关键词选，更具体的词优先，例如「总经理室 / 副总室 / 财务室」先于「办公室」，「会议室」「茶水间」「前台」各自有模板）。
- `outdoor: true`：花园、甲板、露台等，画围栏而不是墙。

### 3.2 门 `doors`

```json
{"name": "店堂门", "room_a": "店堂", "room_b": "库房", "position": [400,175], "size": [20,40], "open": true}
```

- 门中心要**在两个房间之间的墙上**：共用墙时就在墙线上；房间之间有缝时在缝中间，缝宽不超过 80。
- `size` 是门洞的宽高：竖墙上的门 `[20,40]`（洞宽 40），横墙上的门 `[40,20]`。洞宽大于 34 画成双扇门。
- `open: false` 是关着的门：监听者照样能走过去，但声音更难穿过（声学代价 2 而不是 1）。

### 3.3 楼梯 `stairs`

```json
{"name": "楼梯", "room_a": "店堂", "room_b": "阁楼", "end_a": [215,280], "end_b": [215,520]}
```

`end_a` / `end_b` 分别在两个房间里面（离墙 20 左右）。监听者踩到楼梯口就传送到另一端。两端可以在同一层（船上不同甲板就是这样做的）。

### 3.4 外景与家具

- `backdrop`：建筑外的地面，`lawn` `hedge` `cobblestone` `ocean` `asphalt` `gravel` `forest` `sand` `dirt`。
- `props`：家具，一般不手写，走完第 4、5 节后用脚本自动摆（第 6.4 节），再在编辑器里调。格式：

  ```json
  {"type": "sofa", "position": [520,180], "room": "店堂", "flip": true}
  ```

  `type` 取自 `game/art/props/catalog.json`（沙发、床、书架、钢琴、赌桌、酒架、喷泉等 45 种），尺寸和是否挡路由目录决定。

## 4. 角色与走位

```json
{
 "id": "A", "name": "店主", "label": "1", "color": "#c0392b",
 "track": [
  {"t": 0,    "p": [120,150], "m": "idle", "room": "店堂"},
  {"t": 30,   "p": [120,150], "m": "walk", "room": "店堂"},
  {"t": 31.9, "p": [390,175], "m": "walk", "room": "店堂"},
  {"t": 32.2, "p": [420,175], "m": "walk", "room": "库房"},
  {"t": 33.5, "p": [500,200], "m": "idle", "room": "库房"}
 ]
}
```

| 字段 | 说明 |
| --- | --- |
| `id` | 台词、音效引用它，短字母即可 |
| `name` | 真实身份。玩家给棋子指认的名字要和它完全一致才算对；指认后棋子显示这个身份的头像 |
| `label` | 棋子上显示的编号 |
| `color` | 棋子外圈和编号牌的颜色，尽量互相区分 |
| `voice_prompt` / `voice_prompt_text` / `edge_voice` | 配音用，见第 6 节 |

关键帧 `track`：

- `t` 时间（秒），`p` 位置，`room` 所在房间（在门洞里时写离开的那个房间）。
- `m` 描述**从本帧到下一帧**怎么移动：`idle` 站着，`walk` 走（脚步声），`run` 跑（跑步声）。站着不动用两帧同位置、前一帧 `idle`。
- 位置在两帧之间直线插值。速度由距离 / 时间决定，参考：走 150 px/s，跑 300 px/s。
- **换房间必须经过门**：在门前一帧、门后一帧（如上例 390→420 跨过 x=400 的门）；楼梯则是楼梯口一帧、另一端楼梯口一帧。直接从一个房间跳到不相连的房间会被校验为“穿墙”。
- 角色**不会绕开家具**，摆家具时脚本会避开所有轨迹；手动放家具时别压在路线上（校验会警告“穿过家具”）。
- **说话时要站定**：台词开始时还在走、或说到一半离开，校验会警告。写完台词后用 `tools/fix_speech_timing.py` 自动修正（第 6.3 节）。

## 5. 台词与音效

### 5.1 台词 `voice_lines`

```json
{"speaker": "A", "start": 35.0, "duration": 3.2, "text": "（压低声音）账本你藏哪儿了？", "loudness": 0.3}
```

| 字段 | 说明 |
| --- | --- |
| `start` / `duration` | 开始时间和时长（秒）。配音后 `duration` 由脚本按真实音频改写 |
| `text` | 字幕原文。`（）` 里是表演提示：字幕里显示，**不会被念出来**，CosyVoice 用它控制语气 |
| `loudness` | 0–1，决定能穿过几道门（见下表），默认 0.5 |
| `audio` | `audio/xxx.ogg`，由配音脚本填写；为空时只显示字幕 |
| `volume_db` | 单句音量微调 |
| `tts_instruct` | 设为 `false` 时配音不使用语气指令（见 6.2） |

同一角色的台词不能重叠。`loudness` 与可听范围：

| loudness | 同房间 | 隔一道开着的门 | 更远 |
| --- | --- | --- | --- |
| < 0.75（正常、低声） | 清楚 | 闷声，字幕“听不清” | 听不到 |
| 0.75–0.83 | 清楚 | 闷声 | 两道门内闷声 |
| 0.9（尖叫、拍桌） | 清楚 | 闷声 | 三道门内闷声 |
| 1.0（枪声） | 清楚 | 闷声 | 五道门内闷声 |

关着的门算两道。只有同一房间能听清并记入笔记。

### 5.2 音效 `sfx`

```json
{"time": 120, "duration": 1.5, "audio": "audio/shot.ogg", "position": [200,300], "loudness": 1.0, "label": "枪声"}
```

固定位置用 `position`；跟着角色走用 `"attach_to": "A"`。`label` 是听到时字幕和笔记里的文字。音频自己准备，放进 `audio/`，建议 OGG。

脚步声不用写：角色关键帧是 `walk` / `run` 时自动播放。

## 6. 配音

`tools/tts_lines.py` 逐句生成语音，写回 `case.json`。环境见 [setup.md 第 4 节](setup.md#4-配音环境)。

### 6.1 选引擎

| | CosyVoice2（默认） | edge-tts |
| --- | --- | --- |
| 运行环境 | `~/.local/share/unheard-tts/venv/bin/python` | `.venv/bin/python` |
| 音色 | 克隆角色的参考音频 | 微软预置音色 |
| 语气指令 | 支持（括号内容） | 不支持 |
| 速度 | CPU 上每秒语音约数秒 | 快，需联网 |

### 6.2 命令

在仓库根目录运行：

```bash
TTS=~/.local/share/unheard-tts/venv/bin/python

$TTS tools/tts_lines.py case8                 # 生成缺失的、或由其他引擎生成的台词
$TTS tools/tts_lines.py case8 case9           # 一次处理多个案件
$TTS tools/tts_lines.py case8 --only 12 13    # 只重做第 12、13 句（voice_lines 下标，从 0 开始）
$TTS tools/tts_lines.py case8 --force         # 全部重新生成

.venv/bin/python tools/tts_lines.py case8 --engine edge                     # 用 edge-tts
.venv/bin/python tools/tts_lines.py case8 --engine edge --voice A=zh-CN-YunjianNeural --voice B=zh-CN-XiaoxiaoNeural
```

| 参数 | 作用 |
| --- | --- |
| `--engine cosyvoice / edge` | 选引擎，默认 cosyvoice |
| `--only N ...` | 只生成指定下标的台词 |
| `--force` | 不管是否已有音频，全部重做 |
| `--voice ID=音色` | edge 引擎指定角色音色，可重复；也可以在角色上写 `"edge_voice"`。不指定时轮流使用云扬、晓晓、云希、晓伊、云健 |
| `--model 目录` | CosyVoice 模型目录（默认 `~/.local/share/unheard-tts/models/CosyVoice2-0.5B`，也可用 `COSYVOICE_MODEL`） |

脚本每生成一句就保存一次 `case.json`，可以随时 Ctrl+C，再次运行会从没做完的地方继续。

每句生成后脚本会：

- 把音频写到 `audio/<角色>_<文本哈希>.ogg`，填 `audio`、按实际长度改 `duration`，标记 `"tts": "cosyvoice"`（或 `edge`）；
- 表演提示含“尖叫 / 大喊 / 怒吼 / 拍桌 / 吼”时把 `loudness` 设为 0.9，含“低声 / 小声 / 耳语 / 自言自语 / 喃喃”时设为 0.3；
- 阿拉伯数字转成中文再念：年份逐位读（“1983年”→“一九八三年”，“83年的”→“八三年的”，“90年代”→“九零年代”），其他按数值读（“20年”→“二十年”，“120”→“一百二十”）；
- 全部完成后，如果语音比预留的长，把同一角色的下一句顺延（不会让同一人的两句重叠），并删除不再被引用的旧音频。

### 6.3 角色音色（CosyVoice）

CosyVoice 用一段参考音频克隆音色，写在角色上：

```json
"voice_prompt": "tools/voice_prompts/case8/A.wav",
"voice_prompt_text": "参考音频里说的原话，一字不差。"
```

- 参考音频 3–10 秒、单人、干净、无背景音乐，WAV。`voice_prompt_text` 必须和音频内容一致，否则会串音。
- `tools/voice_prompts/` 不提交到 git。
- **没有参考音频时**：脚本会从该角色已有的语音里自动挑一句 3–10 秒、不带括号的作参考，复制到 `tools/voice_prompts/` 并写回 `case.json`。所以全新案件可以先用 edge 生成一版，再用 CosyVoice 重新生成：

  ```bash
  .venv/bin/python tools/tts_lines.py case8 --engine edge --voice A=zh-CN-YunjianNeural ...
  ~/.local/share/unheard-tts/venv/bin/python tools/tts_lines.py case8   # 以 edge 的声音为参考，加上语气
  ```

  要更像真人，就自己录一段或找授权的素材当参考。

### 6.4 生成后的必做步骤

配音改变了台词时长，走位要重新对齐：

```bash
python3 tools/fix_speech_timing.py case8 --dry-run   # 先看会改什么
python3 tools/fix_speech_timing.py case8             # 让角色先走到位再开口、说完再离开
python3 tools/furnish.py case8 --force               # 走位变了就重摆家具（避开新的路线）
godot --headless --path game --import
godot --headless --path game --script res://addons/case_editor/import_cli.gd -- case8
```

`fix_speech_timing.py` 只改关键帧时间、不改路线：说话时还在走就把这段路提前走完（台词前 0.3 秒到达），说到一半要走就推迟到说完；空间不够时把这段路走快一些（最多压缩到原时长的 40%），再不够就不改，留给校验提示你手动处理。

### 6.5 抽查与返工

- 个别句子会把语气指令念出来（比如念出“用符合的语气说这句话”）。在该句加 `"tts_instruct": false`，再 `--only <下标>` 重做。
- 可以用 CosyVoice 环境里的 whisper 转写抽查：

  ```bash
  ~/.local/share/unheard-tts/venv/bin/python -c "import whisper,sys; m=whisper.load_model('small'); print(m.transcribe(sys.argv[1], language='zh')['text'])" game/cases/case8/audio/A_xxxx.ogg
  ```

- 读音不对：改写 `text`（例如用同音字），文本变了文件名也会变，旧文件会自动清理。

## 7. 导入与校验

```bash
godot --headless --path game --import                                              # 新音频 / 图片生成 .import
godot --headless --path game --script res://addons/case_editor/import_cli.gd -- case8   # 不带参数则导入全部
```

输出形如 `case8: 雨夜书店，4 名角色，60 句台词，0 条校验提示`，后面逐条列出问题：

| 提示 | 含义 / 处理 |
| --- | --- |
| ERROR 房间 X 与 Y 重叠 | 同层房间多边形相交，改坐标 |
| ERROR 门 X 没有对着房间 Y 的墙 / 两侧房间相距超过 80 | 门的位置不在两个房间之间的墙上 |
| ERROR 角色 X 从 A 直接到了 B（两房间不相连） | 换房间没经过门或楼梯口，补关键帧 |
| ERROR 关键帧没有按时间排序 | 检查 `t` |
| ERROR 台词的说话人不存在 / 超出案件时间 / 问题答案不在选项中 | 对应改数据 |
| ERROR 家具不在房间里 | `props` 的位置或 `room` 写错 |
| WARN 关键帧标注为 A，但坐标在 B | `room` 字段写错 |
| WARN 开口时还在走 / 说到一半换了房间 | 运行 `fix_speech_timing.py`，或手动调关键帧 |
| WARN 穿过家具 | 挪开家具，或 `furnish.py --force` |
| WARN 与上一句重叠 | 同一角色两句台词时间重叠 |
| WARN N 句台词没有语音 | 只显示字幕，可接受但最好补上 |
| WARN 开场 X 秒才有第一声 / 全图空窗 X 秒 / 最后一声之后还有 X 秒留白 | 节奏规则（2.1 节），补一场戏或缩短 `duration` |

`ERROR` 必须修；测试 `tests/test_case_json.gd`、`tests/test_listener_walk.gd` 会对所有案件检查说话时站定、门能走通、家具不堵路，CI 不过就合不进去。

## 8. 在编辑器里调整

`godot -e --path game` 打开编辑器：

- 在文件系统面板选中 `cases/case8/case.tres`，底部出现“案件时间轴”：每个角色一行显示台词块和关键帧，可拖动改时间，Ctrl+滚轮缩放；时间轴上的游标就是预览时刻；选一个“监听房间”再点“▶ 试听”，能听到站在那个房间时的效果；“校验”列出问题；“保存”写回 `case.tres`。
- 打开 `cases/case8/map.tscn` 编辑地图：视口里会画出预览时刻的人物位置。房间、门、楼梯是普通节点，可在检查器里改；房间的地板在 `floor_texture` 里换。
- 右侧“家具”面板：点选一件，在地图上单击放置（Shift 连续放，右键 / Esc 取消）；拖动已有家具移动；“水平翻转”翻转选中的家具。都能撤销。
- 改完先保存 `map.tscn`，再用“项目 → 工具 → 案件：导出当前案件为 case.json”写回 JSON。**JSON 才是源数据**，不导出的话下次导入会被覆盖。

## 9. 问题与计分

```json
"questions": [
 {"id": "q1", "kind": "character", "prompt": "谁拿走了账本？", "answer": "店员"},
 {"id": "q2", "kind": "choice", "prompt": "账本藏在哪里？", "options": ["收银台", "阁楼", "库房"], "answer": "阁楼"}
]
```

- `character` 题的选项默认是全部角色名，`answer` 写角色的 `name`；`choice` 题要给 `options`，`answer` 必须是其中之一。
- 得分 = （答对的题 + 指认对的角色）/（题数 + 角色数）。**所有题都答对**才算破案，弹出 `truth`，选择界面盖上“已结案”。

## 10. 试玩检查

- 从头到尾在一个房间里不动，能听到的内容是否足以引起好奇、但不足以破案？
- 每道题的关键线索至少在一个房间里能听清，且需要的走位来得及（监听者走路约 170 px/s，Shift 快走 ×1.8）。
- 每个角色至少有一次可以靠对话确认身份。
- 关键事件（尖叫、枪声）在附近房间能听到。
- 删除 `user://saves/case8.json`（位置见 [setup.md](setup.md#1-godot)）后从零玩一遍。

## 11. 提交

提交 `case.json`、`audio/*.ogg` 及 `*.import`、生成的 `case.tres` / `map.tscn`；用剧本文件写的案件还要提交 `case.play`。不要提交 `tools/voice_prompts/`。提交信息用 conventional commits，例如 `feat: add case8 雨夜书店`。

## 12. 用剧本文件编写

`game/cases/<id>/case.play` 是一个纯文本剧本：写清楚“谁在什么时候走到哪、说什么”，`tools/compose_case.py` 把它编译成 `case.json`：

- 按房间矩形自动放门（门放在两个房间相对的墙中间），按门和楼梯规划路线，生成关键帧（走 150 px/s，跑 300 px/s）；
- 台词按书写顺序排时间，说话的人会先走到位再开口（0.3 秒），说完再离开；
- 没指定站位时自动选一个：离门口、楼梯口和房间名远一点，有人在场就站到离他约 60 px 的地方；
- 已有语音（同一角色、同一句文本）保留音频并按真实时长重新排时间；
- 读取 `case.json` 里已摆好的家具：站位不压家具，房间内的路线自动绕开。

对这样的案件，**`case.play` 是源数据**：再次编译会覆盖 `case.json` 里的角色、台词、音效、问题和地图（家具和地板材质会保留）。

### 12.1 格式

```
# 井号开头是注释
标题: 雨夜书店
时长: 自动                     # 或秒数；“自动”= 最后一声结束后再留 8 秒
封面: street
外景: cobblestone
简介: 第一段。
  缩进的行接在上一项后面（换行）。
真相: ……

## 地图
楼层 一层 二层
房间 店堂 0 50,50 400,300 地板=wood        # 名字 楼层 左上角 右下角 [户外] [地板=材质]
房间 库房 0 430,50 650,300
房间 阁楼 1 50,500 400,700
门 店堂 库房                                # 自动放在相对的墙中间；可加 @x,y 指定位置，加“关”表示关着
楼梯 店堂 阁楼 @200,270 @200,530            # 两端分别在两个房间里

## 角色
A 店主 #c0392b 店堂 120,150                 # id 名字 颜色 起始房间 [起点]，编号按顺序自动生成
  音色 tools/voice_prompts/case8/A.wav 参考音频里的原话。

## 问题
问 q1 账本藏在哪里？
  选项 收银台 / 阁楼 / 库房
  答案 阁楼
问 q2 谁拿走了账本？                         # 没有选项，或选项全是角色名 → 角色题
  答案 店员

## 剧本
@ 0:05                       # 新的一场，从 0 分 5 秒开始（也可写秒数）
A: （压低声音）账本你藏哪儿了？
B -> 店堂 A                  # B 走到店堂，站到 A 旁边；也可以写坐标或省略
B: 我没藏。                  # B 会等自己走到了再开口
A => 阁楼                    # => 是跑
等 A                         # 等 A 到达
等 3                         # 停顿 3 秒
~ 枪声 audio/shot.ogg 阁楼 1.0   # 音效：标签 文件 房间|角色 [响度]，时长自动读取
A: （尖叫）啊——！ {1.0}       # 行尾 {} 里可写响度，或 {无语气}（= tts_instruct: false）
```

- 房间都是矩形，坐标规则同第 3 节。两个房间之间要有门，必须有一面相对的墙（重叠 ≥ 40、间距 ≤ 80）。
- 每个 `@` 开始一个“场景”，有自己的时间游标；台词一句接一句排下去，走动不占用游标（别人可以边走边听你说）。不同场景可以同时发生在不同房间。
- 同一个角色的安排要按文件顺序向后排：如果他上一场还没说完 / 没走到，这一场会被推迟，编译时会提示“推迟了 N 秒”。
- 台词的音量提示和 `tts_lines.py` 一致：表演提示里有“尖叫 / 大喊”等为 0.9，“低声 / 小声”等为 0.3。

### 12.2 流程

```bash
python3 tools/compose_case.py case8 --check            # 检查格式，打印总时长、每场的起止时间、推迟提示和节奏检查，不写文件
python3 tools/compose_case.py case8                    # 生成 case.json（台词时长先按字数估算）
python3 tools/furnish.py case8 --force --ignore-tracks # 摆家具，不避让角色轨迹
python3 tools/compose_case.py case8                    # 重新编译：站位和路线绕开家具
~/.local/share/unheard-tts/venv/bin/python tools/tts_lines.py case8   # 配音（可中断续跑）
python3 tools/compose_case.py case8                    # 用真实语音时长重新排时间
godot --headless --path game --import
godot --headless --path game --script res://addons/case_editor/import_cli.gd -- case8
```

- 配音会改变台词时长，配完一定要重新编译，再看一次 `--check` 的场景时间：哪一场拖得太长和后面撞了，就把后面那场的 `@` 时间往后挪，或删减台词。
- 编译时会跑节奏检查（2.1 节）：有错误就打印“节奏错误”并拒绝写 `case.json`，按提示的时间点补戏或调整 `@`；“节奏提示”不挡编译。
- 不要在 `tts_lines.py` 运行时编译（两边都会写 `case.json`）。
- 改了剧本里的台词文本，那一句会变成“没有语音”，再跑一次 `tts_lines.py` 只会补这一句。
- 编辑器里改过的走位，下次编译会被剧本覆盖；用剧本写的案件就一直改剧本。
