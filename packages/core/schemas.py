# packages/core/schemas.py
from pydantic import BaseModel, Field
from typing import List, Literal

class GapDetail(BaseModel):
    skill_name: str = Field(..., description="技能中文名称")
    status: Literal["acquired", "needs_improvement", "to_be_verified"] = Field(
        ..., description="三档状态：已具备/待加强/待验证"
    )
    current_level: int = Field(..., description="用户当前水平(0-5)")
    required_level: int = Field(..., description="职业要求水平(0-5)")

class CareerRecommendation(BaseModel):
    occupation_id: str = Field(..., description="职业唯一ID")
    occupation_name: str = Field(..., description="职业名称")
    match_score: float = Field(..., ge=0, le=1, description="匹配度得分 (0-1之间)")
    gaps: List[GapDetail] = Field(default_factory=list, description="核心能力差距明细")
    top_factors: List[str] = Field(..., description="主要推荐依据")

class RecommendResponse(BaseModel):
    user_id: str = Field(..., description="用户唯一标识")
    model_version: str = Field(..., description="使用的模型版本号")
    recommendations: List[CareerRecommendation] = Field(
        ..., max_length=5, description="推荐的职业方向列表(固定最多5个)"
    )

class TreeNode(BaseModel):
    node_id: str = Field(..., description="节点唯一ID")
    skill_name: str = Field(..., description="技能名称")
    status: Literal["acquired", "needs_improvement", "to_be_verified", "learning", "completed"] = Field(
        ..., description="节点五档状态"
    )
    is_shared: bool = Field(..., description="是否为多职业共享能力节点")
    description: str = Field(..., description="节点学习建议或说明")

class CareerTreeResponse(BaseModel):
    occupation_id: str = Field(..., description="当前发展树对应的职业ID")
    nodes: List[TreeNode] = Field(..., description="树的节点列表")