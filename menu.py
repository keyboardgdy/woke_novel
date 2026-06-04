#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
woke_novel 主菜单（单步 / 完整 / 继续 / 步骤列表）。

所有显示都委托给 ui 模块；本文件只负责交互编排。
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

try:
    import ebooklib
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False

from ui import (
    C, I,
    blank, chip, clear, confirm, dim, error, indent, info, init, line, note,
    print_banner, print_header, print_kv, print_panel, print_projects_table,
    print_section, print_steps_table, print_subheader, prompt, select,
    select_project, success, warn, press_enter,
)
from workflow_runner import STEP_NAMES, STEP_FILES, WorkflowRunner
import cli as cli_module

# 模块级缓存：ask_user_description 拿到的值，留给 full_loop_mode 透传给子进程。
# 一次菜单会话内只可能问一次，所以单变量够用。
_pending_user_description: Optional[str] = None
_pending_novel_size: Optional[str] = None


# ---------------------------------------------------------------------------
# 项目发现 + 摘要
# ---------------------------------------------------------------------------
def _projects_root() -> Path:
    return Path(__file__).parent / "projects"


def list_existing_projects() -> List[Dict[str, Any]]:
    """读取 projects/ 下所有项目，附带 .project_info.json 摘要。"""
    root = _projects_root()
    if not root.exists():
        return []
    items: List[Dict[str, Any]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        items.append(_summarize_project(d.name))
    return items


def _summarize_project(name: str) -> Dict[str, Any]:
    """从 .project_info.json 抽取展示字段。"""
    from project_info import get_project_info
    info_obj = get_project_info(name)
    info_dict: Dict[str, Any] = {"name": name}
    if not info_obj:
        info_dict.update({
            "genre": "—",
            "novel_name": name,
            "progress": "—",
            "last_active": "—",
        })
        return info_dict

    info_dict["genre"] = info_obj.genre or "—"
    info_dict["novel_name"] = info_obj.novel_name or name

    total = info_obj.total_chapters or 0
    current = info_obj.current_round or 1
    if total > 0:
        progress = f"R{current}/{total}"
    elif info_obj.last_step:
        progress = f"{info_obj.last_step}"
    else:
        progress = "未开始"
    info_dict["progress"] = progress
    info_dict["last_active"] = _short_time(info_obj.get("last_step_at"))
    return info_dict


def _short_time(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    return iso[:16].replace("T", " ")


def _project_kv(project: str) -> List[Tuple[str, str]]:
    """把单个项目的 .project_info.json 渲染成键值对。"""
    from project_info import get_project_info
    info_obj = get_project_info(project)
    if not info_obj:
        return [("项目", project), ("状态", "无 .project_info.json")]
    data = info_obj.to_dict()
    return [
        ("项目",   data.get("project_name", project)),
        ("题材",   str(data.get("genre", "—"))),
        ("小说名", str(data.get("novel_name") or "未设置")),
        ("方案",   str(data.get("selected_option") or "未选")),
        ("参考",   str(data.get("ref_works") or "无")),
        ("轮次",   f"R{data.get('current_round', 1)}"
                   + (f" / 总 {data.get('total_chapters', '?')} 章" if data.get('total_chapters') else "")),
        ("最后步骤", str(data.get("last_step") or "无")),
        ("上次执行", _short_time(data.get("last_step_at"))),
    ]


def detect_genre_from_project(project_name: str) -> str:
    from project_info import get_project_info
    info_obj = get_project_info(project_name)
    if info_obj and info_obj.genre:
        return info_obj.genre
    return "都市"


# ---------------------------------------------------------------------------
# 项目选择
# ---------------------------------------------------------------------------
def select_project_mode() -> Tuple[Optional[str], Optional[str]]:
    """项目选择：列表里选一个，或创建新项目。返回 (project, genre)。"""
    clear()
    print_banner("选择项目", subtitle="选择已有项目继续，或创建新项目")

    projects = list_existing_projects()
    if projects:
        idx = select_project(projects, allow_new=True)
        if idx is None:
            return (None, None)
        if idx == "__new__":
            pass  # 落到下面创建流程
        else:
            project = idx
            genre = detect_genre_from_project(project)
            return (project, genre)
    else:
        info("暂无已有项目，将创建新项目。")

    # 创建新项目
    print_section("创建新项目", color=C.ACCENT)
    project = prompt("新项目名称")
    if not project:
        warn("项目名称不能为空。")
        return (None, None)
    if (_projects_root() / project).exists():
        warn(f"目录已存在: projects/{project}")
        return (None, None)
    genre = cli_module.ask_genre()
    user_description = cli_module.ask_user_description()
    novel_size = cli_module.ask_novel_size()

    from project_info import create_project_info
    create_project_info(project, genre, novel_size=novel_size,
                        target_word_count=cli_module.size_to_word_count(novel_size))
    WorkflowRunner(project, genre, novel_size=novel_size,
                   target_word_count=cli_module.size_to_word_count(novel_size))
    success(f"项目已创建: {project}")
    info(f"补充说明：{user_description}")
    info(f"小说规模：{novel_size}")

    global _pending_user_description, _pending_novel_size
    _pending_user_description = user_description
    _pending_novel_size = novel_size
    return (project, genre)


# ---------------------------------------------------------------------------
# 三种模式
# ---------------------------------------------------------------------------
def single_step_mode() -> None:
    """单步执行模式。"""
    result = select_project_mode()
    if not result or result[0] is None:
        return
    project, genre = result

    clear()
    print_banner("单步执行", subtitle=f"项目 {project} · 题材 {genre}")
    print_subheader("项目信息", color=C.PRIMARY)
    print_kv(_project_kv(project))

    steps = list(STEP_NAMES.items())
    print_steps_table(steps, title="可用步骤")
    step = prompt("请输入步骤编号", default="01").strip()
    if not step or step not in STEP_NAMES:
        warn("无效步骤编号。")
        return

    dry_run = confirm("干运行（不实际调用 claude）?", default=False)
    option_count_raw = prompt("创意方案数量", default="3")
    option_count = int(option_count_raw) if option_count_raw.isdigit() else 3

    print_section(f"执行 步骤 {step}  {STEP_NAMES[step]}", color=C.PRIMARY)
    runner = WorkflowRunner(project, genre, dry_run=dry_run)

    if step == "01" and option_count > 1:
        for i in range(option_count):
            note(f"方案 {i+1}/{option_count}")
            if not runner.run_step("01", runner.make_display_id(f"creative_option_{i+1}"), option_index=i+1):
                error(f"方案 {i+1} 生成失败")
                press_enter()
                return
        chosen = select("选择一个创意方案", [f"方案 {i+1}" for i in range(option_count)], default=0)
        success(f"已选择方案 {chosen + 1}")
        if not runner.run_step("02", runner.make_display_id(f"creative_option_{chosen+1}"), option_index=chosen+1):
            error("创意方案补充失败")
    else:
        display_id = runner.make_display_id(step)
        runner.run_step(step, display_id)

    press_enter()


def full_loop_mode() -> None:
    """完整执行模式。"""
    clear()
    print_banner("完整执行", subtitle="一键跑完 创意 → 世界观 → 主轴 → 正文")

    project = prompt("项目名称", default="my_novel")
    if not project:
        warn("项目名称不能为空。")
        return
    genre = cli_module.ask_genre()
    user_description = cli_module.ask_user_description()
    novel_size = cli_module.ask_novel_size()
    target_word_count = cli_module.size_to_word_count(novel_size)
    option_count_raw = prompt("创意方案数量", default="3")
    option_count = int(option_count_raw) if option_count_raw.isdigit() else 3
    dry_run = confirm("干运行（不实际调用 claude）?", default=False)

    # 配置摘要
    body = "\n".join([
        f"项目         {project}",
        f"题材         {genre}",
        f"补充说明     {user_description}",
        f"规模         {novel_size}（约 {target_word_count // 10_000} 万字）",
        f"方案数       {option_count}",
        f"干运行       {'是' if dry_run else '否'}",
    ])
    print_panel("执行配置", body, color=C.ACCENT, icon=I.DIAMOND)

    if not confirm("确认开始?", default=True):
        warn("已取消。")
        return

    cmd = [
        sys.executable, "run_workflow.py", "loop",
        "--project-name", project,
        "--genre", genre,
        "--option-count", str(option_count),
        "--user-description", user_description,
        "--novel-size", novel_size,
    ]
    if dry_run:
        cmd.append("--dry")
    subprocess.run(cmd)
    press_enter()


def continue_mode() -> None:
    """继续执行模式。"""
    from project_info import get_project_info

    clear()
    print_banner("继续执行", subtitle="从上次中断的步骤接续")

    projects = list_existing_projects()
    if not projects:
        warn("暂无已有项目，请先使用「完整执行」创建一个。")
        return

    idx = select_project(projects, allow_new=False)
    if idx is None:
        return
    project = idx
    info_obj = get_project_info(project)

    if not info_obj or not info_obj.last_step:
        error("该项目没有中断点，请使用「完整执行」。")
        press_enter()
        return

    print_subheader(f"项目：{project}", color=C.PRIMARY)
    print_kv([
        ("当前轮次", str(info_obj.current_round)),
        ("中断步骤", info_obj.last_step or "无"),
        ("中断时间", _short_time(info_obj.last_step_at)),
    ])

    if not confirm("确认继续?", default=True):
        warn("已取消。")
        return

    cmd = [sys.executable, "run_workflow.py", "continue", "--project-name", project]
    subprocess.run(cmd)
    press_enter()


# ---------------------------------------------------------------------------
# 步骤列表
# ---------------------------------------------------------------------------
def view_steps_list() -> None:
    clear()
    print_banner("步骤列表", subtitle="step 编号 → 中文名")
    print_steps_table(list(STEP_NAMES.items()), title="完整步骤")
    print_kv([
        ("01-02",   "创意方案（生成 + 补充）"),
        ("03-04",   "世界观 + 人物"),
        ("05+05a+05b", "主轴 + 幕次框架 + 核心骨架"),
        ("06-10",   "开篇（剧情→梗概→指南→正文→状态）"),
        ("11-16",   "每轮创作循环"),
        ("17",      "幕次末精简"),
        ("18",      "项目根 CLAUDE.md"),
    ], key_color=C.ACCENT)
    press_enter()


# ---------------------------------------------------------------------------
# 导出功能
# ---------------------------------------------------------------------------
def export_mode() -> None:
    """导出小说为 md / txt / epub 格式。"""
    clear()
    print_banner("导出小说", subtitle="合并 02_output 章节，导出为多格式")

    projects = list_existing_projects()
    if not projects:
        warn("暂无已有项目。")
        press_enter()
        return

    idx = select_project(projects, allow_new=False)
    if idx is None:
        return
    project_name = idx

    project_path = _projects_root() / project_name
    output_dir = project_path / "02_output"

    if not output_dir.exists():
        error(f"目录不存在: {output_dir}")
        press_enter()
        return

    # 收集正文文件
    chapters: List[Tuple[int, Path]] = []
    for f in output_dir.iterdir():
        if f.is_file() and f.suffix == ".md" and f.stem.startswith("正文v"):
            try:
                version = int(f.stem.replace("正文v", ""))
                chapters.append((version, f))
            except ValueError:
                pass

    if not chapters:
        error("未找到任何正文章节文件。")
        press_enter()
        return

    chapters.sort(key=lambda x: x[0])
    total = len(chapters)

    novel_title = project_name  # 使用文件夹名作为小说名

    print_subheader(f"项目: {project_name}", color=C.PRIMARY)
    print_kv([
        ("小说名", novel_title),
        ("章节数", str(total)),
        ("来源目录", str(output_dir)),
    ])

    # 选择导出格式
    format_options = ["全部格式 (md + txt + epub)", "仅 MD", "仅 TXT", "仅 EPUB"]
    fmt_idx = select("选择导出格式", format_options, default=0)

    export_md = fmt_idx in (0, 1)
    export_txt = fmt_idx in (0, 2)
    export_epub = fmt_idx in (0, 3) and HAS_EBOOKLIB

    if fmt_idx == 3 and not HAS_EBOOKLIB:
        warn("系统未安装 ebooklib 库，EPUB 导出不可用。")

    # 合并内容
    merged_content = ""
    for version, fpath in chapters:
        content = fpath.read_text(encoding="utf-8")
        merged_content += f"\n\n{content}"

    results: List[Tuple[str, str]] = []

    # 导出 MD
    if export_md:
        md_path = project_path / f"{novel_title}.md"
        md_path.write_text(merged_content, encoding="utf-8")
        results.append(("MD", str(md_path)))

    # 导出 TXT
    if export_txt:
        txt_path = project_path / f"{novel_title}.txt"
        # TXT 去掉 markdown 标记
        txt_content = merged_content.replace("#", "").replace("**", "").replace("*", "")
        txt_path.write_text(txt_content, encoding="utf-8")
        results.append(("TXT", str(txt_path)))

    # 导出 EPUB
    if export_epub:
        epub_path = project_path / f"{novel_title}.epub"
        book = epub.EpubBook()
        book.set_identifier(f"woke_novel_{project_name}")
        book.set_title(novel_title)
        book.set_language("zh-CN")

        book.add_author("woke_novel")

        epub_chapters: List[epub.EpubHtml] = []
        for i, (version, fpath) in enumerate(chapters, 1):
            chapter_content = fpath.read_text(encoding="utf-8")
            # 简单处理：提取标题
            lines = chapter_content.split("\n")
            chapter_title = f"第{i}章"
            for line in lines:
                if line.strip().startswith("#"):
                    chapter_title = line.strip().lstrip("#").strip()
                    break

            c = epub.EpubHtml(
                title=chapter_title,
                file_name=f"chapter_{i:03d}.xhtml",
                lang="zh-CN"
            )
            # 转换为简单 HTML
            html_content = f"<html><head><title>{chapter_title}</title></head><body><h1>{chapter_title}</h1>"
            for line in chapter_content.split("\n"):
                line = line.strip()
                if line.startswith("#"):
                    html_content += f"<h2>{line.lstrip('#').strip()}</h2>"
                elif line:
                    html_content += f"<p>{line}</p>"
            html_content += "</body></html>"
            c.content = html_content
            book.add_item(c)
            epub_chapters.append(c)

        book.toc = tuple(epub_chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        book.spine = ["nav"] + epub_chapters

        try:
            epub.write_epub(str(epub_path), book, {})
            results.append(("EPUB", str(epub_path)))
        except Exception as e:
            warn(f"EPUB 导出失败: {e}")

    # 输出结果
    print_section("导出完成", color=C.SUCCESS)
    for fmt, path in results:
        success(f"{fmt} → {path}")

    if not results:
        error("未生成任何文件。")

    press_enter()


# ---------------------------------------------------------------------------
# 主菜单
# ---------------------------------------------------------------------------
def main() -> None:
    init()
    while True:
        clear()
        print_banner("woke_novel 工作流", subtitle="中文网文 · Claude CLI 驱动")
        print_subheader("请选择功能", color=C.PRIMARY)
        options = [
            "单步执行   跑一个指定步骤（试运行 / 修复）",
            "完整执行   一键跑完整个流水线",
            "继续执行   从中断点接续",
            "查看步骤   步骤编号 + 中文名",
            "导出小说   合并 02_output 导出 md/txt/epub",
            "退出",
        ]
        idx = select("主菜单", options, default=0)
        actions = [single_step_mode, full_loop_mode, continue_mode, view_steps_list, export_mode]
        if idx == 5:
            print_panel("再见", "下次再写！", color=C.ACCENT, icon=I.STAR)
            break
        try:
            actions[idx]()
        except KeyboardInterrupt:
            warn("已取消。")
            press_enter()
        except Exception as e:
            error(f"未捕获异常: {e}")
            press_enter()


if __name__ == "__main__":
    main()
