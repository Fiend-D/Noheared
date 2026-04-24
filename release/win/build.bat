@echo off
REM 在 Windows 上构建可执行文件
REM 需要先安装 Python 和依赖

echo ===== 安装依赖 =====
pip install pyinstaller PyQt6 pygame numpy

echo ===== 构建游戏 =====
cd /d "%~dp0..\.."
pyinstaller 疑案追声.spec --distpath release\win --workpath build\pyinstaller

echo ===== 完成！ =====
echo 可执行文件位于: release\win\疑案追声\
pause
