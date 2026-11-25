# packages/service/main.py
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from packages.core.schemas import ApiResponse
from packages.service.routers.career_tree import deprecated_router as tree_legacy_router, router as tree_router
from packages.service.routers.health import router as health_router
from packages.service.routers.occupations import router as occupations_router
from packages.service.routers.recommend import router as recommend_router
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="CareerOS API", version="0.1.0")
logger = logging.getLogger(__name__)

# 内置状态码的中文文案。HTTPException 自带的 detail 是英文（Not Found），
# 统一信封后 message 会被前端直接展示，这里换成中文；未列出的状态码仍用原 detail。
_HTTP_ERROR_MESSAGES = {
    404: "资源不存在",
    405: "请求方法不允许",
    422: "请求参数不符合要求",
    500: "服务器内部错误",
}


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
        # profile 传成字符串/数组时的两种 type 标识（构造模型与 HTTP 请求路径不同）
        "model_type": "必须是对象",
        "model_attributes_type": "必须是对象",
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


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    """未匹配路由 404、方法不符 405、路由内 raise 的 HTTPException 统一成信封。

    FastAPI/Starlette 默认返回 {"detail": "Not Found"}，与 422 的信封是两套格式；
    前端按 code 判断成败时会漏掉这一类分支（组长审查意见第 1 条）。
    """
    message = _HTTP_ERROR_MESSAGES.get(exc.status_code) or str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(code=exc.status_code, message=message, data=None).model_dump(),
        # 401 之类的响应可能带 WWW-Authenticate，透传 headers 否则浏览器行为会变
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    """兜底 500：堆栈进日志、响应体只给通用文案（api_spec §5 不得暴露内部信息）。"""
    logger.exception("未捕获异常：%s", exc)
    return JSONResponse(
        status_code=500,
        content=ApiResponse(code=500, message="服务器内部错误", data=None).model_dump(),
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
# 发展树：正式路径带 /api 前缀；旧路径 /v1/tree 保留但标弃用（见 routers/career_tree.py）
app.include_router(tree_router, prefix="/api/v1")
app.include_router(tree_legacy_router, prefix="/v1")


@app.get("/", response_model=ApiResponse)
def show_route_index():
    # 根路径给个索引，免得打开服务地址看到 Not Found 以为服务挂了。
    # 它会在 /docs 里露出，调用方会当成一个接口来用，所以套统一信封；
    # /health 与 /ready 是探针，按约定保持裸结构，不在此列。
    return ApiResponse(
        code=200,
        message="success",
        data={
            "service": "CareerOS API",
            "docs": "/docs",
            "routes": [
                "GET  /health",
                "GET  /ready",
                "GET  /api/v1/skills",
                "POST /api/v1/recommendations",
                "GET  /api/v1/occupations",
                "GET  /api/v1/occupations/{occupation_id}",
                "GET  /api/v1/tree/{occupation_id}",
                "GET  /v1/tree/{occupation_id}（已弃用，请用 /api/v1/tree）",
            ],
        },
    )


# 发展树路由已迁到 routers/career_tree.py 并改为读真实数据，
# 原位置的 mock 节点（Python / SQL / 业务分析写死 3 条）已删除。

