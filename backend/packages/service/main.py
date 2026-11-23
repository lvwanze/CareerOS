# packages/service/main.py
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from packages.core.schemas import (
    CareerTreeResponse,
    CareerTreeResponseData,
    TreeNode,
)
from packages.service.routers.recommend import router as recommend_router

app = FastAPI(title="CareerOS API", version="0.1.0")


def new_request_id() -> str:
    """统一 request_id 格式，和 docs/api_spec.md 的 req_xxx 对齐。"""
    return f"req_{uuid.uuid4().hex[:8]}"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI 默认的 422 是 {"detail": [...]}，没有 code/message/request_id，
    前端没法按统一信封解析，这里补成同样的结构。"""
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "请求参数不符合要求",
            "data": {"errors": exc.errors()},
            "request_id": new_request_id(),
        },
    )

# 允许跨域，方便代旭写的前端页面联调
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(recommend_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "CareerOS API is running"}

@app.get("/v1/tree/{occupation_id}", response_model=CareerTreeResponse)
def get_career_tree(occupation_id: str):
    # 模拟发展树数据
    mock_nodes = [
        TreeNode(node_id="n1", skill_id="SK002", skill_name="Python", status="mastered", description="已掌握基础语法"),
        TreeNode(node_id="n2", skill_id="SK001", skill_name="SQL", status="in_progress", description="需要加强多表联查"),
        TreeNode(node_id="n3", skill_id="SK003", skill_name="业务分析", status="in_progress", description="正在做实战项目")
    ]
    return CareerTreeResponse(data=CareerTreeResponseData(occupation_id=occupation_id, nodes=mock_nodes))