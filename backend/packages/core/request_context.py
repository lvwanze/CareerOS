#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : request_context.py
# @Path       : backend/packages/core/request_context.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-26 09:00:00
# @Version    : v1.0.0
"""请求上下文：把 request_id 放进 contextvar，供全链路取用。

为什么放在 core 而不是 service（对应清单 M3 P0-2）：
    统一信封 ApiResponse 定义在 core/schemas.py，它在构造时就要拿到本次请求的
    request_id；如果 contextvar 放在 service，core 就得反向 import service，
    正好违反架构测试的分层约束。放在 core 之后，依赖方向仍然是
    service -> core、training -> core，与 ADR-009 一致。

为什么用 contextvar 而不是给每个路由传参：
    全仓有 12 处 ApiResponse(...) 构造点，逐个加 request_id 参数一定会漏；
    contextvar 由中间件在请求入口设置一次，构造点一行都不用改。

注意：contextvar 是「按协程隔离」的，不要在后台线程里取——uvicorn 是单进程
多协程，同步路由跑在线程池里时上下文会自动传递，这一点在 FastAPI 中是成立的。
"""
from contextvars import ContextVar

# 默认值 "-"：不在请求里（如启动阶段、脚本里）打日志时，字段仍存在，
# 便于日志解析方按固定 schema 处理，不用区分「有字段」和「没字段」。
_REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")


def current_request_id() -> str:
    """取当前请求的 request_id；不在请求上下文中时返回 "-"。"""
    return _REQUEST_ID.get()


def set_request_id(request_id: str):
    """设置当前请求的 request_id，返回 token 供 finally 里还原。"""
    return _REQUEST_ID.set(request_id)


def reset_request_id(token) -> None:
    """还原 contextvar，避免复用线程/协程时串号。"""
    _REQUEST_ID.reset(token)
