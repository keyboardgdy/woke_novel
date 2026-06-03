# 路径解析器 - 将模板变量转换为绝对路径
# 支持格式: {project}/01_plots/方向_轮{round}.md

from pathlib import Path
from typing import Dict, Optional
import re

# 项目根目录
PROJECTS_ROOT = Path(__file__).resolve().parent / "projects"

# 日志根目录（与 projects/ 平级，每个小说一个子目录）
LOGS_ROOT = Path(__file__).resolve().parent / "logs"

# 规则文件根目录（相对于当前脚本目录）
RULES_ROOT = Path(__file__).parent / "steps"


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
}


class PathResolver:
    """路径解析器 - 将项目级变量转换为绝对路径"""

    def __init__(self, project_name: str, genre: str = "都市"):
        self.project_name = project_name
        self.genre = genre
        self.project_root = PROJECTS_ROOT / project_name

        # 子目录（日志目录 logs/<name>/ 在仓库根，由 LOGS_ROOT 单独管理，不在这里建）
        self.baseline_dir = self.project_root / "00_baseline"
        self.plots_dir = self.project_root / "01_plots"
        self.guides_dir = self.project_root / "02_guides"
        self.output_dir = self.project_root / "02_output"
        self.state_dir = self.project_root / "03_state"
        self.characters_dir = self.project_root / "04_characters"

        # 确保目录存在
        for d in [self.baseline_dir, self.plots_dir, self.guides_dir, self.output_dir,
                 self.state_dir, self.characters_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def resolve(self, template: str, round_num: int = 1, option_index: int = None,
                user_description: str = "", ref_works: str = "", **kwargs) -> str:
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
        result = result.replace("{act_num}", str(kwargs.get("act_num") or ""))
        act_num = kwargs.get("act_num")
        if act_num is not None and act_num > 1:
            result = result.replace("{prev_act_skeleton}", f"读取：{p}/00_baseline/核心骨架_{act_num - 1}.md（上一幕核心骨架,仅作为连贯性参考）")
            result = result.replace("{act_skeleton}", f"读取：{p}/00_baseline/核心骨架_{act_num}.md")
        else:
            result = result.replace("{prev_act_skeleton}", "")
            result = result.replace("{act_skeleton}", f"读取：{p}/00_baseline/核心骨架_1.md")
        if ref_works is not None:
            result = result.replace("{ref_works}", ref_works)
        # 步骤 18 阶段标识：post_05b（开篇前）或 post_17（每幕末）
        result = result.replace("{phase}", str(kwargs.get("phase") or "post_05b"))

        # ========== 00_baseline 目录 ==========
        result = result.replace("{baseline}", p + "/00_baseline")
        result = result.replace("{world}", p + "/00_baseline/世界观.md")
        result = result.replace("{skeleton}", p + "/00_baseline/故事主轴.md")
        result = result.replace("{axis}", p + "/00_baseline/故事主轴.md")
        result = result.replace("{macro}", p + "/00_baseline/幕次框架.md")
        result = result.replace("{constitution}", str(RULES_ROOT / "00 创作宪法.md").replace("\\", "/"))
        result = result.replace("{evolution}", str(RULES_ROOT / "00 故事演化核心原则.md").replace("\\", "/"))
        result = result.replace("{craft_errors}", str(RULES_ROOT / "00 AI通用文字技法错误清单.md").replace("\\", "/"))
        result = result.replace("{steps}", str(RULES_ROOT).replace("\\", "/"))

        # ========== 04_characters 目录 ==========
        result = result.replace("{chars}", p + "/04_characters")

        # ========== 01_plots 目录 ==========
        result = result.replace("{plots}", p + "/01_plots")

        # ========== 02_guides 目录 ==========
        result = result.replace("{guides}", p + "/02_guides")

        # ========== 02_output 目录 ==========
        result = result.replace("{output}", p + f"/02_output")

        # ========== 03_state 目录 ==========
        result = result.replace("{state}", p + "/03_state")

        return result

    def get_step_file_path(self, step_name: str) -> Path:
        """获取步骤模板文件路径"""
        if step_name in STEP_FILE_MAP:
            return RULES_ROOT / STEP_FILE_MAP[step_name]
        return RULES_ROOT / f"{step_name}.md"

    def load_step_template(self, step_name: str) -> str:
        """加载步骤模板"""
        step_file = self.get_step_file_path(step_name)
        if not step_file.exists():
            simplified = re.sub(r'^\d+\s*', '', step_name).strip()
            step_file = RULES_ROOT / (simplified + ".md")

        with open(step_file, 'r', encoding='utf-8') as f:
            return f.read()


if __name__ == "__main__":
    resolver = PathResolver("test_project")
    print(f"项目: {resolver.project_name}")
    print(f"根目录: {resolver.project_root}")