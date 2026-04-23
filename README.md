# unheared

疑案追声复刻小游戏 - 音频听觉解谜游戏

## 游戏玩法

- **核心机制**：在场景中移动"监听点"来收集声音信息
- **听觉规则**：角色只有处于监听范围内才能被听到
- **解谜目标**：
  1. 根据声音和位置推理每个圆圈对应的真实角色
  2. 回答与案情相关的问题
  3. 提交答案验证推理

## 操作方式

- **鼠标左键点击空白处**：移动监听点
- **鼠标左键点击角色圆圈**：标记角色身份
- **播放控制**：播放/暂停、拖动进度条

## 环境要求

- Python 3.8+
- PyQt6
- pygame
- numpy

安装依赖：
```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 项目结构

```
unheared/
├── main.py                 # 入口
├── unheared/
│   ├── ui/main_window.py # 主界面
│   ├── audio/player.py   # 音频播放
│   ├── scene/map.py      # 场景地图
│   ├── case/case.py      # 案例管理
│   ├── cases/           # 案例数据 JSON
│   └── audio/           # 角色音频文件
```

## 案例格式

每个案例为 JSON 文件，包含：
- `name`：案例名称
- `scene`：场景布局（区域、门）
- `characters`：角色定义（颜色、位置轨迹）
- `audio_tracks`：角色音频文件
- `dialogues`：角色对话字幕
- `questions`：案件问题