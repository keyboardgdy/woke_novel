# -*- coding: utf-8 -*-
"""FastAPI wrapper for the local woke_novel workflow.

The service is intentionally local-first: it exposes project files, logs and
workflow subprocesses through constrained APIs while keeping the existing CLI
entry points unchanged.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Literal

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app_paths import resource_path, runtime_path

WORKSPACE = runtime_path()
PROJECTS_ROOT = WORKSPACE / "projects"
LOGS_ROOT = WORKSPACE / "logs"
CONFIG_FILE = WORKSPACE / ".menu_config.json"
FRONTEND_DIST = resource_path("frontend", "dist")
PRESETS_ZH = resource_path("assets", "style_presets_classified.json")
PRESETS_EN = resource_path("assets", "style_presets_classified_en.json")

PROJECT_DIRS = [
    "00_baseline",
    "01_plots",
    "02_guides",
    "02_output",
    "03_state",
    "04_characters",
]

Provider = Literal["claude", "codex", "mixed"]

STEP_NAMES = {
    "01": "创意方案生成",
    "02": "创意方案补充",
    "03": "世界观与设定生成",
    "04": "人物档案与人物关系",
    "05": "故事主轴",
    "05a": "幕次框架",
    "05b": "幕次核心骨架",
    "06": "开篇剧情提取",
    "07": "开篇剧情梗概",
    "08": "开篇写作指南",
    "09": "开篇正文创作",
    "10": "状态文档",
    "11": "剧情生成方向指导",
    "12": "剧情梗概设计",
    "13": "写作指南",
    "14": "正文创作",
    "15": "状态文档",
    "16": "故事梗概精简",
    "17": "幕次故事梗概精简",
    "18": "项目级 CLAUDE.md",
    "Q1": "章节质量评审",
    "Q2": "章节定向重写",
    "Q3": "风格记忆沉淀",
    "Q4": "剧情吸引力评审",
    "Q5": "剧情强化重构",
    "Q6": "剧情钩子账本沉淀",
    "Q7": "故事主轴吸引力评审",
    "Q7R": "故事主轴吸引力重构",
    "Q8": "幕次框架吸引力评审",
    "Q8R": "幕次框架吸引力重构",
    "Q9": "幕次核心骨架吸引力评审",
    "Q9R": "幕次核心骨架吸引力重构",
    "Q10": "章节上下文包生成",
}

STEP_ORDER = [
    "01", "02", "03", "04",
    "05", "Q7", "Q7R", "05a", "Q8", "Q8R", "05b", "Q9", "Q9R",
    "18", "Q10", "06", "07", "Q4", "Q5", "Q6", "08", "09", "Q1", "Q2", "10",
    "11", "12", "13", "14", "15", "16", "17",
]

STAGES = [
    ("creative", "创意", ["01", "02"]),
    ("world", "世界/人物", ["03", "04"]),
    ("axis", "主轴", ["05", "Q7", "Q7R", "05a", "Q8", "Q8R", "05b", "Q9", "Q9R", "18"]),
    ("opening", "开篇", ["Q10", "06", "07", "Q4", "Q5", "Q6", "08", "09", "Q1", "Q2", "10"]),
    ("draft_loop", "正文循环", ["Q10", "11", "12", "Q4", "Q5", "Q6", "13", "14", "Q1", "Q2", "15", "16"]),
    ("act_end", "幕末整理", ["17", "18"]),
]

SIZE_WORDS = {
    "超短篇": 20_000,
    "中短篇": 80_000,
    "短篇": 80_000,
    "中篇": 300_000,
    "长篇": 800_000,
    "超长篇": 1_500_000,
    "Flash fiction": 20_000,
    "Short novella": 80_000,
    "Short novel": 80_000,
    "Medium-length novel": 300_000,
    "Long novel": 800_000,
    "Very long novel": 1_500_000,
}

SAFE_PROJECT_RE = re.compile(r'^[^<>:"/\\|?*\x00-\x1f.][^<>:"/\\|?*\x00-\x1f]*$')


class Utf8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


class ProjectCreateRequest(BaseModel):
    project_name: str
    genre: str = "都市"
    language: Literal["zh", "en"] = "zh"
    provider: Provider = "mixed"
    novel_size: str = "中篇"
    target_word_count: int | None = None
    user_description: str = ""
    option_count: int = Field(default=3, ge=1, le=10)
    auto_select_option: int = Field(default=1, ge=1, le=10)
    dry_run: bool = False
    pause: bool = True
    start_immediately: bool = False


class ProjectDeleteRequest(BaseModel):
    delete_logs: bool = True
    confirm_text: str = ""


class CreativeOptionSelectRequest(BaseModel):
    option_index: int = Field(ge=1, le=10)


class SettingsPatch(BaseModel):
    language: Literal["zh", "en"] | None = None
    provider: Provider | None = None
    default_dry_run: bool | None = None
    max_retries: int | None = Field(default=None, ge=1, le=20)


class RunRequest(BaseModel):
    genre: str | None = None
    language: Literal["zh", "en"] = "zh"
    provider: Provider = "mixed"
    dry_run: bool = False
    option_count: int = Field(default=3, ge=1, le=10)
    auto_select_option: int = Field(default=1, ge=1, le=10)
    max_retries: int = Field(default=3, ge=1, le=20)
    pause: bool = True
    user_description: str = ""
    novel_size: str | None = None
    target_word_count: int | None = None
    step: str | None = None


class ExportRequest(BaseModel):
    formats: list[Literal["md", "txt", "epub", "all"]] = ["md"]
    novel_title: str | None = None
    include_check: bool = True
    fail_on_check_error: bool = False


class FileContentSaveRequest(BaseModel):
    path: str
    content: str


@dataclass
class RunRecord:
    run_id: str
    project_name: str
    mode: str
    status: str
    provider: str
    language: str
    dry_run: bool
    command: list[str]
    started_at: str
    pid: int | None = None
    ended_at: str | None = None
    elapsed_seconds: float | None = None
    return_code: int | None = None
    current_step: str | None = None
    log_path: str | None = None
    final_project_name: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue, repr=False)
    process: Any | None = field(default=None, repr=False)

    def public(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_name": self.project_name,
            "mode": self.mode,
            "status": self.status,
            "provider": self.provider,
            "language": self.language,
            "dry_run": self.dry_run,
            "command": self.command,
            "pid": self.pid,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "elapsed_seconds": self.elapsed_seconds,
            "return_code": self.return_code,
            "current_step": self.current_step,
            "log_path": self.log_path,
            "final_project_name": self.final_project_name,
        }


app = FastAPI(title="woke_novel visual console", version="0.1.0", default_response_class=Utf8JSONResponse)


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict[str, Any]):
        response = await super().get_response(path, scope)
        if path in {"", ".", "index.html"} or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS: dict[str, RunRecord] = {}
ACTIVE_BY_PROJECT: dict[str, str] = {}


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return path.relative_to(WORKSPACE).as_posix()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def decode_text(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings() -> dict[str, Any]:
    data = read_json(CONFIG_FILE, {})
    return {
        "language": data.get("language", "zh"),
        "provider": data.get("provider", "mixed"),
        "workspace": str(WORKSPACE),
        "projects_root": str(PROJECTS_ROOT),
        "logs_root": str(LOGS_ROOT),
        "config_file": str(CONFIG_FILE),
        "default_dry_run": data.get("default_dry_run", False),
        "max_retries": data.get("max_retries", 3),
    }


def validate_project_name(project: str) -> None:
    if not project or project in {".", ".."} or not SAFE_PROJECT_RE.match(project):
        raise ApiError(400, "BAD_REQUEST", f"Invalid project name: {project}", {"project": project})


def project_path(project: str, must_exist: bool = True) -> Path:
    validate_project_name(project)
    path = (PROJECTS_ROOT / project).resolve()
    if PROJECTS_ROOT.resolve() not in path.parents and path != PROJECTS_ROOT.resolve():
        raise ApiError(400, "PATH_OUT_OF_SCOPE", "Project path is outside projects root", {"project": project})
    if must_exist and not path.is_dir():
        raise ApiError(404, "PROJECT_NOT_FOUND", f"Project not found: {project}", {"project": project})
    return path


def log_project_path(project: str) -> Path:
    validate_project_name(project)
    path = (LOGS_ROOT / project).resolve()
    logs_root = LOGS_ROOT.resolve()
    if logs_root not in path.parents and path != logs_root:
        raise ApiError(400, "PATH_OUT_OF_SCOPE", "Log path is outside logs root", {"project": project})
    return path


def safe_child(root: Path, relative_path: str, must_exist: bool = True) -> Path:
    if not relative_path or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        raise ApiError(400, "PATH_OUT_OF_SCOPE", "Path is outside allowed root", {"path": relative_path})
    target = (root / relative_path).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ApiError(400, "PATH_OUT_OF_SCOPE", "Path is outside allowed root", {"path": relative_path})
    if must_exist and not target.exists():
        raise ApiError(404, "FILE_NOT_FOUND", f"File not found: {relative_path}", {"path": relative_path})
    return target


def file_kind(path: Path) -> str:
    if path.is_dir():
        return "directory"
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".json":
        return "json"
    if suffix in {".txt", ".log"}:
        return "text"
    if suffix == ".epub":
        return "epub"
    return "unknown"


def health(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_file():
        try:
            if path.stat().st_size == 0 or not path.read_text(encoding="utf-8", errors="ignore").strip():
                return "empty"
        except Exception:
            return "unknown"
    return "ok"


def natural_key(path: Path | str) -> list[Any]:
    name = path.name if isinstance(path, Path) else str(path)
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def read_project_info(project: str) -> dict[str, Any]:
    root = project_path(project)
    data = read_json(root / ".project_info.json", {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("project_name", project)
    return data


def step_name(step: str | None) -> str | None:
    if not step:
        return None
    return STEP_NAMES.get(step, step)


def infer_stage(last_step: str | None) -> str:
    if not last_step:
        return "未开始"
    for _, label, steps in STAGES:
        if last_step in steps:
            return label
    return "未知"


def progress_percent(last_step: str | None) -> int:
    if not last_step:
        return 0
    if last_step in STEP_ORDER:
        return round((STEP_ORDER.index(last_step) + 1) / len(STEP_ORDER) * 100)
    return 25


def project_is_complete(
    info: dict[str, Any],
    generated_chapters: int = 0,
    target_chapters: int | None = None,
    max_chapter_index: int = 0,
) -> bool:
    if target_chapters and generated_chapters >= target_chapters:
        return True
    last_step = info.get("last_step")
    if last_step != "18" or info.get("last_step_phase") != "post_17":
        return False
    if target_chapters and max_chapter_index >= target_chapters:
        return True
    current_round = info.get("current_round")
    if target_chapters and isinstance(current_round, int) and current_round > target_chapters:
        return True
    act_count = info.get("act_count")
    last_act = info.get("last_step_act")
    return bool(act_count and last_act and last_act >= act_count)


def count_chapters(project: str) -> tuple[int, int | None, int]:
    check = build_export_check(project)
    return check["chapter_count"], check.get("target_chapter_count"), check.get("max_chapter_index") or 0


def pid_is_alive(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes

            process_query_limited_information = 0x1000
            still_active = 259
            handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid_int)
            if not handle:
                return False
            exit_code = ctypes.c_ulong()
            try:
                if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return exit_code.value == still_active
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        os.kill(pid_int, 0)
        return True
    except Exception:
        return False


def run_status_path(project: str) -> Path:
    return project_path(project) / ".run_status.json"


def read_external_run_status(project: str) -> dict[str, Any] | None:
    path = run_status_path(project)
    data = read_json(path, None)
    if not isinstance(data, dict) or data.get("status") not in {"queued", "running"}:
        return None
    if not pid_is_alive(data.get("pid")):
        try:
            path.unlink()
        except Exception:
            pass
        return None
    return data


def active_project_status(project: str) -> dict[str, Any]:
    active = ACTIVE_BY_PROJECT.get(project)
    if active and active in RUNS and RUNS[active].status in {"queued", "running"}:
        run = RUNS[active]
        return {
            "status": run.status,
            "run_id": active,
            "source": "api",
            "pid": run.pid,
            "started_at": run.started_at,
            "mode": run.mode,
            "provider": run.provider,
            "language": run.language,
            "dry_run": run.dry_run,
        }
    external = read_external_run_status(project)
    if external:
        return {
            "status": "running",
            "run_id": external.get("run_id"),
            "source": external.get("source", "cli"),
            "pid": external.get("pid"),
            "started_at": external.get("started_at"),
            "mode": external.get("mode"),
            "provider": external.get("provider"),
            "language": external.get("language"),
            "dry_run": external.get("dry_run"),
        }
    return {
        "status": "idle",
        "run_id": None,
        "source": None,
        "pid": None,
        "started_at": None,
        "mode": None,
        "provider": None,
        "language": None,
        "dry_run": None,
    }


def active_run_public(project: str) -> dict[str, Any] | None:
    active_status = active_project_status(project)
    if active_status["status"] not in {"queued", "running"}:
        return None
    active = ACTIVE_BY_PROJECT.get(project)
    if active and active in RUNS:
        return RUNS[active].public()
    return {
        "run_id": active_status.get("run_id") or f"cli_{active_status.get('pid') or 'unknown'}",
        "project_name": project,
        "mode": active_status.get("mode") or "cli",
        "status": active_status["status"],
        "provider": active_status.get("provider"),
        "language": active_status.get("language"),
        "dry_run": active_status.get("dry_run"),
        "command": [],
        "pid": active_status.get("pid"),
        "started_at": active_status.get("started_at"),
        "ended_at": None,
        "elapsed_seconds": None,
        "return_code": None,
        "current_step": None,
        "log_path": None,
        "final_project_name": None,
        "source": active_status.get("source"),
    }


def project_summary(project: str) -> dict[str, Any]:
    root = project_path(project)
    info = read_project_info(project)
    settings = load_settings()
    generated, target, max_chapter_index = count_chapters(project)
    stat = root.stat()
    last_active = info.get("last_step_at") or datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
    active_status = active_project_status(project)
    target_chapters = info.get("total_chapters") or target
    is_complete = project_is_complete(info, generated, target_chapters, max_chapter_index)
    return {
        "project_name": project,
        "novel_name": info.get("novel_name"),
        "genre": info.get("genre", "未知题材"),
        "language": info.get("language") or settings["language"],
        "provider": info.get("provider") or settings["provider"],
        "status": active_status["status"],
        "run_source": active_status["source"],
        "run_pid": active_status["pid"],
        "run_started_at": active_status["started_at"],
        "run_id": active_status["run_id"],
        "stage": infer_stage(info.get("last_step")),
        "progress_percent": progress_percent(info.get("last_step")),
        "chapter_progress": {"generated": generated, "target": target_chapters},
        "last_step": info.get("last_step"),
        "last_step_name": step_name(info.get("last_step")),
        "last_active_at": last_active,
        "has_checkpoint": bool(info.get("last_step")),
        "has_errors": latest_log_has_error(project),
        "can_continue": bool(info.get("last_step")) and not is_complete,
        "is_complete": is_complete,
        "project_path": rel(root),
    }


def latest_log_has_error(project: str) -> bool:
    root = LOGS_ROOT / project
    if not root.is_dir():
        return False
    logs = sorted([p for p in root.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return False
    try:
        tail = "\n".join(logs[0].read_text(encoding="utf-8", errors="ignore").splitlines()[-80:]).lower()
    except Exception:
        return False
    return any(token in tail for token in ["error", "failed", "traceback", "return code: 1", "失败"])


def build_workflow_state(project: str) -> dict[str, Any]:
    info = read_project_info(project)
    last_step = info.get("last_step")
    current = {
        "step": last_step,
        "name": step_name(last_step),
        "status": "succeeded" if last_step else "not_started",
        "act_num": info.get("last_step_act"),
        "round_num": info.get("last_step_round") or info.get("current_round", 1),
    }
    active_status = active_project_status(project)
    active_run_id = active_status["run_id"]
    if active_status["status"] in {"queued", "running"}:
        current["status"] = active_status["status"]
    stages = []
    for key, label, steps in STAGES:
        if not last_step:
            status = "not_started"
        elif last_step in steps:
            status = "running" if active_status["status"] in {"queued", "running"} else "succeeded"
        elif any(STEP_ORDER.index(s) < STEP_ORDER.index(last_step) for s in steps if s in STEP_ORDER and last_step in STEP_ORDER):
            status = "succeeded"
        else:
            status = "not_started"
        stages.append({"key": key, "name": label, "status": status, "steps": steps})
    next_label = "启动完整工作流" if not last_step else f"继续：{step_name(last_step)}之后"
    return {
        "project_name": project,
        "active_run_id": active_run_id,
        "overall_status": active_status["status"],
        "run_source": active_status["source"],
        "run_pid": active_status["pid"],
        "current_step": current,
        "stages": stages,
        "loop_matrix": [],
        "next_action": {"type": "full" if not last_step else "continue", "label": next_label, "enabled": True},
    }


def file_node(base: Path, path: Path, include_hidden: bool) -> dict[str, Any] | None:
    if not include_hidden and path.name.startswith(".") and path.name != ".project_info.json":
        return None
    node = {
        "name": path.name,
        "relative_path": path.relative_to(base).as_posix(),
        "kind": file_kind(path),
        "is_directory": path.is_dir(),
        "size": 0 if path.is_dir() else path.stat().st_size,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        "editable": False,
        "health": health(path),
        "children": None,
    }
    if path.is_dir():
        children = []
        for child in sorted(path.iterdir(), key=natural_key):
            child_node = file_node(base, child, include_hidden)
            if child_node:
                children.append(child_node)
        node["children"] = children
    return node


CREATIVE_TITLE_RE = re.compile(r"^#\s*(?:创意方案|Creative\s+Proposal)[：:]\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
CREATIVE_OPENING_RE = re.compile(r"^##\s*(?:开篇设想|Opening\s+Concept)\s*\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
CREATIVE_REF_RE = re.compile(r"^##\s*(?:参考作品|Reference\s+Works).*?\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE)


def creative_file_name(language: str, index: int) -> str:
    return f"Creative_Proposal_{index}.md" if language == "en" else f"创意方案_{index}.md"


def creative_option_path(project: str, index: int, language: str | None = None) -> Path:
    info = read_project_info(project)
    lang = language or info.get("language") or load_settings()["language"]
    path = project_path(project) / "00_baseline" / creative_file_name(lang, index)
    if not path.exists():
        fallback = project_path(project) / "00_baseline" / creative_file_name("en" if lang == "zh" else "zh", index)
        if fallback.exists():
            return fallback
    return path


def creative_excerpt(text: str) -> tuple[str, str, str]:
    title_match = CREATIVE_TITLE_RE.search(text)
    opening_match = CREATIVE_OPENING_RE.search(text)
    refs_match = CREATIVE_REF_RE.search(text)
    return (
        title_match.group(1).strip() if title_match else "",
        opening_match.group(1).strip() if opening_match else "",
        refs_match.group(1).strip() if refs_match else "",
    )


def creative_options(project: str) -> list[dict[str, Any]]:
    info = read_project_info(project)
    count = int(info.get("option_count") or 0)
    if count <= 0:
        baseline = project_path(project) / "00_baseline"
        count = max([
            int(match.group(1))
            for path in baseline.glob("*_*.md")
            if (match := re.search(r"_(\d+)\.md$", path.name))
        ] or [0])
    selected = info.get("selected_option")
    items = []
    for index in range(1, count + 1):
        path = creative_option_path(project, index, info.get("language"))
        exists = path.is_file()
        content = path.read_text(encoding="utf-8", errors="ignore") if exists else ""
        title, opening, ref_works = creative_excerpt(content)
        items.append({
            "index": index,
            "title": title or f"方案 {index}",
            "opening": opening,
            "ref_works": ref_works,
            "content": content,
            "relative_path": path.relative_to(project_path(project)).as_posix(),
            "workspace_path": rel(path),
            "exists": exists,
            "selected": selected == index,
        })
    return items


def chapter_title(text: str, index: int) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.lstrip("#").strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:80]
    return f"第 {index} 章"


def chapter_index_from_path(path: Path) -> int | None:
    matches = re.findall(r"\d+", path.stem)
    if not matches:
        return None
    return int(matches[-1])


def word_count(text: str) -> int:
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    if len(cjk) > 20:
        return len(re.findall(r"\S", text))
    return len(re.findall(r"\b[\w'-]+\b", text))


def chapter_items(project: str) -> list[dict[str, Any]]:
    root = project_path(project) / "02_output"
    if not root.exists():
        return []
    files = sorted([p for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".md"], key=natural_key)
    items = []
    for index, path in enumerate(files, start=1):
        text = path.read_text(encoding="utf-8", errors="ignore")
        file_index = chapter_index_from_path(path)
        items.append({
            "index": file_index or index,
            "file_order": index,
            "title": chapter_title(text, index),
            "relative_path": f"02_output/{path.name}",
            "word_count": word_count(text),
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
            "health": health(path),
        })
    return items


def build_export_check(project: str) -> dict[str, Any]:
    info = read_project_info(project)
    items = chapter_items(project)
    total_words = sum(item["word_count"] for item in items)
    target = info.get("total_chapters") or (sum(info.get("chapter_counts", [])) if isinstance(info.get("chapter_counts"), list) else None)
    numeric_indexes = sorted({item["index"] for item in items if isinstance(item.get("index"), int)})
    max_chapter_index = numeric_indexes[-1] if numeric_indexes else 0
    missing_indexes = []
    if target and numeric_indexes:
        existing = set(numeric_indexes)
        missing_indexes = [index for index in range(1, target + 1) if index not in existing]
    empty = [item for item in items if item["health"] == "empty" or item["word_count"] == 0]
    duplicate_titles = sorted({title for title in [item["title"] for item in items] if [item["title"] for item in items].count(title) > 1})
    checks = [
        {"key": "chapter_order", "label": "章节顺序", "status": "passed", "message": "已按自然顺序排列"},
        {"key": "empty_chapter", "label": "空章节", "status": "failed" if empty else "passed", "message": f"发现 {len(empty)} 个空章节" if empty else "未发现空章节"},
        {"key": "duplicate_title", "label": "重复标题", "status": "warning" if duplicate_titles else "passed", "message": "、".join(duplicate_titles) if duplicate_titles else "未发现重复标题"},
    ]
    if target:
        status = "passed" if len(items) == target else "warning"
        checks.append({"key": "chapter_count", "label": "章节数量", "status": status, "message": f"已生成 {len(items)} / 目标 {target}"})
    if missing_indexes:
        preview = "、".join(str(index) for index in missing_indexes[:20])
        suffix = "..." if len(missing_indexes) > 20 else ""
        checks.append({"key": "missing_chapters", "label": "缺失章节", "status": "warning", "message": f"缺失第 {preview}{suffix} 章"})
    return {
        "project_name": project,
        "source_dir": "02_output",
        "chapter_count": len(items),
        "target_chapter_count": target,
        "max_chapter_index": max_chapter_index,
        "missing_chapter_indexes": missing_indexes,
        "total_words": total_words,
        "checks": checks,
        "chapters": items,
    }


def safe_export_title(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")
    return cleaned or "woke_novel_export"


async def emit(run: RunRecord, event: str, data: dict[str, Any]) -> None:
    payload = {"event": event, "data": {**data, "time": now_iso()}}
    run.events.append(payload)
    await run.queue.put(payload)


def cleanup_old_run_logs(project: str) -> None:
    root = LOGS_ROOT / project
    if not root.is_dir():
        return
    for path in root.glob("run_*.log"):
        try:
            path.unlink()
        except Exception:
            pass


def run_log_path(project: str, run_id: str) -> Path:
    root = LOGS_ROOT / project
    root.mkdir(parents=True, exist_ok=True)
    cleanup_old_run_logs(project)
    return root / "run.log"


def append_run_log_event(log_file: Path | None, event_line: str) -> None:
    if not log_file:
        return
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if log_file.exists() and f"] {event_line}" in log_file.read_text(encoding="utf-8", errors="replace"):
            return
        with log_file.open("a", encoding="utf-8", errors="replace") as fh:
            fh.write(f"[{now_iso()}] {event_line}\n")
    except Exception:
        pass


def write_run_status(project: str, run: RunRecord) -> None:
    write_json(
        run_status_path(project),
        {
            "project_name": project,
            "pid": run.pid,
            "status": run.status,
            "source": "api",
            "run_id": run.run_id,
            "started_at": run.started_at,
        },
    )


def clear_run_status(project: str, run_id: str | None = None) -> None:
    path = run_status_path(project)
    data = read_json(path, {})
    if run_id and isinstance(data, dict) and data.get("run_id") not in {None, run_id}:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except Exception:
        pass


def terminate_process_tree(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0 or not pid_is_alive(pid_int):
        return False
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["taskkill", "/PID", str(pid_int), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 or not pid_is_alive(pid_int)
        os.kill(pid_int, 15)
        return True
    except Exception:
        return False


RENAME_LINE_RE = re.compile(r"(?:项目已重命名|Project renamed):\s*(.+?)\s*(?:→|->)\s*(.+?)\s*$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def clean_event_line(line: str) -> str:
    return re.sub(r"\s+", " ", ANSI_RE.sub("", line).replace("\r", "").strip()).strip()


def summarize_run_event(line: str) -> str | None:
    text = clean_event_line(line)
    if not text:
        return None
    text = re.sub(r"^[✓✗⚠▶✎★✦─═\s]+", "", text).strip()
    if not text:
        return None
    if text.startswith("$ ") or text.startswith("["):
        return text
    rename = RENAME_LINE_RE.search(text)
    if rename:
        return f"RENAME {rename.group(1).strip()} -> {rename.group(2).strip()}"
    step = re.search(r"步骤\s+([0-9a-zA-Z]+)\s+(.+?)(?:\s+(RUN|DRY)\s+会话\s+(.+))?$", text)
    if step:
        session = f" session={step.group(4)}" if step.group(4) else ""
        return f"STEP {step.group(1)} {step.group(2).strip()}{session}"
    if re.search(r"会话\s+\d+\s+·|第\s*\d+\s*幕|轮次|步骤\s+05b\s+循环|开篇创作|世界观|故事主轴|创意方案", text):
        return f"SECTION {text}"
    if re.search(r"完成|工作流完成|已生成|已创建|已追加|已选择|提取到|提取幕次|各幕章节数", text):
        return f"OK {text}"
    if re.search(r"警告|warn", text, re.IGNORECASE):
        return f"WARN {text}"
    if re.search(r"失败|failed|error|traceback|拒绝访问", text, re.IGNORECASE):
        return f"ERROR {text}"
    if re.search(r"生成方案|干运行|自动继续|继续下一轮|当前轮次|断点定位|RUN|DRY", text):
        return f"NOTE {text}"
    return None


def detect_project_rename(line: str) -> tuple[str, str] | None:
    cleaned = ANSI_RE.sub("", line).strip()
    match = RENAME_LINE_RE.search(cleaned)
    if not match:
        return None
    old_name = match.group(1).strip()
    new_name = match.group(2).strip()
    if old_name and new_name and old_name != new_name:
        return old_name, new_name
    return None


async def handle_project_rename(run: RunRecord, old_name: str, new_name: str) -> None:
    if run.final_project_name == new_name:
        return
    run.final_project_name = new_name
    ACTIVE_BY_PROJECT.pop(old_name, None)
    ACTIVE_BY_PROJECT[new_name] = run.run_id
    await emit(run, "project_renamed", {"run_id": run.run_id, "from": old_name, "to": new_name})


async def monitor_run(run: RunRecord, before_projects: set[str]) -> None:
    started = time.monotonic()
    log_file = Path(WORKSPACE / run.log_path) if run.log_path else None
    try:
        await emit(run, "run_started", {"run_id": run.run_id, "command": run.command})
        loop = asyncio.get_running_loop()

        def run_blocking() -> int:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            with (log_file.open("w", encoding="utf-8", errors="replace") if log_file else open(os.devnull, "w", encoding="utf-8")) as fh:
                fh.write(f"[{now_iso()}] COMMAND {' '.join(run.command)}\n")
                fh.flush()
                process = subprocess.Popen(
                    run.command,
                    cwd=str(WORKSPACE),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=creationflags,
                )
                run.process = process
                run.pid = process.pid
                loop.call_soon_threadsafe(asyncio.create_task, emit(run, "run_pid", {"run_id": run.run_id, "pid": run.pid}))
                loop.call_soon_threadsafe(write_run_status, run.project_name, run)
                assert process.stdout is not None
                for line in process.stdout:
                    stripped = line.rstrip("\r\n")
                    event_line = summarize_run_event(stripped)
                    if event_line:
                        fh.write(f"[{now_iso()}] {event_line}\n")
                        fh.flush()
                    rename = detect_project_rename(stripped)
                    if rename:
                        old_name, new_name = rename
                        loop.call_soon_threadsafe(
                            asyncio.create_task,
                            handle_project_rename(run, old_name, new_name),
                        )
                    loop.call_soon_threadsafe(
                        asyncio.create_task,
                        emit(run, "log_line", {"run_id": run.run_id, "stream": "stdout", "line": stripped}),
                    )
            return process.wait()

        return_code = await asyncio.to_thread(run_blocking)
        run.return_code = return_code
        run.ended_at = now_iso()
        run.elapsed_seconds = round(time.monotonic() - started, 2)
        after_projects = {p.name for p in PROJECTS_ROOT.iterdir() if p.is_dir()}
        if run.project_name not in after_projects and not run.final_project_name:
            removed_projects = before_projects - after_projects
            created_projects = after_projects - before_projects
            if run.project_name in removed_projects and created_projects:
                await handle_project_rename(run, run.project_name, sorted(created_projects)[0])
        if run.status == "cancelled":
            append_run_log_event(log_file, "NOTE run cancelled")
            await emit(run, "run_cancelled", {"run_id": run.run_id, "return_code": return_code})
        else:
            run.status = "succeeded" if return_code == 0 else "failed"
            if return_code == 0:
                append_run_log_event(log_file, "OK run succeeded")
            else:
                append_run_log_event(log_file, f"ERROR run failed: return_code={return_code}")
            await emit(run, "run_succeeded" if return_code == 0 else "run_failed", {"run_id": run.run_id, "return_code": return_code})
    except Exception as exc:
        run.status = "failed"
        run.ended_at = now_iso()
        run.elapsed_seconds = round(time.monotonic() - started, 2)
        if log_file:
            append_run_log_event(log_file, f"ERROR failed to start or monitor run: {exc}")
        await emit(run, "run_failed", {"run_id": run.run_id, "message": str(exc)})
    finally:
        ACTIVE_BY_PROJECT.pop(run.project_name, None)
        if run.final_project_name:
            ACTIVE_BY_PROJECT.pop(run.final_project_name, None)
        clear_run_status(run.project_name, run.run_id)
        if run.final_project_name:
            clear_run_status(run.final_project_name, run.run_id)
        await run.queue.put({"event": "end", "data": {"run_id": run.run_id, "time": now_iso()}})


def command_for(project: str, mode: str, req: RunRequest) -> list[str]:
    base = [sys.executable, "run_workflow.py"]
    if mode == "creative":
        cmd = base + [
            "creative",
            "--project-name", project,
            "--genre", req.genre or read_project_info(project).get("genre") or "都市",
            "--language", req.language,
            "--provider", req.provider,
            "--option-count", str(req.option_count),
            "--max-retries", str(req.max_retries),
            "--novel-size", req.novel_size or read_project_info(project).get("novel_size") or ("Medium-length novel" if req.language == "en" else "中篇"),
            "--user-description", req.user_description or "",
        ]
    elif mode == "full":
        cmd = base + [
            "loop",
            "--project-name", project,
            "--genre", req.genre or read_project_info(project).get("genre") or "都市",
            "--language", req.language,
            "--provider", req.provider,
            "--option-count", str(req.option_count),
            "--auto-select-option", str(min(req.auto_select_option, req.option_count)),
            "--max-retries", str(req.max_retries),
            "--novel-size", req.novel_size or read_project_info(project).get("novel_size") or ("Medium-length novel" if req.language == "en" else "中篇"),
            "--user-description", req.user_description or "",
        ]
        cmd.append("--pause" if req.pause else "--no-pause")
    elif mode == "continue":
        cmd = base + [
            "continue",
            "--project-name", project,
            "--language", req.language,
            "--provider", req.provider,
            "--max-retries", str(req.max_retries),
        ]
        cmd.append("--pause" if req.pause else "--no-pause")
    elif mode == "single":
        if not req.step:
            raise ApiError(400, "BAD_REQUEST", "single run requires step")
        cmd = base + [
            "single", req.step,
            "--project-name", project,
            "--genre", req.genre or read_project_info(project).get("genre") or "都市",
            "--language", req.language,
            "--provider", req.provider,
            "--max-retries", str(req.max_retries),
        ]
    else:
        raise ApiError(400, "BAD_REQUEST", f"Unsupported run mode: {mode}")
    if req.dry_run:
        cmd.append("--dry")
    return cmd


async def start_run(project: str, mode: str, req: RunRequest) -> RunRecord:
    project_path(project)
    external = read_external_run_status(project)
    if external:
        raise ApiError(409, "RUN_ALREADY_ACTIVE", f"Project already has active CLI run: {project}", {"pid": external.get("pid"), "source": external.get("source", "cli")})
    active = ACTIVE_BY_PROJECT.get(project)
    if active and RUNS.get(active) and RUNS[active].status in {"queued", "running"}:
        raise ApiError(409, "RUN_ALREADY_ACTIVE", f"Project already has active run: {project}", {"run_id": active})
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    command = command_for(project, mode, req)
    log_path = run_log_path(project, run_id)
    run = RunRecord(
        run_id=run_id,
        project_name=project,
        mode=mode,
        status="running",
        provider=req.provider,
        language=req.language,
        dry_run=req.dry_run,
        command=command,
        started_at=now_iso(),
        log_path=rel(log_path),
    )
    RUNS[run_id] = run
    ACTIVE_BY_PROJECT[project] = run_id
    before = {p.name for p in PROJECTS_ROOT.iterdir() if p.is_dir()}
    asyncio.create_task(monitor_run(run, before))
    return run


async def cancel_project_run(project: str) -> dict[str, Any]:
    project_path(project)
    active = ACTIVE_BY_PROJECT.get(project)
    if active and active in RUNS and RUNS[active].status in {"queued", "running"}:
        run = RUNS[active]
        pid = run.pid
        stopped = False
        if run.process and run.process.returncode is None:
            stopped = terminate_process_tree(pid)
            if not stopped:
                run.process.terminate()
                stopped = True
        elif pid:
            stopped = terminate_process_tree(pid)
        run.status = "cancelled"
        run.ended_at = now_iso()
        append_run_log_event(Path(WORKSPACE / run.log_path) if run.log_path else None, "NOTE run cancelled")
        await emit(run, "run_cancelled", {"run_id": run.run_id, "pid": pid, "stopped": stopped})
        clear_run_status(project, run.run_id)
        return {"ok": True, "message": "run cancelled", "data": {"project": project, "run_id": run.run_id, "pid": pid, "source": "api", "stopped": stopped}}

    external = read_external_run_status(project)
    if external:
        pid = external.get("pid")
        stopped = terminate_process_tree(pid)
        clear_run_status(project, external.get("run_id"))
        return {"ok": True, "message": "CLI run cancelled", "data": {"project": project, "run_id": external.get("run_id"), "pid": pid, "source": external.get("source", "cli"), "stopped": stopped}}

    raise ApiError(404, "RUN_NOT_FOUND", f"No active run for project: {project}", {"project": project})


def check_command(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"available": False, "version": None, "path": None, "message": f"{name} not found in PATH"}
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
        version = (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else None
    except Exception as exc:
        version = None
        return {"available": True, "version": None, "path": path, "message": str(exc)}
    return {"available": True, "version": version, "path": path}


def load_genre_presets(language: str) -> dict[str, Any]:
    path = PRESETS_EN if language == "en" else PRESETS_ZH
    raw = read_json(path, {})
    items: list[dict[str, Any]] = []
    if not isinstance(raw, dict):
        raw = {}
    for channel_id, channel in raw.items():
        if not isinstance(channel, dict):
            continue
        genres = channel.get("genres", {}) or {}
        if not isinstance(genres, dict):
            continue
        for genre_id, genre in genres.items():
            if not isinstance(genre, dict):
                continue
            themes = genre.get("themes", []) or []
            if not themes:
                items.append({
                    "id": f"{channel_id}.{genre_id}",
                    "channel_id": channel_id,
                    "channel_name": channel.get("name", channel_id),
                    "genre_id": genre_id,
                    "genre_name": genre.get("name", genre_id),
                    "theme_id": None,
                    "theme_name": genre.get("name", genre_id),
                    "description": genre.get("desc", ""),
                })
                continue
            for theme in themes:
                if not isinstance(theme, dict):
                    continue
                items.append({
                    "id": f"{channel_id}.{genre_id}.{theme.get('id', theme.get('name', 'theme'))}",
                    "channel_id": channel_id,
                    "channel_name": channel.get("name", channel_id),
                    "genre_id": genre_id,
                    "genre_name": genre.get("name", genre_id),
                    "theme_id": theme.get("id"),
                    "theme_name": theme.get("name", genre.get("name", genre_id)),
                    "description": theme.get("desc") or genre.get("desc", ""),
                })
    return {"items": items, "total": len(items)}


@app.get("/api/v1/health")
def health_check() -> dict[str, Any]:
    return {"status": "ok", "app": "woke_novel", "api_version": "v1", "workspace": str(WORKSPACE), "time": now_iso()}


@app.get("/api/v1/settings")
def settings() -> dict[str, Any]:
    return load_settings()


@app.patch("/api/v1/settings")
def patch_settings(patch: SettingsPatch) -> dict[str, Any]:
    current = read_json(CONFIG_FILE, {})
    for key, value in patch.model_dump(exclude_none=True).items():
        current[key] = value
    write_json(CONFIG_FILE, current)
    return {"ok": True, "message": "settings updated", "data": load_settings()}


@app.get("/api/v1/environment")
def environment() -> dict[str, Any]:
    missing = []
    for package in ["fastapi", "uvicorn", "pydantic"]:
        try:
            __import__(package.split("[", 1)[0])
        except Exception:
            missing.append(package)
    return {
        "python": {"available": True, "version": sys.version.split()[0], "path": sys.executable},
        "requirements": {"installed": not missing, "missing": missing},
        "claude": check_command("claude"),
        "codex": check_command("codex"),
        "filesystem": {
            "workspace_writable": os.access(WORKSPACE, os.W_OK),
            "projects_writable": os.access(PROJECTS_ROOT, os.W_OK),
            "logs_writable": os.access(LOGS_ROOT, os.W_OK),
        },
    }


@app.get("/api/v1/genre-presets")
def genre_presets(language: Literal["zh", "en"] = "zh") -> dict[str, Any]:
    return load_genre_presets(language)


@app.get("/api/v1/projects")
def projects(q: str | None = None) -> dict[str, Any]:
    PROJECTS_ROOT.mkdir(exist_ok=True)
    items = []
    for path in sorted([p for p in PROJECTS_ROOT.iterdir() if p.is_dir()], key=lambda p: p.name.lower()):
        item = project_summary(path.name)
        if q:
            needle = q.lower()
            haystack = " ".join(str(item.get(k) or "") for k in ["project_name", "novel_name", "genre"]).lower()
            if needle not in haystack:
                continue
        items.append(item)
    return {"items": items, "total": len(items)}


@app.post("/api/v1/projects")
async def create_project(req: ProjectCreateRequest) -> dict[str, Any]:
    validate_project_name(req.project_name)
    root = project_path(req.project_name, must_exist=False)
    if root.exists():
        raise ApiError(409, "PROJECT_EXISTS", f"Project exists: {req.project_name}", {"project": req.project_name})
    for dirname in PROJECT_DIRS:
        (root / dirname).mkdir(parents=True, exist_ok=True)
    target_word_count = req.target_word_count or SIZE_WORDS.get(req.novel_size, 300_000)
    info = {
        "project_name": req.project_name,
        "genre": req.genre,
        "language": req.language,
        "provider": req.provider,
        "novel_size": req.novel_size,
        "target_word_count": target_word_count,
        "user_description": req.user_description,
        "dry_run": req.dry_run,
        "created_at": now_iso(),
        "current_round": 1,
        "selected_option": None,
        "ref_works": None,
        "novel_name": None,
        "last_step": None,
        "last_step_at": None,
        "last_step_act": None,
        "last_step_round": None,
        "last_step_option_index": None,
        "last_step_phase": None,
        "workflow_version": 2,
        "option_count": req.option_count,
        "auto_select_option": req.auto_select_option,
        "pause": req.pause,
    }
    write_json(root / ".project_info.json", info)
    data: dict[str, Any] = {"project_name": req.project_name, "project_path": rel(root)}
    if req.start_immediately:
        mode = "creative" if req.option_count > 1 else "full"
        run = await start_run(
            req.project_name,
            mode,
            RunRequest(
                genre=req.genre,
                language=req.language,
                provider=req.provider,
                dry_run=req.dry_run,
                pause=req.pause,
                option_count=req.option_count,
                auto_select_option=req.auto_select_option,
                user_description=req.user_description,
                novel_size=req.novel_size,
                target_word_count=target_word_count,
            ),
        )
        data["run"] = run.public()
    return {"ok": True, "message": "project created", "data": data}


@app.get("/api/v1/projects/{project}")
def project_detail(project: str) -> dict[str, Any]:
    info = read_project_info(project)
    settings_data = load_settings()
    info.setdefault("language", settings_data["language"])
    info.setdefault("provider", settings_data["provider"])
    info["last_step_name"] = step_name(info.get("last_step"))
    generated, target, max_chapter_index = count_chapters(project)
    return {
        "info": info,
        "workflow": build_workflow_state(project),
        "chapter_progress": {"generated": generated, "target": info.get("total_chapters") or target, "max_index": max_chapter_index},
        "latest_artifacts": chapter_items(project)[-5:],
        "latest_run": active_run_public(project),
        "warnings": [],
    }


@app.delete("/api/v1/projects/{project}")
def delete_project(project: str, req: ProjectDeleteRequest = Body(default_factory=ProjectDeleteRequest)) -> dict[str, Any]:
    root = project_path(project)
    if req.confirm_text != project:
        raise ApiError(400, "CONFIRMATION_MISMATCH", "Confirmation text must match the project name", {"project": project})
    active = ACTIVE_BY_PROJECT.get(project)
    if active and RUNS.get(active) and RUNS[active].status in {"queued", "running"}:
        raise ApiError(409, "RUN_ALREADY_ACTIVE", f"Project already has active run: {project}", {"run_id": active})
    external = read_external_run_status(project)
    if external:
        raise ApiError(409, "RUN_ALREADY_ACTIVE", f"Project already has active CLI run: {project}", {"pid": external.get("pid"), "source": external.get("source", "cli")})

    deleted_paths = [rel(root)]
    shutil.rmtree(root)
    if req.delete_logs:
        log_root = log_project_path(project)
        if log_root.is_dir():
            shutil.rmtree(log_root)
            deleted_paths.append(rel(log_root))

    ACTIVE_BY_PROJECT.pop(project, None)
    return {"ok": True, "message": "project deleted", "data": {"project": project, "deleted_paths": deleted_paths}}


@app.post("/api/v1/projects/{project}/delete")
def delete_project_post(project: str, req: ProjectDeleteRequest = Body(default_factory=ProjectDeleteRequest)) -> dict[str, Any]:
    return delete_project(project, req)


@app.get("/api/v1/projects/{project}/workflow")
def workflow(project: str) -> dict[str, Any]:
    return build_workflow_state(project)


@app.get("/api/v1/projects/{project}/creative-options")
def list_creative_options(project: str) -> dict[str, Any]:
    project_path(project)
    items = creative_options(project)
    return {"project_name": project, "items": items, "total": len(items)}


@app.post("/api/v1/projects/{project}/creative-options/select")
def select_creative_option(project: str, req: CreativeOptionSelectRequest) -> dict[str, Any]:
    info = read_project_info(project)
    count = int(info.get("option_count") or len(creative_options(project)) or 1)
    if req.option_index > count:
        raise ApiError(400, "BAD_REQUEST", f"Creative option out of range: {req.option_index}", {"option_count": count})
    path = creative_option_path(project, req.option_index, info.get("language"))
    if not path.is_file():
        raise ApiError(404, "FILE_NOT_FOUND", f"Creative option not found: {req.option_index}", {"path": rel(path)})
    info["selected_option"] = req.option_index
    write_json(project_path(project) / ".project_info.json", info)
    return {"ok": True, "message": "creative option selected", "data": {"project": project, "selected_option": req.option_index}}


@app.post("/api/v1/projects/{project}/runs/creative")
async def run_creative(project: str, req: RunRequest) -> dict[str, Any]:
    return (await start_run(project, "creative", req)).public()


@app.post("/api/v1/projects/{project}/runs/full")
async def run_full(project: str, req: RunRequest) -> dict[str, Any]:
    return (await start_run(project, "full", req)).public()


@app.post("/api/v1/projects/{project}/runs/continue")
async def run_continue(project: str, req: RunRequest) -> dict[str, Any]:
    return (await start_run(project, "continue", req)).public()


@app.post("/api/v1/projects/{project}/runs/single")
async def run_single(project: str, req: RunRequest) -> dict[str, Any]:
    return (await start_run(project, "single", req)).public()


@app.post("/api/v1/projects/{project}/runs/cancel")
async def cancel_run(project: str) -> dict[str, Any]:
    return await cancel_project_run(project)


@app.get("/api/v1/projects/{project}/runs/{run_id}")
def get_run(project: str, run_id: str) -> dict[str, Any]:
    project_path(project)
    run = RUNS.get(run_id)
    if not run:
        raise ApiError(404, "RUN_NOT_FOUND", f"Run not found: {run_id}", {"run_id": run_id})
    return run.public()


@app.get("/api/v1/projects/{project}/runs/{run_id}/events")
async def run_events(project: str, run_id: str) -> StreamingResponse:
    project_path(project)
    run = RUNS.get(run_id)
    if not run:
        raise ApiError(404, "RUN_NOT_FOUND", f"Run not found: {run_id}", {"run_id": run_id})

    async def stream() -> AsyncGenerator[str, None]:
        for item in run.events:
            yield f"event: {item['event']}\ndata: {json.dumps(item['data'], ensure_ascii=False)}\n\n"
        while run.status in {"queued", "running"}:
            try:
                item = await asyncio.wait_for(run.queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield f"event: heartbeat\ndata: {json.dumps({'run_id': run_id, 'time': now_iso()}, ensure_ascii=False)}\n\n"
                continue
            if item["event"] == "end":
                break
            yield f"event: {item['event']}\ndata: {json.dumps(item['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/v1/projects/{project}/files")
def files(project: str, root: str = "", include_hidden: bool = False) -> dict[str, Any]:
    base = project_path(project)
    scan_root = base if not root else safe_child(base, root)
    if not scan_root.is_dir():
        raise ApiError(400, "BAD_REQUEST", "File tree root must be a directory", {"root": root})
    items = []
    for child in sorted(scan_root.iterdir(), key=natural_key):
        node = file_node(base, child, include_hidden)
        if node:
            items.append(node)
    return {"project_name": project, "root": root, "items": items}


@app.get("/api/v1/projects/{project}/files/content")
def file_content(project: str, path: str = Query(...)) -> dict[str, Any]:
    base = project_path(project)
    target = safe_child(base, path)
    if not target.is_file():
        raise ApiError(400, "BAD_REQUEST", "Path is not a file", {"path": path})
    data = target.read_bytes()
    content, encoding = decode_text(data)
    return {
        "project_name": project,
        "relative_path": target.relative_to(base).as_posix(),
        "kind": file_kind(target),
        "encoding": encoding,
        "content": content,
        "size": len(data),
        "updated_at": datetime.fromtimestamp(target.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "editable": file_kind(target) in {"markdown", "text", "json"},
    }


@app.put("/api/v1/projects/{project}/files/content")
def save_file_content(project: str, req: FileContentSaveRequest) -> dict[str, Any]:
    base = project_path(project)
    target = safe_child(base, req.path)
    if not target.is_file():
        raise ApiError(400, "BAD_REQUEST", "Path is not a file", {"path": req.path})
    if file_kind(target) not in {"markdown", "text", "json"}:
        raise ApiError(400, "UNSUPPORTED_FILE_TYPE", "Only text files can be edited", {"path": req.path})
    target.write_text(req.content, encoding="utf-8", newline="\n")
    data = target.read_bytes()
    content, encoding = decode_text(data)
    return {
        "project_name": project,
        "relative_path": target.relative_to(base).as_posix(),
        "kind": file_kind(target),
        "encoding": encoding,
        "content": content,
        "size": len(data),
        "updated_at": datetime.fromtimestamp(target.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "editable": True,
    }


@app.get("/api/v1/projects/{project}/chapters")
def chapters(project: str) -> dict[str, Any]:
    info = read_project_info(project)
    items = chapter_items(project)
    return {
        "project_name": project,
        "source_dir": "02_output",
        "generated": len(items),
        "target": info.get("total_chapters"),
        "total_words": sum(item["word_count"] for item in items),
        "items": items,
    }


@app.get("/api/v1/projects/{project}/export/check")
def export_check(project: str) -> dict[str, Any]:
    return build_export_check(project)


@app.post("/api/v1/projects/{project}/export")
def export_project(project: str, req: ExportRequest) -> dict[str, Any]:
    root = project_path(project)
    check = build_export_check(project)
    if req.fail_on_check_error and any(item["status"] == "failed" for item in check["checks"]):
        raise ApiError(400, "EXPORT_CHECK_FAILED", "Export check failed", {"check": check})
    formats = set(req.formats)
    if "all" in formats:
        formats = {"md", "txt", "epub"}
    title = safe_export_title(req.novel_title or read_project_info(project).get("novel_name") or project)
    chapters_data = []
    for item in check["chapters"]:
        content = safe_child(root, item["relative_path"]).read_text(encoding="utf-8", errors="replace").strip()
        chapters_data.append((item["title"], content))
    merged = "\n\n".join(content for _, content in chapters_data).strip() + "\n"
    outputs = []
    if "md" in formats:
        md_path = root / f"{title}.md"
        md_path.write_text(merged, encoding="utf-8")
        outputs.append({"format": "md", "relative_path": md_path.relative_to(root).as_posix(), "size": md_path.stat().st_size, "created_at": now_iso()})
    if "txt" in formats:
        txt_path = root / f"{title}.txt"
        txt_path.write_text(re.sub(r"[*#`>_]", "", merged), encoding="utf-8")
        outputs.append({"format": "txt", "relative_path": txt_path.relative_to(root).as_posix(), "size": txt_path.stat().st_size, "created_at": now_iso()})
    if "epub" in formats:
        try:
            from ebooklib import epub  # type: ignore
        except Exception as exc:
            raise ApiError(424, "CLI_NOT_AVAILABLE", "EPUB export requires ebooklib", {"error": str(exc)})
        book = epub.EpubBook()
        book.set_identifier(f"woke_novel_{project}_{int(time.time())}")
        book.set_title(title)
        book.set_language(read_project_info(project).get("language", "zh"))
        epub_chapters = []
        for index, (chapter_title_text, content) in enumerate(chapters_data, start=1):
            chapter = epub.EpubHtml(title=chapter_title_text, file_name=f"chap_{index:03d}.xhtml", lang="zh")
            body = "<br/>".join(line for line in content.splitlines())
            chapter.content = f"<h1>{chapter_title_text}</h1><p>{body}</p>"
            book.add_item(chapter)
            epub_chapters.append(chapter)
        book.toc = tuple(epub_chapters)
        book.spine = ["nav", *epub_chapters]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        epub_path = root / f"{title}.epub"
        epub.write_epub(str(epub_path), book)
        outputs.append({"format": "epub", "relative_path": epub_path.relative_to(root).as_posix(), "size": epub_path.stat().st_size, "created_at": now_iso()})
    return {"ok": True, "message": "export completed", "data": {"project_name": project, "outputs": outputs, "check": check if req.include_check else None}}


@app.get("/api/v1/projects/{project}/logs")
def logs(project: str) -> dict[str, Any]:
    project_path(project)
    root = LOGS_ROOT / project
    if not root.is_dir():
        return {"items": [], "total": 0}
    items = []
    for path in sorted([p for p in root.iterdir() if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True):
        match = re.search(r"_step_([0-9a-zA-Z]+)", path.name)
        run_match = re.match(r"(run_[0-9_]+_[a-f0-9]+|run)\.log$", path.name)
        items.append({
            "log_id": path.name,
            "project_name": project,
            "run_id": run_match.group(1) if run_match else None,
            "created_at": datetime.fromtimestamp(path.stat().st_ctime).astimezone().isoformat(timespec="seconds"),
            "updated_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
            "size": path.stat().st_size,
            "status": "unknown",
            "step": match.group(1) if match else None,
            "provider": None,
            "relative_path": path.name,
            "source": "run" if run_match else "step",
        })
    return {"items": items, "total": len(items)}


@app.get("/api/v1/projects/{project}/logs/{log_id}")
def log_content(project: str, log_id: str, tail: int | None = None, q: str | None = None) -> dict[str, Any]:
    project_path(project)
    if "/" in log_id or "\\" in log_id or ".." in log_id:
        raise ApiError(400, "PATH_OUT_OF_SCOPE", "Invalid log id", {"log_id": log_id})
    root = LOGS_ROOT / project
    target = safe_child(root, log_id)
    if not target.is_file():
        raise ApiError(404, "FILE_NOT_FOUND", f"Log not found: {log_id}", {"log_id": log_id})
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    if q:
        lines = [line for line in lines if q.lower() in line.lower()]
    truncated = False
    if tail and tail > 0 and len(lines) > tail:
        lines = lines[-tail:]
        truncated = True
    return {"log_id": log_id, "project_name": project, "content": "\n".join(lines), "line_count": len(lines), "truncated": truncated}


if FRONTEND_DIST.exists():
    app.mount("/", NoCacheStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


def main() -> None:
    import uvicorn

    uvicorn.run("app_server.main:app", host="127.0.0.1", port=8787, reload=False)


if __name__ == "__main__":
    main()
