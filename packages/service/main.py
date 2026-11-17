# packages/service/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.core.schemas import RecommendResponse, CareerRecommendation, GapDetail, CareerTreeResponse, TreeNode

app = FastAPI(title="CareerOS API", version="0.1.0")

# 允许跨域，方便代旭写的前端页面联调
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "CareerOS API is running"}

@app.post("/v1/recommend", response_model=RecommendResponse)
def get_recommendation():
    # 这里目前是 Mock 数据，之后由赵帝臣的模型接管
    mock_gap = GapDetail(
        skill_name="SQL", 
        status="needs_improvement", 
        current_level=2, 
        required_level=4
    )
    mock_rec = CareerRecommendation(
        occupation_id="occ_001",
        occupation_name="数据分析师",
        match_score=0.85,
        gaps=[mock_gap],
        top_factors=["专业对口", "逻辑分析能力强"]
    )
    
    return RecommendResponse(
        user_id="user_123",
        model_version="v1.0-mock",
        recommendations=[mock_rec]
    )

@app.get("/v1/tree/{occupation_id}", response_model=CareerTreeResponse)
def get_career_tree(occupation_id: str):
    # 模拟发展树数据
    mock_nodes = [
        TreeNode(node_id="n1", skill_name="Python", status="acquired", is_shared=True, description="已掌握基础语法"),
        TreeNode(node_id="n2", skill_name="SQL", status="needs_improvement", is_shared=False, description="需要加强多表联查"),
        TreeNode(node_id="n3", skill_name="业务分析", status="learning", is_shared=True, description="正在做实战项目")
    ]
    return CareerTreeResponse(occupation_id=occupation_id, nodes=mock_nodes)