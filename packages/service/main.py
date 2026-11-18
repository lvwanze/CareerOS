#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : main.py
# @Path       : packages/service/main.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 16:10:00
# @Version    : v1.2.0
# @Description: 服务启动入口：装配 app、跨域、请求追踪、异常处理、路由
# @ChangeLog:
#   2026-11-18 16:10:00 | 代旭 | v1.2.0 | 增加 request_id 绑定与统一异常处理，注册技能字典路由
#   2026-11-18 00:05:00 | 代旭 | v1.1.0 | 拆出 routers，入口只做装配
"""CareerOS 后端服务启动入口。

只做装配：创建 app、配跨域、绑定请求追踪 ID、注册异常处理与路由。
业务逻辑放在 routers/ 与 services/ 里，不在本文件堆积。
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.service.config import API_PREFIX, ENGINE_TAG
from packages.service.errors import register_exception_handlers
from packages.service.response import bind_request_id, new_request_id
from packages.service.routers import health, recommendations, skills

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="CareerOS API", version="0.1.0")

# 允许跨域，方便 Flutter 客户端联调。
# allow_origins=["*"] 与 allow_credentials=True 同时打开会被浏览器拒绝，所以这里关掉凭据。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_context(request, call_next):
    """在入口生成 request_id 并绑定到上下文，响应头回填，便于全链路追踪。"""
    request_id = new_request_id()
    bind_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Engine"] = ENGINE_TAG
    return response


register_exception_handlers(app)

app.include_router(health.router)
app.include_router(skills.router, prefix=API_PREFIX)
app.include_router(recommendations.router, prefix=API_PREFIX)


@app.get("/", summary="服务根路径：给调用方指路")
def root() -> dict:
    """返回文档地址与接口前缀，避免直接访问根路径时只看到 404。"""
    return {
        "service": "CareerOS API",
        "docs": "/docs",
        "api_prefix": API_PREFIX,
        "engine": ENGINE_TAG,
    }
