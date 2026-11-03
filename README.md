# unheared

一款用声音查案的推理游戏。你看不见现场里的人，只能在蓝图上走动，听他们说话、走路、争吵。案件是一段固定时长的录音：倒带、换房间、把听到的碎片拼起来，再指认每个圆点是谁、回答问题。

玩法受《疑案追声》（Unheard，NExT Studios）启发。这是另行实现的非官方项目，与 NExT Studios 无关。《疑案追声》和 Unheard 是原作权利人的名称。

本仓库以 [MIT 许可证](LICENSE) 发布，涵盖代码、剧本、语音和自制美术。第三方组件保留各自的许可证，见文末。

## 运行

需要 [Godot 4.7](https://godotengine.org/download) 标准版（非 .NET）。克隆后直接打开项目：

```bash
godot --path game            # 运行
godot -e --path game         # 打开编辑器
```

首次打开会导入资源。没有图形界面时，先执行 `godot --headless --path game --import`。案件语音已经在 `game/cases/*/audio/` 里，不需要再生成就能玩。

主界面是「开始调查 / 设置 / 退出」。开始调查后进入档案室：滚轮或方向键翻案卷，点最前面的档案打开卷宗，再点「开始查案」。

## 操作

| 按键 | 作用 |
| --- | --- |
| WASD / 方向键 | 走动。墙会挡住，只能从门洞进出；走到楼梯口自动上下楼 |
| Shift | 快走 |
| 鼠标左键点房间 | 沿门洞和楼梯走过去 |
| 鼠标指向 / 点击楼梯口 | 楼梯口高亮；点下去后走过去，地图切到对应楼层 |
| 鼠标左键点角色 | 选中，右侧切到「人物」指认 |
| 空格 | 播放 / 暂停 |
| Q / E | 倒退 / 快进 5 秒 |
| R | 切换倍速（×0.5 / ×1 / ×2 / ×4） |
| 滚轮 | 缩放地图，放大后镜头跟随 |

监听者按真实时间移动，暂停和倒带时也可以走。右侧「笔记」点击条目可跳回该时刻。还没指认的角色是带编号的灰色剪影；指认正确后换成该身份的头像和名字。没有头像的案件会一直保持灰色剪影。

## 案件

档案室按目录名排序。目前包含：

| 目录 | 标题 |
| --- | --- |
| case1 | 办公室谜案 |
| case2 | 剧院魅影 |
| case3 | 美术馆 |
| case4 | 豪宅密室谋杀案 |
| case5 | 海神号谋杀案 |
| case6 | 血色晚宴 |
| case7 | 永夜酒店谋杀案 |
| case8 | 白桦岭疗养院 |
| case9 | 午夜电台 |

case1、case2、case3、case8、case9 的源文件是 `case.play`，由 `tools/compose_case.py` 编译成 `case.json`。游戏运行时读的是导入生成的 `case.tres` 和 `map.tscn`。

## 开发

更细的步骤在这些文档里：

| 文档 | 内容 |
| --- | --- |
| [docs/setup.md](docs/setup.md) | 环境：Godot、代码检查、ffmpeg、edge-tts、CosyVoice2 |
| [docs/case-authoring.md](docs/case-authoring.md) | 写案件：`case.json`、`case.play`、地图、声学、配音、校验、编辑器插件 |
| [docs/packaging.md](docs/packaging.md) | 导出 Linux / Windows |
| [docs/unheard-analysis.md](docs/unheard-analysis.md) | 玩法拆解和本项目的设计取舍 |

```
game/          Godot 4.7 项目（核心、地图、界面、案件、美术）
tools/         剧本编译、配音、切图、摆家具
docs/          设计与制作文档
legacy/        旧的 PyQt 实现，只留作参考，不再开发
```

常用命令：

```bash
# 把 case.json 导入成游戏可读的 case.tres / map.tscn
godot --headless --path game --script res://addons/case_editor/import_cli.gd

# 剧本 → case.json。节奏不合格时不会写入
python3 tools/compose_case.py case1 --check
python3 tools/compose_case.py case1

# 给缺语音的台词生成 CosyVoice2 配音，然后再编译一次以使用真实时长
~/.local/share/unheard-tts/venv/bin/python tools/tts_lines.py case1

# 格式、lint、测试
pip install "gdtoolkit==4.*"
cd game
gdformat --check --line-length=120 core map ui addons/case_editor tests
gdlint core map ui addons/case_editor tests
godot --headless -s -d res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://tests
```

导出发行版需要与编辑器同版本的导出模板：

```bash
cd game && mkdir -p export/linux export/windows
godot --headless --export-release Linux
godot --headless --export-release Windows
```

`game/export/` 不提交。CI（`.github/workflows/ci.yml`）会做格式检查、导入、测试，并导出 Linux 和 Windows。

时间轴只有 `TimelineClock` 一个时间源；角色位置由 `TrackMath.sample` 按时间算出，任意拖动都和顺序播放一致。能听到什么由房间连通图决定：同房间清楚，隔门发闷，尖叫和枪声传得更远。字幕和笔记只记录真正听见的内容。

## 许可证与致谢

- 本仓库：MIT，版权所有 © 2026 Fiend-D and contributors。见 [LICENSE](LICENSE)。
- [Godot Engine](https://godotengine.org/)：MIT。
- [gdUnit4](https://github.com/godot-gdunit-labs/gdUnit4)：MIT，许可证在 `game/addons/gdUnit4/LICENSE`，版权归 Mike Schulze。
- 配音脚本调用的 CosyVoice2 和 edge-tts 不包含在本仓库中，使用它们时遵循各自的许可证。
- 参考音色文件 `tools/voice_prompts/` 不提交。本地缺失时，`tts_lines.py` 会从已有台词里重新挑选。
