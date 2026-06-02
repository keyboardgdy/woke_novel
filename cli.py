# -*- coding: utf-8 -*-
"""
CLI 交互模块：询问题材、项目名、用户描述。

所有可见输出都委托给 ui 模块；本文件只保留交互流程，方便 run_workflow.py 复用。
"""

from typing import List, Tuple

from ui import (
    C, I,
    blank, chip, clear, confirm, dim, info, init, line,
    print_banner, print_panel, print_subheader, prompt, select, success, warn,
)


# ---------------------------------------------------------------------------
# 公共 banner
# ---------------------------------------------------------------------------
def print_banner(title: str) -> None:
    """顶部 banner：兼容旧 run_workflow.py 调用。"""
    init()
    print_banner(title)


# ---------------------------------------------------------------------------
# 题材
# ---------------------------------------------------------------------------
_GENRE_OPTIONS: List[Tuple[str, str]] = [
    ("1", "都市"),
    ("2", "玄幻"),
    ("3", "仙侠"),
    ("4", "科幻"),
    ("5", "游戏"),
    ("6", "其他"),
]


def ask_genre() -> str:
    """询问题材，使用 numbered select。"""
    init()
    print_subheader("请选择小说题材", color=C.PRIMARY)
    options = [name for _, name in _GENRE_OPTIONS]
    idx = select("题材", options, default=0)
    return _GENRE_OPTIONS[idx][1]


# ---------------------------------------------------------------------------
# 项目名
# ---------------------------------------------------------------------------
def ask_project_name() -> str:
    """询问项目名（初始目录名）。空名校验。"""
    init()
    print_subheader("创建项目目录", color=C.PRIMARY)
    while True:
        name = prompt("项目名（用于创建项目目录）")
        if name:
            return name
        warn("项目名不能为空，请重新输入。")


# ---------------------------------------------------------------------------
# 用户描述
# ---------------------------------------------------------------------------
def ask_user_description() -> str:
    """询问用户对小说的描述 / 想法 / 要求。可为空。"""
    init()
    print_subheader("补充说明", color=C.PRIMARY)
    desc = prompt("对小说的想法、描述或要求（可为空）", default="")
    return desc if desc else "无"
