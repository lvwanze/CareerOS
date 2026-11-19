from pydantic import BaseModel, Field
from typing import List, Literal, Any, ForwardRef, Optional
import uuid


# 统一API响应结构
class ApiResponse(BaseModel):
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="提示信息")
    data: Any = Field(description="业务数据")
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="请求唯一标识"
    )


# 技能差距模型（完全对齐 data_contract.md §4.1）
class SkillGap(BaseModel):
    skill_id: str = Field(..., description="技能唯一ID")
    skill_name: Optional[str] = Field(None, description="技能名称（可为英文）")
    skill_name_zh: Optional[str] = Field(None, description="技能中文名称")
    gap: int = Field(..., description="技能差距值")
    importance: Optional[float] = Field(None, description="技能重要性分数（原始O*NET IM值）")
    status: Literal["mastered", "needs_improvement", "needs_verification"] = Field(
        ...,
        description="技能状态：已掌握/需提升/需验证"
    )
    current_level: int = Field(..., ge=0, le=4, description="用户当前水平(0-4)")
    required_level: int = Field(..., ge=0, le=4, description="职业要求水平(0-4)")


class SkillOption(BaseModel):
    skill_id: str
    name: str
    name_zh: str = Field(default="", description="中文名；映射缺失时与 name 相同（英文回退）")
    category: str
    used_in_kb: bool


# 职业推荐模型（完全对齐 data_contract.md §3.5）
class CareerRecommendation(BaseModel):
    occupation_id: str = Field(..., description="职业唯一ID")
    occupation_name: str = Field(..., description="职业名称")
    occupation_name_zh: Optional[str] = Field(None, description="职业中文名称")
    match_score: float = Field(..., ge=0, le=1, description="匹配度得分 (0-1之间)")
    skill_gaps: List[SkillGap] = Field(default_factory=list, description="技能差距明细")
    recommendation_reasons: List[str] = Field(..., description="主要推荐依据")
    matched_skills: List[str] = Field(..., description="已掌握的匹配技能ID列表")
    skills_to_improve: List[str] = Field(..., description="需要提升的技能ID列表")
    skills_to_verify: List[str] = Field(..., description="需要验证的技能ID列表")


# 职业推荐响应业务数据
class RecommendResponseData(BaseModel):
    user_id: str = Field(..., description="用户唯一标识")
    model_version: str = Field(..., description="使用的模型版本号")
    recommendations: List[CareerRecommendation] = Field(
        ..., max_length=5, description="推荐的职业方向列表(最多5个)"
    )


class DevelopmentNode(BaseModel):
    node_id: str
    skill_id: str
    name: str
    status: Literal["not_started", "in_progress", "mastered"]
    priority: int
    description: str


class DevelopmentPath(BaseModel):
    path_id: str
    occupation_id: str
    nodes: List[DevelopmentNode] = Field(default_factory=list)


class RecommendationsResponseData(BaseModel):
    user_id: str
    model_version: str
    recommendations: List[CareerRecommendation] = Field(default_factory=list, max_length=5)
    development_paths: List[DevelopmentPath] = Field(default_factory=list, max_length=5)


class RecommendationsResponse(ApiResponse):
    data: RecommendationsResponseData


class RecommendationRequest(BaseModel):
    profile: dict = Field(default_factory=dict)


# 职业推荐响应模型
class RecommendResponse(ApiResponse):
    data: RecommendResponseData


# 发展路径节点模型
class TreeNode(BaseModel):
    node_id: str = Field(..., description="节点唯一ID")
    skill_id: str = Field(..., description="技能唯一ID")
    skill_name: str = Field(..., description="技能名称")
    description: str = Field(..., description="节点学习建议或说明")
    status: Literal["not_started", "in_progress", "mastered"] = Field(
        ...,
        description="节点状态：未开始/进行中/已掌握"
    )


# 发展路径响应业务数据
class CareerTreeResponseData(BaseModel):
    occupation_id: str = Field(..., description="当前发展树对应的职业ID")
    nodes: List[TreeNode] = Field(..., description="树的节点列表")


# 发展路径响应模型
class CareerTreeResponse(ApiResponse):
    data: CareerTreeResponseData