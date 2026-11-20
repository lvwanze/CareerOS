#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : occupations.py
# @Path       : backend/packages/service/routers/occupations.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-19 15:50:00
# @Version    : v1.1.0
"""职业字典接口：列表 + 详情，对齐 api_spec §3.2 / §3.3。

中文名直接读组长那份 `data/reference/*_zh.csv`（已随 main 入库），本文件不再
维护第二份映射表 —— 两份并存会出现同一技能两个译名。

三个取舍：
1. 列表只给 id/名称/类别/技能数，不带 description 和 skills（28 条描述平均 300 字符）；
2. 404 走 JSONResponse 而不是 HTTPException，后者会被渲染成 {"detail": ...}，与信封不符；
3. 映射文件缺失时降级成英文名，不让服务起不来。
"""
import csv
import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from packages.core.name_text import clean_name
from packages.core.schemas import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["occupations"])

# routers/occupations.py -> parents[0]=routers [1]=service [2]=packages [3]=backend
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
REFERENCE_DIR = DATA_DIR / "reference"


def _load_name_mapping(filename: str, id_field: str) -> dict[str, str]:
    """读参考映射，返回 {id: 中文名}。文件缺失返回空表，回退英文名。"""
    path = REFERENCE_DIR / filename
    if not path.is_file():
        logger.warning("中文名映射缺失，回退英文名：%s", path)
        return {}

    table: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            key_value = clean_name(row.get(id_field))
            name_zh = clean_name(row.get("name_zh"))
            if key_value and name_zh:
                table[key_value] = name_zh
    return table


def _name_zh(table: dict[str, str], key_value: str, fallback: str) -> str:
    """回退链：映射命中 -> 英文名 -> id，保证永不为空。"""
    return table.get(key_value) or clean_name(fallback) or key_value


def _load_skill_rows() -> dict[str, dict]:
    with (DATA_DIR / "processed" / "skills.csv").open(encoding="utf-8", newline="") as file:
        return {row["skill_id"]: row for row in csv.DictReader(file)}


def _load_occupations() -> dict[str, dict]:
    """把三张表拼成 {occupation_id: 职业字典}，技能按 importance 降序。"""
    skill_rows = _load_skill_rows()
    skill_names_zh = _load_name_mapping("skill_name_zh.csv", "skill_id")
    occupation_names_zh = _load_name_mapping("occupation_name_zh.csv", "occupation_id")

    occupations: dict[str, dict] = {}
    with (DATA_DIR / "processed" / "occupations.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            occupations[row["occupation_id"]] = {
                "occupation_id": row["occupation_id"],
                "name": row["name"],
                "name_zh": _name_zh(occupation_names_zh, row["occupation_id"], row["name"]),
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
                "name_zh": _name_zh(skill_names_zh, row["skill_id"], skill.get("name", "")),
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
