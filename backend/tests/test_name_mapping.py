#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : test_name_mapping.py
# @Path       : backend/tests/test_name_mapping.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-19 11:30:00
# @Version    : v1.0.0
"""中英名称映射与职业接口的六条验收。

设计口径：
- 中文名必须能被「是不是汉字」证伪，不认拼音、不认英文，防编数据；
- 每条都要能指着数据源说清来源（接口 vs 映射 CSV 逐条对账）；
- 映射文件缺失必须仍返 200，这是组长那份映射提交查无下落时的兜底路径。
"""
import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from packages.service.main import app
from packages.service.routers import occupations, recommend

client = TestClient(app)

BACKEND_DIR = Path(__file__).resolve().parents[1]
REFERENCE_DIR = BACKEND_DIR / "data" / "reference"


def has_cjk(text: str) -> bool:
    """真汉字才算中文，防止把拼音或英文当成中文名。"""
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def read_mapping(filename: str, key_column: str) -> dict[str, str]:
    with (REFERENCE_DIR / filename).open(encoding="utf-8-sig", newline="") as file:
        return {row[key_column]: row["name_zh"] for row in csv.DictReader(file)}


def test_skills_every_item_has_name_zh():
    """35 条技能里 2 条零引用被排除，接口应返 33 条，每条都有中文名。"""
    response = client.get("/api/v1/skills")

    assert response.status_code == 200
    skills = response.json()["data"]
    assert len(skills) == 33
    assert all(skill["name_zh"] and skill["name_zh"].strip() for skill in skills)
    assert sum(1 for skill in skills if has_cjk(skill["name_zh"])) >= 30


def test_skills_name_zh_matches_mapping_file():
    """接口返回值与映射表逐条对账，防止接口里塞死数据。"""
    expected = read_mapping("skill_name_zh.csv", "skill_id")
    skills = client.get("/api/v1/skills").json()["data"]

    for skill in skills:
        assert skill["name_zh"] == expected[skill["skill_id"]]


def test_skills_fall_back_to_english_when_mapping_missing(monkeypatch, tmp_path):
    """映射文件不在时仍返 200，中文名回退英文名。

    skills 的中文名由 recommend 模块提供，occupations 用自己的加载器，
    两条路径都要测，所以两边一起置空。
    """
    monkeypatch.setattr(recommend, "REFERENCE_DIR", tmp_path)
    monkeypatch.setattr(occupations, "REFERENCE_DIR", tmp_path)

    skill_response = client.get("/api/v1/skills")
    assert skill_response.status_code == 200
    skills = skill_response.json()["data"]
    assert len(skills) == 33
    assert all(skill["name_zh"] == skill["name"] for skill in skills)

    occupation_response = client.get("/api/v1/occupations")
    assert occupation_response.status_code == 200
    items = occupation_response.json()["data"]["items"]
    assert len(items) == 28
    assert all(item["name_zh"] == item["name"] for item in items)


def test_occupations_list_returns_28_with_name_zh():
    body = client.get("/api/v1/occupations").json()

    assert body["code"] == 200
    items = body["data"]["items"]
    assert len(items) == 28
    assert body["data"]["total"] == 28
    assert all(item["name_zh"] and has_cjk(item["name_zh"]) for item in items)
    assert all(item["skill_count"] > 0 for item in items)
    assert sum(1 for item in items if item["category"] == "Business and Financial Operations") == 5


def test_occupation_detail_ok_and_404_enveloped():
    ok_response = client.get("/api/v1/occupations/OCC-ONET-15-1252.00")

    assert ok_response.status_code == 200
    detail = ok_response.json()["data"]
    assert detail["name"] == "Software Developers"
    assert detail["name_zh"] == "软件开发人员"
    importances = [skill["importance"] for skill in detail["skills"]]
    assert importances == sorted(importances, reverse=True)
    assert all(has_cjk(skill["name_zh"]) for skill in detail["skills"])

    miss_response = client.get("/api/v1/occupations/OCC-ONET-99-9999.99")

    assert miss_response.status_code == 404
    body = miss_response.json()
    assert set(body) == {"code", "message", "data", "request_id"}
    assert body["code"] == 404
    assert body["data"] is None


def test_openapi_exposes_occupation_paths():
    paths = app.openapi()["paths"]

    assert "/api/v1/occupations" in paths
    assert "/api/v1/occupations/{occupation_id}" in paths
    assert "/api/v1/skills" in paths
    assert "/api/v1/recommendations" in paths


def test_reference_mapping_ids_are_unique():
    """映射表主键不重复：重复会让字典后值覆盖前值，静默丢掉一个中文名。"""
    for filename, key_column in (
        ("skill_name_zh.csv", "skill_id"),
        ("occupation_name_zh.csv", "occupation_id"),
    ):
        with (REFERENCE_DIR / filename).open(encoding="utf-8-sig", newline="") as file:
            ids = [row[key_column] for row in csv.DictReader(file)]

        assert len(ids) == len(set(ids)), f"{filename} 主键有重复"
        assert all(ids), f"{filename} 存在空主键"


def test_reference_mapping_matches_manifest():
    """产物与 manifest 登记一致，等价于「构建脚本重跑一次还是这个结果」。

    注意：manifest 的 sha256 按 LF 字节算，Windows checkout 会把 CSV 转成
    CRLF（仓库没有 .gitattributes），所以先归一化再比对，否则本地红、Linux 绿。
    """
    manifest = json.loads((BACKEND_DIR / "data" / "manifest.json").read_text(encoding="utf-8"))
    registered = manifest["derived_reference_data"]["files"]

    assert set(registered) == {"skill_name_zh.csv", "occupation_name_zh.csv"}

    for filename, meta in registered.items():
        raw_bytes = (REFERENCE_DIR / filename).read_bytes().replace(b"\r\n", b"\n")
        actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        assert actual_sha256 == meta["sha256"], f"{filename} 与 manifest 登记的 sha256 不一致"

        with (REFERENCE_DIR / filename).open(encoding="utf-8-sig", newline="") as file:
            row_count = sum(1 for _ in csv.DictReader(file))
        assert row_count == meta["row_count"], f"{filename} 行数与 manifest 登记不一致"
