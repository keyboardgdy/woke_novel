#!/bin/bash
# macOS 双击启动器：在 Finder 中双击本文件即可打开交互式菜单。
# 等价于 menu.bat（Windows）。

cd "$(dirname "$0")"

# 优先用 python3；找不到时再回退到 python（python.org 安装包会建 python 链接）。
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    osascript -e 'display alert "未找到 Python" message "请先通过 brew install python@3.12 或 python.org 安装包安装 Python 3，然后再双击本文件。详见《Mac os 配置指南.md》。"'
    exit 1
fi

# 强制 UTF-8，避免菜单里的中文乱码。
export LANG="zh_CN.UTF-8"
export LC_ALL="zh_CN.UTF-8"

"$PY" menu.py
EXIT_CODE=$?

# 退出后让窗口停留一下，方便查看报错；用户按回车关闭。
echo
echo "按回车键关闭窗口…"
read -r _
exit $EXIT_CODE
