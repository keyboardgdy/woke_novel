#!/bin/bash
# macOS 终端启动器：在命令行里 `./menu.sh` 启动交互式菜单。
# 等价于 `python3 menu.py`，但会自动 cd 到脚本所在目录并设置 UTF-8 locale。

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "未找到 Python，请先安装（详见《Mac os 配置指南.md》）。" >&2
    exit 1
fi

export LANG="zh_CN.UTF-8"
export LC_ALL="zh_CN.UTF-8"

exec "$PY" menu.py
