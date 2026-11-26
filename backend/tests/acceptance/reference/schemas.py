"""CareerOS 公共数据契约 V1.0 的可执行表达。

来源：docs/data_contract.md
用途：
  1. 作为字段校验测试的标准答案（test_contract.py）
  2. 供后端负责人参考，作为 packages/core/schemas.py 的基础

设计原则：兼容 Pydantic v1 / v2，只使用两者都支持的语法。
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, StrictInt, ValidationError

# 技能等级：0 未掌握 / 1 了解 / 2 能做基础任务 / 3 独立常见任务 / 4 熟练复杂任务
SkillLevel = Literal[0, 1, 2, 3, 4]

GapStatus = Literal["mastered", "needs_improvement", "needs_verification"]
# 发展任务状态：2026-11-25 契约 §3.7 收敛为 3 档（与 schemas.py、Flutter 一致）。
# 旧值 learning / needs_improvement / needs_verification / completed 已废弃：
# 前两者语义并入 in_progress / mastered，后两者属 SkillGap.status（能力状态），
# 不是学习任务状态；Flutter 对未知枚举会抛 ArgumentError，不能再留在契约里。
NodeStatus = Literal["not_started", "in_progress", "mastered"]


def error_locations(exc: ValidationError):
    """统一提取校验错误的字段路径，兼容 v1 / v2。"""
    return [tuple(str(part) for part in err.get("loc", ())) for err in exc.errors()]


# ---------- UserProfile 用户画像 ----------

class LearningStage(BaseModel):
    education_level: str
    major: str
    current_stage: str


class Preferences(BaseModel):
    interest_areas: List[str]
    work_style: List[str]


class SkillInput(BaseModel):
    """用户填写的技能项（区别于知识库里的 Skill 定义）。"""

    skill_id: str
    self_level: StrictInt = Field(ge=0, le=4)
    evidence_level: Optional[str] = None


class Constraints(BaseModel):
    available_hours_per_week: Optional[int] = None
    preferred_regions: Optional[List[str]] = None
    relocation_willingness: Optional[bool] = None


class CareerGoals(BaseModel):
    target_occupations: Optional[List[str]] = None
    goal_description: Optional[str] = Field(default=None, max_length=1000)


class UserProfile(BaseModel):
    user_id: str
    learning_stage: LearningStage
    preferences: Preferences
    skills: List[SkillInput]
    constraints: Optional[Constraints] = None
    career_goals: Optional[CareerGoals] = None


# ---------- 知识库模型 ----------

class Skill(BaseModel):
    skill_id: str
    name: str
    category: str
    description: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class Occupation(BaseModel):
    occupation_id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class OccupationSkill(BaseModel):
    occupation_id: str
    skill_id: str
    importance: float
    required_level: int = Field(ge=0, le=4)


# ---------- 输出模型 ----------

class Recommendation(BaseModel):
    occupation_id: str
    occupation_name: str
    match_score: float
    matched_skills: List[str]
    skills_to_improve: List[str]
    skills_to_verify: List[str]
    recommendation_reasons: List[str]


class SkillGap(BaseModel):
    skill_id: str
    current_level: StrictInt = Field(ge=0, le=4)
    required_level: StrictInt = Field(ge=0, le=4)
    gap: int
    status: GapStatus


class DevelopmentNode(BaseModel):
    node_id: str
    skill_id: str
    name: str
    status: NodeStatus
    priority: Optional[int] = None
    description: Optional[str] = None


class DevelopmentPath(BaseModel):
    path_id: str
    occupation_id: str
    nodes: List[DevelopmentNode]


class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict] = None
    request_id: str
