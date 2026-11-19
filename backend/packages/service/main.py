# packages/service/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.core.schemas import (
    CareerTreeResponse,
    CareerTreeResponseData,
    TreeNode,
)
from packages.service.routers.health import router as health_router
from packages.service.routers.occupations import router as occupations_router
from packages.service.routers.recommend import router as recommend_router

app = FastAPI(title="CareerOS API", version="0.1.0")

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
