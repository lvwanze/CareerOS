"""测试数据工厂：合法样本 + 各类异常样本。

所有函数返回 dict（而非模型对象），方便直接作为请求 JSON 使用。
修改样本时只改这里，测试代码不要内联构造大段 JSON。

ID 已全部换成高帅龙 M1 交付包里的真实 O*NET ID，
来源：dataset/M1_职业知识库_数据交付_v0.5.0_20261118/data/processed/。
"""

import copy

# 真实技能 ID（skills.csv）
SKILL_PROGRAMMING = "SKILL-ONET-2.B.3.e"
SKILL_MATHEMATICS = "SKILL-ONET-2.A.1.e"
SKILL_CRITICAL_THINKING = "SKILL-ONET-2.A.2.a"
SKILL_ACTIVE_LEARNING = "SKILL-ONET-2.A.2.b"
SKILL_WRITING = "SKILL-ONET-2.A.1.c"
SKILL_READING = "SKILL-ONET-2.A.1.a"
SKILL_LISTENING = "SKILL-ONET-2.A.1.b"
SKILL_SYSTEMS_ANALYSIS = "SKILL-ONET-2.B.4.g"
SKILL_COMPLEX_PROBLEM_SOLVING = "SKILL-ONET-2.B.2.i"

# 真实职业 ID（occupations.csv）
OCC_SOFTWARE_DEVELOPERS = "OCC-ONET-15-1252.00"
OCC_COMPUTER_PROGRAMMERS = "OCC-ONET-15-1251.00"
OCC_DATA_SCIENTISTS = "OCC-ONET-15-2051.00"
OCC_BI_ANALYSTS = "OCC-ONET-15-2051.01"
OCC_STATISTICIANS = "OCC-ONET-15-2041.00"
OCC_WEB_DESIGNERS = "OCC-ONET-15-1255.00"


def base_profile(**overrides):
    """一份合法的用户画像，可作为所有用例的起点（使用真实 ID）。"""
    profile = {
        "user_id": "user_001",
        "learning_stage": {
            "education_level": "本科",
            "major": "计算机科学与技术",
            "current_stage": "大三",
        },
        "preferences": {
            "interest_areas": ["数据科学", "编程"],
            "work_style": ["独立工作"],
        },
        "skills": [
            {"skill_id": SKILL_PROGRAMMING, "self_level": 3, "evidence_level": "certificate"},
            {"skill_id": SKILL_MATHEMATICS, "self_level": 2, "evidence_level": "self"},
            {"skill_id": SKILL_CRITICAL_THINKING, "self_level": 3, "evidence_level": "project"},
        ],
        "constraints": {
            "available_hours_per_week": 10,
            "preferred_regions": ["深圳"],
            "relocation_willingness": False,
        },
        "career_goals": {
            "target_occupations": [OCC_DATA_SCIENTISTS],
            "goal_description": "希望从开发转向数据科学方向",
        },
    }
    for key, value in overrides.items():
        if key in profile and isinstance(profile[key], dict) and isinstance(value, dict):
            profile[key] = {**profile[key], **value}
        else:
            profile[key] = value
    return profile


def minimal_profile():
    """只含必填字段的最小画像，用于验证 constraints/career_goals 可缺省。"""
    profile = base_profile()
    profile.pop("constraints")
    profile.pop("career_goals")
    return profile


def skill_level(level, skill_id=SKILL_PROGRAMMING, evidence_level="self"):
    """构造单技能画像，便于覆盖 0～4 及越界值。"""
    profile = base_profile()
    profile["skills"] = [
        {"skill_id": skill_id, "self_level": level, "evidence_level": evidence_level}
    ]
    return profile


def empty_skills_profile():
    profile = base_profile()
    profile["skills"] = []
    return profile


def unknown_skill_profile():
    profile = base_profile()
    profile["skills"] = [
        {"skill_id": "SKILL-ONET-NOT-IN-KB", "self_level": 2, "evidence_level": "self"}
    ]
    return profile


def profile_with_skills(skills):
    """按 (skill_id, self_level, evidence_level) 三元组构造画像。"""
    profile = base_profile()
    profile["skills"] = [
        {"skill_id": sid, "self_level": level, "evidence_level": evidence}
        for sid, level, evidence in skills
    ]
    return profile


def payload(profile=None):
    """包装成 POST /recommendations 的请求体。"""
    return {"profile": copy.deepcopy(profile if profile is not None else base_profile())}
