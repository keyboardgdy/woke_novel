# -*- coding: utf-8 -*-
"""
工作流运行器核心类 —— 三层架构：模板 + 变量替换 + CLI 执行。

所有显示都委托给 ui 模块（步骤卡片、耗时、错误/警告/成功提示）。
"""

import os
import subprocess
import sys
import time
import uuid
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import ui
from ui import C, I, error, info, line, note, print_section, prompt as ui_prompt, step_header, \
    step_result, spinner, success, warn
from path_resolver import PathResolver, PROJECTS_ROOT, LOGS_ROOT
from project_structure import ProjectStructure
from project_info import ProjectInfo, create_project_info

# 步骤定义（序号 -> 名称）
STEP_FILES = {
    "01": "01 创意方案生成.md",
    "02": "02 创意方案补充.md",
    "03": "03 世界观与设定生成.md",
    "04": "04 人物档案与人物关系.md",
    "05": "05 故事主轴.md",
    "05a": "05a 幕次框架.md",
    "05b": "05b 幕次核心骨架.md",
    "06": "06 开篇剧情提取.md",
    "07": "07 开篇剧情梗概.md",
    "08": "08 开篇写作指南.md",
    "09": "09 开篇正文创作.md",
    "10": "10 状态文档.md",
    "11": "11 剧情生成方向指导.md",
    "12": "12 剧情梗概设计.md",
    "13": "13 写作指南.md",
    "14": "14 正文创作.md",
    "15": "15 状态文档.md",
    "16": "16 故事梗概精简.md",
    "17": "17 幕次故事梗概精简.md",
    "18": "18 项目级 CLAUDE.md.md",
}

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
    "16": "幕次故事梗概精简",
    "17": "故事梗概精简",
    "18": "项目级 CLAUDE.md",
}


# 中文数字解析（支持 0-99，兼容 "三"/"十"/"十二"/"二十"/"二十六" 等写法）
_CN_DIGITS = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
              '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}


def _parse_int_token(token: str) -> Optional[int]:
    """把阿拉伯数字或中文数字 token 解析成 int，失败返回 None（不抛异常）。"""
    if not token:
        return None
    if token.isdigit():
        return int(token)
    if token == '十':
        return 10
    if token.startswith('十'):
        rest = token[1:]
        if not rest:
            return 10
        d = _CN_DIGITS.get(rest)
        return 10 + d if d is not None else None
    if '十' in token:
        a, b = token.split('十', 1)
        tens = _CN_DIGITS.get(a)
        if tens is None:
            return None
        if not b:
            return tens * 10
        ones = _CN_DIGITS.get(b)
        return tens * 10 + ones if ones is not None else None
    return _CN_DIGITS.get(token)


def _prompt_int_fallback(label: str, hint: str = "") -> Optional[int]:
    """提取失败时让用户手动输入正整数。

    - 交互式 TTY：循环直到用户输入合法正整数；空回车 / `q` 视为主动跳过，返回 None。
    - 非交互环境（管道、CI）：直接 warn + 返回 None，不阻塞。
    - 任何异常（EOFError / KeyboardInterrupt）也视为跳过。

    返回的整数保证 > 0；跳过时返回 None，由调用方决定降级策略。
    """
    if not sys.stdin.isatty():
        warn(f"非交互环境，无法手动兜底输入「{label}」")
        return None

    line(color=C.DIM)
    warn(f"「{label}」自动提取失败，进入手动兜底输入")
    if hint:
        note(hint)
    note("提示：输入正整数确认；直接回车或输入 q 跳过（流程将降级处理）")

    def _valid(s: str) -> bool:
        s = s.strip()
        if s == "" or s.lower() == "q":
            return True  # 允许跳过
        return s.isdigit() and int(s) > 0

    try:
        raw = ui_prompt(f"请手动输入「{label}」", default="", validator=_valid)
    except (EOFError, KeyboardInterrupt):
        print()
        warn(f"已取消「{label}」的手动输入")
        return None

    raw = (raw or "").strip()
    if not raw or raw.lower() == "q":
        warn(f"用户跳过「{label}」的手动输入")
        return None

    n = int(raw)
    success(f"已手动设置「{label}」= {n}")
    return n


class WorkflowRunner:
    """工作流运行器 - 三层架构"""

    def __init__(self, project_name: str, genre: str = "都市", dry_run: bool = False,
                 auto_create: bool = True, max_retries: int = 3,
                 novel_size: str = "中篇", target_word_count: int = 300_000,
                 provider: str = "claude"):
        self.project_name = project_name
        self.genre = genre
        self.dry_run = dry_run
        self.provider = self._normalize_provider(provider)
        self.novel_size = novel_size
        self.target_word_count = target_word_count
        self.round = 1
        self.option_index = None  # 当前选中的创意方案编号
        self.ref_works = ""  # 从创意方案提取的参考作品，用于提示词渲染
        self._step_sequence = 0  # 全局步骤序号
        self._current_act_num = None  # 当前幕次
        self._session_counter = 0  # 会话序号
        self._session_number_map = {}  # display_id → 会话编号

        # 失败重试配置：步骤失败时自动重试次数（不含首次），指数退避 2s/4s/8s
        self.max_retries = max_retries
        self._retry_backoff_base = 2.0

        # 干运行默认章节数配置
        self._dry_default_chapter_counts = [12, 10, 8]  # 各幕章节数默认值
        self._dry_default_act_count = 3  # 幕次总数默认值
        self._dry_default_total_chapters = 30  # 总章节数默认值

        # 自动创建项目结构
        if auto_create:
            self.project_structure = ProjectStructure(project_name, PROJECTS_ROOT)
            self.project_structure.create()

        # 创建路径解析器
        self.path_resolver = PathResolver(project_name, genre,
                                          novel_size=novel_size,
                                          target_word_count=target_word_count)

        # 项目信息管理
        self.project_info = ProjectInfo(project_name)
        if not self.project_info.info_file.exists():
            self.project_info.initialize(genre, novel_size=novel_size,
                                         target_word_count=target_word_count)
            self.genre = genre
        else:
            # 从项目信息文件读取已保存的数据
            self.genre = self.project_info.genre or genre
            self.novel_size = self.project_info.novel_size or novel_size
            self.target_word_count = self.project_info.target_word_count or target_word_count
            self.option_index = self.project_info.selected_option
            self.ref_works = self.project_info.ref_works or ""
            self.round = self.project_info.current_round
            # 同步到 path_resolver（构造时已用入参建过，这里覆盖成项目档案里的值）
            self.path_resolver.novel_size = self.novel_size
            self.path_resolver.target_word_count = self.target_word_count

        # 会话管理
        self._session_uuids: Dict[str, str] = {}

    def make_display_id(self, session_name: str) -> str:
        """生成会话ID"""
        return f"novel_{self.project_name}_{session_name}"

    def load_step_template(self, step: str) -> str:
        """第一层：加载 .md 模板"""
        return self.path_resolver.load_step_template(step)

    def resolve_prompt(self, template: str, option_index: int = None, user_description: str = "",
                       ref_works: str = None, act_num: int = None, phase: Optional[str] = None,
                       novel_size: str = None, target_word_count: int = None) -> str:
        """第二层：替换 {变量} 为实际路径"""
        if option_index is None:
            option_index = self.option_index
        if ref_works is None:
            ref_works = self.ref_works
        return self.path_resolver.resolve(template, round_num=self.round, option_index=option_index,
                                          user_description=user_description, ref_works=ref_works,
                                          act_num=act_num, phase=phase,
                                          novel_size=novel_size or self.novel_size,
                                          target_word_count=target_word_count or self.target_word_count)

    def _retry_backoff(self, retry_num: int) -> float:
        """第 N 次重试前的等待秒数（指数退避 2s, 4s, 8s ...）"""
        return self._retry_backoff_base * (2 ** (retry_num - 1))

    @staticmethod
    def _normalize_provider(provider: str) -> str:
        """规范化 CLI 后端名称。"""
        normalized = (provider or "claude").strip().lower()
        if normalized not in {"claude", "codex"}:
            raise ValueError(f"不支持的 CLI 后端: {provider}（可选: claude / codex）")
        return normalized

    def execute_step(self, step: str, prompt: str, display_id: str,
                     session_uuid: str = None, resume: bool = False) -> Optional[subprocess.CompletedProcess]:
        """第三层：调用外部 CLI 后端执行

        resume: 是否使用 --resume 继续已有会话

        失败自动重试：超时或 returncode != 0 时按 self.max_retries 次数重试。
        重试复用同一 session_uuid（从第二次起切换为 --resume 续接上下文），
        退避策略指数递增 2s/4s/8s。
        """
        if session_uuid is None:
            session_uuid = str(uuid.uuid4())

        mode = "dry" if self.dry_run else "run"
        step_header(step, STEP_NAMES.get(step, step), display_id, mode=mode)

        if self.dry_run:
            note(f"干运行 · 模板 {STEP_FILES.get(step, 'unknown')}")
            dry_result = self._dry_result()
            self._log_step(step, prompt, [(dry_result, 1)], display_id, session_uuid)
            step_result(True, message=f"(干运行) 已跳过 {self.provider} 调用")
            return dry_result

        # 检查外部 CLI 命令
        cli_cmd = self._find_cli_command(self.provider)
        if not cli_cmd:
            error(self._missing_cli_message(self.provider))
            return None

        # 临时文件传递 prompt
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', encoding='utf-8', delete=False)
        try:
            temp_file.write(prompt)
            temp_file.flush()
            temp_path = temp_file.name
            temp_file.close()

            class _AttemptResult:
                def __init__(self, returncode, stdout, stderr, elapsed, timed_out, session_id=None):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
                    self.elapsed = elapsed
                    self.timed_out = timed_out
                    self.session_id = session_id

            max_attempts = self.max_retries + 1  # 首次 + N 次重试
            attempts: List[tuple] = []
            result: Optional[_AttemptResult] = None
            effective_session_uuid = session_uuid if self.provider == "claude" or resume else None

            for attempt in range(1, max_attempts + 1):
                is_retry = attempt > 1
                if is_retry:
                    backoff = self._retry_backoff(attempt - 1)
                    warn(
                        f"↻ 步骤 {step} 重试 {attempt - 1}/{self.max_retries}"
                        f"（{backoff:.0f}s 后开始 · 续接会话 {session_uuid[:8]}）"
                    )
                    time.sleep(backoff)

                # 重试时强制续接上下文；Codex 首次执行后会尽量从 JSONL 输出解析真实 session id。
                effective_resume = resume or is_retry
                if self.provider == "codex" and not effective_session_uuid:
                    effective_resume = False
                cmd, stdin_payload = self._build_cli_command(
                    cli_cmd, temp_path, prompt, effective_session_uuid, effective_resume
                )

                spinner_label = (
                    f"调用 {self.provider}（{I.STEP} {step}"
                    + (f" · 重试 {attempt - 1}" if is_retry else "")
                    + "）"
                )

                # 调用外部 CLI，期间显示 spinner + elapsed
                start = time.monotonic()
                timed_out = False
                try:
                    with spinner(spinner_label, color=C.PRIMARY):
                        process = subprocess.Popen(
                            cmd,
                            shell=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE if stdin_payload is not None else None,
                            cwd=self.path_resolver.project_root,
                        )
                        try:
                            input_bytes = stdin_payload.encode("utf-8") if stdin_payload is not None else None
                            stdout, stderr = process.communicate(input=input_bytes, timeout=1800)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            stdout, stderr = process.communicate()
                            timed_out = True
                            warn("命令执行超时（>1800s）")
                except FileNotFoundError as e:
                    error(f"启动子进程失败：{e}")
                    return None

                elapsed = time.monotonic() - start
                result = _AttemptResult(
                    returncode=process.returncode,
                    stdout=stdout.decode('utf-8', errors='ignore') if stdout else "",
                    stderr=stderr.decode('utf-8', errors='ignore') if stderr else "",
                    elapsed=elapsed,
                    timed_out=timed_out,
                )
                if self.provider == "codex":
                    parsed_session_id = self._extract_codex_session_id(result.stdout)
                    if parsed_session_id:
                        result.session_id = parsed_session_id
                        effective_session_uuid = parsed_session_id
                        self._session_uuids[display_id] = parsed_session_id
                attempts.append((result, attempt))

                if result.returncode == 0:
                    if is_retry:
                        success(f"步骤 {step} 在第 {attempt}/{max_attempts} 次尝试时成功")
                    step_result(True, elapsed=elapsed)
                    break

                err = (
                    f"超时（>1800s）" if timed_out
                    else (result.stderr[:200] if result.stderr else "unknown error")
                )
                if attempt < max_attempts:
                    warn(f"步骤 {step} 第 {attempt}/{max_attempts} 次尝试失败：{err}")
                else:
                    step_result(False, message=err, elapsed=elapsed)

            # 一次性记录所有尝试的日志（含重试）
            self._log_step(step, prompt, attempts, display_id, session_uuid)
            return result
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _dry_result(self):
        """干运行假结果"""
        class DryResult:
            returncode = 0
            stdout = "[干运行] 模拟成功"
            stderr = ""
            elapsed = 0.0
            timed_out = False
            session_id = None
        return DryResult()

    def _log_step(self, step: str, prompt: str, attempts: List[tuple], display_id: str, session_uuid: str):
        """记录步骤日志

        attempts: [(result, attempt_num), ...]  本次步骤的每次调用结果与序号
        （失败重试场景下长度 = 实际尝试次数）
        """
        log_dir = LOGS_ROOT / self.project_name
        log_dir.mkdir(parents=True, exist_ok=True)

        self._step_sequence += 1
        seq_str = f"{self._step_sequence}"
        act_str = f"_A{self._current_act_num}" if self._current_act_num else ""
        session_num = self._session_number_map.get(display_id, 0)
        session_str = f"C{session_num}" if session_num else ""
        log_file = log_dir / f"{seq_str}_step_{step}{act_str}_R{self.round}_{session_str}.log"

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"步骤: {step}\n")
            f.write(f"轮次: {self.round}\n")
            f.write(f"幕次: {self._current_act_num or 'N/A'}\n")
            f.write(f"显示ID: {display_id}\n")
            f.write(f"CLI后端: {self.provider}\n")
            f.write(f"会话UUID: {session_uuid}\n")
            f.write(f"时间: {datetime.now().isoformat()}\n")
            f.write(f"尝试次数: {len(attempts)}\n")
            f.write(f"\n--- Prompt ({len(prompt)} chars) ---\n")
            f.write(prompt)
            f.write("\n")
            for result, attempt in attempts:
                f.write(f"\n{'='*60}\n")
                f.write(f"--- 尝试 {attempt} ---\n")
                f.write(f"{'='*60}\n")
                f.write(f"返回码: {result.returncode}\n")
                f.write(f"耗时: {result.elapsed:.2f}s\n")
                if getattr(result, 'timed_out', False):
                    f.write(f"超时: 是\n")
                if getattr(result, 'session_id', None):
                    f.write(f"CLI会话ID: {result.session_id}\n")
                if result.stdout:
                    f.write(f"\n--- Stdout ({len(result.stdout)} chars) ---\n")
                    f.write(result.stdout)
                if result.stderr:
                    f.write(f"\n--- Stderr ---\n")
                    f.write(result.stderr)

    def _build_cli_command(self, cli_cmd: str, temp_path: str, prompt: str,
                           session_uuid: str, resume: bool) -> tuple[List[str], Optional[str]]:
        """构造指定后端的命令行。"""
        if self.provider == "claude":
            # list 形式 + shell=False：避免 shell 引号在带空格/中文路径时翻车。
            session_flag = ["--session-id", session_uuid] if not resume else ["--resume", session_uuid]
            cmd = [cli_cmd, f"@{temp_path}", *session_flag]
            # 整条流水线无 TTY，必须显式跳过权限确认，否则子进程会卡在 confirm 框直到 1800s 超时。
            cmd += ["--permission-mode", "bypassPermissions"]
            return cmd, None

        cmd = [
            cli_cmd, "exec",
            "--json",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
        ]
        if resume and session_uuid:
            cmd = [
                cli_cmd, "exec", "resume",
                "--json",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                session_uuid,
            ]
        cmd.append("-")
        return cmd, prompt

    def _find_cli_command(self, provider: str) -> Optional[str]:
        """查找外部 CLI 命令"""
        import shutil
        cmd = shutil.which(provider)
        if cmd:
            return cmd
        if os.name == 'nt':
            for name in [f"{provider}.cmd", f"{provider}.bat"]:
                cmd = shutil.which(name)
                if cmd:
                    return cmd
        return None

    def _missing_cli_message(self, provider: str) -> str:
        if provider == "codex":
            return "找不到 'codex' 命令（请确认 PATH 上有 codex / codex.cmd / codex.bat）"
        return "找不到 'claude' 命令（请确认 PATH 上有 claude / claude.cmd / claude.bat）"

    def _extract_codex_session_id(self, stdout: str) -> Optional[str]:
        """从 Codex `--json` JSONL 输出中尽量解析 session id。"""
        if not stdout:
            return None

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"session_id", "sessionId", "conversation_id", "conversationId"} and isinstance(item, str):
                        return item
                    found = walk(item)
                    if found:
                        return found
            elif isinstance(value, list):
                for item in value:
                    found = walk(item)
                    if found:
                        return found
            return None

        for line_text in stdout.splitlines():
            line_text = line_text.strip()
            if not line_text:
                continue
            try:
                payload = json.loads(line_text)
            except json.JSONDecodeError:
                continue
            found = walk(payload)
            if found:
                return found
        return None

    def _rename_logs(self, old_name: str, new_name: str) -> None:
        """同步迁移日志目录（如果存在）"""
        old_logs = LOGS_ROOT / old_name
        new_logs = LOGS_ROOT / new_name
        if not old_logs.exists():
            return
        if new_logs.exists():
            warn(f"日志目标目录已存在，跳过迁移: {new_logs}")
            return
        try:
            old_logs.rename(new_logs)
            success(f"日志目录已重命名: {old_logs.name} → {new_logs.name}")
        except Exception as e:
            warn(f"日志目录迁移失败（项目目录已重命名）: {e}")

    def rename_project(self, new_name: str) -> bool:
        """重命名项目文件夹"""
        old_name = self.project_name
        old_path = PROJECTS_ROOT / old_name
        new_path = PROJECTS_ROOT / new_name
        if not old_path.exists():
            error(f"项目路径不存在: {old_path}")
            return False
        if new_path.exists():
            warn(f"目标路径已存在: {new_path}")
            return False
        try:
            old_path.rename(new_path)
            success(f"项目已重命名: {old_name} → {new_name}")
            self.project_name = new_name
            self.path_resolver = PathResolver(new_name, self.genre)
            self.project_info = ProjectInfo(new_name)
            self._rename_logs(old_name, new_name)
            return True
        except Exception as e:
            info(f"直接重命名失败，尝试复制+删除策略…")
            import shutil
            try:
                shutil.copytree(old_path, new_path)
                shutil.rmtree(old_path)
                success(f"项目已重命名: {old_name} → {new_name}")
                self.project_name = new_name
                self.path_resolver = PathResolver(new_name, self.genre)
                self.project_info = ProjectInfo(new_name)
                self._rename_logs(old_name, new_name)
                return True
            except Exception as e2:
                error(f"重命名失败: {e2}")
                return False

    def extract_novel_name_from_creative(self, option_num: int) -> Optional[str]:
        """从创意方案文件中提取小说名"""
        if self.dry_run:
            return "干运行小说"
        creative_file = PROJECTS_ROOT / self.project_name / "00_baseline" / f"创意方案_{option_num}.md"
        if not creative_file.exists():
            warn(f"创意方案文件不存在: {creative_file}")
            return None
        try:
            content = creative_file.read_text(encoding='utf-8')
            match = re.search(r'^#\s*创意方案[：:]\s*(.+)', content, re.MULTILINE)
            if match:
                novel_name = match.group(1).strip()
                # 移除文件名中的非法字符
                novel_name = re.sub(r'[<>:"/\\|?*《》]', '', novel_name)
                return novel_name
            else:
                warn("无法从创意方案中提取小说名")
                return None
        except Exception as e:
            warn(f"读取创意方案文件失败: {e}")
            return None

    def extract_ref_works_from_creative(self, option_num: int) -> Optional[str]:
        """从创意方案文件中提取参考作品，用于提示词渲染"""
        if self.dry_run:
            return "《干运行参考作品》"
        creative_file = PROJECTS_ROOT / self.project_name / "00_baseline" / f"创意方案_{option_num}.md"
        if not creative_file.exists():
            return None
        try:
            content = creative_file.read_text(encoding='utf-8')
            # 提取 ## 参考作品 部分
            match = re.search(r'^##\s*参考作品.*?\n(.*?)(?=^##)', content, re.MULTILINE | re.DOTALL)
            if not match:
                return None
            ref_section = match.group(1).strip()
            # 解析每一行，格式：- 《作品名》：描述
            works = []
            for line in ref_section.split('\n'):
                line = line.strip()
                if not line.startswith('- '):
                    continue
                # 去掉 "- " 前缀，保留《》及其内容
                rest = line[2:].strip()
                if rest.startswith('《') and '》' in rest:
                    end_idx = rest.index('》')
                    title = rest[1:end_idx]  # 提取作品名
                    works.append(f"《{title}》")
            return '、'.join(works) if works else None
        except Exception as e:
            warn(f"提取参考作品失败: {e}")
            return None

    def extract_summary_from_state(self, round_num: int) -> Optional[str]:
        """从状态文档提取本轮故事梗概"""
        if self.dry_run:
            return f"[干运行] 第{round_num}轮故事梗概占位内容"
        state_file = PROJECTS_ROOT / self.project_name / "03_state" / f"状态v{round_num}.md"
        if not state_file.exists():
            warn(f"状态文档不存在: {state_file}")
            return None
        try:
            content = state_file.read_text(encoding='utf-8')
            match = re.search(r'^# 故事总梗概\s*\n(.*?)(?=\n#|\n---|\Z)',
                              content, re.MULTILINE | re.DOTALL)
            return match.group(1).strip() if match else None
        except Exception as e:
            warn(f"提取故事梗概失败: {e}")
            return None

    def extract_and_create_story_summary(self, round_num: int) -> bool:
        """从状态文档提取梗概并创建故事总梗概.md"""
        summary = self.extract_summary_from_state(round_num)
        if not summary:
            warn(f"无法从状态v{round_num}提取故事梗概")
            return False
        summary_file = PROJECTS_ROOT / self.project_name / "03_state" / "故事总梗概.md"
        content = f"# 故事总梗概\n\n{summary}\n"
        summary_file.write_text(content, encoding='utf-8')
        success(f"已创建故事总梗概.md（来自状态v{round_num}）")
        return True

    def append_story_summary(self, round_num: int) -> bool:
        """从状态文档提取梗概并追加到故事总梗概.md"""
        summary = self.extract_summary_from_state(round_num)
        if not summary:
            warn(f"无法从状态v{round_num}提取故事梗概")
            return False
        summary_file = PROJECTS_ROOT / self.project_name / "03_state" / "故事总梗概.md"
        existing = summary_file.read_text(encoding='utf-8') if summary_file.exists() else ""
        updated = existing + f"{summary}\n"
        summary_file.write_text(updated, encoding='utf-8')
        success(f"已追加故事梗概到故事总梗概.md（来自状态v{round_num}）")
        return True

    def sync_summary_to_state(self, round_num: int) -> bool:
        """将故事总梗概.md内容同步到对应状态文档的# 故事总梗概部分"""
        if self.dry_run:
            note(f"干运行：跳过同步故事总梗概到状态v{round_num}.md")
            return True
        summary_file = PROJECTS_ROOT / self.project_name / "03_state" / "故事总梗概.md"
        if not summary_file.exists():
            warn("故事总梗概.md 不存在")
            return False
        summary_content = summary_file.read_text(encoding='utf-8')
        # 去掉开头的 # 故事总梗概 标题
        summary_text = re.sub(r'^#\s*故事总梗概\s*\n*', '', summary_content, flags=re.MULTILINE).strip()

        state_file = PROJECTS_ROOT / self.project_name / "03_state" / f"状态v{round_num}.md"
        if not state_file.exists():
            warn(f"状态文档不存在: {state_file}")
            return False
        state_content = state_file.read_text(encoding='utf-8')
        # 替换 # 故事总梗概 部分
        new_state_content = re.sub(
            r'^#\s*故事总梗概\s*\n.*?(?=\n#|\n---|\Z)',
            f"# 故事总梗概\n\n{summary_text}",
            state_content,
            flags=re.MULTILINE | re.DOTALL
        )
        state_file.write_text(new_state_content, encoding='utf-8')
        success(f"已将故事总梗概同步到状态v{round_num}.md")
        return True

    def extract_act_count_from_macro_model(self) -> Optional[int]:
        """从幕次框架.md中提取幕次总数"""
        if self.dry_run:
            note(f"干运行：幕次总数 = {self._dry_default_act_count}")
            return self._dry_default_act_count
        macro_file = PROJECTS_ROOT / self.project_name / "00_baseline" / "幕次框架.md"
        if not macro_file.exists():
            warn(f"幕次框架.md 不存在: {macro_file}")
            return _prompt_int_fallback("幕次总数", hint=f"未找到文件: {macro_file}")
        try:
            content = macro_file.read_text(encoding='utf-8')
            match = re.search(r'幕次总数[：:\s]*(\d+|[零一二三四五六七八九十]{1,3})\s*幕', content)
            if match:
                num_str = match.group(1)
                act_count = _parse_int_token(num_str)
                if act_count is None:
                    warn(f"无法解析幕次数字: {num_str}")
                    return _prompt_int_fallback(
                        "幕次总数",
                        hint=f"正则捕获到 {num_str!r} 但无法转 int",
                    )
                note(f"提取幕次总数：{act_count}")
                return act_count
            warn("无法从幕次框架.md 中提取幕次总数")
            return _prompt_int_fallback(
                "幕次总数",
                hint=f"在 {macro_file.name} 中未匹配到 '幕次总数：N 幕' 模式",
            )
        except Exception as e:
            warn(f"提取幕次总数失败: {e}")
            return _prompt_int_fallback(
                "幕次总数",
                hint=f"读取/解析 {macro_file.name} 时异常: {e}",
            )

    def extract_chapter_count_from_skeleton(self, act_num: int) -> Optional[int]:
        """从核心骨架_{act_num}.md中提取章节数"""
        if self.dry_run:
            chapter_count = self._dry_default_chapter_counts[act_num - 1] if act_num <= len(self._dry_default_chapter_counts) else 12
            note(f"干运行：第 {act_num} 幕章节数 = {chapter_count}")
            return chapter_count
        label = f"第 {act_num} 幕章节数"
        skeleton_file = PROJECTS_ROOT / self.project_name / "00_baseline" / f"核心骨架_{act_num}.md"
        if not skeleton_file.exists():
            warn(f"核心骨架_{act_num}.md 不存在: {skeleton_file}")
            return _prompt_int_fallback(label, hint=f"未找到文件: {skeleton_file}")
        try:
            content = skeleton_file.read_text(encoding='utf-8')
            match = re.search(r'章节数[：:\s]*(\d+|[零一二三四五六七八九十]{1,3})\s*章', content)
            if match:
                num_str = match.group(1)
                chapter_count = _parse_int_token(num_str)
                if chapter_count is None:
                    warn(f"无法解析章节数字: {num_str}")
                    return _prompt_int_fallback(
                        label,
                        hint=f"正则捕获到 {num_str!r} 但无法转 int",
                    )
                note(f"提取{label}：{chapter_count}")
                return chapter_count
            warn(f"无法从核心骨架_{act_num}.md 中提取章节数")
            return _prompt_int_fallback(
                label,
                hint=f"在 {skeleton_file.name} 中未匹配到 '章节数：N 章' 模式",
            )
        except Exception as e:
            warn(f"提取章节数失败: {e}")
            return _prompt_int_fallback(
                label,
                hint=f"读取/解析 {skeleton_file.name} 时异常: {e}",
            )

    def extract_all_chapter_counts(self, act_count: int) -> List[int]:
        """从所有核心骨架中提取章节数"""
        if self.dry_run:
            chapter_counts = self._dry_default_chapter_counts[:act_count] if act_count <= len(self._dry_default_chapter_counts) else self._dry_default_chapter_counts * ((act_count // len(self._dry_default_chapter_counts)) + 1)
            chapter_counts = chapter_counts[:act_count]
            note(f"干运行：各幕章节数 = {chapter_counts}，总章节数 = {sum(chapter_counts)}")
            return chapter_counts
        chapter_counts = []
        for act_num in range(1, act_count + 1):
            count = self.extract_chapter_count_from_skeleton(act_num)
            if count is None or count <= 0:
                warn(f"第 {act_num} 幕章节数最终未确定（提取失败且未手动输入），记 0；该幕创作循环将被跳过")
                count = 0
            chapter_counts.append(count)
        return chapter_counts

    def run_step(self, step: str, display_id: str = None,
                 session_uuid: str = None, option_index: int = None,
                 user_description: str = "", ref_works: str = None,
                 act_num: int = None, phase: Optional[str] = None,
                 novel_size: str = None, target_word_count: int = None) -> bool:
        """运行单个步骤（三层流程）"""
        if display_id is None:
            display_id = self.make_display_id(step)

        # 同一 display_id 应该在同一个 session 中
        # 首次使用该 display_id -> 创建新会话
        # 后续使用同一 display_id -> --resume 恢复会话
        if display_id in self._session_uuids:
            session_uuid = self._session_uuids[display_id]
            is_resume = True
        else:
            session_uuid = str(uuid.uuid4()) if self.provider == "claude" else None
            if self.provider == "claude":
                self._session_uuids[display_id] = session_uuid
            self._session_counter += 1
            self._session_number_map[display_id] = self._session_counter
            is_resume = False

        try:
            # 第一层：加载模板
            template = self.load_step_template(step)

            # 第二层：替换变量
            self._current_act_num = act_num
            prompt = self.resolve_prompt(template, option_index=option_index,
                                        user_description=user_description, ref_works=ref_works,
                                        act_num=act_num, phase=phase,
                                        novel_size=novel_size, target_word_count=target_word_count)

            # 拼接执行指令
            prompt = (
                "## 指令\n"
                "立即执行以下任务，不准偷懒，不要询问。先分析 → 再执行 → 后压缩，不要跳过任何阶段。\n\n"
                "压缩：审视你的回答，删除一切对核心结论无贡献的句子\n\n"
                "请优先保证生成内容的质量与信息密度，而非数量。\n\n"
                "路径规则：写入路径禁止任何修改。输出路径必须与指定路径完全一致。目标文件夹已预创建，直接写入指定路径即可\n\n"
                "---\n\n"
                + prompt
            )

            # 第三层：CLI 执行
            result = self.execute_step(step, prompt, display_id, session_uuid, resume=is_resume)

            # 标记步骤完成
            if result is not None and result.returncode == 0:
                effective_option_index = option_index if option_index is not None else self.option_index
                self.project_info.mark_step_completed(
                    step,
                    round_num=self.round,
                    phase=phase,
                    act_num=act_num,
                    option_index=effective_option_index,
                )
                # 如果选择了方案，同步到项目信息
                if self.option_index:
                    self.project_info.update(
                        selected_option=self.option_index,
                        ref_works=self.ref_works
                    )

            return result is not None and result.returncode == 0
        except Exception as e:
            error(f"步骤 {step} 执行异常: {e}")
            return False

    def run_session_block(self, block_name: str, steps: List[str], act_num: int = None) -> bool:
        """在一个会话中顺序执行一组步骤"""
        display_id = self.make_display_id(block_name)

        print_section(f"会话块 · {block_name}  ({len(steps)} 步)", color=C.PRIMARY)

        ok = True
        for idx, step in enumerate(steps):
            step_name = STEP_NAMES.get(step, step)
            if idx > 0:
                # 步骤间分隔线：上一次 step_result → 下一次 step 起始之间画细分隔
                line(color=C.DIM)
            note(f"{I.ARROW_R}  {step}  {step_name}")

            if not self.run_step(step, display_id, act_num=act_num):
                error(f"步骤 {step} 失败，停止当前会话块")
                ok = False
                break

        return ok
