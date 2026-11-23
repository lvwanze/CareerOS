"""按 api_spec.md 实现的极简 FastAPI 服务，仅供测试自检。

真实后端（代旭）接入后，conftest.py 会自动改用真实 app，本文件即被绕过。
"""

import uuid

from fastapi import FastAPI
from pydantic import BaseModel

from .algorithm import match_profile
from .schemas import ApiResponse, UserProfile

app = FastAPI(title="CareerOS reference stub", version="v1-reference")


class RecommendRequest(BaseModel):
    profile: UserProfile


def _to_dict(model):
    """兼容 Pydantic v1 / v2 的序列化。"""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/recommendations")
def recommendations(req: RecommendRequest):
    data = match_profile(_to_dict(req.profile))
    return _to_dict(ApiResponse(
        code=200,
        message="success",
        data=data,
        request_id=f"req_{uuid.uuid4().hex[:8]}",
    ))
