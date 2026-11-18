#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : errors.py
# @Path       : packages/service/errors.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 16:10:00
# @Version    : v1.0.0
# @Description: 统一异常处理：参数校验、资源不存在、未捕获异常
# @ChangeLog:
#   2026-11-18 16:10:00 | 代旭 | v1.0.0 | 初始化创建
"""统一异常处理。

FastAPI 默认把参数错误返回成 {"detail": [...]}，与 api_spec.md §2 的信封不一致，
前端同时判 HTTP 状态码与业务 code 就会失配，因此这里统一包装：

- 422 参数校验失败：data 里给 errors 列表（字段 + 原因），前端能直接定位到输入项
- 404 / 其他 HTTP 异常：沿用异常自带状态码，data 为 null
- 500 未捕获异常：只返回通用文案，堆栈只进服务端日志，绝不外泄
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from packages.service.response import current_request_id

logger = logging.getLogger(__name__)


def build_envelope(code: int, message: str, data: object = None) -> dict:
    """构造统一信封，供各异常处理器复用。

    Args:
        code: 业务状态码，与 HTTP 状态码保持一致。
        message: 面向调用方的错误说明。
        data: 附加数据，无则为 None。

    Returns:
        含四个固定键的字典。
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": current_request_id(),
    }


def pick_error_items(exc: RequestValidationError) -> list[dict]:
    """把 Pydantic 的报错压成前端能用的字段级列表。

    Args:
        exc: FastAPI 抛出的参数校验异常。

    Returns:
        每项含 field / message / type 的列表；loc 里的 body 前缀会被去掉，
        否则前端拿到的字段名会是 "body.profile.skills"。
    """
    items: list[dict] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part != "body"]
        items.append(
            {
                "field": ".".join(location) if location else "body",
                "message": str(error.get("msg", "")),
                "type": str(error.get("type", "")),
            }
        )
    return items


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """参数校验失败：返回 422 与字段级错误列表。"""
    return JSONResponse(
        status_code=422,
        content=build_envelope(422, "请求参数不符合要求", {"errors": pick_error_items(exc)}),
    )


async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """路由不存在或业务主动抛出的 HTTP 异常：沿用原状态码与说明。"""
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(exc.status_code, message),
        headers=getattr(exc, "headers", None),
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常：日志留全量堆栈，响应只给通用文案。"""
    logger.exception("未处理异常 request_id=%s path=%s", current_request_id(), request.url.path)
    return JSONResponse(
        status_code=500,
        content=build_envelope(500, "服务器内部错误，请稍后重试或联系管理员"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """把三个处理器注册到应用上。

    Args:
        app: FastAPI 实例。
    """
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
