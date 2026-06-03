# -*- coding: utf-8 -*-
"""
小说生成自动工作流运行器 v1.2
模块化架构：cli.py（交互） + workflow_runner.py（执行） + ui.py（视觉）。

所有可见输出都委托给 ui 模块；本文件只保留流程编排。
"""

import re
import sys
from pathlib import Path

from ui import (
    C, I,
    blank, confirm, dim, error, info, init, line, note, press_enter,
    print_banner, print_creative_cards, print_done, print_header, print_kv,
    print_panel, print_section, prompt, select, success, warn,
)
from cli import (
    ask_genre, ask_project_name, ask_user_description,
)
from workflow_runner import STEP_NAMES, WorkflowRunner


# ---------------------------------------------------------------------------
# 顶部用法
# ---------------------------------------------------------------------------
def _print_usage() -> None:
    init()
    print_banner("woke_novel", subtitle="用法 & 可用命令")
    print_kv([
        ("single <step>",         "运行单个步骤"),
        ("session <block> <…>",   "在新会话中运行多个步骤"),
        ("init",                  "初始化项目（询问题材和项目名）"),
        ("loop",                  "完整循环流程（自动初始化）"),
        ("continue",              "从上次中断的步骤继续执行"),
    ], key_color=C.ACCENT, value_color=C.MUTED)


# ---------------------------------------------------------------------------
# 共用流水线：开篇 06-10 + 按幕执行 11-16/17/18 post_17
# ---------------------------------------------------------------------------
# Loop 主流程和 Continue 续跑都调本函数，保证两条路径产物完全一致。
#
# 游标 cursor = (opening_done, start_act, start_round_in_act, skip_act_end)
#   opening_done        — True=开篇 06-10 + create_story_summary 已完成
#   start_act           — 从哪一幕开始（1-based）
#   start_round_in_act  — 该幕内从第几轮开始（0-based）
#   skip_act_end        — True=本幕（start_act）的 17 + 18 post_17 已完成
#
# Loop 调：cursor = (False, 1, 0, False)
# Continue 调：根据 last_step / last_phase 算出 cursor，详见下方
# ---------------------------------------------------------------------------
def _run_writing_pipeline(runner, opening_done, start_act, start_round_in_act, skip_act_end):
    chapter_counts = runner.project_info.chapter_counts or []
    total_chapters = runner.project_info.total_chapters or 0
    success(f"各幕章节数：{chapter_counts}，总章节数：{total_chapters}")

    if not opening_done:
        print_section("会话 · 开篇创作", color=C.PRIMARY)
        runner.run_session_block("opening", ["06", "07", "08", "09", "10"], act_num=1)
        runner.extract_and_create_story_summary(1)

    runner.round = 2 if not opening_done else max(2, runner.round)

    for act_num in range(start_act, len(chapter_counts) + 1):
        act_chapters = chapter_counts[act_num - 1]
        loop_count = (act_chapters - 1) if act_num == 1 else act_chapters
        if loop_count <= 0:
            warn(f"第 {act_num} 幕可用轮次为 0，跳过")
            continue

        print_section(f"第 {act_num} 幕创作循环（共 {loop_count} 轮）", color=C.PRIMARY)

        begin_in_act = start_round_in_act if act_num == start_act else 0
        for loop_idx in range(begin_in_act, loop_count):
            relative = loop_idx + 1
            print_section(
                f"第 {act_num} 幕 · 轮次 {relative}/{loop_count}（R{runner.round}）",
                color=C.ACCENT,
            )

            session_name = f"round_{runner.round}"
            if not runner.run_session_block(session_name, ["11", "12", "13", "14", "15"], act_num=act_num):
                error("创作循环失败")
                sys.exit(1)

            runner.append_story_summary(runner.round)

            if not runner.run_session_block(session_name, ["16"], act_num=act_num):
                error("步骤 16 失败")
                sys.exit(1)

            runner.sync_summary_to_state(runner.round)
            runner.project_info.update(current_round=runner.round)

            note("继续下一轮…")
            runner.round += 1

        # 幕末 17 + 18 post_17：仅当本幕不是"已做完"形态时跑
        if act_num == start_act and skip_act_end:
            continue

        print_section(f"步骤 17 · 第 {act_num} 幕故事梗概精简", color=C.PRIMARY)
        if not runner.run_step(
            "17", runner.make_display_id(f"act_{act_num}"), act_num=act_num,
        ):
            error("步骤 17 失败")
            sys.exit(1)
        runner.sync_summary_to_state(runner.round - 1)

        print_section(
            f"步骤 18 · post_17 刷新项目根 CLAUDE.md（第 {act_num} 幕后）",
            color=C.ACCENT,
        )
        if not runner.run_step(
            "18", runner.make_display_id(f"act_{act_num}"),
            phase="post_17", act_num=act_num,
        ):
            warn("步骤 18 post_17 失败，不影响后续流程")


def _compute_resume_cursor(last_step, last_phase, current_round, chapter_counts):
    """根据断点状态算出 (_run_writing_pipeline 用的) 游标。

    返回 (opening_done, start_act, start_round_in_act, skip_act_end)。
    返回 None 表示"该断点不属于本函数管辖范围"（continue 调用方另处理）。
    """
    # ---- 18 post_05b：规划层完成、开篇没做 → 跑开篇
    if last_step == "18" and last_phase == "post_05b":
        return (False, 1, 0, False)

    # ---- 开篇 06-09 中断：续跑开篇
    if last_step in {"06", "07", "08", "09"}:
        return (False, 1, 0, False)

    # ---- 10 完成：进入循环段
    if last_step == "10":
        return (True, 1, 0, False)

    # ---- 循环段/幕末：反推游标
    if last_step in {"11", "12", "13", "14", "15"}:
        completed_loops = current_round - 2  # 该轮没完成
    elif last_step in {"16", "17"} or (last_step == "18" and last_phase == "post_17"):
        completed_loops = current_round - 1
    else:
        return None

    cum = 0
    for i, cnt in enumerate(chapter_counts, start=1):
        loop_count = (cnt - 1) if i == 1 else cnt
        if completed_loops < cum + loop_count:
            start_act = i
            start_round_in_act = completed_loops - cum
            break
        cum += loop_count
    else:
        return None  # completed_loops 超出总循环段

    skip_act_end = last_step == "18" and last_phase == "post_17"
    return (True, start_act, start_round_in_act, skip_act_end)


# ---------------------------------------------------------------------------
# 三方确认（开篇创作会话：y / n / q）
# ---------------------------------------------------------------------------
def _confirm_open_session() -> str:
    """开篇会话默认自动继续，不再停顿。

    历史上这里会停在 `y=继续 / n=暂停 / q=退出` 等待用户输入；现在改成
    直接放行并打印一行提示，调用方后续的 n / q 分支成为死代码（保留无害）。
    如需恢复交互式确认，把函数体换回原 `prompt(...)` 循环即可。
    """
    info("自动继续【开篇创作】会话（默认 y，不停顿）。")
    return "y"


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> None:
    init()
    if len(sys.argv) < 2:
        _print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "single":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("step", help="步骤编号，如 01")
        parser.add_argument("-g", "--genre", default="都市")
        parser.add_argument("-p", "--project-name", default="test_project")
        parser.add_argument("--dry", action="store_true", help="干运行")
        parser.add_argument("--max-retries", type=int, default=3,
                            help="失败自动重试次数（不含首次，默认 3）")
        args = parser.parse_args(sys.argv[2:])

        runner = WorkflowRunner(args.project_name, args.genre, dry_run=args.dry,
                                max_retries=args.max_retries)
        display_id = runner.make_display_id(args.step)
        ok = runner.run_step(args.step, display_id)
        sys.exit(0 if ok else 1)

    elif command == "session":
        if len(sys.argv) < 4:
            error("用法: python run_workflow.py session <block> <step1,step2,...> [选项]")
            sys.exit(1)

        block_name = sys.argv[2]
        steps_str = sys.argv[3]
        steps = steps_str.split(",")

        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("-g", "--genre", default="都市")
        parser.add_argument("-p", "--project-name", default="test_project")
        parser.add_argument("--dry", action="store_true")
        parser.add_argument("--max-retries", type=int, default=3,
                            help="失败自动重试次数（不含首次，默认 3）")
        args, unknown = parser.parse_known_args(sys.argv[4:])

        runner = WorkflowRunner(args.project_name, args.genre, dry_run=args.dry,
                                max_retries=args.max_retries)
        ok = runner.run_session_block(block_name, steps)
        sys.exit(0 if ok else 1)

    elif command == "init":
        genre = ask_genre()
        project_name = ask_project_name()

        runner = WorkflowRunner(project_name, genre)
        print_panel("项目初始化完成", "", color=C.SUCCESS, icon=I.OK)
        print_kv([
            ("项目",   runner.project_name),
            ("题材",   runner.genre),
            ("项目目录", str(runner.path_resolver.project_root)),
        ])
        sys.exit(0)

    elif command == "loop":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry", action="store_true", help="干运行")
        parser.add_argument("--option-count", type=int, default=3, help="创意方案生成数量")
        parser.add_argument("--genre", default=None, help="小说题材（省略则交互询问）")
        parser.add_argument("--project-name", default=None, help="项目名（省略则交互询问）")
        parser.add_argument("--max-retries", type=int, default=3,
                            help="失败自动重试次数（不含首次，默认 3）")
        args = parser.parse_args(sys.argv[2:])

        genre = args.genre or ask_genre()
        project_name = args.project_name or ask_project_name()
        user_description = ask_user_description()

        runner = WorkflowRunner(project_name, genre, dry_run=args.dry,
                                max_retries=args.max_retries)

        print_banner(
            f"项目：{runner.project_name}",
            subtitle=f"题材 {runner.genre} · 目录 {runner.path_resolver.project_root}",
        )

        # ========== 会话1: 创意方案生成 ==========
        print_section("会话 1 · 创意方案生成", color=C.PRIMARY)

        option_count = args.option_count
        creative_display_id = runner.make_display_id("creative_option")
        for i in range(option_count):
            if i > 0:
                # 步骤间分隔：每次 step 完成 → 下一次 "生成方案" 注记之间画一条细线
                line(color=C.DIM)
            note(f"生成方案 {i+1}/{option_count}")
            if not runner.run_step(
                "01", creative_display_id,
                option_index=i + 1, user_description=user_description,
            ):
                error("创意方案生成失败")
                sys.exit(1)

        chosen = select_creative(runner, option_count)
        success(f"已选择方案 {chosen}")

        if not runner.run_step("02", creative_display_id, option_index=chosen):
            error("创意方案补充失败")
            sys.exit(1)

        novel_name = runner.extract_novel_name_from_creative(chosen)
        if novel_name:
            success(f"提取到小说名：{novel_name}")
            runner.rename_project(novel_name)

        runner.option_index = chosen

        ref_works = runner.extract_ref_works_from_creative(chosen)
        if ref_works:
            note(f"参考作品：{ref_works}")
            runner.ref_works = ref_works

        runner.project_info.select_option(
            option_num=chosen, novel_name=novel_name, ref_works=ref_works,
        )

        # ========== 会话2: 世界观与设定 ==========
        print_section("会话 2 · 世界观与设定", color=C.PRIMARY)
        runner.run_session_block("world", ["03", "04"])

        # ========== 会话3: 故事主轴 ==========
        print_section("会话 3 · 故事主轴", color=C.PRIMARY)
        act_display_id = runner.make_display_id("arc")
        for idx, step in enumerate(["05", "05a"]):
            step_name = STEP_NAMES.get(step, step)
            if idx > 0:
                line(color=C.DIM)
            note(f"执行步骤 {step} · {step_name}")
            if not runner.run_step(step, act_display_id):
                error(f"步骤 {step} 失败")
                sys.exit(1)

        act_count = runner.extract_act_count_from_macro_model()
        if act_count:
            runner.project_info.update(act_count=act_count)
            success(f"提取幕次总数：{act_count}")

            print_section(f"步骤 05b 循环 · 幕次核心骨架（共 {act_count} 幕）", color=C.PRIMARY)
            for act_num in range(1, act_count + 1):
                if act_num > 1:
                    line(color=C.DIM)
                note(f"幕次 {act_num}/{act_count}")
                if not runner.run_step(
                    "05b", act_display_id,
                    user_description=f"幕次{act_num}", act_num=act_num,
                ):
                    error(f"步骤 05b (幕次{act_num}) 失败")
                    sys.exit(1)

            chapter_counts = runner.extract_all_chapter_counts(act_count)
            total_chapters = sum(chapter_counts)
            success(f"各幕章节数：{chapter_counts}，总章节数：{total_chapters}")

            runner.project_info.update(
                chapter_counts=chapter_counts, total_chapters=total_chapters,
            )

            # 步骤 18 post_05b
            print_section("步骤 18 · post_05b 生成项目级 CLAUDE.md", color=C.ACCENT)
            if not runner.run_step("18", act_display_id, phase="post_05b"):
                warn("步骤 18 post_05b 失败，不影响后续流程")
        else:
            warn("无法获取幕次总数，跳过 05b 循环")

        # ========== 会话4: 开篇创作 ==========
        print_section("会话 4 · 开篇创作", color=C.PRIMARY)
        choice = _confirm_open_session()
        if choice == "n":
            info("已暂停。重新运行可使用 'continue' 命令从断点继续。")
            sys.exit(0)
        if choice == "q":
            info("用户主动退出。")
            sys.exit(0)

        runner.run_session_block("opening", ["06", "07", "08", "09", "10"], act_num=1)
        runner.extract_and_create_story_summary(1)

        runner.round = 2

        _run_writing_pipeline(runner, opening_done=True, start_act=1, start_round_in_act=0, skip_act_end=False)

        print_done(
            project=runner.project_name,
            extra=f"创作轮次 {runner.round - 1}",
        )

    elif command == "continue":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry", action="store_true", help="干运行")
        parser.add_argument("--project-name", default=None, help="项目名（省略则交互询问）")
        parser.add_argument("--max-retries", type=int, default=3,
                            help="失败自动重试次数（不含首次，默认 3）")
        args = parser.parse_args(sys.argv[2:])

        project_name = args.project_name or ask_project_name()
        runner = WorkflowRunner(project_name, dry_run=args.dry,
                                max_retries=args.max_retries)

        last_step = runner.project_info.last_step
        current_round = runner.project_info.current_round
        last_phase = runner.project_info.last_step_phase

        print_banner(
            f"继续执行：{runner.project_name}",
            subtitle=f"当前轮次 R{current_round} · 上次中断 步骤 {last_step or '无'}",
        )

        if last_step is None:
            error("没有找到中断点，请使用 'loop' 命令从头开始")
            sys.exit(1)

        if runner.project_info.selected_option:
            runner.option_index = runner.project_info.selected_option
        if runner.project_info.ref_works:
            runner.ref_works = runner.project_info.ref_works

        chapter_counts = runner.project_info.chapter_counts or []

        # ====================================================================
        # 1) 规划层/世界观/创意/主轴（01-05b）断点：直接重跑该 step
        # ====================================================================
        non_writing_steps = {
            "01", "02", "03", "04", "05", "05a", "05b",
        }
        if last_step in non_writing_steps:
            step_name = STEP_NAMES.get(last_step, last_step)
            note(f"将重新执行：{last_step} {step_name}")
            if not confirm("确认继续?", default=True):
                warn("已取消")
                sys.exit(0)
            runner.run_step(last_step, runner.make_display_id(last_step))
            print_done(
                project=runner.project_name,
                extra=f"最后执行步骤 {last_step}",
            )
            sys.exit(0)

        # ====================================================================
        # 2) 开篇/循环段/幕末断点：算出游标，调共用流水线
        # ====================================================================
        cursor = _compute_resume_cursor(last_step, last_phase, current_round, chapter_counts)
        if cursor is None:
            error(f"无法识别的循环段断点 last_step={last_step!r} last_phase={last_phase!r}")
            sys.exit(1)
        opening_done, start_act, start_round_in_act, skip_act_end = cursor

        if not opening_done and last_step in {"06", "07", "08", "09"}:
            note(f"检测到开篇中断 步骤 {last_step}，将续跑开篇 06-10")
        elif not opening_done and last_step == "18" and last_phase == "post_05b":
            note("检测到 18 (post_05b) 断点：规划层已完成，开篇 06-10 尚未开始")
        else:
            note(
                f"断点定位：第 {start_act} 幕内已完成 {start_round_in_act} 轮"
                + (" · 本幕 17/18 已完成" if skip_act_end else "")
            )
        if not confirm("确认继续?", default=True):
            warn("已取消")
            sys.exit(0)

        # runner.round 对齐：开篇未做 → 2；循环段中 → current_round
        runner.round = 2 if not opening_done else current_round
        runner.project_info.update(current_round=1 if not opening_done else current_round)

        _run_writing_pipeline(
            runner,
            opening_done=opening_done,
            start_act=start_act,
            start_round_in_act=start_round_in_act,
            skip_act_end=skip_act_end,
        )

        print_done(
            project=runner.project_name,
            extra=f"创作轮次 R{runner.round - 1}",
        )

    else:
        error(f"未知命令：{command}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# helper：创意方案预览
# ---------------------------------------------------------------------------
# 标题格式：`# 创意方案：<name>`，冒号兼容全/半角
_CREATIVE_TITLE_RE = re.compile(r"^#\s*创意方案[：:]\s*(.+?)\s*$", re.MULTILINE)
# 开篇段定位：`## 开篇设想` 段头
_CREATIVE_OPENING_HEAD = re.compile(r"##\s*开篇设想\s*\n")
# 段尾边界：下一个二级标题（不撞空段，整段保留）
_CREATIVE_OPENING_END = re.compile(r"\n##\s")


def _extract_creative_meta(text: str) -> tuple[str, str]:
    """从单个创意方案 Markdown 抽出 (方案名, 完整开篇设想)。

    取 `## 开篇设想` 之后到下一个 `##` 二级标题之间的全部内容（不再被
    空段截断），完整呈现整段开篇设想；段落内的换行交给 rich Panel 在
    宽度内自动折行。任一字段抽不到时返回空串，由 UI 层兜底为占位文字。
    """
    title_match = _CREATIVE_TITLE_RE.search(text)
    title = title_match.group(1).strip() if title_match else ""

    head_match = _CREATIVE_OPENING_HEAD.search(text)
    if not head_match:
        return title, ""
    after = text[head_match.end():]
    end_match = _CREATIVE_OPENING_END.search(after)
    opening = after if not end_match else after[:end_match.start()]
    return title, opening.strip()


def _read_creative_card(path: Path) -> tuple[str, str]:
    """读单个 `创意方案_{n}.md`，返回 (方案名, 开篇缩略)。

    缺失 / 编码异常时返回空串，让 UI 显示占位而不是抛错。
    """
    if not path.exists():
        return "", ""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "", ""
    return _extract_creative_meta(text)


def select_creative(runner, n: int) -> int:
    """创意方案选择。

    先把 `00_baseline/创意方案_{1..n}.md` 的方案名 + 开篇设想渲染成一摞
    预览卡片（`ui.print_creative_cards`），再调用 `select` 拿编号。
    """
    baseline_dir = runner.path_resolver.baseline_dir
    items = []
    for i in range(1, n + 1):
        path = Path(baseline_dir) / f"创意方案_{i}.md"
        title, opening = _read_creative_card(path)
        items.append((i, title, opening))
    print_creative_cards(items)
    options = [f"方案 {i+1}" for i in range(n)]
    return select("选择一个创意方案", options, default=0) + 1


if __name__ == "__main__":
    main()
