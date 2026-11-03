# 打包发布

游戏用 Godot 自带的导出功能打包成单个可执行文件（资源包内嵌）。导出配置在 `game/export_presets.cfg`，目前有 Linux 和 Windows 两个预设。环境准备见 [setup.md](setup.md)。

本地用 4.7.2 导出模板打过 Linux 发行版，产物与下面的路径、单文件内嵌资源包一致。CI 的 export 任务同样会打 Linux 和 Windows。

## 1. 安装导出模板（一次性）

导出模板必须与编辑器版本完全一致（4.7.2.stable），约 1 GB。

**编辑器里装**：`godot -e --path game` → 编辑器 → 管理导出模板 → 下载并安装。

**命令行装**：

```bash
cd /tmp
wget https://github.com/godotengine/godot/releases/download/4.7.2-stable/Godot_v4.7.2-stable_export_templates.tpz
unzip Godot_v4.7.2-stable_export_templates.tpz        # 解出 templates/ 目录
mkdir -p ~/.local/share/godot/export_templates/4.7.2.stable
mv templates/* ~/.local/share/godot/export_templates/4.7.2.stable/
```

装好后 `~/.local/share/godot/export_templates/4.7.2.stable/` 下应有 `linux_release.x86_64`、`windows_release_x86_64.exe` 等文件。

## 2. 导出前检查

```bash
godot --headless --path game --import                                    # 资源导入
godot --headless --path game --script res://addons/case_editor/import_cli.gd   # 所有案件 case.json → case.tres / map.tscn，看校验提示
cd game && godot --headless -s -d res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://tests
```

确认没有 `ERROR` 校验提示、测试全部通过。游戏运行时只读 `case.tres` / `map.tscn`，忘了重新导入就会打包进旧数据。

## 3. 导出

```bash
cd game
mkdir -p export/linux export/windows
godot --headless --export-release Linux        # → export/linux/unheard.x86_64
godot --headless --export-release Windows      # → export/windows/unheard.exe
```

- 预设名区分大小写，就是 `export_presets.cfg` 里的 `name`。
- 输出目录必须事先存在。
- 也可以指定输出路径：`godot --headless --export-release Linux /tmp/unheard.x86_64`。
- 调试版（带控制台输出、可连远程调试）：把 `--export-release` 换成 `--export-debug`。Windows 调试版会额外生成 `unheard.console.exe`，双击它能看到日志。
- 在 Linux 上导出 Windows 版不需要 Wine：预设里关闭了 `application/modify_resources`（改 exe 图标 / 版本信息需要 rcedit），见第 6 节。

导出后先在本机跑一下：

```bash
./export/linux/unheard.x86_64
```

检查主界面 → 档案室列出全部案件且海报正常、取出档案能展开卷宗、进游戏能听到声音、给角色指认身份后棋子换成头像、存档能写入（Linux 在 `~/.local/share/godot/app_userdata/疑案追声/saves/`，Windows 在 `%APPDATA%\Godot\app_userdata\疑案追声\saves\`）。

## 4. 打包了什么

预设的 `export_filter="all_resources"` 打包全部资源，再按 `exclude_filter` 排除：

| 排除 | 原因 |
| --- | --- |
| `tests/*`、`reports/*` | 测试和测试报告 |
| `addons/gdUnit4/*` | 测试框架 |
| `addons/case_editor/*` | 编辑器插件（导入 CLI、时间轴、家具面板） |
| `cases/*/case.json`、`cases/*/case.play` | 源数据，运行时用的是导入生成的 `case.tres` |

`embed_pck=true` 把资源包嵌进可执行文件，所以每个平台只有一个文件。语音是 OGG，按原样打包，整包大小主要由 `cases/*/audio` 决定；`art/`（海报、头像、家具、地板）也随包。美术原图 `tools/art_sources/` 在 `game/` 外面，不会打包。

新增运行时不需要的文件（比如资料、草图）时，放到 `game/` 外面，或加进 `exclude_filter`。

> 运行时用到的脚本不能依赖 `addons/case_editor/` 里的东西，否则导出版会报错。`CaseJson`、`CaseValidator` 等在 `core/` 里，不受影响。

## 5. 发布

```bash
cd game/export
tar czf unheard-linux-x86_64.tar.gz -C linux unheard.x86_64
(cd windows && zip -r ../unheard-windows-x86_64.zip .)
```

Linux 用户解压后可能需要 `chmod +x unheard.x86_64`。`game/export/` 已在 `.gitignore` 里，不要提交构建产物。

### CI

`.github/workflows/ci.yml` 在 push 到 `main` 和每个 PR 上运行：lint → 导入 + 测试 → 用 `barichello/godot-ci:4.7.2` 容器（自带导出模板）按矩阵导出 Linux、Windows。产物在该次运行页面的 Artifacts 里（`unheard-Linux`、`unheard-Windows`），下载即可发布。

升级 Godot 版本时要同时改：`ci.yml` 里的 `GODOT_VERSION` 和两处容器标签、本地编辑器与导出模板、[setup.md](setup.md) 和 AGENTS.md 里的版本号。

## 6. 定制

- **游戏名**：`project.godot` 的 `config/name`（同时决定存档目录名，改了玩家旧存档会“丢失”）；Windows 预设的 `application/product_name`。
- **版本号**：`project.godot` 加 `config/version="1.0.0"`；Windows 预设加 `application/file_version`、`application/product_version`。
- **图标**：`project.godot` 设 `config/icon="res://icon.png"`（窗口和 Linux 图标）。Windows exe 图标需要设 `application/icon` 并打开 `application/modify_resources`，这需要 rcedit：在 Linux 上导出时还要装 Wine，并在 编辑器设置 → 导出 → Windows 里填 rcedit 路径。
- **新平台（如 macOS）**：编辑器 → 项目 → 导出 → 添加预设，排除过滤器照抄上面那一行，保存后会写进 `export_presets.cfg`；再把预设名加进 `ci.yml` 的 `matrix.preset`，并在第 3 节补上命令。macOS 版要在苹果设备上签名公证，否则用户需要手动放行。
