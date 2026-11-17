#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : response.py
# @Path       : packages/service/response.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 00:05:00
# @Version    : v1.0.0
# @Description: 统一响应信封与 request_id 生成
# @ChangeLog:
#   2026-11-18 00:05:00 | 代旭 | v1.0.0 | 初始化创建
"""统一响应信封。

字段口径见 docs/data_contract.md §3.8 与 docs/api_spec.md §2：
code / message / data / request_id。注意是 request_id，不是 requestId。
"""

import uuid
from typing import Any


def new_request_id() -> str:
    """生成请求追踪 ID。

    Returns:
        形如 req_2f7c9a1b 的字符串，前缀固定、后 8 位随机。
    """
    return f"req_{uuid.uuid4().hex[:8]}"


def ok(data: Any = None, request_id: str | None = None) -> dict:
    """按统一信封包装成功响应。

    Args:
        data: 业务数据，失败时为 None。
        request_id: 已有追踪 ID 时传入，不传则现场生成。

    Returns:
        含 code / message / data / request_id 四个键的字典。
    """
    return {
        "code": 200,
        "message": "success",
        "data": data,
        "request_id": request_id or new_request_id(),
    }
