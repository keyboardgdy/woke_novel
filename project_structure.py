# -*- coding: utf-8 -*-
# 项目结构生成器
# 用于创建小说项目的标准目录结构

import os
import sys
import shutil
from pathlib import Path
from typing import Dict, List

import ui
from i18n import t

# 默认项目根目录
DEFAULT_PROJECTS_ROOT = Path(__file__).resolve().parent / "projects"

# 项目目录结构定义
PROJECT_STRUCTURE = {
    "00_baseline": [
        # 创意方案目录（对应步骤01-02）
    ],
    "01_plots": [
        # 剧情目录（对应步骤06-07, 11-12）
    ],
    "02_guides": [
        # 写作指南目录（对应步骤08, 13）
    ],
    "02_output": [
        # 正文输出目录（对应步骤09, 14）
    ],
    "03_state": [
        # 状态文档目录（对应步骤10）
    ],
    "04_characters": [
        # 人物档案目录（对应步骤04-05, 15）
    ],
    "05_quality": [
        # 质量评审、定向重写、风格记忆目录（对应 tools 质量闭环）
    ],
}


class ProjectStructure:
    """项目结构生成器"""

    def __init__(self, project_name: str, root_dir: Path = None):
        self.project_name = project_name
        self.root_dir = root_dir or DEFAULT_PROJECTS_ROOT
        self.project_path = self.root_dir / project_name

    def create(self) -> bool:
        """创建项目目录结构"""
        try:
            self.project_path.mkdir(parents=True, exist_ok=True)
            for subdir in PROJECT_STRUCTURE.keys():
                (self.project_path / subdir).mkdir(parents=True, exist_ok=True)
            ui.success(t("structure.created", path=self.project_path))
            return True
        except Exception as e:
            ui.error(t("structure.create_failed", error=e))
            return False

    def get_path(self, subdir: str, filename: str = None) -> Path:
        """获取项目内的路径"""
        if filename:
            return self.project_path / subdir / filename
        return self.project_path / subdir

    def exists(self) -> bool:
        """检查项目是否存在"""
        return self.project_path.exists() and self.project_path.is_dir()

    def rename(self, new_name: str) -> bool:
        """重命名项目文件夹"""
        old_path = self.project_path
        new_path = self.root_dir / new_name
        if not old_path.exists():
            ui.error(t("structure.path_missing", path=old_path))
            return False
        if new_path.exists():
            ui.warn(t("structure.target_exists", path=new_path))
            return False
        try:
            old_path.rename(new_path)
            ui.success(t("structure.renamed", old=self.project_name, new=new_name))
            self.project_name = new_name
            self.project_path = new_path
            return True
        except Exception as e:
            ui.info(t("structure.rename_copy_fallback"))
            try:
                shutil.copytree(old_path, new_path)
                shutil.rmtree(old_path)
                ui.success(t("structure.renamed", old=self.project_name, new=new_name))
                self.project_name = new_name
                self.project_path = new_path
                return True
            except Exception as e2:
                ui.error(t("structure.rename_failed", error=e2))
                return False


def generate_project_structure(project_name: str, root_dir: str = None) -> ProjectStructure:
    """生成项目结构的便捷函数"""
    root = Path(root_dir) if root_dir else DEFAULT_PROJECTS_ROOT
    ps = ProjectStructure(project_name, root)
    ps.create()
    return ps


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(t("structure.usage"))
        sys.exit(1)

    project_name = sys.argv[1]
    root_dir = sys.argv[2] if len(sys.argv) > 2 else None

    ps = generate_project_structure(project_name, root_dir)
    print(t("structure.created_plain", path=ps.project_path))
