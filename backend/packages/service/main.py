# packages/service/main.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from packages.core.schemas import (
    ApiResponse,
    CareerTreeResponse,
    CareerTreeResponseData,
    TreeNode,
)
from packages.service.routers.health import router as health_router
from packages.service.routers.occupations import router as occupations_router
from packages.service.routers.recommend import router as recommend_router

app = FastAPI(title="CareerOS API", version="0.1.0")


def _format_validation_error(err: dict) -> dict:
    """把 pydantic 的单条错误转成 {field, message}。

    loc 形如 ("body", "profile", "skills", 0, "self_level")，去掉 body 后
    用点连接，与路由内手写校验（如 profile.skills）保持同一种路径写法。
    """
    loc = [str(part) for part in err.get("loc", ()) if part != "body"]
    field = ".".join(loc) or "body"
    ctx = err.get("ctx") or {}
    message = {
        "less_than_equal": f"不能大于 {ctx.get('le')}",
        "greater_than_equal": f"不能小于 {ctx.get('ge')}",
        "missing": "为必填项",
        "int_parsing": "必须是整数",
        "int_type": "必须是整数",
        "string_type": "必须是字符串",
        "string_too_short": "不能为空",
    }.get(err.get("type", ""), err.get("msg", "格式不正确"))
    return {"field": field, "message": message}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """统一 422 响应格式。

    FastAPI 原生返回 {"detail": [...]}，而路由内 _reject_empty_skills 返回
    {"code", "message", "data": {"errors"}}。同一接口出现两种错误格式，
    前端要写两套解析、测试侧会当成两套契约，故统一为后者。
    """
    return JSONResponse(
        status_code=422,
        content=ApiResponse(
            code=422,
            message="请求参数不符合要求",
            data={"errors": [_format_validation_error(err) for err in exc.errors()]},
        ).model_dump(),
    )


# 允许跨域，方便前端联调
# allow_credentials 必须为 False：与 allow_origins=["*"] 共存时浏览器会直接拒绝响应
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend_router)
app.include_router(occupations_router)
app.include_router(health_router)


@app.get("/")
def show_route_index():
    # 根路径给个索引，免得打开服务地址看到 Not Found 以为服务挂了
    return {
        "service": "CareerOS API",
        "docs": "/docs",
        "routes": [
            "GET  /health",
            "GET  /ready",
            "GET  /api/v1/skills",
            "POST /api/v1/recommendations",
            "GET  /api/v1/occupations",
            "GET  /api/v1/occupations/{occupation_id}",
            "GET  /v1/tree/{occupation_id}",
        ],
    }


@app.get("/v1/tree/{occupation_id}", response_model=CareerTreeResponse)
def get_career_tree(occupation_id: str):
    # 模拟发展树数据
    mock_nodes = [
        TreeNode(node_id="n1", skill_id="SK002", skill_name="Python", status="mastered", description="已掌握基础语法"),
        TreeNode(node_id="n2", skill_id="SK001", skill_name="SQL", status="in_progress", description="需要加强多表联查"),
        TreeNode(node_id="n3", skill_id="SK003", skill_name="业务分析", status="in_progress", description="正在做实战项目")
    ]
    return CareerTreeResponse(data=CareerTreeResponseData(occupation_id=occupation_id, nodes=mock_nodes))
