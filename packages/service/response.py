#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : response.py
# @Path       : packages/service/response.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 16:10:00
# @Version    : v1.1.0
# @Description: 统一响应信封、request_id 生成与本次请求的追踪 ID
# @ChangeLog:
#   2026-11-18 16:10:00 | 代旭 | v1.1.0 | 增加请求级 request_id 绑定，响应头与响应体保持一致
#   2026-11-18 00:05:00 | 代旭 | v1.0.0 | 初始化创建
"""统一响应信封。

字段口径见 docs/data_contract.md §3.8 与 docs/api_spec.md §2：
code / message / data / request_id。注意是 request_id，不是 requestId。

request_id 由中间件在入口生成并绑定到当前请求上下文，
响应体与响应头 X-Request-Id 取同一个值，排查问题时能对上。
"""

import uuid
from contextvars import ContextVar
from typing import Any

_REQUEST_ID: ContextVar[str | None] = ContextVar("careeros_request_id", default=None)


def new_request_id() -> str:
    """生成一个新的请求追踪 ID。

    Returns:
        形如 req_2f7c9a1b 的字符串，前缀固定、后 8 位随机。
    """
    return f"req_{uuid.uuid4().hex[:8]}"


def bind_request_id(request_id: str) -> None:
    """把本次请求的追踪 ID 绑定到当前上下文，供响应与日志复用。

    Args:
        request_id: 中间件在入口生成的追踪 ID。
    """
    _REQUEST_ID.set(request_id)


def current_request_id() -> str:
    """返回本次请求的追踪 ID。

    Returns:
        上下文里已绑定的 ID；没有绑定时现场生成一个新的。
    """
    existing = _REQUEST_ID.get()
    return existing if existing else new_request_id()


def ok(data: Any = None, request_id: str | None = None) -> dict:
    """按统一信封包装成功响应。

    Args:
        data: 业务数据，失败时为 None。
        request_id: 已有追踪 ID 时传入，不传则取本次请求的 ID。

    Returns:
        含 code / message / data / request_id 四个键的字典。
    """
    return {
        "code": 200,
        "message": "success",
        "data": data,
        "request_id": request_id or current_request_id(),
    }
