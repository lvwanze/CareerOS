#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : career_tree.py
# @Path       : backend/packages/service/routers/career_tree.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-25 14:50:00
# @Version    : v2.0.0
"""发展树接口，对齐 api_spec §3.6。

上一版这里返回 main.py 里写死的 3 个节点（Python / SQL / 业务分析），
传 occ_eng 和传一个不存在的 ID 结果一模一样，节点之间也没有父子关系——验收时
判为"树是 mock、结构不合法"。这一版改成按 occupation_id 从三张表现拼：

    GET /api/v1/tree/{occupation_id}   正式路径，带 /api 前缀（与其余接口一致）
    GET /v1/tree/{occupation_id}       旧路径，保留兼容，响应头标 Deprecation

三个取舍：
1. 职业不存在返回 404 而不是空树：空树会被前端当成"该职业没有技能要求"，
   与"ID 写错了"完全分不清。
2. 旧路径不删只标弃用：frontend/lib/services/api_service.dart 还在请求 /v1/tree，
   直接删会让发展树页白屏；留一个版本的迁移窗口，下个版本再摘。
3. 结构合法性在拼树时就用 knowledge.validate_tree 校验，坏数据直接报错，
   不把半成品树返回给前端——树的形状错了，前端画不出来也查不到原因。
"""

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from packages.core.schemas import ApiResponse, CareerTreeResponse, CareerTreeResponseData
from packages.service.knowledge import build_career_tree

router = APIRouter(tags=["tree"])
deprecated_router = APIRouter(tags=["tree"], deprecated=True)


def _build(
    occupation_id: str,
    response: Response,
    extra_headers: dict[str, str] | None = None,
) -> CareerTreeResponse | JSONResponse:
    """拼树 → 套统一信封。两条路径共用，保证新旧路径返回字节级一致的 data。

    成功分支故意返回模型实例而不是 JSONResponse：
    一旦这里自己 dump 成 JSON，路由上的 response_model 就形同虚设——
    schemas.py 改了字段、拼树代码没跟上，接口照样 200 吐旧结构，测试也很难发现。
    交给 FastAPI 按 response_model 序列化，字段不匹配当场 500，坏得早比坏得静默好。
    404 才用 JSONResponse：它不是 CareerTreeResponse，塞不进同一个 response_model。
    """
    tree = build_career_tree(occupation_id)
    if tree is None:
        # 404 也走统一信封：前端按 code 判断成败，退化成 {"detail": ...} 会漏分支
        return JSONResponse(
            status_code=404,
            content=ApiResponse(
                code=404,
                message=f"职业不存在：{occupation_id}",
                data=None,
            ).model_dump(),
            headers=extra_headers,
        )
    if extra_headers:
        # 返回 Response 实例时注入的 response 会被丢弃，成功分支的响应头要显式写
        response.headers.update(extra_headers)
    return CareerTreeResponse(data=CareerTreeResponseData(**tree))


@router.get(
    "/tree/{occupation_id}",
    response_model=CareerTreeResponse,
    responses={404: {"model": ApiResponse, "description": "职业不存在"}},
    summary="获取指定职业的发展树（职业根 → 技能类别 → 技能）",
)
async def get_career_tree(occupation_id: str, response: Response):
    return _build(occupation_id, response)


@deprecated_router.get(
    "/tree/{occupation_id}",
    response_model=CareerTreeResponse,
    responses={404: {"model": ApiResponse, "description": "职业不存在"}},
    include_in_schema=False,
)
async def get_career_tree_legacy(occupation_id: str, response: Response):
    """旧路径 /v1/tree/{id}（缺 /api 前缀）。数据与正式路径完全一致，
    只在响应头声明弃用，让还在用旧路径的前端有迁移窗口。"""
    return _build(
        occupation_id,
        response,
        extra_headers={
            "Deprecation": "true",
            "Link": f'</api/v1/tree/{occupation_id}>; rel="successor-version"',
        },
    )
