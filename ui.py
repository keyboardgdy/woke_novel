# -*- coding: utf-8 -*-
"""
统一 CLI 视觉层。

本模块是 woke_novel 唯一的输出入口。所有 CLI 输出（菜单、状态、步骤执行、
确认提示等）都应通过这里的辅助函数，**不要在业务代码里直接 print**。

视觉风格参考 modern TUI 工具（gum / lazygit / poetry）：
- 清淡配色（cyan / magenta / green / yellow / red / dim）
- 圆角 box（╭─╮ │ ╰─╯）
- 大量使用 unicode icon（▶ ✓ ✗ ⚠ ℹ ✦）
- 关键操作有 spinner + elapsed time
- 表格用 rich.Table，单行 chip 用 rich.Text
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Windows 编码修复：默认 GBK 编码打不出 ✦ ✓ 等 unicode
# ---------------------------------------------------------------------------
def _force_utf8() -> None:
    """把 stdout/stderr 切到 UTF-8，跨平台幂等。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_force_utf8()

# ---------------------------------------------------------------------------
# 依赖：colorama 处理 Windows ANSI，rich 提供 Table/Panel/Spinner/Prompt
# ---------------------------------------------------------------------------
import colorama
from colorama import init as _colorama_init

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# 颜色 + icon 调色板
# ---------------------------------------------------------------------------
class C:
    """集中管理的颜色名（直接喂给 rich 的样式字符串）。"""
    PRIMARY = "cyan"
    ACCENT = "magenta"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    INFO = "blue"
    DIM = "bright_black"
    MUTED = "white"
    HL = "bold white"


class I:
    """集中管理的 icon 字符。"""
    STEP = "▶"        # 步骤前缀
    ARROW = "❯"        # 提示符
    BULLET = "▸"       # 列表项
    DOT = "●"          # 装饰点
    SPARK = "✦"        # 装饰
    STAR = "★"         # 强调
    OK = "✓"           # 成功
    FAIL = "✗"         # 失败
    WARN = "⚠"          # 警告
    INFO = "ℹ"          # 提示
    NOTE = "✎"          # 草稿/批注
    TIME = "⏱"          # 时间
    BOOK = "❖"          # 书籍/小说
    DIAMOND = "◆"       # 装饰
    PICK = "▌"          # 高亮条
    DASH = "─"          # 短线
    ARROW_R = "→"       # 步骤流向


# ---------------------------------------------------------------------------
# 初始化 colorama + rich 控制台
# ---------------------------------------------------------------------------
_BOX_WIDTH = 78          # box 默认宽度（含两边边距）
_colorama_init(autoreset=False, strip=False)


def indent(icon: str = "") -> str:
    """统一缩进字符串：默认 2 空格；可附带 icon。"""
    if icon:
        return f"  {icon}"
    return "  "

# 强制开启 TTY 着色：用户一般直接看终端，但若 TTY 不可用也不强求彩色。
_console = Console(
    highlight=False,
    soft_wrap=False,
    force_terminal=sys.stdout.isatty() if hasattr(sys.stdout, "isatty") else False,
    width=min(_BOX_WIDTH + 4, 100),
)


def console() -> Console:
    """获取全局 rich Console，业务代码需要时使用。"""
    return _console


def init() -> None:
    """入口初始化（main 启动时调一次即可）。"""
    _colorama_init(autoreset=True, strip=False)


def clear() -> None:
    """清屏。"""
    os.system("cls" if os.name == "nt" else "clear")


# ---------------------------------------------------------------------------
# 文本/样式辅助
# ---------------------------------------------------------------------------
def t(text: Any, color: Optional[str] = None, bold: bool = False, dim: bool = False) -> Text:
    """返回一个 rich Text 对象。"""
    style: List[str] = []
    if color:
        style.append(color)
    if bold:
        style.append("bold")
    if dim:
        style.append("dim")
    if style:
        return Text(str(text), style=" ".join(style))
    return Text(str(text))


def stylize(s: str, color: str, bold: bool = False, dim: bool = False) -> str:
    """返回带 ANSI 颜色代码的字符串（用于嵌入大字符串）。"""
    style = []
    if bold:
        style.append("1")
    if dim:
        style.append("2")
    style.append(_ansi_color_code(color))
    return f"\x1b[{';'.join(style)}m{s}\x1b[0m"


def _ansi_color_code(name: str) -> str:
    """rich 颜色名 → ANSI 前置码（用于 stylize 拼字符串）。"""
    mapping = {
        C.PRIMARY: "36",   # cyan
        C.ACCENT: "35",    # magenta
        C.SUCCESS: "32",   # green
        C.WARNING: "33",   # yellow
        C.ERROR: "31",     # red
        C.INFO: "34",      # blue
        C.DIM: "90",       # bright black
        C.MUTED: "37",     # white
        C.HL: "97",        # bright white
    }
    return mapping.get(name, "0")


def chip(label: str, color: str, bold: bool = True) -> Text:
    """一个带颜色背景感的 chip：[ OK ]、[WARN] 等风格。"""
    text = f" {label} "
    return Text(text, style=f"bold {color}")


def line(char: str = I.DASH, width: int = _BOX_WIDTH, color: str = C.DIM) -> None:
    """打印一行分隔线。"""
    _console.print(char * width, style=color)


def blank(n: int = 1) -> None:
    """打印 n 个空行。"""
    for _ in range(n):
        _console.print("")


# ---------------------------------------------------------------------------
# 顶部 banner / 章节头 / 段落
# ---------------------------------------------------------------------------
def print_banner(title: str, subtitle: Optional[str] = None, accent: str = C.PRIMARY) -> None:
    """最顶部的 banner：大标题 + 渐变下划线 + 可选副标题。"""
    bar = I.SPARK * 3
    _console.print()
    _console.print(f"  {bar}  ", end="")
    _console.print(title, style=f"bold {accent}")
    if subtitle:
        _console.print(f"     {subtitle}", style=C.DIM)
    line(color=accent)
    _console.print()


def print_header(title: str, color: str = C.PRIMARY, icon: str = I.STEP) -> None:
    """小章节头：一行 icon + 标题 + 浅色分隔。"""
    _console.print()
    _console.print(f"{indent(icon)} {title}", style=f"bold {color}")
    line(color=C.DIM)


def print_subheader(title: str, color: str = C.DIM) -> None:
    """二级小标题（更暗淡）。"""
    _console.print()
    _console.print(f"{indent(I.BULLET)} {title}", style=f"bold {color}")


def print_section(title: str, color: str = C.PRIMARY) -> None:
    """会话/阶段分隔：上下双线 + 居中标题。"""
    _console.print()
    _console.print("─" * _BOX_WIDTH, style=color)
    _console.print(f"  {I.STEP}  {title}", style=f"bold {color}")
    _console.print("─" * _BOX_WIDTH, style=color)


# ---------------------------------------------------------------------------
# 面板 + 键值 + 表格
# ---------------------------------------------------------------------------
def print_panel(title: str, body: str = "", color: str = C.PRIMARY, icon: Optional[str] = None) -> None:
    """圆角 box 包住一段内容。"""
    title_text = Text()
    if icon:
        title_text.append(f"{icon}  ", style=f"bold {color}")
    title_text.append(title, style=f"bold {color}")
    panel = Panel(
        body or "",
        title=title_text,
        title_align="left",
        border_style=color,
        padding=(0, 2),
        width=_BOX_WIDTH,
    )
    _console.print()
    _console.print(panel)


def print_kv(items: Sequence[Tuple[str, Any]], indent: int = 2, key_color: str = C.DIM,
            value_color: str = C.MUTED) -> None:
    """键值对列表（左键右值，颜色不同）。"""
    pad = " " * indent
    if not items:
        return
    key_w = max(_display_width(k) for k, _ in items)
    for k, v in items:
        _console.print(f"{pad}{k.ljust(key_w)}  ", style=key_color, end="")
        _console.print(str(v), style=value_color)


def _display_width(s: str) -> int:
    """中文按 2 宽计算的字符串显示宽度。"""
    w = 0
    for ch in s:
        if ord(ch) > 127:
            w += 2
        else:
            w += 1
    return w


def print_creative_cards(items: Sequence[Tuple[int, str, str]]) -> None:
    """把若干 (序号, 方案名, 开篇设想) 渲染成一摞小卡片。

    用法：在 `select("选择一个创意方案", ...)` 之前调用一次，让用户在
    数字选择之前先看到每个方案的标题和开篇缩略，避免只看到 "方案 1/2/3"。

    items 为空时静默不输出。任一字段为空字符串时显示占位文字。
    """
    if not items:
        return
    _console.print()
    _console.print(
        f"  {I.SPARK}  创意方案预览",
        style=f"bold {C.PRIMARY}",
    )
    for idx, title, opening in items:
        title_text = Text()
        title_text.append(f"  {idx}. ", style=f"bold {C.ACCENT}")
        title_text.append(title or "（未命名方案）", style=f"bold {C.PRIMARY}")
        body = opening.strip() or "（暂无开篇设想）"
        panel = Panel(
            Text(body, style=C.MUTED),
            title=title_text,
            title_align="left",
            border_style=C.DIM,
            padding=(0, 2),
            width=_BOX_WIDTH,
        )
        _console.print(panel)


def print_steps_table(steps: Sequence[Tuple[str, str]], current: Optional[str] = None,
                     title: str = "可用步骤") -> None:
    """步骤列表表格：编号 + 名称 + 状态。"""
    table = Table(
        title=Text(f"  {I.BOOK}  {title}", style=f"bold {C.PRIMARY}"),
        title_justify="left",
        border_style=C.DIM,
        header_style=f"bold {C.PRIMARY}",
        show_lines=False,
        padding=(0, 1),
        width=_BOX_WIDTH,
    )
    table.add_column("编号", style=f"bold {C.ACCENT}", width=6, no_wrap=True)
    table.add_column("名称", style=C.MUTED)
    table.add_column("状态", justify="right", width=8, no_wrap=True)
    for step, name in steps:
        if current and step == current:
            status = Text("▶ 当前", style=f"bold {C.WARNING}")
            table.add_row(step, Text(name, style="bold"), status)
        else:
            table.add_row(step, name, Text(" ", style=C.DIM))
    _console.print()
    _console.print(table)


def print_choices_table(items: Sequence[Tuple[int, str, str]], title: str,
                         allow_custom: bool = True,
                         custom_label: str = "自定义") -> None:
    """编号 + 名称 + 简介 的紧凑表格，专门用于题材/频道等多选场景。

    - items:  (编号, 名称, 简介) 列表，编号从调用方传，不强制从 1 起
    - allow_custom: True 时在表格外另起一行追加 "[0] {custom_label}"，与表格内编号保持一致风格
    """
    _console.print()
    table = Table(
        title=Text(f"  {I.BOOK}  {title}", style=f"bold {C.PRIMARY}"),
        title_justify="left",
        border_style=C.DIM,
        header_style=f"bold {C.PRIMARY}",
        show_lines=False,
        padding=(0, 1),
        width=_BOX_WIDTH,
    )
    table.add_column("编号", style=f"bold {C.ACCENT}", width=4, no_wrap=True)
    table.add_column("名称", style=f"bold {C.MUTED}", width=12, no_wrap=True)
    table.add_column("简介", style=C.MUTED, overflow="fold")
    for idx, name, desc in items:
        table.add_row(
            f"[{idx}]",
            name,
            Text(desc or "", style=C.DIM),
        )
    if allow_custom:
        table.add_row(
            Text("[0]", style=f"bold {C.WARNING}"),
            Text(custom_label, style=f"bold {C.WARNING}"),
            Text("", style=C.DIM),
        )
    _console.print(table)


def print_projects_table(projects: Sequence[Dict[str, Any]], title: str = "已有项目") -> None:
    """项目列表表格：编号 + 项目名 + 题材 + 进度 + 最后活动。"""
    table = Table(
        title=Text(f"  {I.DIAMOND}  {title}", style=f"bold {C.PRIMARY}"),
        title_justify="left",
        border_style=C.DIM,
        header_style=f"bold {C.PRIMARY}",
        show_lines=False,
        padding=(0, 1),
        width=_BOX_WIDTH,
    )
    table.add_column("#", style=f"bold {C.ACCENT}", width=3, no_wrap=True)
    table.add_column("项目名", style=f"bold {C.MUTED}", no_wrap=True)
    table.add_column("题材", style=C.PRIMARY)
    table.add_column("进度", style=C.WARNING, justify="right")
    table.add_column("最后活动", style=C.DIM)
    for i, p in enumerate(projects, 1):
        table.add_row(
            str(i),
            p.get("novel_name") or p.get("name", "?"),
            p.get("genre", "—"),
            p.get("progress", "—"),
            p.get("last_active", "—"),
        )
    _console.print()
    _console.print(table)


# ---------------------------------------------------------------------------
# 单行 chip 输出（成功/警告/错误/信息/debug）
# ---------------------------------------------------------------------------
def success(msg: Any, icon: str = I.OK) -> None:
    _console.print(f"{indent()}{icon} ", style=f"bold {C.SUCCESS}", end="")
    _console.print(str(msg), style=C.MUTED)


def warn(msg: Any, icon: str = I.WARN) -> None:
    _console.print(f"{indent()}{icon} ", style=f"bold {C.WARNING}", end="")
    _console.print(str(msg), style=C.MUTED)


def error(msg: Any, icon: str = I.FAIL) -> None:
    _console.print(f"{indent()}{icon} ", style=f"bold {C.ERROR}", end="")
    _console.print(str(msg), style=C.MUTED)


def info(msg: Any, icon: str = I.INFO) -> None:
    _console.print(f"{indent()}{icon} ", style=f"bold {C.INFO}", end="")
    _console.print(str(msg), style=C.MUTED)


def dim(msg: Any) -> None:
    _console.print(f"{indent()}{I.BULLET} {msg}", style=C.DIM)


def debug(msg: Any) -> None:
    _console.print(f"{indent()}{I.NOTE} {msg}", style=C.DIM)


def note(msg: Any) -> None:
    _console.print(f"{indent()}{I.NOTE} ", style=f"bold {C.ACCENT}", end="")
    _console.print(str(msg), style=C.MUTED)


# ---------------------------------------------------------------------------
# 步骤执行卡片（workflow_runner 调用最频繁）
# ---------------------------------------------------------------------------
def step_header(step: str, name: str, session: str, mode: str = "run") -> None:
    """步骤开始卡片：粗体 step + 名称 + session。"""
    mode_chip = chip("DRY", C.WARNING) if mode == "dry" else chip("RUN", C.PRIMARY)
    _console.print()
    _console.print(f"{indent()}{I.STEP} ", style=f"bold {C.PRIMARY}", end="")
    _console.print(f"步骤 {step}  ", style=f"bold {C.HL}", end="")
    _console.print(f"{name}", style=C.MUTED, end="")
    _console.print("   ")
    _console.print(mode_chip, end="")
    _console.print(f"  会话 ", style=C.DIM, end="")
    _console.print(session, style=f"italic {C.DIM}")


def step_result(success_: bool, message: Optional[str] = None, elapsed: Optional[float] = None) -> None:
    """步骤结束行：✓/✗ + 提示 + 可选耗时。"""
    if success_:
        _console.print(f"{indent()}{I.OK} ", style=f"bold {C.SUCCESS}", end="")
        _console.print("完成", style=f"bold {C.SUCCESS}", end="")
    else:
        _console.print(f"{indent()}{I.FAIL} ", style=f"bold {C.ERROR}", end="")
        _console.print("失败", style=f"bold {C.ERROR}", end="")
    if elapsed is not None:
        _console.print(f"   {I.TIME}  {format_elapsed(elapsed)}", style=C.DIM, end="")
    if message:
        _console.print(f"   {I.ARROW_R}  {message}", style=C.DIM, end="")
    _console.print()


# ---------------------------------------------------------------------------
# 计时器 / Spinner
# ---------------------------------------------------------------------------
def format_elapsed(seconds: float) -> str:
    """把秒数格式化成 1m23s / 12s / 234ms。"""
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    if seconds < 60:
        return f"{int(seconds)}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"


@contextmanager
def spinner(text: str, color: str = C.PRIMARY):
    """
    显示一个 spinner + 实时更新 text。会在退出时把最终状态行打印出来。

    用法::

        with spinner("正在执行步骤 11 …") as s:
            do_long_thing()
            s.update("正在写入状态文档…")
            write_state()
    """
    progress = Progress(
        SpinnerColumn(style=color),
        TextColumn("[bold]{task.description}[/]"),
        TimeElapsedColumn(),
        console=_console,
        transient=True,
    )
    task_id = progress.add_task(text, total=None)

    class _Handle:
        def update(self, msg: str) -> None:
            progress.update(task_id, description=msg)

    with progress:
        yield _Handle()


# ---------------------------------------------------------------------------
# 输入：confirm / prompt / select
# ---------------------------------------------------------------------------
def confirm(message: str, default: bool = True) -> bool:
    """y/n 确认。"""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        return Confirm.ask(f"  {I.ARROW} {message} {suffix}", default=default, console=_console)
    except EOFError:
        # 非交互管道：返回默认值
        warn("无输入，使用默认值。")
        return default


def prompt(message: str, default: Optional[str] = None,
          validator: Optional[Callable[[str], bool]] = None,
          show_default: bool = True,
          preface: Optional[str] = None) -> str:
    """文本输入（可选默认值 + 校验器）。

    - 默认值的回显由 rich.Prompt.ask 负责（自动在括号里展示），本函数不重复拼 [default]，
      否则会与 rich 的 show_default 重复输出。
    - ``show_default=False`` 时不在 ``❯`` 行后追加默认值的回显；调用方可借助
      ``preface`` 把默认值单独打印到 ``❯`` 行上方。
    - ``preface`` 是一段附加文本，会在 ``❯`` 行**之前**以 dim 风格单独打印一行。
    """
    while True:
        try:
            if preface:
                _console.print(f"{indent()}{preface}", style=C.DIM)
            value = Prompt.ask(
                f"  {I.ARROW} {message}",
                console=_console,
                default=default,
                show_default=show_default,
            )
        except EOFError:
            value = default or ""
        value = (value or "").strip()
        if validator and not validator(value):
            warn(f"输入无效：{message}")
            continue
        return value


def select(message: str, options: Sequence[str], default: int = 0) -> int:
    """单选菜单（数字选择）。返回选中下标。"""
    n = len(options)
    _console.print()
    _console.print(f"  {I.ARROW} {message}", style=f"bold {C.PRIMARY}")
    for i, opt in enumerate(options, 1):
        marker = f"{I.STEP} " if i - 1 == default else "  "
        style = f"bold {C.PRIMARY}" if i - 1 == default else C.MUTED
        _console.print(f"     {marker}{i}. {opt}", style=style)
    while True:
        try:
            raw = Prompt.ask(
                f"  {I.ARROW} 选择",
                default=str(default + 1),
                console=_console,
            ).strip()
        except EOFError:
            # 非交互管道：用默认值
            warn("无输入，使用默认值。")
            return default
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= n:
                return idx - 1
        warn("无效选择，请重试。")


def select_project(projects: Sequence[Dict[str, Any]], allow_new: bool = True) -> Optional[str]:
    """从项目表里选一个；返回项目名（None = 取消）。"""
    print_projects_table(projects, title="选择项目")
    options = [p.get("novel_name") or p.get("name", "?") for p in projects]
    if allow_new:
        options.append(Text("＋  创建新项目", style=f"bold {C.ACCENT}").plain)
    if not options:
        return None
    idx = select("请选择项目编号", options)
    if allow_new and idx == len(projects):
        return "__new__"
    return projects[idx].get("name")


def select_projects(projects: Sequence[Dict[str, Any]]) -> List[str]:
    """从项目表里批量选择项目；返回项目名列表。"""
    print_projects_table(projects, title="选择项目")
    if not projects:
        return []

    _console.print()
    _console.print(f"  {I.ARROW} 请选择项目编号", style=f"bold {C.PRIMARY}")
    _console.print(f"     支持多个编号，例如 1,3,5 或 1-3；输入 all 全选，输入 0 取消。", style=C.DIM)

    max_index = len(projects)
    while True:
        try:
            raw = Prompt.ask(
                f"  {I.ARROW} 选择",
                default="0",
                console=_console,
            ).strip()
        except EOFError:
            warn("无输入，已取消。")
            return []

        value = raw.lower()
        if value in {"0", "q", "quit", "cancel"}:
            return []
        if value in {"all", "*", "全部"}:
            return [p.get("name") for p in projects if p.get("name")]

        selected: List[int] = []
        valid = True
        for part in raw.replace("，", ",").split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start_raw, end_raw = [item.strip() for item in part.split("-", 1)]
                if not start_raw.isdigit() or not end_raw.isdigit():
                    valid = False
                    break
                start, end = int(start_raw), int(end_raw)
                if start > end:
                    start, end = end, start
                selected.extend(range(start, end + 1))
                continue
            if not part.isdigit():
                valid = False
                break
            selected.append(int(part))

        deduped = []
        for idx in selected:
            if idx < 1 or idx > max_index:
                valid = False
                break
            if idx not in deduped:
                deduped.append(idx)

        if valid and deduped:
            return [projects[idx - 1].get("name") for idx in deduped if projects[idx - 1].get("name")]
        warn("无效选择，请输入编号、范围、all 或 0。")


# ---------------------------------------------------------------------------
# 杂项
# ---------------------------------------------------------------------------
def print_done(project: Optional[str] = None, extra: Optional[str] = None) -> None:
    """工作流结束 banner。"""
    _console.print()
    _console.print("═" * _BOX_WIDTH, style=C.SUCCESS)
    _console.print(f"  {I.STAR}  ", style=f"bold {C.SUCCESS}", end="")
    _console.print("工作流完成", style=f"bold {C.SUCCESS}")
    if project:
        _console.print(f"     项目: {project}", style=C.MUTED)
    if extra:
        _console.print(f"     {extra}", style=C.DIM)
    _console.print("═" * _BOX_WIDTH, style=C.SUCCESS)
    _console.print()


def press_enter() -> None:
    """按回车继续。"""
    Prompt.ask(f"  {I.DASH * 2} 按回车继续…", default="", show_default=False, console=_console)


def pause(msg: str = "按回车继续…") -> None:
    press_enter()


# ---------------------------------------------------------------------------
# 内部：方便拼 indent
# ---------------------------------------------------------------------------
__all__ = [
    "C", "I", "console", "init", "clear", "indent",
    "t", "stylize", "chip", "line", "blank",
    "print_banner", "print_header", "print_subheader", "print_section",
    "print_panel", "print_kv", "print_creative_cards", "print_steps_table",
    "print_projects_table", "print_choices_table",
    "success", "warn", "error", "info", "dim", "debug", "note",
    "step_header", "step_result", "format_elapsed", "spinner",
    "confirm", "prompt", "select", "select_project", "select_projects",
    "print_done", "press_enter", "pause",
]
