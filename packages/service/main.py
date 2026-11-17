#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : main.py
# @Path       : packages/service/main.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 00:05:00
# @Version    : v1.1.0
# @Description: 服务启动入口：装配 app、跨域、路由
# @ChangeLog:
#   2026-11-18 00:05:00 | 代旭 | v1.1.0 | 拆出 routers，入口只做装配
"""CareerOS 后端服务启动入口。

只做四件事：创建 app、配跨域、注册路由。业务逻辑放 routers/ 与 services/。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.service.config import API_PREFIX, ENGINE_TAG
from packages.service.routers import health, recommendations

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
async def add_engine_header(request, call_next):
    """给每个响应打上引擎标识，便于前端与测试区分占位结果与真实算法。"""
    response = await call_next(request)
    response.headers["X-Engine"] = ENGINE_TAG
    return response


app.include_router(health.router)
app.include_router(recommendations.router, prefix=API_PREFIX)
