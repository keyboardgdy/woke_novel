# 路径解析器 - 将模板变量转换为绝对路径
# 支持格式: {project}/01_plots/方向_轮{round}.md

from pathlib import Path
from typing import Dict, Optional
import re

from app_paths import resource_path, runtime_path

# 项目根目录
PROJECTS_ROOT = runtime_path("projects")

# 日志根目录（与 projects/ 平级，每个小说一个子目录）
LOGS_ROOT = runtime_path("logs")

# 规则文件根目录（相对于当前脚本目录）
RULES_ROOT = resource_path("steps")
RULES_ROOT_EN = resource_path("steps_en")


# 步骤到文件的映射
STEP_FILE_MAP = {
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
    "Q1": "tools/Q1 章节质量评审.md",
    "Q2": "tools/Q2 章节定向重写.md",
    "Q3": "tools/Q3 风格记忆沉淀.md",
    "Q4": "tools/Q4 剧情吸引力评审.md",
    "Q5": "tools/Q5 剧情强化重构.md",
    "Q6": "tools/Q6 剧情钩子账本沉淀.md",
    "Q7": "tools/Q7 故事主轴吸引力评审.md",
    "Q7R": "tools/Q7R 故事主轴吸引力重构.md",
    "Q8": "tools/Q8 幕次框架吸引力评审.md",
    "Q8R": "tools/Q8R 幕次框架吸引力重构.md",
    "Q9": "tools/Q9 幕次核心骨架吸引力评审.md",
    "Q9R": "tools/Q9R 幕次核心骨架吸引力重构.md",
    "Q10": "tools/Q10 章节上下文包生成.md",
}

STEP_FILE_MAP_EN = {
    "01": "01 Creative Proposal Generation.md",
    "02": "02 Creative Proposal Supplement.md",
    "03": "03 Worldbuilding and Setting Generation.md",
    "04": "04 Character Profiles and Relationship Matrix.md",
    "05": "05 Story Axis.md",
    "05a": "05a Act Framework.md",
    "05b": "05b Act Core Skeleton.md",
    "06": "06 Opening Plot Direction Extraction.md",
    "07": "07 Opening Chapter Synopsis.md",
    "08": "08 Opening Writing Guide.md",
    "09": "09 Opening Chapter Draft.md",
    "10": "10 State Document.md",
    "11": "11 Plot Direction Guidance.md",
    "12": "12 Plot Synopsis Design.md",
    "13": "13 Writing Guide.md",
    "14": "14 Chapter Draft.md",
    "15": "15 State Document.md",
    "16": "16 Story Summary Compression.md",
    "17": "17 Act-Level Story Summary Compression.md",
    "18": "18 Project-Level CLAUDE.md.md",
    "Q1": "tools/Q1 Chapter Quality Review.md",
    "Q2": "tools/Q2 Targeted Chapter Rewrite.md",
    "Q3": "tools/Q3 Style Memory Update.md",
    "Q4": "tools/Q4 Plot Appeal Review.md",
    "Q5": "tools/Q5 Plot Appeal Rewrite.md",
    "Q6": "tools/Q6 Plot Hook Ledger Update.md",
    "Q7": "tools/Q7 Story Axis Appeal Review.md",
    "Q7R": "tools/Q7R Story Axis Appeal Rewrite.md",
    "Q8": "tools/Q8 Act Framework Appeal Review.md",
    "Q8R": "tools/Q8R Act Framework Appeal Rewrite.md",
    "Q9": "tools/Q9 Act Skeleton Appeal Review.md",
    "Q9R": "tools/Q9R Act Skeleton Appeal Rewrite.md",
    "Q10": "tools/Q10 Chapter Context Pack.md",
}


class PathResolver:
    """路径解析器 - 将项目级变量转换为绝对路径"""

    def __init__(self, project_name: str, genre: str = "都市",
                 novel_size: str = "中篇", target_word_count: int = 300_000,
                 language: str = "zh"):
        self.project_name = project_name
        self.genre = genre
        self.novel_size = novel_size
        self.target_word_count = target_word_count
        self.language = "en" if (language or "zh").strip().lower() == "en" else "zh"
        self.rules_root = RULES_ROOT_EN if self.language == "en" else RULES_ROOT
        self.step_file_map = STEP_FILE_MAP_EN if self.language == "en" else STEP_FILE_MAP
        self.project_root = PROJECTS_ROOT / project_name

        # 子目录（日志目录 logs/<name>/ 在仓库根，由 LOGS_ROOT 单独管理，不在这里建）
        self.baseline_dir = self.project_root / "00_baseline"
        self.plots_dir = self.project_root / "01_plots"
        self.guides_dir = self.project_root / "02_guides"
        self.output_dir = self.project_root / "02_output"
        self.state_dir = self.project_root / "03_state"
        self.characters_dir = self.project_root / "04_characters"
        self.quality_dir = self.project_root / "05_quality"

        # 确保目录存在
        for d in [self.baseline_dir, self.plots_dir, self.guides_dir, self.output_dir,
                 self.state_dir, self.characters_dir, self.quality_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def resolve(self, template: str, round_num: int = 1, option_index: int = None,
                user_description: str = "", ref_works: str = "",
                novel_size: str = None, target_word_count: int = None, **kwargs) -> str:
        """将模板中的路径变量替换为绝对路径

        支持格式：
        - {project} -> 项目根目录绝对路径
        - {round} -> 当前轮次数字
        - {option_index} -> 当前方案索引（1-based）
        """
        result = template
        p = str(self.project_root).replace("\\", "/")
        opt_idx = str(option_index) if option_index else ""
        r = str(round_num)
        prev_r = str(round_num - 1)

        # ========== 基础变量 ==========
        result = result.replace("{project}", p)
        result = result.replace("{genre}", self.genre)
        result = result.replace("{project_name}", self.project_name)
        result = result.replace("{round}", r)
        result = result.replace("{round-1}", prev_r)
        result = result.replace("{option_index}", opt_idx)
        result = result.replace("{user_description}", user_description)
        size_label = novel_size or self.novel_size or "中篇"
        if self.language == "en":
            size_label = {
                "短篇": "Short novel",
                "中篇": "Medium-length novel",
                "长篇": "Long novel",
                "超长篇": "Very long novel",
            }.get(size_label, size_label)
        result = result.replace("{novel_size}", size_label)
        # 渲染成中文「X万字」，方便人读；底层整数还是 target_word_count
        _wc = target_word_count or self.target_word_count or 300_000
        target_words = f"{_wc:,} words" if self.language == "en" else f"{_wc // 10_000}万字"
        result = result.replace("{target_word_count}", target_words)
        result = result.replace("{act_num}", str(kwargs.get("act_num") or ""))
        act_num = kwargs.get("act_num")
        if self.language == "en":
            prev_skeleton_name = f"Core_Skeleton_{act_num - 1}.md" if act_num is not None else "Core_Skeleton_1.md"
            current_skeleton_name = f"Core_Skeleton_{act_num or 1}.md"
            read_prefix = "Read"
            prev_note = "previous act core skeleton, for continuity reference only"
            prev_quality_review_name = f"Act_Skeleton_Appeal_Review_{act_num - 1}.md" if act_num is not None else "Act_Skeleton_Appeal_Review_1.md"
            prev_quality_rewrite_name = f"Act_Skeleton_Rewrite_Notes_{act_num - 1}.md" if act_num is not None else "Act_Skeleton_Rewrite_Notes_1.md"
            prev_quality_note = "previous act appeal gate, for continuity reference only"
        else:
            prev_skeleton_name = f"核心骨架_{act_num - 1}.md" if act_num is not None else "核心骨架_1.md"
            current_skeleton_name = f"核心骨架_{act_num or 1}.md"
            read_prefix = "读取"
            prev_note = "上一幕核心骨架,仅作为连贯性参考"
            prev_quality_review_name = f"核心骨架吸引力评审_{act_num - 1}.md" if act_num is not None else "核心骨架吸引力评审_1.md"
            prev_quality_rewrite_name = f"核心骨架重构说明_{act_num - 1}.md" if act_num is not None else "核心骨架重构说明_1.md"
            prev_quality_note = "上一幕吸引力门禁,仅作为连贯性参考"
        if act_num is not None and act_num > 1:
            result = result.replace("{prev_act_skeleton}", f"{read_prefix}: {p}/00_baseline/{prev_skeleton_name} ({prev_note})")
            result = result.replace(
                "{prev_act_quality}",
                f"{read_prefix}: {p}/05_quality/{prev_quality_review_name} ({prev_quality_note})\n"
                f"{read_prefix}: {p}/05_quality/{prev_quality_rewrite_name} ({prev_quality_note})"
            )
            result = result.replace("{act_skeleton}", f"{read_prefix}: {p}/00_baseline/{current_skeleton_name}")
        else:
            result = result.replace("{prev_act_skeleton}", "")
            result = result.replace("{prev_act_quality}", "")
            result = result.replace("{act_skeleton}", f"{read_prefix}: {p}/00_baseline/{current_skeleton_name}")
        if ref_works is not None:
            result = result.replace("{ref_works}", ref_works)
        # 步骤 18 阶段标识：post_05b（开篇前）或 post_17（每幕末）
        result = result.replace("{phase}", str(kwargs.get("phase") or "post_05b"))

        # ========== 00_baseline 目录 ==========
        result = result.replace("{baseline}", p + "/00_baseline")
        if self.language == "en":
            result = result.replace("{world}", p + "/00_baseline/Worldbuilding.md")
            result = result.replace("{skeleton}", p + "/00_baseline/Story_Axis.md")
            result = result.replace("{axis}", p + "/00_baseline/Story_Axis.md")
            result = result.replace("{macro}", p + "/00_baseline/Act_Framework.md")
        else:
            result = result.replace("{world}", p + "/00_baseline/世界观.md")
            result = result.replace("{skeleton}", p + "/00_baseline/故事主轴.md")
            result = result.replace("{axis}", p + "/00_baseline/故事主轴.md")
            result = result.replace("{macro}", p + "/00_baseline/幕次框架.md")
        if self.language == "en":
            constitution = "00 Creative Constitution.md"
            evolution = "00 Story Evolution Core Principles.md"
            craft_errors = "00 AI General Prose Craft Error Checklist.md"
        else:
            constitution = "00 创作宪法.md"
            evolution = "00 故事演化核心原则.md"
            craft_errors = "00 AI通用文字技法错误清单.md"
        result = result.replace("{constitution}", str(self.rules_root / constitution).replace("\\", "/"))
        result = result.replace("{evolution}", str(self.rules_root / evolution).replace("\\", "/"))
        result = result.replace("{craft_errors}", str(self.rules_root / craft_errors).replace("\\", "/"))
        result = result.replace("{steps}", str(self.rules_root).replace("\\", "/"))

        # ========== 04_characters 目录 ==========
        result = result.replace("{chars}", p + "/04_characters")

        # ========== 01_plots 目录 ==========
        result = result.replace("{plots}", p + "/01_plots")
        if self.language == "en":
            result = result.replace("{chapter_context}", p + f"/01_plots/Chapter_Context_Pack_v{r}.md")
        else:
            result = result.replace("{chapter_context}", p + f"/01_plots/章节上下文包v{r}.md")

        # ========== 02_guides 目录 ==========
        result = result.replace("{guides}", p + "/02_guides")

        # ========== 02_output 目录 ==========
        result = result.replace("{output}", p + f"/02_output")

        # ========== 03_state 目录 ==========
        result = result.replace("{state}", p + "/03_state")

        # ========== 05_quality 目录 ==========
        result = result.replace("{quality}", p + "/05_quality")

        return result

    def get_step_file_path(self, step_name: str) -> Path:
        """获取步骤模板文件路径"""
        if step_name in self.step_file_map:
            return self.rules_root / self.step_file_map[step_name]
        return self.rules_root / f"{step_name}.md"

    def load_step_template(self, step_name: str) -> str:
        """加载步骤模板"""
        step_file = self.get_step_file_path(step_name)
        if not step_file.exists():
            simplified = re.sub(r'^\d+\s*', '', step_name).strip()
            step_file = self.rules_root / (simplified + ".md")

        with open(step_file, 'r', encoding='utf-8') as f:
            return f.read()


if __name__ == "__main__":
    resolver = PathResolver("test_project")
    print(f"项目: {resolver.project_name}")
    print(f"根目录: {resolver.project_root}")
