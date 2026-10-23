# 环境搭建

按用途分三档，只做自己需要的部分：

| 想做什么 | 需要 |
| --- | --- |
| 玩游戏、在编辑器里改剧本 | Godot 4.7（第 1 节） |
| 改代码并通过 CI 检查 | + gdtoolkit（第 2 节） |
| 生成配音、美术切图、自动摆家具 | + ffmpeg、Python 环境（第 3、4 节） |

以下命令以 Linux 为例，仓库根目录记作 `<repo>`。Windows / macOS 上路径不同，步骤相同。

## 1. Godot

1. 从 [godotengine.org](https://godotengine.org/download/archive/4.7.2-stable/) 下载 **Godot 4.7.2 标准版**（不是 .NET 版）。版本要和 `.github/workflows/ci.yml` 里的 `GODOT_VERSION` 一致，否则导入的资源和导出模板对不上。
2. 解压到任意位置，建议做一个 `godot` 命令：

   ```bash
   mkdir -p ~/.local/share/godot ~/.local/bin
   unzip Godot_v4.7.2-stable_linux.x86_64.zip -d ~/.local/share/godot
   ln -s ~/.local/share/godot/Godot_v4.7.2-stable_linux.x86_64 ~/.local/bin/godot
   ```

3. 首次导入资源（生成 `game/.godot/` 缓存，之后打开编辑器会快很多）：

   ```bash
   cd <repo>
   godot --headless --path game --import
   ```

4. 运行 / 打开编辑器：

   ```bash
   godot --path game        # 运行游戏
   godot -e --path game     # 打开编辑器；“案件编辑”插件默认启用
   ```

存档位置：Linux `~/.local/share/godot/app_userdata/疑案追声/saves/`，Windows `%APPDATA%\Godot\app_userdata\疑案追声\saves\`。每个案件一个 JSON，删掉即可重玩。

## 2. 代码检查（gdtoolkit）

仓库里的 `.venv/`（Python 3.12+）装 gdtoolkit 和 edge-tts。没有的话：

```bash
cd <repo>
uv venv .venv                                   # 或 python3 -m venv .venv
uv pip install --python .venv/bin/python "gdtoolkit==4.*" edge-tts
```

检查（与 CI 相同）：

```bash
cd game
../.venv/bin/gdformat --check --line-length=120 core map ui addons/case_editor tests
../.venv/bin/gdlint core map ui addons/case_editor tests
godot --headless -s -d res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://tests
```

`addons/gdUnit4/runtest.sh` 在 headless 下会失败，直接调用 `GdUnitCmdTool.gd`。

## 3. ffmpeg 与系统 Python 库

- **ffmpeg**：配音脚本用它转码 OGG、测时长。`sudo apt install ffmpeg`（Windows 用 `winget install ffmpeg`，确保在 PATH 中）。
- **Pillow / numpy / scipy**：`tools/art_sheets.py`（美术切图）和 `tools/furnish.py`（自动摆家具）用系统 Python 跑：

  ```bash
  sudo apt install python3-pil python3-numpy python3-scipy
  # 或：python3 -m pip install --user pillow numpy scipy
  ```

`tools/fix_speech_timing.py`、`tools/migrate_legacy_case.py` 只用标准库（后者还要 ffmpeg）。

## 4. 配音环境

两种引擎，按需选一种：

### 4.1 edge-tts（简单，在线）

装在第 2 节的 `.venv/` 里即可，需要联网。音色是微软的预置中文音色，**不支持语气指令**（括号里的“冷笑”“低声”只影响字幕和音量判断）。适合快速出一版能玩的配音。

### 4.2 CosyVoice2（推荐，本地离线）

用每个角色的参考音频克隆音色，括号里的表演提示会作为语气指令。需要 Python 3.10 的独立环境（约 6 GB，含模型），装在仓库之外：

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

要点：

- uv 建的 venv 里没有 `pip`，补装包用 `uv pip install --python ~/.local/share/unheard-tts/venv/bin/python <包>`。
- 有 NVIDIA 显卡时可把 `+cpu` 的 torch 换成 CUDA 版，速度快一个数量级；纯 CPU 每秒语音需要数秒计算。
- 路径可以用环境变量覆盖：`COSYVOICE_HOME`（CosyVoice 源码目录）、`COSYVOICE_MODEL`（模型目录）。
- 自检：`~/.local/share/unheard-tts/venv/bin/python <repo>/tools/tts_lines.py --help` 能打印帮助即可。

用法见 [自制剧本 · 配音](case-authoring.md#6-配音)。

## 5. 常见问题

| 现象 | 处理 |
| --- | --- |
| 编辑器里案件节点显示成占位符 / 脚本报 “not a tool script” | 编辑器插件用到的脚本必须带 `@tool`（见 `AGENTS.md`），改完重启编辑器 |
| 新加的图片 / 音频在游戏里找不到 | 先 `godot --headless --path game --import` 生成 `.import` |
| 案件列表里没有新案件 | 只列出有 `case.tres` 的目录；运行导入 CLI（[自制剧本 · 导入](case-authoring.md#7-导入与校验)） |
| CosyVoice 日志出现 `no frontend is avaliable` | 文本规范化模型下载失败，不影响使用；数字由脚本自己转成中文 |
| 窗口被遮挡时截图脚本很慢 | Godot 在窗口不可见时降到 1 FPS，属正常 |
