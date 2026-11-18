#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : request.py
# @Path       : packages/service/schemas/request.py
# @Project    : CareerOS
# @Author     : 代旭
# @Date       : 2026-11-18 15:40:00
# @Version    : v1.0.0
# @Description: 请求模型：用户画像填报与校验
# @ChangeLog:
#   2026-11-18 15:40:00 | 代旭 | v1.0.0 | 初始化创建
"""请求模型：用户画像填报。

字段口径见 docs/data_contract.md §3.1（UserProfile）与 §2.2（技能等级 0~4）。
evidence_level 的七个枚举值由算法负责人赵帝臣 11-18 定稿，
这里手写一份并在 tests 里断言与 matcher.EVIDENCE_LEVELS 一致，防止两边漂移。

未知枚举值直接返回 422：前端传错一个值，页面只会显示"待验证"，
用户会误以为系统判定他能力不足，实际是他传错了字。这种错必须在联调阶段暴露。
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

EvidenceLevel = Literal["none", "self", "course", "project", "work", "certificate", "test"]

# 与 matcher.EVIDENCE_LEVELS 对应，导出给测试做一致性断言
EVIDENCE_LEVELS = frozenset({"none", "self", "course", "project", "work", "certificate", "test"})

MAX_SKILLS = 30


class UserSkill(BaseModel):
    """用户填报的一项技能。"""

    skill_id: str = Field(..., min_length=1, description="技能唯一 ID，形如 SKILL-ONET-2.B.3.e")
    self_level: int = Field(..., ge=0, le=4, description="用户自评等级，0~4")
    evidence_level: EvidenceLevel = Field(default="none", description="能力证据状态")

    @field_validator("skill_id", mode="before")
    @classmethod
    def strip_skill_id(cls, value: object) -> object:
        """去掉首尾空白：粘贴进来的 ID 常带空格，去掉后仍能匹配知识库。"""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("evidence_level", mode="before")
    @classmethod
    def normalize_evidence_level(cls, value: object) -> str:
        """先 strip + lower 再查白名单；缺失、null、空串一律按 none。

        归一化规则与赵帝臣 11-18 的口径一致；不在白名单的值抛 ValueError，
        FastAPI 会转成 422 并把允许值写进 message，不让它静默变成"待验证"。
        """
        if value is None:
            return "none"
        text = str(value).strip().lower()
        if not text:
            return "none"
        if text not in EVIDENCE_LEVELS:
            allowed = "、".join(sorted(EVIDENCE_LEVELS))
            raise ValueError(f"evidence_level 只能是 {allowed} 之一，收到 {value!r}")
        return text


class LearningStage(BaseModel):
    """学习阶段。字段允许为空对象，与 api_spec.md §3.1 的请求示例一致。"""

    education_level: str | None = Field(default=None, description="学历阶段")
    major: str | None = Field(default=None, description="当前专业")
    current_stage: str | None = Field(default=None, description="当前学习或工作阶段")


class Preferences(BaseModel):
    """兴趣与偏好。"""

    interest_areas: list[str] = Field(default_factory=list, description="感兴趣的领域")
    work_style: list[str] = Field(default_factory=list, description="偏好的工作方式")


class Constraints(BaseModel):
    """现实条件，第一阶段选填。"""

    available_hours_per_week: int | None = Field(default=None, ge=0, description="每周可投入时间")
    preferred_regions: list[str] = Field(default_factory=list, description="偏好就业地域")
    relocation_willingness: bool | None = Field(default=None, description="是否接受异地发展")


class CareerGoals(BaseModel):
    """职业目标，第一阶段选填。"""

    target_occupations: list[str] = Field(default_factory=list, description="目标职业 ID")
    goal_description: str | None = Field(default=None, description="个人目标描述")


class UserProfile(BaseModel):
    """用户画像，对应 data_contract.md §3.1。"""

    user_id: str = Field(..., min_length=1, description="用户唯一标识")
    learning_stage: LearningStage = Field(..., description="学习阶段")
    preferences: Preferences = Field(..., description="兴趣与偏好")
    skills: list[UserSkill] = Field(..., min_length=1, max_length=MAX_SKILLS, description="技能列表")
    constraints: Constraints | None = Field(default=None, description="现实条件")
    career_goals: CareerGoals | None = Field(default=None, description="职业目标")

    @field_validator("user_id", mode="before")
    @classmethod
    def strip_user_id(cls, value: object) -> object:
        """去掉首尾空白，避免 user_id 里混入空格却通过 min_length 校验。"""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("skills")
    @classmethod
    def reject_duplicated_skill(cls, skills: list[UserSkill]) -> list[UserSkill]:
        """同一 skill_id 重复填报直接报错，不静默取第一条。

        理由：重复值会让技能向量的权重凭空翻倍，分数虚高且无法解释。
        """
        seen: set[str] = set()
        duplicated: list[str] = []
        for item in skills:
            if item.skill_id in seen:
                duplicated.append(item.skill_id)
            seen.add(item.skill_id)
        if duplicated:
            raise ValueError(f"skills 中存在重复的 skill_id：{'、'.join(sorted(set(duplicated)))}")
        return skills


class RecommendRequest(BaseModel):
    """推荐接口请求体，对应 api_spec.md §3.1。"""

    profile: UserProfile
