# -*- coding: utf-8 -*-
"""
CLI 交互模块：询问题材、项目名、用户描述。

所有可见输出都委托给 ui 模块；本文件只保留交互流程，方便 run_workflow.py 复用。
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple

from ui import (
    C, I,
    blank, chip, clear, confirm, dim, info, init, line,
    print_banner, print_choices_table, print_creative_cards, print_panel,
    print_subheader, prompt, success, warn,
)


PRESETS_PATH = Path(__file__).parent / "assets" / "style_presets_classified.json"

# ask_genre 选完小类后写入这里，ask_user_description 读取作为默认值。
# 一次 init / loop 流程只跑一次题材选择，所以模块级缓存够用。
_last_theme_desc: Optional[str] = None


# ---------------------------------------------------------------------------
# 小说规模档位
# ---------------------------------------------------------------------------
# 4 档固定：10万 / 30万 / 50万 / 100万 字。供 ask_novel_size() 选择；
# 也供 workflow_runner / path_resolver 在 prompt 中以 {novel_size} 形式引用。
NOVEL_SIZES: List[Tuple[str, int]] = [
    ("短篇",   100_000),   # 10万字
    ("中篇",   300_000),   # 30万字
    ("长篇",   500_000),   # 50万字
    ("超长篇", 1_000_000), # 100万字
]
_SIZE_LABEL_TO_WORDS = {label: words for label, words in NOVEL_SIZES}


def _load_presets() -> dict:
    if not PRESETS_PATH.exists():
        return {}
    try:
        return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        warn(f"读取题材预设失败: {e}")
        return {}


# ---------------------------------------------------------------------------
# 公共 banner
# ---------------------------------------------------------------------------
def print_banner(title: str) -> None:
    """顶部 banner：兼容旧 run_workflow.py 调用。"""
    init()
    print_banner(title)


# ---------------------------------------------------------------------------
# 题材
# ---------------------------------------------------------------------------
def ask_genre() -> str:
    """四级选材：频道 → 类型 → 小类 theme → 补充说明。

    频道（男频 / 女频 / 其他）必选；类型可"0 自定义"直接输入；
    小类 theme 可直接输入自定义题材名跳过（此时补充说明默认值为空）。

    返回类型中文名（写入 .project_info.json 的 genre 字段），小类 desc
    通过模块级缓存传给 ask_user_description 作为"补充说明"的默认值。
    """
    global _last_theme_desc

    presets = _load_presets()
    channel_keys: List[str] = list(presets.keys())

    init()
    print_subheader("项目类型选择", color=C.PRIMARY)
    if not channel_keys:
        warn("题材预设加载失败，回退为自由输入。")
        genre = prompt("小说题材", default="都市")
        _last_theme_desc = None
        return genre

    # 1) 频道
    ch_items: List[Tuple[int, str, str]] = [
        (i + 1, presets[k].get("name", k), presets[k].get("desc", ""))
        for i, k in enumerate(channel_keys)
    ]
    print_choices_table(ch_items, title="请选择创作频道", allow_custom=False)
    ch_raw = prompt(
        f"请选择",
        default="1",
    ).strip()

    if not ch_raw.isdigit() or not (1 <= int(ch_raw) <= len(channel_keys)):
        warn(f"无效编号 {ch_raw}，将按自定义题材处理。")
        _last_theme_desc = None
        return ch_raw

    ch_key = channel_keys[int(ch_raw) - 1]
    ch_data = presets[ch_key]
    ch_name = ch_data.get("name", ch_key)
    genres: dict = ch_data.get("genres", {}) or {}

    # 2) 类型（0 = 自定义）
    if not genres:
        _last_theme_desc = None
        return ch_name

    genre_keys: List[str] = list(genres.keys())
    g_items: List[Tuple[int, str, str]] = [
        (i + 1, genres[k].get("name", k), genres[k].get("desc", ""))
        for i, k in enumerate(genre_keys)
    ]
    print_subheader(f"━━━ {ch_name}类型 ━━━", color=C.ACCENT)
    print_choices_table(g_items, title="请选择小说类型", allow_custom=True, custom_label="自定义类型")

    g_raw = prompt(
        f"请选择",
        default="1",
    ).strip()

    # 自定义类型
    if not g_raw.isdigit() or g_raw == "0":
        if not g_raw.isdigit():
            _last_theme_desc = None
            return g_raw
        # 0 = 自定义类型，但没输入内容 → 让用户再输一次
        custom = prompt("自定义类型", default="").strip()
        _last_theme_desc = None
        return custom or ch_name

    g_idx = int(g_raw) - 1
    if not (0 <= g_idx < len(genre_keys)):
        warn(f"无效编号 {g_raw}，将按自定义题材处理。")
        _last_theme_desc = None
        return g_raw

    g_key = genre_keys[g_idx]
    g_data = genres[g_key]
    g_name = g_data.get("name", g_key)
    themes: List[dict] = g_data.get("themes", []) or []

    # 3) 小类 theme
    if not themes:
        _last_theme_desc = None
        return g_name

    print_subheader(f"「{g_name}」细分主题", color=C.ACCENT)
    cards: List[Tuple[int, str, str]] = [
        (i + 1, t.get("name", "?"), t.get("desc", ""))
        for i, t in enumerate(themes)
    ]
    print_creative_cards(cards)
    raw = prompt(
        f"输入数字选题材，或直接输入自定义题材",
        default="1",
    ).strip()

    if not raw.isdigit():
        # 直接输入自由文本 = 自定义题材
        _last_theme_desc = None
        return raw

    idx = int(raw) - 1
    if 0 <= idx < len(themes):
        _last_theme_desc = themes[idx].get("desc")
    else:
        warn(f"无效编号 {raw}，将按自定义题材处理。")
        _last_theme_desc = None
        return raw
    return g_name


# ---------------------------------------------------------------------------
# 项目名
# ---------------------------------------------------------------------------
def ask_project_name() -> str:
    """询问项目名（初始目录名）。空名校验。"""
    init()
    print_subheader("创建项目目录", color=C.PRIMARY)
    while True:
        name = prompt("项目名（用于创建项目目录）")
        if name:
            return name
        warn("项目名不能为空，请重新输入。")


# ---------------------------------------------------------------------------
# 用户描述
# ---------------------------------------------------------------------------
def ask_user_description() -> str:
    """询问用户对小说的描述 / 想法 / 要求。默认值为 ask_genre 选中小类的 desc。"""
    global _last_theme_desc
    init()
    print_subheader("补充说明", color=C.PRIMARY)
    default = _last_theme_desc or ""
    if default:
        info("默认值来自所选小类主题，可直接回车或修改。")
    desc = prompt(
        "对小说的想法、描述或要求（可为空）",
        default=default,
        show_default=False,
        preface=f"({default})" if default else None,
    )
    # 一旦消费完就清空，防止后续误用
    _last_theme_desc = None
    return desc if desc else "无"


# ---------------------------------------------------------------------------
# 小说规模
# ---------------------------------------------------------------------------
def ask_novel_size() -> str:
    """询问小说规模档位（短篇/中篇/长篇/超长篇），返回中文档名。

    4 档固定对应 10万 / 30万 / 50万 / 100万 字，详见 NOVEL_SIZES。
    通过 select 数字选 1-4，默认 2（中篇）。
    """
    init()
    print_subheader("小说规模", color=C.PRIMARY)
    items: List[Tuple[int, str, str]] = [
        (i + 1, label, f"{words // 10_000}万字") for i, (label, words) in enumerate(NOVEL_SIZES)
    ]
    print_choices_table(items, title="请选择小说规模", allow_custom=False)
    raw = prompt("请选择", default="2").strip()
    if not raw.isdigit():
        warn(f"无效编号 {raw}，使用默认中篇。")
        return "中篇"
    idx = int(raw) - 1
    if not (0 <= idx < len(NOVEL_SIZES)):
        warn(f"无效编号 {raw}，使用默认中篇。")
        return "中篇"
    label, words = NOVEL_SIZES[idx]
    info(f"已选规模：{label}（约 {words // 10_000} 万字）")
    return label


def size_to_word_count(size_label: str) -> int:
    """把规模档名（中/短/长/超长篇）映射到目标字数。未知档名兜底 30 万。"""
    return _SIZE_LABEL_TO_WORDS.get(size_label, 300_000)
