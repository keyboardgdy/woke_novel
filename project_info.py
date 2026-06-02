# 项目信息管理
# 保存项目的元数据：题材、创意方案、参考作品、执行进度等

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from path_resolver import PROJECTS_ROOT


class ProjectInfo:
    """项目信息管理器"""

    INFO_FILENAME = ".project_info.json"

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_path = PROJECTS_ROOT / project_name
        self.info_file = self.project_path / self.INFO_FILENAME
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> bool:
        """从文件加载项目信息"""
        if not self.info_file.exists():
            return False
        try:
            self._data = json.loads(self.info_file.read_text(encoding='utf-8'))
            return True
        except Exception:
            return False

    def save(self) -> bool:
        """保存项目信息到文件"""
        try:
            self.info_file.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            return True
        except Exception:
            return False

    def get(self, key: str, default=None):
        """获取项目信息"""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置项目信息"""
        self._data[key] = value
        return self.save()

    def update(self, **kwargs) -> bool:
        """批量更新项目信息"""
        self._data.update(kwargs)
        return self.save()

    @property
    def genre(self) -> Optional[str]:
        """获取题材"""
        return self._data.get("genre")

    @property
    def selected_option(self) -> Optional[int]:
        """获取选中的创意方案编号"""
        return self._data.get("selected_option")

    @property
    def ref_works(self) -> Optional[str]:
        """获取参考作品"""
        return self._data.get("ref_works")

    @property
    def current_round(self) -> int:
        """获取当前轮次"""
        return self._data.get("current_round", 1)

    @property
    def last_step(self) -> Optional[str]:
        """获取最后执行的步骤"""
        return self._data.get("last_step")

    @property
    def novel_name(self) -> Optional[str]:
        """获取小说名称"""
        return self._data.get("novel_name")

    @property
    def act_count(self) -> Optional[int]:
        """获取幕次总数"""
        return self._data.get("act_count")

    @property
    def chapter_counts(self) -> Optional[List[int]]:
        """获取各幕章节数列表"""
        return self._data.get("chapter_counts")

    @property
    def total_chapters(self) -> Optional[int]:
        """获取总章节数"""
        return self._data.get("total_chapters")

    @property
    def created_at(self) -> Optional[str]:
        """获取创建时间"""
        return self._data.get("created_at")

    def mark_step_completed(self, step: str, round_num: int = 1) -> bool:
        """标记步骤已完成"""
        self._data["last_step"] = step
        self._data["last_step_at"] = datetime.now().isoformat()
        if round_num > self.current_round:
            self._data["current_round"] = round_num
        return self.save()

    def select_option(self, option_num: int, novel_name: str = None, ref_works: str = None) -> bool:
        """选择创意方案"""
        self._data["selected_option"] = option_num
        if novel_name:
            self._data["novel_name"] = novel_name
        if ref_works:
            self._data["ref_works"] = ref_works
        return self.save()

    def initialize(self, genre: str) -> bool:
        """初始化项目信息"""
        self._data = {
            "project_name": self.project_name,
            "genre": genre,
            "created_at": datetime.now().isoformat(),
            "current_round": 1,
            "selected_option": None,
            "ref_works": None,
            "novel_name": None,
            "last_step": None,
            "last_step_at": None,
        }
        return self.save()

    def to_dict(self) -> Dict[str, Any]:
        """返回完整数据字典"""
        return self._data.copy()


def create_project_info(project_name: str, genre: str = "都市") -> ProjectInfo:
    """创建新项目信息文件"""
    info = ProjectInfo(project_name)
    info.initialize(genre)
    return info


def get_project_info(project_name: str) -> Optional[ProjectInfo]:
    """获取已有项目信息，如果不存在返回None"""
    info = ProjectInfo(project_name)
    if not info.info_file.exists():
        return None
    return info