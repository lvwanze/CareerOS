#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : test_health.py
# @Path       : backend/tests/test_health.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-19 15:08:00
# @Version    : v1.0.0
"""健康检查两条探针的验收。

重点不是「返 200」，而是「数据不在时必须返 503」—— 这条不测，探针就只是个摆设。
"""
import pytest
from fastapi.testclient import TestClient

from packages.service.main import app
from packages.service.routers import health

client = TestClient(app)


def test_health_is_bare_and_always_200():
    """存活探针：裸结构、不套信封、不查依赖。"""
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "request_id" not in body


def test_ready_reports_real_row_counts():
    """就绪探针：真读三表，行数与冻结数据一致。"""
    health.reset_cache()
    response = client.get("/ready?refresh=1")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["engine"] == "real"
    assert body["contract_version"] == "V1.0"
    assert body["data"]["occupations"] == 28
    assert body["data"]["skills"] == 35
    assert body["data"]["occupation_skills"] == 492


def test_ready_returns_503_when_data_missing(monkeypatch, tmp_path):
    """把数据目录指到空目录，必须 503，而不是装作就绪。"""
    monkeypatch.setattr(health, "PROCESSED_DIR", tmp_path)
    health.reset_cache()
    try:
        response = client.get("/ready?refresh=1")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert "缺失" in body["reason"]
    finally:
        monkeypatch.undo()
        health.reset_cache()


def test_ready_recovers_after_data_restored():
    """数据回来后立刻恢复 200，证明缓存不会把 503 粘住。"""
    health.reset_cache()
    response = client.get("/ready?refresh=1")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
