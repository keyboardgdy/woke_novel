#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
woke_novel 主菜单（单步 / 完整 / 继续 / 步骤列表）。

所有显示都委托给 ui 模块；本文件只负责交互编排。
"""

import shutil
import subprocess
import sys
import json
import posixpath
import re
import zipfile
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote
import xml.etree.ElementTree as ET

from app_paths import runtime_path

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
    select_project, select_projects, success, warn, press_enter,
)
from workflow_runner import STEP_NAMES, STEP_FILES, WorkflowRunner, step_name
import cli as cli_module
import i18n as i18n_module
from i18n import t

# 模块级缓存：ask_user_description 拿到的值，留给 full_loop_mode 透传给子进程。
# 一次菜单会话内只可能问一次，所以单变量够用。
_pending_user_description: Optional[str] = None
_pending_novel_size: Optional[str] = None
_current_provider: str = "mixed"
_current_language: str = "zh"
# 默认作家模式（停顿）。用户在设置里可切换为全自动模式（--no-pause）。
_current_pause_mode: bool = True
CONFIG_FILE = runtime_path(".menu_config.json")
SUPPORTED_PROVIDERS = ("claude", "codex", "mixed")
SUPPORTED_LANGUAGES = ("zh", "en")


def _normalize_provider(provider: Optional[str]) -> str:
    value = (provider or "mixed").strip().lower()
    return value if value in SUPPORTED_PROVIDERS else "mixed"


def _normalize_language(language: Optional[str]) -> str:
    value = (language or "zh").strip().lower()
    return value if value in SUPPORTED_LANGUAGES else "zh"


def _normalize_pause_mode(value: Optional[Any]) -> bool:
    """统一 pause_mode 序列化：truthy 都视为 True（作家模式）。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", "auto", "full-auto"}
    return bool(value)


def _load_menu_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        warn(t("config.load_failed", error=e))
        return {}
    return data if isinstance(data, dict) else {}


def _save_menu_config(config: Dict[str, Any]) -> bool:
    try:
        CONFIG_FILE.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return True
    except Exception as e:
        warn(t("config.save_failed", error=e))
        return False


def _load_configured_provider() -> str:
    return _normalize_provider(_load_menu_config().get("provider"))


def _save_configured_provider(provider: str) -> bool:
    config = _load_menu_config()
    config["provider"] = _normalize_provider(provider)
    return _save_menu_config(config)


def _load_configured_language() -> str:
    return _normalize_language(_load_menu_config().get("language"))


def _save_configured_language(language: str) -> bool:
    config = _load_menu_config()
    config["language"] = _normalize_language(language)
    return _save_menu_config(config)


def _has_configured_provider(config: Dict[str, Any]) -> bool:
    value = config.get("provider")
    return isinstance(value, str) and value.strip().lower() in SUPPORTED_PROVIDERS


def _has_configured_language(config: Dict[str, Any]) -> bool:
    value = config.get("language")
    return isinstance(value, str) and value.strip().lower() in SUPPORTED_LANGUAGES


def _has_configured_pause_mode(config: Dict[str, Any]) -> bool:
    return isinstance(config.get("pause_mode"), bool)


def _load_configured_pause_mode() -> bool:
    return _normalize_pause_mode(_load_menu_config().get("pause_mode"))


def _save_configured_pause_mode(pause_mode: bool) -> bool:
    config = _load_menu_config()
    config["pause_mode"] = bool(pause_mode)
    return _save_menu_config(config)


def _provider_label(provider: Optional[str] = None) -> str:
    value = (provider or _current_provider or "mixed").lower()
    if value == "claude":
        return "Claude CLI"
    if value == "codex":
        return "Codex CLI"
    return "混合架构" if _current_language == "zh" else "Mixed"


def _command_status(command: str) -> Dict[str, Any]:
    """Return PATH/version status for a model CLI command."""
    path = shutil.which(command)
    if not path:
        return {"available": False, "path": None, "version": None, "message": f"{command} not found in PATH"}

    try:
        if path.lower().endswith((".cmd", ".bat")):
            result = subprocess.run(
                f'"{path}" --version',
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                shell=True,
            )
        else:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
        output = (result.stdout or result.stderr).strip()
        version = output.splitlines()[0] if output else None
    except Exception as exc:
        return {"available": True, "path": path, "version": None, "message": str(exc)}

    return {"available": True, "path": path, "version": version, "message": None}


def _provider_install_help(provider: str) -> str:
    if provider == "codex":
        if _current_language == "en":
            return (
                "Install Codex CLI:\n"
                "  npm install -g @openai/codex\n"
                "  codex --version\n"
                "  codex\n\n"
                "If your installation method differs, follow the official OpenAI Codex CLI setup guide, then make sure `codex` is available in PATH."
            )
        return (
            "安装 Codex CLI：\n"
            "  npm install -g @openai/codex\n"
            "  codex --version\n"
            "  codex\n\n"
            "如果你使用其他安装方式，请按 OpenAI Codex CLI 官方说明配置，并确认 `codex` 已加入 PATH。"
        )

    if _current_language == "en":
        return (
            "Install Claude Code CLI:\n"
            "  npm install -g @anthropic-ai/claude-code\n"
            "  claude --version\n"
            "  claude\n\n"
            "Official setup guide: https://docs.anthropic.com/en/docs/claude-code/setup"
        )
    return (
        "安装 Claude Code CLI：\n"
        "  npm install -g @anthropic-ai/claude-code\n"
        "  claude --version\n"
        "  claude\n\n"
        "官方安装说明：https://docs.anthropic.com/en/docs/claude-code/setup"
    )


def _show_model_cli_environment_check(selected_provider: Optional[str] = None) -> bool:
    """Show startup environment status and install guidance for Claude/Codex CLI."""
    selected = _normalize_provider(selected_provider or _current_provider)
    statuses = {
        "claude": _command_status("claude"),
        "codex": _command_status("codex"),
    }

    def status_line(command: str) -> str:
        status = statuses[command]
        label = "Claude CLI" if command == "claude" else "Codex CLI"
        if status["available"]:
            detail = status["version"] or status["path"] or "available"
            return f"{label}: OK - {detail}"
        return f"{label}: MISSING - {status['message']}"

    selected_status = statuses[selected]
    any_available = any(status["available"] for status in statuses.values())
    if _current_language == "en":
        title = "Environment Check"
        selected_name = _provider_label(selected)
        summary = (
            f"Selected backend: {selected_name}\n"
            f"{status_line('claude')}\n"
            f"{status_line('codex')}"
        )
        if selected_status["available"]:
            body = summary + "\n\nThe selected backend is ready."
            color = C.SUCCESS
        elif any_available:
            body = (
                summary
                + f"\n\nThe selected backend is not installed or not in PATH. You can switch to an installed backend in Settings, or install {selected_name}:\n\n"
                + _provider_install_help(selected)
            )
            color = C.WARNING
        else:
            body = (
                summary
                + "\n\nNo supported model CLI was found. Install at least one backend before running real workflows:\n\n"
                + _provider_install_help("claude")
                + "\n\n"
                + _provider_install_help("codex")
            )
            color = C.ERROR
    else:
        title = "环境检查"
        selected_name = _provider_label(selected)
        summary = (
            f"当前选择：{selected_name}\n"
            f"{status_line('claude')}\n"
            f"{status_line('codex')}"
        )
        if selected_status["available"]:
            body = summary + "\n\n已选后端可用。"
            color = C.SUCCESS
        elif any_available:
            body = (
                summary
                + f"\n\n已选后端未安装或未加入 PATH。你可以在系统设置里切换到已安装后端，或安装 {selected_name}：\n\n"
                + _provider_install_help(selected)
            )
            color = C.WARNING
        else:
            body = (
                summary
                + "\n\n未检测到可用的模型 CLI。真实运行工作流前，请至少安装 Claude CLI 或 Codex CLI 其中一种：\n\n"
                + _provider_install_help("claude")
                + "\n\n"
                + _provider_install_help("codex")
            )
            color = C.ERROR

    print_panel(title, body, color=color, icon=I.WARN if color != C.SUCCESS else I.OK)
    return bool(selected_status["available"])


def _language_label(language: Optional[str] = None) -> str:
    value = _normalize_language(language or _current_language)
    return t("language.en_label") if value == "en" else t("language.zh_label")


def _pause_mode_label(pause_mode: Optional[bool] = None) -> str:
    value = _current_pause_mode if pause_mode is None else bool(pause_mode)
    return t("pause_mode.author") if value else t("pause_mode.full_auto")


def _main_option(icon: str, text: str) -> str:
    return f"{icon}  {text}"


def choose_language(default_language: Optional[str] = None) -> str:
    """选择提示词和题材预设语言。"""
    clear()
    print_banner(t("app.title"), subtitle=t("language.subtitle"))
    default_value = _normalize_language(default_language)
    idx = select(
        t("language.prompt"),
        [
            t("language.zh_option"),
            t("language.en_option"),
        ],
        default=1 if default_value == "en" else 0,
        allow_escape=True,
    )
    if idx is None:
        return default_value
    return "en" if idx == 1 else "zh"


def choose_provider(default_provider: Optional[str] = None) -> str:
    """选择外部 CLI 后端。"""
    clear()
    print_banner(t("app.title"), subtitle=t("provider.subtitle"))
    default_value = _normalize_provider(default_provider)
    idx = select(
        t("provider.prompt"),
        [
            t("provider.claude_option"),
            t("provider.codex_option"),
            t("provider.mixed_option"),
        ],
        default={"claude": 0, "codex": 1, "mixed": 2}.get(default_value, 2),
        allow_escape=True,
    )
    if idx is None:
        return default_value
    return ("claude", "codex", "mixed")[idx]


def choose_pause_mode(default_pause_mode: Optional[bool] = None) -> bool:
    """选择运行模式：True=作家模式（停顿），False=全自动模式（跳过停顿）。"""
    clear()
    print_banner(t("app.title"), subtitle=t("settings.pause_mode_subtitle"))
    default_value = _current_pause_mode if default_pause_mode is None else bool(default_pause_mode)
    options = [
        t("pause_mode.author") + "  " + t("pause_mode.author_desc"),
        t("pause_mode.full_auto") + "  " + t("pause_mode.full_auto_desc"),
    ]
    idx = select(t("settings.pause_mode_prompt"), options, default=0 if default_value else 1, allow_escape=True)
    if idx is None:
        return default_value
    return idx == 0


# ---------------------------------------------------------------------------
# 项目发现 + 摘要
# ---------------------------------------------------------------------------
def _projects_root() -> Path:
    return runtime_path("projects")


def _logs_root() -> Path:
    return runtime_path("logs")


def _run_workflow_command(args: List[str]) -> None:
    if getattr(sys, "frozen", False):
        import run_workflow

        old_argv = sys.argv[:]
        try:
            sys.argv = ["run_workflow.py", *args]
            run_workflow.main()
        finally:
            sys.argv = old_argv
        return

    subprocess.run([sys.executable, "run_workflow.py", *args])


def _is_direct_child(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return path.parent.resolve() == parent.resolve()


def prompt_new_project_name(message: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    if message is None:
        message = t("project.new_name_prompt")
    current_message = message
    current_default = default
    while True:
        value = prompt(current_message, default=current_default, allow_escape=True)
        if value is None:
            return None
        project = value.strip()
        if not project:
            warn(t("project.name_empty"))
            current_message = t("project.name_retry")
            current_default = None
            continue
        if (_projects_root() / project).exists():
            warn(t("project.exists", project=project))
            current_message = t("project.name_retry")
            current_default = None
            continue
        return project


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
        progress = t("project.not_started")
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
        return [(t("delete.project"), project), (t("project.status"), t("project.no_info"))]
    data = info_obj.to_dict()
    return [
        (t("delete.project"), data.get("project_name", project)),
        (t("project.col_genre"), str(data.get("genre", "—"))),
        (t("project.novel_name"), str(data.get("novel_name") or t("project.unset"))),
        (t("project.option"), str(data.get("selected_option") or t("project.unselected"))),
        (t("project.reference"), str(data.get("ref_works") or t("common.none"))),
        (t("project.round"), f"R{data.get('current_round', 1)}"
                   + (t("common.total_chapters", count=data.get('total_chapters', '?')) if data.get('total_chapters') else "")),
        (t("project.last_step"), str(data.get("last_step") or t("common.none"))),
        (t("project.last_run"), _short_time(data.get("last_step_at"))),
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
    print_banner(t("project.select_title"), subtitle=t("project.select_subtitle"))

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
        info(t("project.none_create"))

    # 创建新项目
    print_section(t("project.create_section"), color=C.ACCENT)
    project = prompt_new_project_name()
    if project is None:
        return (None, None)
    genre = cli_module.ask_genre()
    user_description = cli_module.ask_user_description()
    novel_size = cli_module.ask_novel_size()

    from project_info import create_project_info
    create_project_info(project, genre, novel_size=novel_size,
                        target_word_count=cli_module.size_to_word_count(novel_size))
    WorkflowRunner(project, genre, novel_size=novel_size,
                   target_word_count=cli_module.size_to_word_count(novel_size),
                   provider=_current_provider,
                   language=_current_language)
    success(t("project.created", project=project))
    info(t("project.description", description=user_description))
    info(t("project.size", size=novel_size))

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
    print_banner(
        t("single.title"),
        subtitle=t(
            "single.subtitle",
            project=project,
            genre=genre,
            language=_language_label(),
            provider=_provider_label(),
        ),
    )
    print_subheader(t("single.project_info"), color=C.PRIMARY)
    print_kv(_project_kv(project))

    steps = [(step, step_name(step)) for step in STEP_NAMES]
    print_steps_table(steps, title=t("single.steps_title"))
    step = prompt(t("single.step_prompt"), default="01").strip()
    if not step or step not in STEP_NAMES:
        warn(t("single.invalid_step"))
        return

    dry_run = confirm(t("single.dry_run_prompt", provider=_provider_label()), default=False)
    option_count_raw = prompt(t("single.option_count_prompt"), default="3")
    option_count = int(option_count_raw) if option_count_raw.isdigit() else 3

    print_section(t("single.run_section", step=step, name=step_name(step)), color=C.PRIMARY)
    runner = WorkflowRunner(project, genre, dry_run=dry_run,
                            provider=_current_provider,
                            language=_current_language)

    if step == "01" and option_count > 1:
        for i in range(option_count):
            note(t("single.option_note", current=i + 1, total=option_count))
            if not runner.run_step("01", runner.make_display_id(f"creative_option_{i+1}"), option_index=i+1):
                error(t("single.option_failed", index=i + 1))
                press_enter()
                return
        chosen = select(
            t("single.choose_creative"),
            [t("single.creative_option", index=i + 1) for i in range(option_count)],
            default=0,
            allow_escape=True,
        )
        if chosen is None:
            return
        success(t("single.creative_chosen", index=chosen + 1))
        if not runner.run_step("02", runner.make_display_id(f"creative_option_{chosen+1}"), option_index=chosen+1):
            error(t("single.supplement_failed"))
    else:
        display_id = runner.make_display_id(step)
        runner.run_step(step, display_id)

    press_enter()


def full_loop_mode() -> None:
    """完整执行模式。"""
    clear()
    print_banner(t("full.title"), subtitle=t("full.subtitle"))

    project = prompt_new_project_name(t("full.project_prompt"), default="my_novel")
    if project is None:
        return
    genre = cli_module.ask_genre()
    user_description = cli_module.ask_user_description()
    novel_size = cli_module.ask_novel_size()
    target_word_count = cli_module.size_to_word_count(novel_size)
    option_count_raw = prompt(t("full.option_count_prompt"), default="3")
    option_count = int(option_count_raw) if option_count_raw.isdigit() else 3
    dry_run = confirm(t("full.dry_run_prompt", provider=_provider_label()), default=False)

    # 配置摘要
    body = "\n".join([
        t("full.config_project", project=project),
        t("full.config_genre", genre=genre),
        t("full.config_description", description=user_description),
        t("full.config_size", size=novel_size, words=cli_module.format_word_count(target_word_count)),
        t("full.config_options", count=option_count),
        t("full.config_language", language=_language_label()),
        t("full.config_provider", provider=_provider_label()),
        t("full.config_mode", mode=_pause_mode_label()),
        t("full.config_dry_run", value=t("common.yes") if dry_run else t("common.no")),
    ])
    print_panel(t("full.config_title"), body, color=C.ACCENT, icon=I.DIAMOND)

    if not confirm(t("common.confirm_start"), default=True):
        warn(t("common.cancelled"))
        return

    cmd = [
        "loop",
        "--project-name", project,
        "--genre", genre,
        "--option-count", str(option_count),
        "--user-description", user_description,
        "--novel-size", novel_size,
        "--provider", _current_provider,
        "--language", _current_language,
    ]
    if dry_run:
        cmd.append("--dry")
    if not _current_pause_mode:
        cmd.append("--no-pause")
    _run_workflow_command(cmd)
    press_enter()


def continue_mode() -> None:
    """继续执行模式。"""
    from project_info import get_project_info

    clear()
    print_banner(t("continue.title"), subtitle=t("continue.subtitle"))

    projects = list_existing_projects()
    if not projects:
        warn(t("continue.no_projects"))
        return

    idx = select_project(projects, allow_new=False)
    if idx is None:
        return
    project = idx
    info_obj = get_project_info(project)

    if not info_obj or not info_obj.last_step:
        error(t("continue.no_checkpoint"))
        press_enter()
        return

    print_subheader(t("continue.project_header", project=project), color=C.PRIMARY)
    print_kv([
        (t("continue.current_round"), str(info_obj.current_round)),
        (t("continue.last_step"), info_obj.last_step or t("common.none")),
        (t("continue.last_time"), _short_time(info_obj.last_step_at)),
    ])

    if not confirm(t("common.confirm_continue"), default=True):
        warn(t("common.cancelled"))
        return

    cmd = [
        "continue",
        "--project-name", project,
        "--provider", _current_provider,
        "--language", _current_language,
    ]
    if not _current_pause_mode:
        cmd.append("--no-pause")
    _run_workflow_command(cmd)
    press_enter()


# ---------------------------------------------------------------------------
# 删除项目
# ---------------------------------------------------------------------------
def delete_project_mode() -> None:
    """删除小说项目目录和对应日志目录。"""
    clear()
    print_banner(t("delete.title"), subtitle=t("delete.subtitle"), accent=C.ERROR)

    projects = list_existing_projects()
    if not projects:
        warn(t("delete.no_projects"))
        press_enter()
        return

    project_names = select_projects(projects)
    if not project_names:
        warn(t("common.cancelled"))
        press_enter()
        return

    entries: List[Tuple[str, Path, Path, List[Path]]] = []
    targets: List[Tuple[str, Path, Path]] = []
    for project_name in project_names:
        project_path = _projects_root() / project_name
        log_path = _logs_root() / project_name
        project_targets = [path for path in (project_path, log_path) if path.exists()]
        entries.append((project_name, project_path, log_path, project_targets))
        for path in project_targets:
            parent = _projects_root() if path == project_path else _logs_root()
            targets.append((project_name, path, parent))

    print_subheader(t("delete.pending_title"), color=C.ERROR)
    for project_name, project_path, log_path, _ in entries:
        print_kv([
            (t("delete.project"), project_name),
            (t("delete.project_dir"), str(project_path) if project_path.exists() else f"{project_path}{t('delete.missing_suffix')}"),
            (t("delete.log_dir"), str(log_path) if log_path.exists() else f"{log_path}{t('delete.missing_suffix')}"),
        ])
        blank()

    if not targets:
        warn(t("delete.no_targets"))
        press_enter()
        return

    for _, path, parent in targets:
        if not path.is_dir() or not _is_direct_child(path, parent):
            error(t("delete.reject_path", path=path))
            press_enter()
            return

    warn(t("delete.warning"))
    if not confirm(t("delete.confirm", count=len(project_names)), default=False):
        warn(t("common.cancelled"))
        press_enter()
        return

    typed = prompt(t("delete.type_confirm"), show_default=False)
    if typed != "DELETE":
        error(t("delete.confirm_mismatch"))
        press_enter()
        return

    for project_name, path, _ in targets:
        shutil.rmtree(path)
        success(t("delete.deleted", project=project_name, path=path))

    press_enter()


# ---------------------------------------------------------------------------
# 步骤列表
# ---------------------------------------------------------------------------
def view_steps_list() -> None:
    clear()
    print_banner(t("steps.title"), subtitle=t("steps.subtitle"))
    print_steps_table([(step, step_name(step)) for step in STEP_NAMES], title=t("steps.table_title"))
    print_kv([
        ("01-02",   t("steps.range_01_02")),
        ("03-04",   t("steps.range_03_04")),
        ("05+05a+05b", t("steps.range_05")),
        ("06-10",   t("steps.range_06_10")),
        ("11-16",   t("steps.range_11_16")),
        ("17",      t("steps.range_17")),
        ("18",      t("steps.range_18")),
    ], key_color=C.ACCENT)
    press_enter()


# ---------------------------------------------------------------------------
# 系统设置
# ---------------------------------------------------------------------------
def settings_mode() -> None:
    """系统设置：修改菜单会话使用的语言、外部 CLI 架构和运行模式。"""
    global _current_provider, _current_language, _current_pause_mode

    clear()
    print_banner(
        t("settings.title"),
        subtitle=t(
            "settings.subtitle",
            language=_language_label(),
            provider=_provider_label(),
            mode=_pause_mode_label(),
        ),
    )
    print_kv([
        (t("settings.current_language"), _language_label()),
        (t("settings.current_provider"), _provider_label()),
        (t("settings.current_mode"), _pause_mode_label()),
        (t("settings.config_file"), str(CONFIG_FILE)),
    ])

    options = [
        t("settings.change_language"),
        t("settings.change_provider"),
        t("settings.change_pause_mode"),
        t("settings.back"),
    ]
    idx = select(t("settings.prompt"), options, default=0, allow_escape=True)
    if idx is None or idx == 3:
        return

    if idx == 0:
        selected_language = choose_language(_current_language)
        if selected_language == _current_language:
            info(t("settings.language_unchanged", language=_language_label()))
            press_enter()
            return

        _current_language = selected_language
        i18n_module.set_language(_current_language)
        cli_module.set_language(_current_language)
        if _save_configured_language(_current_language):
            success(t("settings.language_changed", language=_language_label()))
        press_enter()
        return

    if idx == 1:
        selected_provider = choose_provider(_current_provider)
        if selected_provider == _current_provider:
            info(t("settings.provider_unchanged", provider=_provider_label()))
            press_enter()
            return

        _current_provider = selected_provider
        if _save_configured_provider(_current_provider):
            success(t("settings.provider_changed", provider=_provider_label()))
        _show_model_cli_environment_check(_current_provider)
        press_enter()
        return

    selected_pause_mode = choose_pause_mode(_current_pause_mode)
    if selected_pause_mode == _current_pause_mode:
        info(t("settings.pause_mode_unchanged", mode=_pause_mode_label()))
        press_enter()
        return

    _current_pause_mode = selected_pause_mode
    if _save_configured_pause_mode(_current_pause_mode):
        success(t("settings.pause_mode_changed", mode=_pause_mode_label()))
    press_enter()


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
class _EpubTextParser(HTMLParser):
    """Convert simple XHTML content from EPUB spine items into plain text."""

    _BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "div", "dl", "dt",
        "dd", "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5",
        "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre",
        "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
    }
    _SKIP_TAGS = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        raw = unescape("".join(self._parts)).replace("\r", "\n")
        lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in raw.splitlines()]
        collapsed: List[str] = []
        blank_seen = False
        for line in lines:
            if not line:
                if collapsed and not blank_seen:
                    collapsed.append("")
                    blank_seen = True
                continue
            collapsed.append(line)
            blank_seen = False
        return "\n".join(collapsed).strip()


def _safe_output_name(title: str, index: int) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")
    if not safe:
        safe = t("ui.chapter_title", index=index)
    return f"{index:03d}_{safe[:80]}.txt"


def _read_zip_text(zf: zipfile.ZipFile, name: str) -> str:
    data = zf.read(name)
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _parse_xml_bytes(data: bytes) -> ET.Element:
    return ET.fromstring(data)


def _xml_attr(element: ET.Element, name: str) -> Optional[str]:
    value = element.attrib.get(name)
    if value is not None:
        return value
    for key, value in element.attrib.items():
        if key.endswith("}" + name):
            return value
    return None


def _element_text(element: Optional[ET.Element]) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _find_opf_path(zf: zipfile.ZipFile) -> str:
    container = _parse_xml_bytes(zf.read("META-INF/container.xml"))
    for element in container.iter():
        if element.tag.endswith("rootfile"):
            path = _xml_attr(element, "full-path")
            if path:
                return path
    raise ValueError(t("tools.epub_missing_opf"))


def _chapter_title_from_html(html: str, fallback: str) -> str:
    try:
        root = ET.fromstring(html.encode("utf-8"))
    except ET.ParseError:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip() or fallback
        return fallback

    for element in root.iter():
        if element.tag.lower().endswith("title"):
            title = _element_text(element)
            if title:
                return title
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1].lower()
        if local in {"h1", "h2", "h3"}:
            title = _element_text(element)
            if title:
                return title
    return fallback


def split_epub_to_txt(epub_path: Path) -> Tuple[Path, int]:
    """Split EPUB spine documents into one txt file per chapter."""
    if not epub_path.exists():
        raise FileNotFoundError(t("tools.epub_path_missing", path=epub_path))
    if not epub_path.is_file() or epub_path.suffix.lower() != ".epub":
        raise ValueError(t("tools.epub_invalid"))

    output_dir = epub_path.parent / "Output"
    output_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(epub_path) as zf:
        opf_path = _find_opf_path(zf)
        opf_root = _parse_xml_bytes(zf.read(opf_path))
        opf_dir = posixpath.dirname(opf_path)

        manifest: Dict[str, Dict[str, str]] = {}
        spine_ids: List[str] = []
        for element in opf_root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "item":
                item_id = _xml_attr(element, "id")
                href = _xml_attr(element, "href")
                media_type = _xml_attr(element, "media-type") or ""
                if item_id and href:
                    manifest[item_id] = {"href": href, "media_type": media_type}
            elif tag == "itemref":
                idref = _xml_attr(element, "idref")
                if idref:
                    spine_ids.append(idref)

        count = 0
        used_names = set()
        for idref in spine_ids:
            item = manifest.get(idref)
            if not item or "html" not in item["media_type"].lower():
                continue

            href = unquote(item["href"].split("#", 1)[0])
            chapter_path = posixpath.normpath(posixpath.join(opf_dir, href))
            if chapter_path.startswith("../") or chapter_path not in zf.namelist():
                continue

            html = _read_zip_text(zf, chapter_path)
            parser = _EpubTextParser()
            parser.feed(html)
            text = parser.text()
            if not text:
                continue

            count += 1
            fallback = t("ui.chapter_title", index=count)
            title = _chapter_title_from_html(html, fallback)
            file_name = _safe_output_name(title, count)
            while file_name.lower() in used_names:
                file_name = _safe_output_name(f"{title}_{count}", count)
            used_names.add(file_name.lower())
            (output_dir / file_name).write_text(text + "\n", encoding="utf-8")

    if count == 0:
        raise ValueError(t("tools.epub_no_chapters"))
    return output_dir, count


def tools_mode() -> None:
    """Tools submenu."""
    clear()
    print_banner(t("tools.title"), subtitle=t("tools.subtitle"))

    options = [
        t("tools.split_epub_option"),
        t("tools.back"),
    ]
    idx = select(t("tools.prompt"), options, default=0, allow_escape=True)
    if idx is None or idx == 1:
        return

    epub_input = prompt(t("tools.epub_path_prompt"), show_default=False).strip().strip('"')
    if not epub_input:
        warn(t("common.cancelled"))
        press_enter()
        return

    try:
        output_dir, count = split_epub_to_txt(Path(epub_input).expanduser())
    except Exception as e:
        error(t("tools.epub_split_failed", error=e))
        press_enter()
        return

    print_section(t("tools.epub_split_done"), color=C.SUCCESS)
    print_kv([
        (t("tools.epub_output_dir"), str(output_dir)),
        (t("tools.epub_output_count"), str(count)),
    ])
    press_enter()


# ---------------------------------------------------------------------------
# 导出功能
# ---------------------------------------------------------------------------
def export_mode() -> None:
    """导出小说为 md / txt / epub 格式。"""
    clear()
    print_banner(t("export.title"), subtitle=t("export.subtitle"))

    projects = list_existing_projects()
    if not projects:
        warn(t("export.no_projects"))
        press_enter()
        return

    idx = select_project(projects, allow_new=False)
    if idx is None:
        return
    project_name = idx

    project_path = _projects_root() / project_name
    output_dir = project_path / "02_output"

    if not output_dir.exists():
        error(t("export.missing_dir", path=output_dir))
        press_enter()
        return

    # 收集正文文件
    chapters: List[Tuple[int, Path]] = []
    for f in output_dir.iterdir():
        if f.is_file() and f.suffix == ".md" and (f.stem.startswith("正文v") or f.stem.startswith("Draft_v")):
            try:
                version = int(f.stem.replace("正文v", "").replace("Draft_v", ""))
                chapters.append((version, f))
            except ValueError:
                pass

    if not chapters:
        error(t("export.no_chapters"))
        press_enter()
        return

    chapters.sort(key=lambda x: x[0])
    total = len(chapters)

    novel_title = project_name  # 使用文件夹名作为小说名

    print_subheader(t("export.project_header", project=project_name), color=C.PRIMARY)
    print_kv([
        (t("export.novel_name"), novel_title),
        (t("export.chapter_count"), str(total)),
        (t("export.source_dir"), str(output_dir)),
    ])

    # 选择导出格式
    format_options = [
        t("export.format_all"),
        t("export.format_md"),
        t("export.format_txt"),
        t("export.format_epub"),
    ]
    fmt_idx = select(t("export.format_prompt"), format_options, default=0, allow_escape=True)
    if fmt_idx is None:
        return

    export_md = fmt_idx in (0, 1)
    export_txt = fmt_idx in (0, 2)
    export_epub = fmt_idx in (0, 3) and HAS_EBOOKLIB

    if fmt_idx == 3 and not HAS_EBOOKLIB:
        warn(t("export.epub_unavailable"))

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
            chapter_title = t("ui.chapter_title", index=i)
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
            warn(t("export.epub_failed", error=e))

    # 输出结果
    print_section(t("export.done"), color=C.SUCCESS)
    for fmt, path in results:
        success(f"{fmt} → {path}")

    if not results:
        error(t("export.no_outputs"))

    press_enter()


# ---------------------------------------------------------------------------
# 主菜单
# ---------------------------------------------------------------------------
def main() -> None:
    global _current_provider, _current_language, _current_pause_mode
    init()
    config = _load_menu_config()
    has_language = _has_configured_language(config)
    has_provider = _has_configured_provider(config)
    has_pause_mode = _has_configured_pause_mode(config)
    _current_language = _normalize_language(config.get("language"))
    i18n_module.set_language(_current_language)
    _current_provider = _normalize_provider(config.get("provider"))
    # 旧配置没写过 pause_mode 字段时，保持作家模式（停顿）。
    _current_pause_mode = _normalize_pause_mode(config.get("pause_mode", True))

    if not has_language:
        _current_language = choose_language(_current_language)
        config["language"] = _current_language

    i18n_module.set_language(_current_language)
    cli_module.set_language(_current_language)

    if not has_provider:
        _current_provider = choose_provider(_current_provider)
        config["provider"] = _current_provider

    if not has_pause_mode:
        _current_pause_mode = choose_pause_mode(_current_pause_mode)

    config["pause_mode"] = _current_pause_mode

    if not has_language or not has_provider or not has_pause_mode:
        _save_menu_config(config)
        _show_model_cli_environment_check(_current_provider)
        press_enter()

    while True:
        clear()
        print_banner(
            t("app.title"),
            subtitle=t("main.subtitle", language=_language_label(), provider=_provider_label()),
        )
        print_subheader(t("main.choose_feature"), color=C.PRIMARY)
        options = [
            _main_option("🚀", t("main.full_option")),
            _main_option("🎯", t("main.single_option")),
            _main_option("🔁", t("main.continue_option")),
            _main_option("📜", t("main.steps_option")),
            _main_option("📦", t("main.export_option")),
            _main_option("🧰", t("main.tools_option")),
            _main_option("🗑️", t("main.delete_option")),
            _main_option("⚙️", t("main.settings_option")),
            _main_option("🌙", t("main.exit_option")),
        ]
        idx = select(t("main.menu_prompt"), options, default=0, allow_escape=True)
        if idx is None:
            continue
        actions = [
            full_loop_mode,
            single_step_mode,
            continue_mode,
            view_steps_list,
            export_mode,
            tools_mode,
            delete_project_mode,
            settings_mode,
        ]
        if idx == 8:
            print_panel(t("main.goodbye_title"), t("main.goodbye_body"), color=C.ACCENT, icon=I.STAR)
            break
        try:
            actions[idx]()
        except KeyboardInterrupt:
            warn(t("common.cancelled"))
            press_enter()
        except Exception as e:
            error(t("common.uncaught", error=e))
            press_enter()


if __name__ == "__main__":
    main()
