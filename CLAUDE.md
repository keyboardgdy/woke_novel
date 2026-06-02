# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

`woke_novel` 是一个驱动 **Claude CLI** 写中文网文的工作流工具。运行器不直接产出文字，而是按流水线顺序调用 `claude` CLI，把 `steps/` 下的 Markdown 模板填入变量后投喂给它，让模型把每一步产物（创意方案、世界观、人物、剧情、正文、状态…）落到 `projects/<小说名>/` 对应子目录里。

模板里夹带硬约束（`steps/00 创作宪法.md`、`steps/00 故事演化核心原则.md`、`steps/00 流程编排.md`、`steps/00 六大创意激发技巧.md`）和题材选型建议（`docs/AI 擅长题材.md`），修改步骤模板前先看这五份。

## 三层架构

文件分工：

- `workflow_runner.py` — `WorkflowRunner`（`workflow_runner.py:62`）+ `STEP_FILES`/`STEP_NAMES`（`workflow_runner.py:17,39`）+ 日志/session 调度。
- `path_resolver.py` — `PathResolver.resolve()`（`path_resolver.py:61`）做模板变量替换，`STEP_FILE_MAP`（`path_resolver.py:16`）必须与 `STEP_FILES` 同步维护。
- `project_info.py` — `ProjectInfo` 读 / 写 `projects/<name>/.project_info.json`，是断点依据。
- `project_structure.py` — 项目首次构造时自动建出 `00_baseline/` ~ `04_characters/` 6 个子目录（`project_structure.py:13`）。
- `run_workflow.py` — 顶层 CLI（`init` / `loop` / `continue` / `single` / `session`）。
- `cli.py` — `run_workflow.py init` 用的交互式提示模块（`ask_genre` / `ask_project_name` / `ask_user_description` / `print_banner`），所有 `loop` / `continue` 跑前都会先调它。
- `menu.py`（+ `menu.bat`）— 交互式菜单，封装 `single` / `full_loop` / `continue` 三种入口。

每个步骤都走同一条三段管线：

1. **模板加载** — `path_resolver.PathResolver.load_step_template()`（`path_resolver.py:128`）读 `steps/<编号 名称>.md`。
2. **变量替换** — `WorkflowRunner.resolve_prompt()`（`workflow_runner.py:114`）→ `PathResolver.resolve()`（`path_resolver.py:61`）把 `{project}`、`{round}`、`{option_index}`、`{act_num}`、`{ref_works}`、`{prev_act_skeleton}` 等替换为绝对路径或值。**任何新步骤模板如果要写入文件，路径必须用这些变量，禁止硬编码绝对路径。**
3. **CLI 执行** — `WorkflowRunner.execute_step()`（`workflow_runner.py:125`）把渲染好的 prompt 写入临时文件，用 `claude "@<temp>" --session-id/--resume <uuid>` 子进程跑（Windows 上 `shutil.which` 也会找 `claude.cmd`/`claude.bat`），超时 1800s（30 分钟）。每一步日志写到 `logs/<name>/<seq>_step_<step>[_A<act>]_R<round>_C<session>.log`（`logs/` 与 `projects/` 平级，不再放在项目目录里；老项目里的 `projects/<name>/logs/` 保持原样不动）。

### 关键不变量

- **同一 `display_id` 永远落到同一个 Claude session**：`WorkflowRunner._session_uuids` 首次分配 UUID 并 `--session-id` 起新会话；后续命中即 `--resume` 续聊。`run_step()` 末尾才把 `display_id` 写进 map，因此**单次 `run_step()` 调用内复用同一 `display_id` 才会续 session**，跨调用才算"新"步骤。
- **`--dry` 模式**下完全不调 `claude`，每步返回伪造的 `DryResult`，并走 `ProjectInfo`/`_dry_default_*` 占位分支，便于在没有 Claude 的环境跑通流程。
- **`ProjectInfo`**（`project_info.py:12`）持久化在 `projects/<name>/.project_info.json`，是 `continue` 续跑的断点依据：`last_step`、`current_round`、`selected_option`、`ref_works`、`act_count`、`chapter_counts`、`total_chapters`、`novel_name`。`continue` 模式只覆盖循环段（`11-17`）和非循环段的单步重跑，不重做已完成的世界观/主轴。
- **状态摘要的"提取-追加-同步"三件套**：`extract_summary_from_state()` → `append_story_summary()` → `sync_summary_to_state()`（`workflow_runner.py:336-402`），对应步骤 15/16/17 之间维护 `03_state/故事总梗概.md` 的流程。每幕最后还要把精简后的总梗概写回该幕最后一个 `状态v{n}.md`。

## 流水线与会话分组

完整流水线（`run_workflow.py loop`）按 Claude session 切片：

| 会话 | 步骤 | display_id 模式 | 备注 |
| --- | --- | --- | --- |
| 1 创意 | 01（×option_count 循环）→ 02 | `novel_<proj>_creative_option` | 选完后用 `extract_novel_name_from_creative` 抽书名并 `rename_project` 把目录改成最终小说名 |
| 2 世界/人物 | 03 → 04 | `novel_<proj>_world` | |
| 3 主轴 | 05 → 05a → 05b（每幕一次），随后 18（`post_05b`） | `novel_<proj>_arc` | 05a 后调 `extract_act_count_from_macro_model` 拿幕数；05b 全部跑完调 `extract_all_chapter_counts` 拿每幕章节数和总章节数，并写回 `.project_info.json`；18 在 05b 后用同一 arc 会话生成 `projects/<name>/CLAUDE.md`（项目根） |
| 4 开篇 | 06 → 07 → 08 → 09 → 10 | `novel_<proj>_opening` | act_num=1；10 之后 `extract_and_create_story_summary(1)` |
| 创作循环 | 11 → 12 → 13 → 14 → 15 → 16（每轮一轮） | `novel_<proj>_round_<n>` | 第一幕章节数 -1 次（开篇已用掉一章），其余幕 `act_chapters` 次；16 在该轮内同一 session 跑 |
| 幕末 | 17，随后 18（`post_17`） | `novel_<proj>_act_<n>` | act 循环结束后跑一次；17 后用同一 act 会话刷新 `projects/<name>/CLAUDE.md`，最后 `sync_summary_to_state` 写回末轮状态文档 |

> 模板目录里另有 `steps/04a 更新人物档案与人物关系.md` 和 `steps/00 进阶提示技术.md` 两份文件，但都不在 `run_workflow.py loop` 的主循环里——前者是手动按需增量更新人物 JSON 的工具步骤，后者是早期探索残留；如要把它们纳入 `STEP_FILES` / `STEP_FILE_MAP` 需同步改两处。`steps/18 项目级 CLAUDE.md.md` 由 `run_workflow.py` 在 05b / 17 后**自动**调用（不需要用户在 `loop` 阶段手动触发），失败仅打印警告不阻断流程。

第一步执行前会要求用户确认开篇会话（`y/n/q`），中间用 `q` 退出会留下 `last_step` 断点供 `continue` 拾起。

## 运行命令

工具集入口是两个：

- `python menu.py`（Windows 还可以 `menu.bat`）— 交互式菜单：单步 / 完整 / 继续 / 步骤列表。所有路径都从脚本所在目录推。
- `python run_workflow.py <command> [args]` — CLI 入口：
  - `init` — 交互式建项目（询问题材、项目名）。
  - `loop --project-name <name> --genre <g> [--option-count 3] [--dry]` — 跑完整流水线。
  - `continue --project-name <name> [--dry]` — 从 `.project_info.json` 的 `last_step` 续跑。
  - `single <step> -p <name> -g <g> [--dry]` — 跑单个步骤。
  - `session <block> <step1,step2,...> -p <name> -g <g> [--dry]` — 在一个 Claude session 里顺序跑一组步骤。
- 单步模式下若 `step == "01" 且 option_count > 1`，菜单会自动循环 01 然后再调 02，无需手动 `session` 编排。

执行前置：系统 PATH 上需要 `claude`（或 `claude.cmd`/`claude.bat`）。`--dry` 下可以省略。

## 项目目录结构

每个项目落在 `projects/<小说名>/` 下（`project_structure.py:13` 定义、首次 `WorkflowRunner` 构造时自动创建）：

```
projects/<name>/
├── .project_info.json   # 进度断点 + 元数据（ProjectInfo 读写）
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

- 步骤模板文件 = `steps/<两位编号（可选后缀）空格<中文名>.md`，由 `path_resolver.STEP_FILE_MAP` 维护，加新步骤时**同时**改 `STEP_FILES` / `STEP_NAMES`（`workflow_runner.py:17,40`）和 `STEP_FILE_MAP`（`path_resolver.py:16`）。**注意：`STEP_NAMES` 中 `"16"` / `"17"` 的中文名当前与对应文件名是反的**（`16 故事梗概精简.md` 在 `STEP_NAMES` 里写成了"幕次故事梗概精简"，反之亦然），改模板/名字时请同时核对 `STEP_FILES` 的实际文件名，必要时回正。
- 步骤变量（`PathResolver.resolve`）：
  - 目录简写：`{project}`、`{baseline}`、`{plots}`、`{guides}`、`{output}`、`{state}`、`{chars}`、`{steps}`
  - 文件简写：`{world}`、`{skeleton}`/`{axis}`（=故事主轴）、`{macro}`（=幕次框架）、`{constitution}`、`{evolution}`
  - 上下文变量：`{genre}`、`{project_name}`、`{round}`、`{round-1}`、`{option_index}`、`{user_description}`、`{ref_works}`、`{act_num}`、`{act_skeleton}`、`{prev_act_skeleton}`（后两个仅 `act_num > 1` 时填出读取指令）
- Claude 输出写入路径**禁止改动**：`run_step()` 会在 prompt 头部注入「路径规则：写入路径禁止任何修改。输出中提到路径时必须与指定路径完全一致。」——修改路径时把 `path_resolver` 的简写一起改，否则后续步骤会找不到文件。
- 数字提取：`extract_act_count_from_macro_model` 兼中英文数字（一/二/…/十 和 0-9），从 `幕次框架.md` 抓 `幕次总数：N幕`；`extract_chapter_count_from_skeleton(act)` 抓 `章节数：N章`。改这两份文件格式时同步改提取正则。
- `extract_ref_works_from_creative` 解析 `## 参考作品` 段落，保留 `《…》` 标题并用顿号拼接，用于后续 prompt 渲染。
- 干运行默认值（`_dry_default_chapter_counts = [12,10,8]`、`_dry_default_act_count = 3`、`_dry_default_total_chapters = 30`）只在 `--dry` 下生效。

## 调试 / 续跑小贴士

- 改完某个步骤模板后想重测单步：`python run_workflow.py single <step> -p <name> -g <genre> --dry`（先 dry 验证流程，再去掉 `--dry` 让 Claude 真跑）。
- 想从开篇开始重做：删 `projects/<name>/.project_info.json` 与 `00_baseline/` 下的产物，或 `python run_workflow.py init` 重建项目。
- 想换题材复用项目：`.project_info.json` 里的 `genre` 会被 `WorkflowRunner.__init__` 优先于参数 `genre` 加载（`workflow_runner.py:97`），改完需要同步清理依赖题材名的旧产物（如 `世界观.md`）。
- 续跑行为由 `step_sequence = ["11","12","13","14","15","16","17","18"]` 控制（`run_workflow.py:319`），非循环段（03-10）只重跑当前 `last_step` 一次；`18` 之所以也入表，是因为 `continue` 在幕末 18 处会再次刷新项目根的 `CLAUDE.md`。
- 项目根的 `projects/<name>/CLAUDE.md` 由步骤 18 生成（`{project}/CLAUDE.md`，与 `.project_info.json` 同级），供未来 Claude 会话直接读这一份就掌握项目背景；它跟仓库根的 `CLAUDE.md` 是两件事——前者是工作流产物、后者是工具自身的说明。
