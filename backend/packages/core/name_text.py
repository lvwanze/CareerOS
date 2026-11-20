#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : name_text.py
# @Path       : backend/packages/core/name_text.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-20 09:25:00
# @Version    : v1.0.0
"""中文名映射的取值清洗。

为什么单独抽一个文件
--------------------
occupations.py 和 recommend.py 各自写过一遍映射加载，清洗口径却不同：
前者有残留值黑名单，后者只挡空串。结果是同一份 CSV 里某行 name_zh 为
Excel 导出的 `nan` 时，`/api/v1/occupations` 回退英文名，`/api/v1/skills`
却把 "nan" 当中文名返回 —— 同一个技能两个接口两个名字。

两份实现已经偏差过一次，这里收成一份，两边 import，不再各写各的。
"""
from typing import Any

# Excel 另存 CSV 的常见残留值，统一当作「没有中文名」
EMPTY_NAME_VALUES = {"", "nan", "none", "null", "na", "n/a", "-"}


def clean_name(value: Any) -> str:
    """去掉 BOM 与首尾空白；命中残留值返回空串，交给调用方回退英文名。"""
    if value is None:
        return ""
    text = str(value).replace("\ufeff", "").strip()
    if text.lower() in EMPTY_NAME_VALUES:
        return ""
    return text
