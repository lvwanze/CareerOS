# -*- coding: utf-8 -*-
# @File       : test_response_envelope.py
# @Path       : backend/tests/test_response_envelope.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-20 09:10:00
# @Version    : v1.0.0
"""统一响应封装的验收。

背景：组长审查 0f8f1ae 时指出「根路径返回裸 JSON、其余请求错误仍可能返回
FastAPI 默认的 {"detail": ...}」。本文件把「所有对外响应都必须是
{code, message, data, request_id}」这条约定固化成测试，避免以后新增路由
又漏掉一处。

不测 /health 与 /ready：这两个是运维探针，按约定保持裸结构，
test_health.py 里已有「不得出现 request_id」的反向断言。
"""
from fastapi.testclient import TestClient

from packages.service.main import app
from packages.service.routers import recommend

client = TestClient(app)
# 兜底 500 的处理器会被 TestClient 默认的 raise_server_exceptions 抢先抛出，
# 这里单独开一个不抛异常的客户端，才能看到真正的响应体。
lenient_client = TestClient(app, raise_server_exceptions=False)

ENVELOPE_KEYS = {"code", "message", "data", "request_id"}


def test_root_index_returns_envelope():
    """根路径是服务索引，会在 /docs 里露出，必须与业务接口同一套格式。"""
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == 200
    assert body["data"]["service"] == "CareerOS API"
    assert body["data"]["docs"] == "/docs"
    assert body["request_id"]


def test_unknown_route_returns_envelope_404():
    """路由不存在时不再返回 {"detail": "Not Found"}。"""
    response = client.get("/no-such-route")

    assert response.status_code == 404
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == 404
    assert body["data"] is None
    assert "detail" not in body


def test_method_not_allowed_returns_envelope_405():
    response = client.delete("/api/v1/skills")

    assert response.status_code == 405
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == 405
    assert "detail" not in body


def test_auto_validation_error_returns_envelope():
    """pydantic 在进入路由前拦下的错误，也要走信封 + 点分字段路径。"""
    response = client.post("/api/v1/recommendations", json={"profile": "not-an-object"})

    assert response.status_code == 422
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == 422
    assert body["data"]["errors"][0]["field"] == "profile"
    assert "detail" not in body


def test_unhandled_error_returns_envelope_500(monkeypatch):
    """未捕获异常只回通用文案，堆栈进日志不进响应体（api_spec §5）。"""

    def boom():
        raise RuntimeError("模拟数据文件读失败")

    monkeypatch.setattr(recommend, "_load_used_skills", boom)
    response = lenient_client.get("/api/v1/skills")

    assert response.status_code == 500
    body = response.json()
    assert set(body) == ENVELOPE_KEYS
    assert body["code"] == 500
    assert "RuntimeError" not in response.text
    assert "模拟数据文件读失败" not in response.text
