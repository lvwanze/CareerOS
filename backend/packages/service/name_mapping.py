#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : name_mapping.py
# @Path       : backend/packages/service/name_mapping.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-19 11:20:00
# @Version    : v1.0.0
"""中英名称映射：按 ID 查中文名，查不到就回退英文名。

设计取舍（三条硬约束）：
1. 只用标准库 csv —— 与 routers/recommend.py 的读表方式保持一致，不引 pandas；
2. 映射文件缺失不能让服务起不来 —— 组长那条 cd9e2aa 在远端查无此提交，
   所以必须有「找不到文件就降级成空表、回退英文」这条路；
3. 键必须是 ID，不能用英文名 —— 英文名有空格/大小写/连字符差异，
   按名字 join 查不到时静默回退英文，页面看着正常但没中文，最难查。
"""
import csv
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# service/name_mapping.py -> parents[0]=service, [1]=packages, [2]=backend
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MAP_DIR = DATA_DIR / "mappings"

# Excel 另存 CSV 常见残留值，统一当作「没有中文名」
_EMPTY_VALUES = {"", "nan", "none", "null", "na", "n/a", "-"}


def _clean(value: object) -> str:
    """把 None、空串、nan、null、BOM 统一洗成空串。"""
    if value is None:
        return ""
    text = str(value).replace("\ufeff", "").strip()
    if text.lower() in _EMPTY_VALUES:
        return ""
    return text


@lru_cache(maxsize=4)
def _load(filename: str, key_column: str) -> dict[str, str]:
    """读一份映射表，返回 {id: 中文名}。文件缺失返回空表，不抛异常。"""
    path = MAP_DIR / filename
    if not path.is_file():
        logger.warning("中文名映射文件缺失，本次回退英文名：%s", path)
        return {}

    table: dict[str, str] = {}
    # utf-8-sig 吃掉 BOM，否则首列表头会变成 "\ufeffskill_id"，整表静默失效
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            key_value = _clean(row.get(key_column))
            name_zh = _clean(row.get("name_zh"))
            if key_value and name_zh:
                table[key_value] = name_zh

    logger.info("已加载中文名映射 %s：%d 条", filename, len(table))
    return table


def skill_zh(skill_id: str, fallback: str = "") -> str:
    """技能中文名。回退链：映射命中 -> 英文名 -> id，保证永不为空。"""
    return _load("skill_name_zh.csv", "skill_id").get(skill_id) or _clean(fallback) or skill_id


def occupation_zh(occupation_id: str, fallback: str = "") -> str:
    """职业中文名。回退链同上。"""
    return (
        _load("occupation_name_zh.csv", "occupation_id").get(occupation_id)
        or _clean(fallback)
        or occupation_id
    )


def reset_cache() -> None:
    """清缓存。测试里换了 MAP_DIR 必须调用，否则空表会被缓存给后面的用例。"""
    _load.cache_clear()
