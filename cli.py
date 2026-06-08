# -*- coding: utf-8 -*-
"""
CLI 交互模块：询问题材、项目名、用户描述。

所有可见输出都委托给 ui 模块；本文件只保留交互流程，方便 run_workflow.py 复用。
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple

import i18n as i18n_module
from i18n import t
from ui import (
    C, I,
    blank, chip, clear, confirm, dim, info, init, line,
    print_banner, print_choices_table, print_creative_cards, print_panel,
    print_subheader, prompt, success, warn,
)


PRESETS_PATH = Path(__file__).parent / "assets" / "style_presets_classified.json"
PRESETS_PATH_EN = Path(__file__).parent / "assets" / "style_presets_classified_en.json"
_current_language = "zh"

# ask_genre 选完小类后写入这里，ask_user_description 读取作为默认值。
# 一次 init / loop 流程只跑一次题材选择，所以模块级缓存够用。
_last_theme_desc: Optional[str] = None


def set_language(language: str) -> None:
    """设置交互层使用的语言资源。"""
    global _current_language
    _current_language = "en" if (language or "zh").strip().lower() == "en" else "zh"
    i18n_module.set_language(_current_language)


def get_language() -> str:
    return _current_language


def _presets_path() -> Path:
    return PRESETS_PATH_EN if _current_language == "en" else PRESETS_PATH


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
    presets_path = _presets_path()
    if not presets_path.exists():
        return {}
    try:
        return json.loads(presets_path.read_text(encoding="utf-8"))
    except Exception as e:
        warn(t("genre.presets_failed", error=e))
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
    print_subheader(t("genre.title"), color=C.PRIMARY)
    if not channel_keys:
        warn(t("genre.presets_fallback"))
        genre = prompt(t("genre.prompt"), default="都市")
        _last_theme_desc = None
        return genre

    # 1) 频道
    ch_items: List[Tuple[int, str, str]] = [
        (i + 1, presets[k].get("name", k), presets[k].get("desc", ""))
        for i, k in enumerate(channel_keys)
    ]
    print_choices_table(ch_items, title=t("genre.channel_title"), allow_custom=False)
    ch_raw = prompt(
        t("common.choose"),
        default="1",
    ).strip()

    if not ch_raw.isdigit() or not (1 <= int(ch_raw) <= len(channel_keys)):
        warn(t("genre.invalid_custom", value=ch_raw))
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
    print_subheader(t("genre.type_subtitle", name=ch_name), color=C.ACCENT)
    print_choices_table(g_items, title=t("genre.type_title"), allow_custom=True, custom_label=t("genre.custom_type"))

    g_raw = prompt(
        t("common.choose"),
        default="1",
    ).strip()

    # 自定义类型
    if not g_raw.isdigit() or g_raw == "0":
        if not g_raw.isdigit():
            _last_theme_desc = None
            return g_raw
        # 0 = 自定义类型，但没输入内容 → 让用户再输一次
        custom = prompt(t("genre.custom_type"), default="").strip()
        _last_theme_desc = None
        return custom or ch_name

    g_idx = int(g_raw) - 1
    if not (0 <= g_idx < len(genre_keys)):
        warn(t("genre.invalid_custom", value=g_raw))
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

    print_subheader(t("genre.theme_subtitle", name=g_name), color=C.ACCENT)
    cards: List[Tuple[int, str, str]] = [
        (i + 1, t.get("name", "?"), t.get("desc", ""))
        for i, t in enumerate(themes)
    ]
    print_creative_cards(cards)
    raw = prompt(
        t("genre.theme_prompt"),
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
        warn(t("genre.invalid_custom", value=raw))
        _last_theme_desc = None
        return raw
    return g_name


# ---------------------------------------------------------------------------
# 项目名
# ---------------------------------------------------------------------------
def ask_project_name() -> str:
    """询问项目名（初始目录名）。空名校验。"""
    init()
    print_subheader(t("cli.project_dir_title"), color=C.PRIMARY)
    while True:
        name = prompt(t("cli.project_name_prompt"))
        if name:
            return name
        warn(t("cli.project_name_empty"))


# ---------------------------------------------------------------------------
# 用户描述
# ---------------------------------------------------------------------------
def ask_user_description() -> str:
    """询问用户对小说的描述 / 想法 / 要求。默认值为 ask_genre 选中小类的 desc。"""
    global _last_theme_desc
    init()
    print_subheader(t("cli.description_title"), color=C.PRIMARY)
    default = _last_theme_desc or ""
    if default:
        info(t("cli.description_default_hint"))
    desc = prompt(
        t("cli.description_prompt"),
        default=default,
        show_default=False,
        preface=f"({default})" if default else None,
    )
    # 一旦消费完就清空，防止后续误用
    _last_theme_desc = None
    return desc if desc else t("common.none")


# ---------------------------------------------------------------------------
# 小说规模
# ---------------------------------------------------------------------------
def ask_novel_size() -> str:
    """询问小说规模档位（短篇/中篇/长篇/超长篇），返回中文档名。

    4 档固定对应 10万 / 30万 / 50万 / 100万 字，详见 NOVEL_SIZES。
    通过 select 数字选 1-4，默认 2（中篇）。
    """
    init()
    print_subheader(t("size.title"), color=C.PRIMARY)
    items: List[Tuple[int, str, str]] = [
        (i + 1, t(f"size.{label}", default=label), t("size.words", words=words // 10_000))
        for i, (label, words) in enumerate(NOVEL_SIZES)
    ]
    print_choices_table(items, title=t("size.choose_title"), allow_custom=False)
    raw = prompt(t("common.choose"), default="2").strip()
    if not raw.isdigit():
        warn(t("size.invalid_default", value=raw))
        return "中篇"
    idx = int(raw) - 1
    if not (0 <= idx < len(NOVEL_SIZES)):
        warn(t("size.invalid_default", value=raw))
        return "中篇"
    label, words = NOVEL_SIZES[idx]
    info(t("size.selected", label=t(f"size.{label}", default=label), words=words // 10_000))
    return label


def size_to_word_count(size_label: str) -> int:
    """把规模档名（中/短/长/超长篇）映射到目标字数。未知档名兜底 30 万。"""
    return _SIZE_LABEL_TO_WORDS.get(size_label, 300_000)
