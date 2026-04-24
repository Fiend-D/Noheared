#!/usr/bin/env bash
set -euo pipefail

# 在 Linux/macOS 上构建可执行文件
# 需要先安装 Python 和依赖

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR"

echo "===== 安装依赖 ====="
pip install pyinstaller PyQt6 pygame numpy

echo "===== 构建游戏 ====="
pyinstaller 疑案追声.spec --distpath "$SCRIPT_DIR" --workpath build/pyinstaller

echo "===== 完成！======"
echo "可执行文件位于: $SCRIPT_DIR/疑案追声/"
