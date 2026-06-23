# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

`woke_novel` 是一个驱动外部模型 CLI（**Claude CLI** 或 **Codex CLI**）写**中 / 英**长篇网文的工作流工具。运行器不直接产出文字，而是按流水线顺序调用所选 CLI，把 `steps/`（中文）或 `steps_en/`（English）下的 Markdown 模板填入变量后投喂给它，让模型把每一步产物（创意方案、世界观、人物、剧情、正文、状态…）落到 `projects/<小说名>/` 对应子目录里。UI 文案走 `i18n/{zh,en}.json`（`i18n.py` 的 `t()` 加载），通过 `--language zh|en` 或菜单切换；模板语言由 `PathResolver` 按 `language` 自动选 `steps/` 还是 `steps_en/`。

模板里夹带硬约束（`steps/00 创作宪法.md`、`steps/00 故事演化核心原则.md`、`steps/00 流程编排.md`、`steps/00 六大创意激发技巧.md`，英文版在 `steps_en/00 *.md`）和题材选型建议（`docs/AI 擅长题材.md`），修改步骤模板前先看这五份。

## 三层架构

文件分工：

- `workflow_runner.py` — `WorkflowRunner`（`workflow_runner.py:187`）+ `STEP_FILES`/`STEP_NAMES`（`workflow_runner.py:37,73`）+ 日志/session 调度；重试 / provider 切换 / Codex thread-id 解析都在这里。
- `path_resolver.py` — `PathResolver.resolve()`（`path_resolver.py:61`）做模板变量替换，`STEP_FILE_MAP` / `STEP_FILE_MAP_EN`（`path_resolver.py:20` 起）必须与 `STEP_FILES` 同步维护。
- `project_info.py` — `ProjectInfo` 读 / 写 `projects/<name>/.project_info.json`，是断点依据。
- `project_structure.py` — 项目首次构造时自动建出 `00_baseline/` ~ `04_characters/` 6 个子目录（`project_structure.py:13`）。
- `run_workflow.py` — 顶层 CLI（`init` / `loop` / `continue` / `single` / `session`），负责把 `WorkflowRunner` 按编排跑起来。
- `cli.py` — `run_workflow.py init` 用的交互式提示模块（`ask_genre` / `ask_novel_size` / `ask_project_name` / `ask_user_description` / `print_banner`），所有 `loop` / `continue` 跑前都会先调它。
- `menu.py`（+ `menu.bat`）— 交互式菜单，封装 `single` / `full_loop` / `continue` 三种入口。
- `app_server/main.py` + `frontend/` + `woke.bat` / `woke_launcher.py` — 可视化控制台：FastAPI 后端（`python -m app_server.main` 监听 `127.0.0.1:8787`）+ Vite/React/TS 前端（`cd frontend && npm install && npm run build`），`woke` 一行命令拉起后端并开浏览器。
- `i18n.py` + `i18n/{zh,en}.json` — UI 文案翻译层；`i18n.t(key, **kwargs)` 在缺 key 时回退到中文。
- `ui.py` — 所有屏幕输出（步骤卡片、spinner、错误/警告/成功提示）走这里，runner 不直接 `print`。

每个步骤都走同一条三段管线：

1. **模板加载** — `path_resolver.PathResolver.load_step_template()`（`path_resolver.py:128`）读 `steps/<编号 名称>.md`。
2. **变量替换** — `WorkflowRunner.resolve_prompt()`（`workflow_runner.py:114`）→ `PathResolver.resolve()`（`path_resolver.py:61`）把 `{project}`、`{round}`、`{option_index}`、`{act_num}`、`{ref_works}`、`{prev_act_skeleton}` 等替换为绝对路径或值。**任何新步骤模板如果要写入文件，路径必须用这些变量，禁止硬编码绝对路径。**
3. **CLI 执行** — `WorkflowRunner.execute_step()`（`workflow_runner.py`）把渲染好的 prompt 写入临时文件，按 `provider` 起子进程：
   - Claude：`claude "@<temp>" --session-id/--resume <uuid> --permission-mode bypassPermissions`（Windows 上 `shutil.which` 也会找 `claude.cmd`/`claude.bat`）。
   - Codex：`codex exec ... --dangerously-bypass-approvals-and-sandbox`，thread id 由后端颁发并从 stdout 解析回写（不能本地 `uuid4` 伪造）。
   超时 1800s（30 分钟）。每一步日志写到 `logs/<name>/<seq>_step_<step>[_A<act>]_R<round>_C<session>.log`（`logs/` 与 `projects/` 平级，不再放在项目目录里；老项目里的 `projects/<name>/logs/` 保持原样不动）。Codex 的 stdout 默认会做 head/tail 截断，需要全量日志排查时设环境变量 `WOKE_NOVEL_CODEX_VERBOSE_LOG=1`。

### 关键不变量

- **同一 `display_id` 永远落到同一个 Claude/Codex session**：`WorkflowRunner._session_uuids` 是嵌套字典 `{"claude": {display_id: id}, "codex": {display_id: id}}`，按 provider 分桶以防跨 provider 误用。Claude 首次本地 `uuid4` 起新会话、后续命中即 `--resume` 续聊；Codex 首次不传 id（让后端颁发 thread id）、从 stdout 解析后回写，续接时由 `session_was_dead`（"no rollout found"）检测死链并丢 resume 标志重开。映射会持久化到 `.project_info.json` 的 `session_uuids`，`continue` 新进程会优先复用旧 CLI 会话。
- **重试语义**：`max_retries=3` 默认值，指数退避 2s/4s/8s。前 N-1 次重试沿用原 session 续接，**最后一次（第 3 次）重试刻意切到全新 session** —— 避免在已被污染的上下文里反复失败（参见 commit a5d17b7）。超时或非零 returncode 触发重试，超时阈值 1800s。
- **运行状态心跳**：`WorkflowRunner` 启动时写 `projects/<name>/.run_status.json`（`status: "running" / pid / token / provider / language / dry_run / started_at`），`atexit` 时清掉；可视化控制台通过这份文件判断是否有人正在跑、要不要拒绝并发。
- **`--dry` 模式**下完全不调 `claude`/`codex`，每步返回伪造的 `DryResult`，并走 `ProjectInfo`/`_dry_default_*` 占位分支，便于在没有外部 CLI 的环境跑通流程。
- **`ProjectInfo`**（`project_info.py`）持久化在 `projects/<name>/.project_info.json`，是 `continue` 续跑的断点依据：`last_step`、`last_step_round`、`last_step_act`、`last_step_phase`、`current_round`、`selected_option`、`ref_works`、`act_count`、`chapter_counts`、`total_chapters`、`novel_name`、`genre`、`novel_size`、`target_word_count`、按 provider 分桶的 `session_uuids`。`continue` 模式只覆盖循环段（`11-17`）和非循环段的单步重跑，不重做已完成的世界观/主轴。`genre` / `novel_size` / `target_word_count` 在 `WorkflowRunner.__init__` 优先于命令行参数加载，改完需要同步清理依赖它们的旧产物。
- **状态摘要的"提取-追加-同步"三件套**：`extract_summary_from_state()` → `append_story_summary()` → `sync_summary_to_state()`（`workflow_runner.py:336-402`），对应步骤 15/16/17 之间维护 `03_state/故事总梗概.md` 的流程。每幕最后还要把精简后的总梗概写回该幕最后一个 `状态v{n}.md`。

## 流水线与会话分组

完整流水线（`run_workflow.py loop`）按混合 provider session 切片：创意生成步骤 `01` 使用 Claude 的 `novel_<proj>_creative_option` 会话；正文创作步骤 `09` / `14` 以及 `Q2` 统一走 Claude，同一个 `novel_<proj>_drafting_claude` 会话贯穿全部章节；其他步骤走 Codex，按原阶段/轮次 display_id 切片。Claude 正文会话只有在失败重试的最后一次或会话失效时才会切新会话。

| 会话 | 步骤 | display_id 模式 | 备注 |
| --- | --- | --- | --- |
| 1 创意 | 01（×option_count 循环）→ 02 | Claude: `novel_<proj>_creative_option` | 01 走 Claude 生成多个创意方案；02 也走 Claude 补充选中方案；选完后用 `extract_novel_name_from_creative` 抽书名并 `rename_project` 把目录改成最终小说名 |
| 2 世界/人物 | 03 → 04 | `novel_<proj>_world` | |
| 3 主轴 | 05 → Q7 → Q7R → 05a → Q8 → Q8R，随后 05b → Q9 → Q9R（每幕一次），再 18（`post_05b`） | Claude: `novel_<proj>_arc`；所有幕次骨架共用 Claude: `novel_<proj>_arc_act` | Q7R/Q8R/Q9R 是门禁重构步骤，会覆盖对应主轴/幕次/骨架产物；Q8R 后调 `extract_act_count_from_macro_model` 拿幕数；05b 全部跑完调 `extract_all_chapter_counts` 拿每幕章节数和总章节数，并写回 `.project_info.json` |
| 4 开篇 | Q10 → 06 → 07 → Q4 → Q5 → Q6 → 08 → 09 → Q1 → Q2 → 10 | Codex: `novel_<proj>_opening`; Claude: `novel_<proj>_drafting_claude` | act_num=1；09/Q2 走 Claude 正文会话，其余走 Codex；10 之后 `extract_and_create_story_summary(1)` |
| 创作循环 | Q10 → 11 → 12 → Q4 → Q5 → Q6 → 13 → 14 → Q1 → Q2 → 15 → 16（每轮一轮） | Codex: `novel_<proj>_round_<n>`; Claude: `novel_<proj>_drafting_claude` | 第一幕章节数 -1 次（开篇已用掉一章），其余幕 `act_chapters` 次；14/Q2 走同一个 Claude 正文会话，其余走 Codex，16 紧跟 15 后在同一 round session 内执行 |
| 幕末 | 17，随后 18（`post_17`） | `novel_<proj>_act_<n>` | act 循环结束后跑一次；17 后用同一 act 会话刷新 `projects/<name>/CLAUDE.md`，最后 `sync_summary_to_state` 写回末轮状态文档 |

> 模板目录里另有 `steps/04a 更新人物档案与人物关系.md` 和 `steps/00 进阶提示技术.md` 两份文件，但都不在 `run_workflow.py loop` 的主循环里——前者是手动按需增量更新人物 JSON 的工具步骤，后者是早期探索残留；如要把它们纳入 `STEP_FILES` / `STEP_FILE_MAP` 需同步改两处。`steps/18 项目级 CLAUDE.md.md` 由 `run_workflow.py` 在 05b / 17 后**自动**调用（不需要用户在 `loop` 阶段手动触发），失败仅打印警告不阻断流程。

第一步执行前会要求用户确认开篇会话（`y/n/q`），中间用 `q` 退出会留下 `last_step` 断点供 `continue` 拾起。

## 运行命令

工具集入口有两个：

- `python menu.py`（Windows 还可以 `menu.bat`）— 交互式菜单：单步 / 完整 / 继续 / 步骤列表。所有路径都从脚本所在目录推。
- `python run_workflow.py <command> [args]` — CLI 入口：
  - `init` — 交互式建项目（询问题材 `genre`、项目名 `novel_name`、规模档 `novel_size`）。
  - `loop --project-name <name> --genre <g> [--provider claude|codex] [--option-count 3] [--language zh|en] [--novel-size 超短篇|中短篇|短篇|中篇|长篇|超长篇] [--dry]` — 跑完整流水线。
  - `continue --project-name <name> [--provider ...] [--language ...] [--dry]` — 从 `.project_info.json` 的 `last_step` 续跑。
  - `single <step> -p <name> -g <g> [--provider ...] [--language ...] [--max-retries N] [--dry]` — 跑单个步骤。
  - `session <block> <step1,step2,...> -p <name> -g <g> [--provider ...] [--language ...] [--dry]` — 在一个 CLI session 里顺序跑一组步骤。
- 单步模式下若 `step == "01" 且 option_count > 1`，菜单会自动循环 01 然后再调 02，无需手动 `session` 编排。
- 可视化控制台（管理项目 / 跑流程 / 读章节 / 看日志 / 导 EPUB）：先 `cd frontend && npm install && npm run build` 构建一次，再 `python -m app_server.main`（或 Windows 上一键 `woke`）开 `http://127.0.0.1:8787`。后端是 FastAPI（`app_server/main.py`），配套 `app_server/STEP_NAMES` / `STEP_ORDER` / `STAGES` 三张静态表给前端展示用。

执行前置：完整流程需要系统 PATH 上同时有 `claude`/`claude.cmd` 和 `codex`/`codex.cmd`，因为流程会按步骤混用两者；`--dry` 下可以省略。`--provider` 仍保留为兼容参数，但完整编排会按步骤路由：创意生成(01)、正文创作(09/14)和章节定向重写(Q2)用 Claude，其余用 Codex。`--language` 缺省 `zh`，`--novel-size` 缺省 `中篇`（30 万字；档位定义在 `cli.py:52` 的 `NOVEL_SIZES`，包含超短篇 8千-2万字、中短篇 2.5万-8万字、短篇 10 万、中篇 30 万、长篇 50 万、超长篇 100 万）。

## 项目目录结构

每个项目落在 `projects/<小说名>/` 下（`project_structure.py:13` 定义、首次 `WorkflowRunner` 构造时自动创建）：

```
projects/<name>/
├── .project_info.json   # 进度断点 + 元数据（ProjectInfo 读写）
├── .run_status.json     # 运行心跳（runner 写 / atexit 清理，给可视化控制台判活）
├── CLAUDE.md            # 步骤18 生成的项目级说明，未来 Claude 续写前先读这一份
├── 00_baseline/         # 创意方案_{n}.md、文风建议.md、世界观.md、故事主轴.md、幕次框架.md、核心骨架_{n}.md
├── 01_plots/            # 剧情v{n}.md（开篇的 06/07 也写这里，文件叫 剧情方向v{round}.md）
├── 02_guides/           # 写作指南v{n}.md
├── 02_output/           # 正文v{n}.md
├── 03_state/            # 状态v{n}.md、故事总梗概.md
├── 04_characters/       # 人物档案.json、关系矩阵.json（步骤04 写、06+ 读、04a 增量更新）
```

仓库根另起一个 `logs/<小说名>/` 目录存放工作流运行日志（与 `projects/` 平级，结构镜像项目目录）。

## 命名 / 模板约定

- 步骤模板文件 = `steps/<两位编号（可选后缀）空格<中文名>.md`（评审 / 重构类 Q 步骤落在 `steps/tools/Q* *.md`），由 `path_resolver.STEP_FILE_MAP` 维护。英文版镜像在 `steps_en/`（评审类在 `steps_en/tools/`）。加新步骤时**同时**改 `STEP_FILES` / `STEP_NAMES`（`workflow_runner.py:37,73`）和 `STEP_FILE_MAP`（`path_resolver.py:20`），并同步 `i18n/`、`app_server/main.py` 的 `STEP_NAMES` / `STEP_ORDER` / `STAGES` 三张静态表、`path_resolver.STEP_FILE_MAP_EN`。
- 步骤变量（`PathResolver.resolve`）：
  - 目录简写：`{project}`、`{baseline}`、`{plots}`、`{guides}`、`{output}`、`{state}`、`{chars}`、`{steps}`
  - 文件简写：`{world}`、`{skeleton}`/`{axis}`（=故事主轴）、`{macro}`（=幕次框架）、`{constitution}`、`{evolution}`
  - 上下文变量：`{genre}`、`{project_name}`、`{round}`、`{round-1}`、`{option_index}`、`{user_description}`、`{ref_works}`、`{act_num}`、`{act_skeleton}`、`{prev_act_skeleton}`、`{prev_act_quality}`（后两个仅 `act_num > 1` 时填出读取指令）
- Claude 输出写入路径**禁止改动**：`run_step()` 会在 prompt 头部注入「路径规则：写入路径禁止任何修改。输出中提到路径时必须与指定路径完全一致。」——修改路径时把 `path_resolver` 的简写一起改，否则后续步骤会找不到文件。
- 数字提取：`extract_act_count_from_macro_model` 兼中英文数字（一/二/…/十 和 0-9），从 `幕次框架.md` 抓 `幕次总数：N幕`；`extract_chapter_count_from_skeleton(act)` 抓 `章节数：N章`。改这两份文件格式时同步改提取正则。
- `extract_ref_works_from_creative` 解析 `## 参考作品` 段落，保留 `《…》` 标题并用顿号拼接，用于后续 prompt 渲染。
- 干运行默认值（`_dry_default_chapter_counts = [12,10,8]`、`_dry_default_act_count = 3`、`_dry_default_total_chapters = 30`）只在 `--dry` 下生效。

## 调试 / 续跑小贴士

- 改完某个步骤模板后想重测单步：`python run_workflow.py single <step> -p <name> -g <genre> --dry`（先 dry 验证流程，再去掉 `--dry` 让所选 provider 真跑）。
- 想从开篇开始重做：删 `projects/<name>/.project_info.json` 与 `00_baseline/` 下的产物，或 `python run_workflow.py init` 重建项目。
- 想换题材 / 规模 / 语言复用项目：`.project_info.json` 里的 `genre` / `novel_size` / `target_word_count` / `language` 会被 `WorkflowRunner.__init__` 优先于命令行参数加载，改完需要同步清理依赖它们的旧产物（如 `世界观.md`、英文版的章节摘要等）。
- 续跑行为由 `compute_resume_cursor()` 推断下一执行单元，依赖 `.project_info.json` 里的 `last_step`、`last_step_round`、`last_step_act`、`last_step_phase`、`chapter_counts` 与按 provider 分桶的 `session_uuids`。
- 切 provider 续跑：`.project_info.json` 里 `session_uuids` 是分桶的，`continue` 不会把 claude 的 session id 误用到 codex；切换后对方桶的旧 session 仍会保留（启动时 `runner.cross_provider_sessions_detected` 会打条 info），如不需要可手工删 `session_uuids.<other>` 整段。
- Codex 日志截断：默认会做 head/tail 截断，排查"输出为什么不完整"时设 `WOKE_NOVEL_CODEX_VERBOSE_LOG=1` 取全量。
- 项目根的 `projects/<name>/CLAUDE.md` 由步骤 18 生成（`{project}/CLAUDE.md`，与 `.project_info.json` 同级），供未来 Claude 会话直接读这一份就掌握项目背景；它跟仓库根的 `CLAUDE.md` 是两件事——前者是工作流产物、后者是工具自身的说明。
