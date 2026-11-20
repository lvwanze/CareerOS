#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : health.py
# @Path       : backend/packages/service/routers/health.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-19 15:05:00
# @Version    : v1.0.0
"""存活探针与就绪探针。

两个探针的职责必须分开（这是课程硬要求，也是编排器的通用约定）：
- /health 只判断进程还活着，依赖挂了也要返 200，否则编排器会把一个正在等数据的
  服务反复重启；
- /ready 判断能不能干活，三表读不到就返 503，让流量别进来。

就绪检查是真读文件，不是 return True。答辩时把 data/processed 移走再打一次，
必须看到 503 —— 这是这套探针唯一的价值证明。
"""
import csv
import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])

# routers/health.py -> parents[0]=routers [1]=service [2]=packages [3]=backend
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# 必需列：缺一列就说明数据包不是 V1.0 那一份，宁可 503 也不要带病返回
REQUIRED_COLUMNS = {
    "occupations.csv": ("occupation_id", "name", "description", "category"),
    "skills.csv": ("skill_id", "name", "category"),
    "occupation_skills.csv": ("occupation_id", "skill_id", "importance", "required_level"),
}

CACHE_SECONDS = 10.0
_cache = {"checked_at": 0.0, "payload": None, "ready": False}


def _read_id_column(filename: str, column: str) -> set[str]:
    with (PROCESSED_DIR / filename).open(encoding="utf-8", newline="") as file:
        return {row[column] for row in csv.DictReader(file)}


def _probe_knowledge_base() -> tuple[bool, dict]:
    """真读三表：文件在、列齐、行数非空、关联表无孤儿外键。"""
    counts: dict[str, int] = {}

    for filename, required in REQUIRED_COLUMNS.items():
        path = PROCESSED_DIR / filename
        if not path.is_file():
            return False, {"reason": f"数据文件缺失: {filename}"}

        with path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            header = tuple(reader.fieldnames or ())
            missing = [column for column in required if column not in header]
            if missing:
                return False, {"reason": f"{filename} 缺列: {missing}"}
            counts[filename.replace(".csv", "")] = sum(1 for _ in reader)

        if counts[filename.replace(".csv", "")] <= 0:
            return False, {"reason": f"{filename} 是空表"}

    occupation_ids = _read_id_column("occupations.csv", "occupation_id")
    skill_ids = _read_id_column("skills.csv", "skill_id")

    orphan_occupation = 0
    orphan_skill = 0
    with (PROCESSED_DIR / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row["occupation_id"] not in occupation_ids:
                orphan_occupation += 1
            if row["skill_id"] not in skill_ids:
                orphan_skill += 1

    if orphan_occupation or orphan_skill:
        return False, {
            "reason": "关联表存在孤儿外键",
            "orphan_occupation": orphan_occupation,
            "orphan_skill": orphan_skill,
        }

    return True, counts


def _readiness_payload(force_refresh: bool) -> tuple[bool, dict]:
    now = time.monotonic()
    if not force_refresh and _cache["payload"] is not None and now - _cache["checked_at"] < CACHE_SECONDS:
        return _cache["ready"], _cache["payload"]

    ready, detail = _probe_knowledge_base()
    if ready:
        payload = {
            "status": "ready",
            "engine": "stub",
            "contract_version": "V1.0",
            "data": detail,
        }
    else:
        payload = {"status": "not_ready", **detail}

    _cache["checked_at"] = now
    _cache["payload"] = payload
    _cache["ready"] = ready
    return ready, payload


def reset_cache() -> None:
    """清就绪缓存。测试里换了数据目录必须调用。"""
    _cache["checked_at"] = 0.0
    _cache["payload"] = None
    _cache["ready"] = False


@router.get("/health")
def health_check():
    return {"status": "ok", "message": "CareerOS API is running"}


@router.get("/ready")
def readiness_check(refresh: int = 0):
    ready, payload = _readiness_payload(force_refresh=bool(refresh))
    if not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload
