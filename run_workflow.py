# -*- coding: utf-8 -*-
"""
小说生成自动工作流运行器 v1.2
模块化架构：cli.py（交互） + workflow_runner.py（执行） + ui.py（视觉）。

所有可见输出都委托给 ui 模块；本文件只保留流程编排。
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import cli as cli_module
from i18n import t
from ui import (
    C, I,
    blank, confirm, dim, error, info, init, line, note, press_enter,
    print_banner, print_creative_cards, print_done, print_header, print_kv,
    print_panel, print_section, prompt, select, success, warn,
)
from cli import (
    ask_genre, ask_novel_size, ask_project_name, ask_user_description, size_to_word_count,
)
from workflow_runner import STEP_NAMES, WorkflowRunner, step_name


# ---------------------------------------------------------------------------
# 顶部用法
# ---------------------------------------------------------------------------
def _print_usage() -> None:
    init()
    print_banner("woke_novel", subtitle=t("usage.subtitle"))
    print_kv([
        ("single <step>",         t("usage.single")),
        ("session <block> <...>", t("usage.session")),
        ("init",                  t("usage.init")),
        ("loop",                  t("usage.loop")),
        ("continue",              t("usage.continue")),
    ], key_color=C.ACCENT, value_color=C.MUTED)


# ---------------------------------------------------------------------------
# 统一工作流执行器：loop 和 continue 都从执行单元游标进入
# ---------------------------------------------------------------------------

OPENING_STEPS = ["06", "07", "08", "09", "10"]
ROUND_STEPS = ["11", "12", "13", "14", "15"]


@dataclass(frozen=True)
class WorkflowCursor:
    kind: str
    step: str = None
    option_index: int = None
    act_num: int = None
    round_num: int = None
    phase: str = None


def _step_cursor(step: str, option_index: int = None, act_num: int = None,
                 round_num: int = None, phase: str = None) -> WorkflowCursor:
    return WorkflowCursor("step", step, option_index, act_num, round_num, phase)


def _loop_count_for_act(act_num: int, chapter_counts: list[int]) -> int:
    if act_num < 1 or act_num > len(chapter_counts):
        return 0
    count = chapter_counts[act_num - 1]
    return max(0, count - 1) if act_num == 1 else max(0, count)


def _first_round_for_act(act_num: int, chapter_counts: list[int]) -> int:
    return 2 + sum(_loop_count_for_act(i, chapter_counts) for i in range(1, act_num))


def _locate_round(round_num: int, chapter_counts: list[int]) -> tuple[int, int] | None:
    if round_num < 2:
        return (1, 0) if chapter_counts else None
    offset = round_num - 2
    seen = 0
    for act_num in range(1, len(chapter_counts) + 1):
        loop_count = _loop_count_for_act(act_num, chapter_counts)
        if offset < seen + loop_count:
            return act_num, offset - seen
        seen += loop_count
    return None


def _next_after_round(round_num: int, act_num: int, chapter_counts: list[int]) -> WorkflowCursor:
    located = _locate_round(round_num, chapter_counts)
    loop_idx = located[1] if located else 0
    if loop_idx + 1 < _loop_count_for_act(act_num, chapter_counts):
        return _step_cursor("11", act_num=act_num, round_num=round_num + 1)
    return _step_cursor("17", act_num=act_num)


def _next_after_act_end(act_num: int, chapter_counts: list[int]) -> WorkflowCursor:
    next_act = act_num + 1
    if next_act <= len(chapter_counts):
        return _step_cursor("11", act_num=next_act, round_num=_first_round_for_act(next_act, chapter_counts))
    return WorkflowCursor("done")


def _infer_next_05b_act(runner) -> int | None:
    act_count = runner.project_info.act_count
    if not act_count:
        return None
    baseline_dir = runner.path_resolver.baseline_dir
    for act_num in range(1, act_count + 1):
        if not (Path(baseline_dir) / runner.skeleton_file_name(act_num)).exists():
            return act_num
    return act_count + 1


def compute_resume_cursor(runner, option_count: int) -> WorkflowCursor | None:
    info_obj = runner.project_info
    last_step = info_obj.last_step
    if last_step is None:
        return None

    chapter_counts = info_obj.chapter_counts or []
    last_phase = info_obj.last_step_phase
    last_round = info_obj.last_step_round or info_obj.current_round
    last_act = info_obj.last_step_act

    if last_step == "01":
        option_index = info_obj.last_step_option_index
        if option_index and option_index < option_count:
            return _step_cursor("01", option_index=option_index + 1)
        return WorkflowCursor("choose_creative")
    if last_step == "02":
        return WorkflowCursor("finalize_creative")
    if last_step == "03":
        return _step_cursor("04")
    if last_step == "04":
        return _step_cursor("05")
    if last_step == "05":
        return _step_cursor("05a")
    if last_step == "05a":
        return WorkflowCursor("extract_act_count")
    if last_step == "05b":
        act_count = info_obj.act_count
        if last_act is None:
            next_act = _infer_next_05b_act(runner)
        else:
            next_act = last_act + 1
        if act_count and next_act and next_act <= act_count:
            return _step_cursor("05b", act_num=next_act)
        return WorkflowCursor("extract_chapter_counts")
    if last_step == "18":
        if last_phase == "post_05b" or (last_phase is None and not last_act):
            return _step_cursor("06", act_num=1, round_num=1)
        if last_phase == "post_17" or last_act:
            return _next_after_act_end(last_act or 1, chapter_counts)
        return None
    if last_step in OPENING_STEPS:
        idx = OPENING_STEPS.index(last_step)
        if idx + 1 < len(OPENING_STEPS):
            return _step_cursor(OPENING_STEPS[idx + 1], act_num=1, round_num=1)
        return WorkflowCursor("create_story_summary", round_num=1)
    if last_step in ROUND_STEPS:
        if last_act is None:
            located = _locate_round(last_round, chapter_counts)
            last_act = located[0] if located else 1
        idx = ROUND_STEPS.index(last_step)
        if idx + 1 < len(ROUND_STEPS):
            return _step_cursor(ROUND_STEPS[idx + 1], act_num=last_act, round_num=last_round)
        return WorkflowCursor("append_story_summary", act_num=last_act, round_num=last_round)
    if last_step == "16":
        if last_act is None:
            located = _locate_round(last_round, chapter_counts)
            last_act = located[0] if located else 1
        return WorkflowCursor("sync_summary", act_num=last_act, round_num=last_round)
    if last_step == "17":
        return _step_cursor("18", act_num=last_act or 1, phase="post_17")
    return None


class WorkflowExecutor:
    def __init__(self, runner, cursor: WorkflowCursor = None):
        self.runner = runner
        self.cursor = cursor
        self.started = cursor is None
        self.completed = False

    def _matches(self, unit: WorkflowCursor) -> bool:
        if self.cursor is None:
            return True
        return unit == self.cursor

    def should_run(self, unit: WorkflowCursor) -> bool:
        if self.completed:
            return False
        if not self.started:
            self.started = self._matches(unit)
        return self.started

    def require_started(self) -> None:
        if not self.started and not self.completed:
            error(t("workflow.cursor_not_found", cursor=self.cursor))
            sys.exit(1)

    def run_step(self, step: str, display_id: str, option_index: int = None,
                 user_description: str = "", act_num: int = None, round_num: int = None,
                 phase: str = None) -> bool:
        unit = _step_cursor(step, option_index=option_index, act_num=act_num,
                            round_num=round_num, phase=phase)
        if not self.should_run(unit):
            return True
        if round_num is not None:
            self.runner.round = round_num
        return self.runner.run_step(
            step,
            display_id,
            option_index=option_index,
            user_description=user_description,
            act_num=act_num,
            phase=phase,
        )

    def run_unit(self, unit: WorkflowCursor, action) -> bool:
        if not self.should_run(unit):
            return True
        return action()

    def finish_if_target_done(self, unit: WorkflowCursor) -> bool:
        if not self.should_run(unit):
            return False
        self.completed = True
        return True


def _finalize_creative_selection(runner, chosen: int, novel_name: str = None) -> None:
    if novel_name is None:
        novel_name = runner.extract_novel_name_from_creative(chosen)
    if novel_name:
        success(t("workflow.extracted_novel_name", name=novel_name))
        runner.rename_project(novel_name)

    runner.option_index = chosen

    ref_works = runner.extract_ref_works_from_creative(chosen)
    if ref_works:
        note(t("workflow.ref_works", works=ref_works))
        runner.ref_works = ref_works

    runner.project_info.select_option(
        option_num=chosen, novel_name=novel_name, ref_works=ref_works,
    )


def _run_or_exit(ok: bool, message: str) -> None:
    if not ok:
        error(message)
        sys.exit(1)


def run_workflow_from_cursor(runner, cursor: WorkflowCursor = None, option_count: int = 3,
                             user_description: str = "") -> None:
    executor = WorkflowExecutor(runner, cursor)
    runner.project_info.update(option_count=option_count)
    creative_display_id = runner.make_display_id("creative_option")
    act_display_id = runner.make_display_id("arc")

    print_section(t("workflow.session_creative"), color=C.PRIMARY)
    for option_index in range(1, option_count + 1):
        if option_index > 1 and executor.started:
            line(color=C.DIM)
        if executor.started or executor._matches(_step_cursor("01", option_index=option_index)):
            note(t("workflow.generate_option", index=option_index, total=option_count))
        _run_or_exit(
            executor.run_step(
                "01", creative_display_id,
                option_index=option_index, user_description=user_description,
            ),
            t("workflow.creative_generation_failed"),
        )

    chosen = runner.project_info.selected_option

    def choose_creative() -> bool:
        nonlocal chosen
        chosen = select_creative(runner, option_count)
        success(t("workflow.creative_selected", index=chosen))
        runner.option_index = chosen
        return True

    _run_or_exit(executor.run_unit(WorkflowCursor("choose_creative"), choose_creative), t("workflow.creative_selection_failed"))
    chosen = chosen or runner.project_info.selected_option or 1

    _run_or_exit(
        executor.run_step("02", creative_display_id, option_index=chosen),
        t("workflow.creative_supplement_failed"),
    )
    _run_or_exit(
        executor.run_unit(WorkflowCursor("finalize_creative"), lambda: (_finalize_creative_selection(runner, chosen) or True)),
        t("workflow.creative_finalize_failed"),
    )

    print_section(t("workflow.session_world"), color=C.PRIMARY)
    for step in ["03", "04"]:
        _run_or_exit(executor.run_step(step, runner.make_display_id("world")), t("workflow.step_failed", step=step))

    print_section(t("workflow.session_axis"), color=C.PRIMARY)
    for step in ["05", "05a"]:
        _run_or_exit(executor.run_step(step, act_display_id), t("workflow.step_failed", step=step))

    def extract_act_count() -> bool:
        act_count = runner.extract_act_count_from_macro_model()
        if not act_count:
            warn(t("workflow.no_act_count"))
            return True
        runner.project_info.update(act_count=act_count)
        success(t("workflow.extracted_act_count", count=act_count))
        return True

    _run_or_exit(executor.run_unit(WorkflowCursor("extract_act_count"), extract_act_count), t("workflow.extract_act_failed"))

    act_count = runner.project_info.act_count or 0
    if act_count:
        print_section(t("workflow.step_05b_loop", count=act_count), color=C.PRIMARY)
    for act_num in range(1, act_count + 1):
        if act_num > 1 and executor.started:
            line(color=C.DIM)
        if executor.started or executor._matches(_step_cursor("05b", act_num=act_num)):
            note(t("workflow.act_progress", act=act_num, total=act_count))
        _run_or_exit(
            executor.run_step(
                "05b", act_display_id,
                user_description=f"幕次{act_num}", act_num=act_num,
            ),
            t("workflow.step_05b_failed", act=act_num),
        )

    def extract_chapter_counts() -> bool:
        act_count_inner = runner.project_info.act_count or 0
        if not act_count_inner:
            return True
        chapter_counts = runner.extract_all_chapter_counts(act_count_inner)
        total_chapters = sum(chapter_counts)
        success(t("workflow.chapter_counts", counts=chapter_counts, total=total_chapters))
        runner.project_info.update(chapter_counts=chapter_counts, total_chapters=total_chapters)
        return True

    _run_or_exit(
        executor.run_unit(WorkflowCursor("extract_chapter_counts"), extract_chapter_counts),
        t("workflow.extract_chapters_failed"),
    )

    print_section(t("workflow.step_18_post_05b"), color=C.ACCENT)
    if not executor.run_step("18", act_display_id, phase="post_05b"):
        warn(t("workflow.step_18_post_05b_failed"))

    print_section(t("workflow.session_opening"), color=C.PRIMARY)
    choice = _confirm_open_session()
    if choice == "n":
        info(t("workflow.paused"))
        sys.exit(0)
    if choice == "q":
        info(t("workflow.user_quit"))
        sys.exit(0)

    opening_display_id = runner.make_display_id("opening")
    for step in OPENING_STEPS:
        _run_or_exit(
            executor.run_step(step, opening_display_id, act_num=1, round_num=1),
            t("workflow.step_failed", step=step),
        )

    _run_or_exit(
        executor.run_unit(
            WorkflowCursor("create_story_summary", round_num=1),
            lambda: runner.extract_and_create_story_summary(1),
        ),
        t("workflow.opening_summary_failed"),
    )

    chapter_counts = runner.project_info.chapter_counts or []
    total_chapters = runner.project_info.total_chapters or sum(chapter_counts)
    success(t("workflow.chapter_counts", counts=chapter_counts, total=total_chapters))

    for act_num in range(1, len(chapter_counts) + 1):
        loop_count = _loop_count_for_act(act_num, chapter_counts)
        if loop_count <= 0:
            warn(t("workflow.act_zero_rounds", act=act_num))
            continue

        print_section(t("workflow.act_loop", act=act_num, count=loop_count), color=C.PRIMARY)
        first_round = _first_round_for_act(act_num, chapter_counts)
        for loop_idx in range(loop_count):
            round_num = first_round + loop_idx
            print_section(
                t("workflow.round_section", act=act_num, index=loop_idx + 1, total=loop_count, round=round_num),
                color=C.ACCENT,
            )
            session_name = runner.make_display_id(f"round_{round_num}")
            for step in ROUND_STEPS:
                _run_or_exit(
                    executor.run_step(step, session_name, act_num=act_num, round_num=round_num),
                    t("workflow.step_failed", step=step),
                )

            _run_or_exit(
                executor.run_unit(
                    WorkflowCursor("append_story_summary", act_num=act_num, round_num=round_num),
                    lambda round_num=round_num: runner.append_story_summary(round_num),
                ),
                t("workflow.append_summary_failed"),
            )

            _run_or_exit(
                executor.run_step("16", session_name, act_num=act_num, round_num=round_num),
                t("workflow.step_16_failed"),
            )

            def sync_round(round_num=round_num) -> bool:
                ok = runner.sync_summary_to_state(round_num)
                runner.project_info.update(current_round=round_num)
                runner.round = round_num + 1
                return ok

            _run_or_exit(
                executor.run_unit(
                    WorkflowCursor("sync_summary", act_num=act_num, round_num=round_num),
                    sync_round,
                ),
                t("workflow.sync_summary_failed"),
            )
            note(t("workflow.next_round"))

        print_section(t("workflow.step_17", act=act_num), color=C.PRIMARY)
        _run_or_exit(
            executor.run_step("17", runner.make_display_id(f"act_{act_num}"), act_num=act_num),
            t("workflow.step_17_failed"),
        )
        runner.sync_summary_to_state(_first_round_for_act(act_num, chapter_counts) + loop_count - 1)

        print_section(
            t("workflow.step_18_post_17", act=act_num),
            color=C.ACCENT,
        )
        if not executor.run_step(
            "18", runner.make_display_id(f"act_{act_num}"),
            phase="post_17", act_num=act_num,
        ):
            warn(t("workflow.step_18_post_17_failed"))

    if cursor and cursor.kind == "done" and executor.finish_if_target_done(WorkflowCursor("done")):
        success(t("workflow.already_done"))
    executor.require_started()


# ---------------------------------------------------------------------------
# 三方确认（开篇创作会话：y / n / q）
# ---------------------------------------------------------------------------
def _confirm_open_session() -> str:
    """开篇会话默认自动继续，不再停顿。

    历史上这里会停在 `y=继续 / n=暂停 / q=退出` 等待用户输入；现在改成
    直接放行并打印一行提示，调用方后续的 n / q 分支成为死代码（保留无害）。
    如需恢复交互式确认，把函数体换回原 `prompt(...)` 循环即可。
    """
    info(t("workflow.auto_continue_opening"))
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
        parser.add_argument("step", help=t("argparse.step_help"))
        parser.add_argument("-g", "--genre", default="都市")
        parser.add_argument("-p", "--project-name", default="test_project")
        parser.add_argument("--dry", action="store_true", help=t("argparse.dry_help"))
        parser.add_argument("--provider", choices=["claude", "codex"], default="claude",
                            help=t("argparse.provider_help"))
        parser.add_argument("--language", choices=["zh", "en"], default="zh",
                            help=t("argparse.language_help"))
        parser.add_argument("--max-retries", type=int, default=3,
                            help=t("argparse.retry_help"))
        args = parser.parse_args(sys.argv[2:])

        cli_module.set_language(args.language)
        runner = WorkflowRunner(args.project_name, args.genre, dry_run=args.dry,
                                max_retries=args.max_retries, provider=args.provider,
                                language=args.language)
        display_id = runner.make_display_id(args.step)
        ok = runner.run_step(args.step, display_id)
        sys.exit(0 if ok else 1)

    elif command == "session":
        if len(sys.argv) < 4:
            error(t("argparse.session_usage"))
            sys.exit(1)

        block_name = sys.argv[2]
        steps_str = sys.argv[3]
        steps = steps_str.split(",")

        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("-g", "--genre", default="都市")
        parser.add_argument("-p", "--project-name", default="test_project")
        parser.add_argument("--dry", action="store_true")
        parser.add_argument("--provider", choices=["claude", "codex"], default="claude",
                            help=t("argparse.provider_help"))
        parser.add_argument("--language", choices=["zh", "en"], default="zh",
                            help=t("argparse.language_help"))
        parser.add_argument("--max-retries", type=int, default=3,
                            help=t("argparse.retry_help"))
        args, unknown = parser.parse_known_args(sys.argv[4:])

        cli_module.set_language(args.language)
        runner = WorkflowRunner(args.project_name, args.genre, dry_run=args.dry,
                                max_retries=args.max_retries, provider=args.provider,
                                language=args.language)
        ok = runner.run_session_block(block_name, steps)
        sys.exit(0 if ok else 1)

    elif command == "init":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--genre", default=None, help=t("argparse.genre_help"))
        parser.add_argument("--novel-size", default=None,
                            help=t("argparse.novel_size_help"))
        parser.add_argument("--language", choices=["zh", "en"], default="zh",
                            help=t("argparse.language_help"))
        args = parser.parse_args(sys.argv[2:])

        cli_module.set_language(args.language)
        genre = args.genre or ask_genre()
        project_name = ask_project_name()
        novel_size = args.novel_size or ask_novel_size()
        target_word_count = size_to_word_count(novel_size)

        runner = WorkflowRunner(project_name, genre,
                                novel_size=novel_size, target_word_count=target_word_count,
                                language=args.language)
        print_panel(t("workflow.init_done"), "", color=C.SUCCESS, icon=I.OK)
        print_kv([
            (t("workflow.init_project"), runner.project_name),
            (t("workflow.init_genre"), runner.genre),
            (t("workflow.init_size"), t("full.config_size", size=novel_size, words=target_word_count // 10_000).split(None, 1)[-1]),
            (t("workflow.init_project_dir"), str(runner.path_resolver.project_root)),
        ])
        sys.exit(0)

    elif command == "loop":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry", action="store_true", help=t("argparse.dry_help"))
        parser.add_argument("--provider", choices=["claude", "codex"], default="claude",
                            help=t("argparse.provider_help"))
        parser.add_argument("--language", choices=["zh", "en"], default="zh",
                            help=t("argparse.language_help"))
        parser.add_argument("--option-count", type=int, default=3, help=t("argparse.option_count_help"))
        parser.add_argument("--genre", default=None, help=t("argparse.genre_help"))
        parser.add_argument("--project-name", default=None, help=t("argparse.project_name_help"))
        parser.add_argument("--max-retries", type=int, default=3,
                            help=t("argparse.retry_help"))
        parser.add_argument("--user-description", default=None,
                            help=t("argparse.user_description_help"))
        parser.add_argument("--novel-size", default=None,
                            help=t("argparse.novel_size_help"))
        args = parser.parse_args(sys.argv[2:])

        cli_module.set_language(args.language)
        genre = args.genre or ask_genre()
        project_name = args.project_name or ask_project_name()
        user_description = args.user_description or ask_user_description()
        novel_size = args.novel_size or ask_novel_size()
        target_word_count = size_to_word_count(novel_size)

        runner = WorkflowRunner(project_name, genre, dry_run=args.dry,
                                max_retries=args.max_retries,
                                novel_size=novel_size, target_word_count=target_word_count,
                                provider=args.provider, language=args.language)

        print_banner(
            t("workflow.banner_project", project=runner.project_name),
            subtitle=t("workflow.banner_subtitle", genre=runner.genre, size=novel_size,
                       words=target_word_count // 10_000, provider=runner.provider,
                       path=runner.path_resolver.project_root),
        )

        run_workflow_from_cursor(
            runner,
            option_count=args.option_count,
            user_description=user_description,
        )

        print_done(
            project=runner.project_name,
            extra=t("workflow.done_extra", round=runner.round - 1),
        )

    elif command == "continue":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry", action="store_true", help=t("argparse.dry_help"))
        parser.add_argument("--provider", choices=["claude", "codex"], default="claude",
                            help=t("argparse.provider_help"))
        parser.add_argument("--language", choices=["zh", "en"], default="zh",
                            help=t("argparse.language_help"))
        parser.add_argument("--project-name", default=None, help=t("argparse.project_name_help"))
        parser.add_argument("--max-retries", type=int, default=3,
                            help=t("argparse.retry_help"))
        args = parser.parse_args(sys.argv[2:])

        cli_module.set_language(args.language)
        project_name = args.project_name or ask_project_name()
        runner = WorkflowRunner(project_name, dry_run=args.dry,
                                max_retries=args.max_retries, provider=args.provider,
                                language=args.language)

        last_step = runner.project_info.last_step
        current_round = runner.project_info.current_round
        last_phase = runner.project_info.last_step_phase

        print_banner(
            t("workflow.continue_title", project=runner.project_name),
            subtitle=t("workflow.continue_subtitle", round=current_round, provider=runner.provider,
                       step=last_step or t("common.none")),
        )

        if last_step is None:
            error(t("workflow.no_checkpoint"))
            sys.exit(1)

        if runner.project_info.selected_option:
            runner.option_index = runner.project_info.selected_option
        if runner.project_info.ref_works:
            runner.ref_works = runner.project_info.ref_works

        option_count = runner.project_info.get("option_count", 3)
        cursor = compute_resume_cursor(runner, option_count=option_count)
        if cursor is None:
            error(t("workflow.unknown_cursor", last_step=last_step, last_phase=last_phase))
            sys.exit(1)

        if cursor.kind == "done":
            note(t("workflow.cursor_done"))
        elif cursor.kind == "step":
            detail = t("workflow.cursor_step", step=cursor.step)
            if cursor.act_num:
                detail += t("workflow.cursor_act", act=cursor.act_num)
            if cursor.round_num:
                detail += f" · R{cursor.round_num}"
            if cursor.phase:
                detail += f" · {cursor.phase}"
            note(t("workflow.cursor_resume", detail=detail))
        else:
            note(t("workflow.cursor_kind_resume", kind=cursor.kind))
        if not args.dry and not confirm(t("common.confirm_continue"), default=True):
            warn(t("common.cancelled"))
            sys.exit(0)

        run_workflow_from_cursor(runner, cursor=cursor, option_count=option_count)

        print_done(
            project=runner.project_name,
            extra=t("workflow.done_extra", round=f"R{runner.round - 1}"),
        )

    else:
        error(t("workflow.unknown_command", command=command))
        sys.exit(1)


# ---------------------------------------------------------------------------
# helper：创意方案预览
# ---------------------------------------------------------------------------
# 标题格式：`# 创意方案：<name>`，冒号兼容全/半角
_CREATIVE_TITLE_RE = re.compile(r"^#\s*创意方案[：:]\s*(.+?)\s*$", re.MULTILINE)
_CREATIVE_TITLE_RE_EN = re.compile(r"^#\s*Creative\s+Proposal[：:]\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
# 开篇段定位：`## 开篇设想` 段头
_CREATIVE_OPENING_HEAD = re.compile(r"##\s*开篇设想\s*\n")
_CREATIVE_OPENING_HEAD_EN = re.compile(r"##\s*Opening\s+Concept\s*\n", re.IGNORECASE)
# 段尾边界：下一个二级标题（不撞空段，整段保留）
_CREATIVE_OPENING_END = re.compile(r"\n##\s")


def _extract_creative_meta(text: str) -> tuple[str, str]:
    """从单个创意方案 Markdown 抽出 (方案名, 完整开篇设想)。

    取 `## 开篇设想` 之后到下一个 `##` 二级标题之间的全部内容（不再被
    空段截断），完整呈现整段开篇设想；段落内的换行交给 rich Panel 在
    宽度内自动折行。任一字段抽不到时返回空串，由 UI 层兜底为占位文字。
    """
    title_match = _CREATIVE_TITLE_RE.search(text) or _CREATIVE_TITLE_RE_EN.search(text)
    title = title_match.group(1).strip() if title_match else ""

    head_match = _CREATIVE_OPENING_HEAD.search(text) or _CREATIVE_OPENING_HEAD_EN.search(text)
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
        name = f"Creative_Proposal_{i}.md" if runner.language == "en" else f"创意方案_{i}.md"
        path = Path(baseline_dir) / name
        title, opening = _read_creative_card(path)
        items.append((i, title, opening))
    print_creative_cards(items)
    options = [t("single.creative_option", index=i + 1) for i in range(n)]
    return select(t("single.choose_creative"), options, default=0) + 1


if __name__ == "__main__":
    main()
