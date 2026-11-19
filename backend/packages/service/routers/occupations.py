#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : occupations.py
# @Path       : backend/packages/service/routers/occupations.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-19 11:22:00
# @Version    : v1.0.0
"""职业字典接口：列表 + 详情，对齐 api_spec §3.2 / §3.3。

两个取舍：
1. 列表只给 id/名称/类别/技能数，不带 description 和 skills —— 28 条职业的
   描述平均 300 字符，带上会把响应体撑到 10KB 以上，列表页也用不到；
2. 404 走 JSONResponse 而不是 HTTPException —— 后者会被 FastAPI 渲染成
   {"detail": ...}，与统一信封的四键结构对不上，前端判不出来。
"""
import csv
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from packages.core.schemas import ApiResponse
from packages.service.name_mapping import occupation_zh, skill_zh

router = APIRouter(prefix="/api/v1", tags=["occupations"])

# routers/occupations.py -> parents[0]=routers [1]=service [2]=packages [3]=backend
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_skill_rows() -> dict[str, dict]:
    with (DATA_DIR / "processed" / "skills.csv").open(encoding="utf-8", newline="") as file:
        return {row["skill_id"]: row for row in csv.DictReader(file)}


def _load_occupations() -> dict[str, dict]:
    """把三张表拼成 {occupation_id: 职业字典}，技能按 importance 降序。"""
    skill_rows = _load_skill_rows()

    occupations: dict[str, dict] = {}
    with (DATA_DIR / "processed" / "occupations.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            occupations[row["occupation_id"]] = {
                "occupation_id": row["occupation_id"],
                "name": row["name"],
                "name_zh": occupation_zh(row["occupation_id"], row["name"]),
                "description": row["description"],
                "category": row["category"],
                "skill_count": 0,
                "skills": [],
            }

    with (DATA_DIR / "processed" / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            occupation = occupations.get(row["occupation_id"])
            if occupation is None:
                continue
            skill = skill_rows.get(row["skill_id"], {})
            occupation["skills"].append({
                "skill_id": row["skill_id"],
                "name": skill.get("name", row["skill_id"]),
                "name_zh": skill_zh(row["skill_id"], skill.get("name", "")),
                "category": skill.get("category", ""),
                "importance": float(row["importance"]),
                "required_level": int(row["required_level"]),
            })

    for occupation in occupations.values():
        occupation["skills"].sort(key=lambda item: (-item["importance"], item["skill_id"]))
        occupation["skill_count"] = len(occupation["skills"])

    return occupations


def _to_list_item(occupation: dict) -> dict:
    return {
        "occupation_id": occupation["occupation_id"],
        "name": occupation["name"],
        "name_zh": occupation["name_zh"],
        "category": occupation["category"],
        "skill_count": occupation["skill_count"],
    }


@router.get("/occupations", response_model=ApiResponse)
async def list_occupations():
    occupations = _load_occupations()
    items = [
        _to_list_item(item)
        for item in sorted(occupations.values(), key=lambda occupation: occupation["occupation_id"])
    ]
    return ApiResponse(code=200, message="success", data={"items": items, "total": len(items)})


@router.get(
    "/occupations/{occupation_id}",
    response_model=ApiResponse,
    responses={404: {"model": ApiResponse, "description": "职业不存在"}},
)
async def get_occupation(occupation_id: str):
    occupation = _load_occupations().get(occupation_id)
    if occupation is None:
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                code=404,
                message=f"职业不存在：{occupation_id}",
                data=None,
            ).model_dump(),
        )
    return ApiResponse(code=200, message="success", data=occupation)
