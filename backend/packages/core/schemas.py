from pydantic import BaseModel, ConfigDict, Field, StrictInt
from typing import List, Literal, Any, ForwardRef, Optional
import uuid


# 统一API响应结构
class ApiResponse(BaseModel):
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="提示信息")
    data: Any = Field(description="业务数据")
    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}",
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
    used_in_kb: bool = Field(
        ...,
        description="是否至少关联一个职业；由 occupation_skills.csv 现算，不是常量",
    )
    description: str = Field(
        default="",
        description="技能说明（O*NET 31.0 原文英文，取自 reference/skill_description.csv）",
    )


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


class SkillInput(BaseModel):
    """画像中的单条技能自评，对齐 data_contract.md §2.2。

    self_level 契约规定 0～4，越界由 pydantic 直接拒为 422。
    此前路由层用 `0 <= level <= 4` 做过滤，越界条目被静默丢弃且仍返回 200，
    调用方无法感知数据没生效；改为模型校验后越界即报错。

    类型必须是 StrictInt 而不是 int：pydantic 的宽松模式会把 "3" 转成 3、
    把 3.0 截成 3、把 true 当成 1 级。契约 §2.2 写的是 int，字符串和布尔
    都不该被"善意猜测"，否则 true 会静默变成 1 级，比报错更难查。
    """

    model_config = ConfigDict(extra="allow")

    skill_id: str = Field(
        ...,
        min_length=1,
        description="技能唯一ID，必须存在于知识库技能表",
    )
    self_level: StrictInt = Field(
        0,
        ge=0,
        le=4,
        description="用户自评等级(0-4)，字段缺失按 0 处理；不接受字符串/浮点/布尔",
    )
    evidence_level: Optional[str] = Field(None, description="能力证据状态")


class ProfileInput(BaseModel):
    """用户画像。推荐链路只读 user_id 与 skills，其余字段原样保留。"""

    model_config = ConfigDict(extra="allow")

    user_id: Optional[str] = Field(None, description="用户ID")
    skills: List[SkillInput] = Field(default_factory=list, description="技能自评列表")


class RecommendationRequest(BaseModel):
    profile: ProfileInput = Field(default_factory=ProfileInput)


# 职业推荐响应模型
class RecommendResponse(ApiResponse):
    data: RecommendResponseData


# 发展树节点模型
class TreeNode(BaseModel):
    """发展树节点：职业根节点 → 技能类别 → 技能，共三层。

    原来只有 node_id/skill_id/skill_name/description/status 五个字段，节点之间
    没有父子关系，前端拿到 3 条平铺记录只能当列表渲染，不构成"树"。
    这里补 parent_id + level + order，并把 kind 显式写出来：前端可以用
    node_type 决定画成根、分组标题还是技能条目，不必靠 skill_id 是否为空去猜。
    """

    node_id: str = Field(..., description="节点唯一ID")
    parent_id: Optional[str] = Field(None, description="父节点ID；根节点为 null")
    node_type: Literal["occupation", "category", "skill"] = Field(
        ..., description="节点类型：职业根/技能类别/技能"
    )
    level: int = Field(..., ge=0, le=2, description="层级：0 根、1 类别、2 技能")
    order: int = Field(..., ge=0, description="同一父节点下的排序，从 1 连续递增；根为 0")
    skill_id: Optional[str] = Field(None, description="技能唯一ID；根与类别节点为 null")
    skill_name: str = Field(..., description="显示名（技能节点为中文名，缺失回退英文）")
    name_en: Optional[str] = Field(None, description="英文原名，便于和 O*NET 对照")
    description: str = Field(..., description="节点说明：技能取 O*NET 原文，类别取分组说明")
    status: Literal["not_started", "in_progress", "mastered"] = Field(
        ..., description="节点状态：未开始/进行中/已掌握（本接口统一 not_started，进度在前端）"
    )
    priority: int = Field(
        ..., ge=0, description="全树学习顺序，从 1 递增；根与类别节点为 0"
    )
    category: Optional[str] = Field(
        None, description="技能类别：essential / transferable；根节点为职业类别"
    )
    required_level: Optional[int] = Field(
        None, ge=0, le=4, description="职业要求等级(0-4)；非技能节点为 null"
    )
    importance: Optional[float] = Field(
        None, ge=1, le=5, description="O*NET 原始 IM 重要程度(1-5)；非技能节点为 null"
    )


# 发展路径响应业务数据
class CareerTreeResponseData(BaseModel):
    occupation_id: str = Field(..., description="当前发展树对应的职业ID")
    occupation_name: str = Field(..., description="职业英文名")
    occupation_name_zh: str = Field(..., description="职业中文名，缺失回退英文名")
    root_id: str = Field(..., description="根节点ID，便于前端直接定位树根")
    node_count: int = Field(..., description="节点总数（含根与类别节点）")
    max_depth: int = Field(..., description="最大层级，当前为 2")
    nodes: List[TreeNode] = Field(..., description="树的节点列表，按层级/order 升序")


# 发展路径响应模型
class CareerTreeResponse(ApiResponse):
    data: CareerTreeResponseData