# unheared

复刻《疑案追声》玩法的声音推理游戏（Godot 4 重写版）。

你是一个看不见的“耳朵”：案件是一段固定时长的录音，角色在多房间的蓝图地图上走动、交谈。你只能听清自己所在房间的对话，隔壁只有闷声，尖叫枪声能穿墙。反复倒带、换房间跟人，最后指认每个圆点的身份并回答问题。

玩法拆解与设计说明见 [docs/unheard-analysis.md](docs/unheard-analysis.md)。

## 运行

需要 [Godot 4.7](https://godotengine.org/download)（标准版，非 .NET）。

```bash
godot --path game            # 直接运行
godot -e --path game         # 打开编辑器
```

首次打开会自动导入资源。命令行环境可先执行 `godot --headless --path game --import`。

操作：点击房间移动监听者，点击圆点选中，空格播放/暂停，←/→ 快退/快进 5 秒；右侧“笔记”点击条目可跳回该时刻。

## 目录

```
game/                    Godot 项目
  core/                  时间轴、轨迹采样、声学、调度、存档、JSON 导入导出、校验
  map/                   Room / Door / Stair / CaseMap 节点，蓝图着色器，监听者
  ui/                    案件选择、游戏控制器、HUD
  cases/<id>/            case.json（源数据）、case.tres + map.tscn（导入结果）、audio/*.ogg
  addons/case_editor/    编辑器插件：时间轴面板、地图预览、试听、校验、导入导出
  addons/gdUnit4/        测试框架
  tests/                 gdUnit4 测试
tools/                   Python 内容流水线（迁移、配音）
docs/                    设计文档
legacy/                  旧版 PyQt 实现（只保留代码和案件 JSON 作参考）
```

### 仓库里提交什么

提交代码、文档、案件源数据（`case.json`）以及运行游戏必需的资源：`game/cases/*/audio/*.ogg`、`game/audio/`、导入生成的 `case.tres` / `map.tscn` 和 `*.import`。这样 clone 下来就能直接运行，CI 导出的版本也带声音。

以下内容只留在本地，已写进 `.gitignore`：

- `legacy/release/`（旧版打包产物）、`legacy/unheared/audio/` 及旧版的 WAV / MP3 录音：已迁移成 `game/cases/*/audio` 下的逐句 OGG。
- `tools/voice_prompts/`：配音时的参考音频，缺失时 `tts_lines.py` 会自动从现有语音里重新挑。
- Godot 缓存和产物：`game/.godot/`、`game/export/`、`game/reports/`、`*.translation`（导入时由 `i18n/strings.csv` 生成）。

## 核心设计

- **确定性时间轴**：`TimelineClock` 是唯一时间源；角色位置是关键帧插值的纯函数 `TrackMath.sample(track, t)`，任意 seek、倒退结果都与顺序播放一致。
- **逐句语音**：每句台词一个音频片段，`CueScheduler` 按当前时间决定播放哪些片段、从哪个偏移量开始，并做漂移校正。变速时在 Master 总线上做音高补偿。
- **声学**：`Acoustics` 用房间连通图（门、楼梯；关着的门代价更高）决定可听性。同房间走 `Room` 总线（定位声像 + 按房间大小的混响），隔一道门走 `Muffled`（低通），大音量事件按跳数衰减走 `Far`。切换总线时淡入淡出。
- **只记录听到的内容**：字幕只显示能听到的台词，隔墙的只显示“听不清”；听清的台词进入笔记。

## 案件数据

`game/cases/<id>/case.json` 是源数据，格式示例：

```json
{
  "id": "case1", "title": "…", "description": "…", "duration": 120, "truth": "…",
  "map": {
    "floors": ["一层"],
    "rooms":  [{"name": "房间1", "floor": 0, "polygon": [[100,100],[300,100],[300,250],[100,250]]}],
    "doors":  [{"name": "门", "room_a": "房间1", "room_b": "走廊", "position": [200,250], "size": [20,10], "open": true}],
    "stairs": [{"name": "楼梯", "room_a": "大厅", "room_b": "卧室", "end_a": [215,226], "end_b": [215,524]}]
  },
  "characters": [{"id": "A", "name": "经理", "label": "1", "color": "#ff0000",
                  "track": [{"t": 0, "p": [160,160], "m": "idle", "room": "房间1"}]}],
  "voice_lines": [{"speaker": "A", "start": 5.0, "duration": 3.2, "text": "（低声）……", "audio": "audio/A_xxx.ogg", "loudness": 0.5}],
  "sfx": [{"time": 60, "duration": 1.5, "audio": "audio/shot.ogg", "position": [200,300], "loudness": 1.0, "label": "枪声"}],
  "questions": [{"id": "q1", "kind": "character", "prompt": "谁是凶手？", "options": ["…"], "answer": "…"}]
}
```

关键帧的 `m` 描述“从本帧到下一帧”的移动方式（idle / walk / run）。跨房间时必须经过门或楼梯两侧的点，校验器会检查穿墙。

修改 `case.json` 后重新生成 `case.tres` 和 `map.tscn`：

```bash
godot --headless --path game --import
godot --headless --path game --script res://addons/case_editor/import_cli.gd -- case1 case5   # 不带参数则全部导入
```

也可以在编辑器里用“项目 → 工具 → 案件：从 case.json 导入…”。

## 编辑器插件

在文件系统面板选中某个 `case.tres`，底部会打开“案件时间轴”：

- 每个角色一行：上半是台词块（半透明表示没有语音），下半是关键帧。拖动修改时间，点击空白处设置预览时刻，Ctrl+滚轮缩放；选中的条目会显示在检查器中。
- 打开对应的 `map.tscn` 时，视口中会画出预览时刻的人物位置。
- 选一个“监听房间”后点“试听”，可以听到从该房间听见的效果（隔墙会被压低）。
- “校验”列出数据问题；“保存”写回 `case.tres`。“工具 → 案件：导出当前案件为 case.json”把编辑结果写回 JSON。

## 内容流水线（tools/）

### 迁移旧案件

```bash
python3 tools/migrate_legacy_case.py            # 全部；或指定 case1 case5
```

读取 `legacy/unheared/cases/*.json` 和整段角色录音，输出新格式 `case.json`、逐句 OGG 和脚步声。旧版的“时间段 + 目标点”会按旧版速度沿门洞路线展开成确定性关键帧。只依赖标准库和 ffmpeg。

迁移已经做完，结果都在 `game/cases/` 里。旧版录音（`legacy/unheared/audio/`）不在仓库中，只有本地有这些文件时才能重新跑迁移。

### 配音

`tools/tts_lines.py` 逐句生成语音并回写 `case.json`。台词里的括号内容（“（冷笑）”“（举杯）”）不会被念出来，而是作为语气指令交给 CosyVoice；“尖叫/拍桌”会提高台词的穿墙能力，“低声/小声”会降低。

默认引擎是本地 [CosyVoice2](https://github.com/FunAudioLLM/CosyVoice)，用每个角色的参考音频克隆音色。参考音频存放在 `tools/voice_prompts/`（不提交），路径写在 `case.json` 角色的 `voice_prompt` 字段。文件缺失时，脚本会从该角色现有的语音里重新挑一句 3~10 秒、不带括号的作参考，音色可能略有变化。CosyVoice 需要 Python 3.10，安装到仓库之外：

```bash
mkdir -p ~/.local/share/unheard-tts && cd ~/.local/share/unheard-tts
git clone --depth 1 --recursive https://github.com/FunAudioLLM/CosyVoice.git
uv venv --python 3.10 venv && export VIRTUAL_ENV=$PWD/venv
uv pip install "setuptools<70" wheel
uv pip install --no-build-isolation --index-strategy unsafe-best-match \
  --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.3.1+cpu" numpy==1.26.4 openai-whisper==20231117
uv pip install --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu \
  "torch==2.3.1+cpu" "torchaudio==2.3.1+cpu" conformer==0.3.2 diffusers==0.29.0 hydra-core==1.3.2 \
  HyperPyYAML==1.2.3 inflect==7.3.1 librosa==0.10.2 lightning==2.2.4 matplotlib==3.7.5 modelscope==1.20.0 \
  networkx==3.1 numpy==1.26.4 omegaconf==2.3.0 onnx==1.16.0 onnxruntime==1.18.0 protobuf==4.25 \
  pyarrow==18.1.0 pydantic==2.7.0 pyworld==0.3.4 rich==13.7.1 soundfile==0.12.1 transformers==4.51.3 \
  x-transformers==2.11.24 wetext==0.0.4 wget==3.2 gdown==5.1.0
venv/bin/python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice2-0.5B', local_dir='models/CosyVoice2-0.5B')"
```

然后在仓库根目录：

```bash
~/.local/share/unheard-tts/venv/bin/python tools/tts_lines.py case6 case7      # 生成缺失/非 CosyVoice 的台词，可中断续跑
~/.local/share/unheard-tts/venv/bin/python tools/tts_lines.py case7 --only 12  # 重做单句
```

纯 CPU 下大约每秒语音需要数秒计算（case6 + case7 共 326 句约两小时）。路径可用 `COSYVOICE_HOME`、`COSYVOICE_MODEL` 环境变量覆盖。也可用 `--engine edge` 走 edge-tts（不支持语气指令）。

注意事项：

- 个别台词的语气指令偶尔会被念出来。在该句上加 `"tts_instruct": false` 后用 `--only` 重做即可（case7 第 12 句就是这样处理的）。生成后建议用 venv 里的 `openai-whisper` 抽查转写结果。
- CosyVoice 的文本规范化模型可能下载失败（日志里出现 `no frontend is avaliable`），所以脚本自己把阿拉伯数字转成中文：“83年的”读作“八三年的”，其他数字按数值读。

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

`game/export_presets.cfg` 包含 Linux 和 Windows 预设（需要安装对应版本的导出模板）：

```bash
cd game && godot --headless --export-release Linux
```
