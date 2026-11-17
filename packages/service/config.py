#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : config.py
# @Path       : packages/service/config.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 00:05:00
# @Version    : v1.0.0
# @Description: 后端服务配置：项目根定位、接口常量、数据目录
# @ChangeLog:
#   2026-11-18 00:05:00 | 代旭 | v1.0.0 | 初始化创建
"""后端服务配置。

项目根用「标记文件法」定位，不数 parents 层数、不写绝对路径：
从本文件所在目录逐级向上找含 README.md 的目录，找到的那一级就是仓库根。
"""

from pathlib import Path

WORKSPACE_MARKER = "README.md"


def find_project_root(marker: str = WORKSPACE_MARKER) -> Path:
    """从当前文件所在目录逐级向上查找项目根。

    Args:
        marker: 项目根目录里必然存在的标记文件名。

    Returns:
        项目根目录的 Path 对象。

    Raises:
        FileNotFoundError: 向上找到磁盘根还没找到标记文件时抛出。
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / marker).exists():
            return parent
    raise FileNotFoundError(f"未找到项目根标记文件 {marker!r}，请确认它存在于仓库根目录")


PROJECT_ROOT = find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

API_PREFIX = "/api/v1"
TOP_K = 5
ENGINE_TAG = "stub"
KB_CONTRACT_VERSION = "V1.0"
