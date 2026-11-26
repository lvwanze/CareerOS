"""TC-DATA：数据契约与字段校验测试。

依据 docs/data_contract.md，把契约固化为可执行检查。
这部分不依赖任何队友代码，现在就能真正运行。
"""

import pytest
from factories import (
    OCC_DATA_SCIENTISTS,
    SKILL_PROGRAMMING,
    base_profile,
    minimal_profile,
    skill_level,
)
from pydantic import ValidationError
from reference.schemas import (
    ApiResponse,
    DevelopmentNode,
    DevelopmentPath,
    Recommendation,
    SkillGap,
    UserProfile,
    error_locations,
)


def field_names(model_cls):
    """兼容 Pydantic v1 / v2 地取模型字段名。"""
    fields = getattr(model_cls, "model_fields", None) or getattr(
        model_cls, "__fields__", {}
    )
    return set(fields.keys())


@pytest.mark.contract
def test_TC_DATA_01_valid_profile_passes():
    """合法画像应通过校验。"""
    profile = UserProfile(**base_profile())
    assert profile.user_id == "user_001"
    assert len(profile.skills) == 3


@pytest.mark.contract
def test_TC_DATA_02_missing_user_id_rejected():
    """必填字段 user_id 缺失应被拒绝。"""
    data = base_profile()
    data.pop("user_id")
    with pytest.raises(ValidationError) as exc:
        UserProfile(**data)
    assert ("user_id",) in error_locations(exc.value)


@pytest.mark.parametrize("level", [5, -1, 100])
@pytest.mark.contract
def test_TC_DATA_03_skill_level_out_of_range_rejected(level):
    """TC-EX-01：技能等级越界（0～4 之外）应被拒绝。"""
    with pytest.raises(ValidationError) as exc:
        UserProfile(**skill_level(level))
    assert any("self_level" in loc for loc in error_locations(exc.value))


@pytest.mark.parametrize("level", ["3", "high", None])
@pytest.mark.contract
def test_TC_DATA_04_skill_level_wrong_type_rejected(level):
    """TC-EX-06：等级必须是整数，字符串 / None 应被拒绝。"""
    with pytest.raises(ValidationError):
        UserProfile(**skill_level(level))


@pytest.mark.parametrize("level", [0, 1, 2, 3, 4])
@pytest.mark.contract
def test_TC_DATA_05_all_valid_levels_accepted(level):
    """0～4 全量覆盖，确认边界值 0 与 4 都合法。"""
    assert UserProfile(**skill_level(level)).skills[0].self_level == level


@pytest.mark.contract
def test_TC_DATA_06_optional_sections_can_be_omitted():
    """TC-EX-03：constraints 与 career_goals 非必填。"""
    profile = UserProfile(**minimal_profile())
    assert profile.constraints is None
    assert profile.career_goals is None


@pytest.mark.contract
def test_TC_DATA_07_skill_without_id_rejected():
    """技能项的 skill_id 必填。"""
    data = base_profile()
    data["skills"] = [{"self_level": 2, "evidence_level": "self"}]
    with pytest.raises(ValidationError) as exc:
        UserProfile(**data)
    assert any("skill_id" in loc for loc in error_locations(exc.value))


@pytest.mark.contract
def test_TC_DATA_08_all_fields_use_snake_case():
    """全局规范：JSON 字段统一 snake_case。"""
    for model in (UserProfile, Recommendation, SkillGap, DevelopmentPath, ApiResponse):
        for name in field_names(model):
            assert "_" not in name or name.islower(), f"{model.__name__}.{name} 非 snake_case"
            assert not any(c.isupper() for c in name), f"{model.__name__}.{name} 含大写"


@pytest.mark.contract
def test_TC_DATA_09_legacy_missing_skills_is_not_a_contract_field():
    """防止分工说明里的旧字段 missing_skills 回流。"""
    fields = field_names(Recommendation)
    assert "missing_skills" not in fields
    assert "skills_to_improve" in fields
    assert "skills_to_verify" in fields


@pytest.mark.contract
def test_TC_DATA_10_recommendation_required_fields():
    """推荐结果的 7 个字段均为必填。"""
    expected = {
        "occupation_id", "occupation_name", "match_score", "matched_skills",
        "skills_to_improve", "skills_to_verify", "recommendation_reasons",
    }
    assert field_names(Recommendation) == expected
    with pytest.raises(ValidationError):
        Recommendation(occupation_id=OCC_DATA_SCIENTISTS, occupation_name="Data Scientists")


@pytest.mark.contract
def test_TC_DATA_11_gap_status_enum():
    """差距状态只接受契约规定的三个值。"""
    base = {
        "skill_id": SKILL_PROGRAMMING, "current_level": 2,
        "required_level": 3, "gap": 1,
    }
    for status in ("mastered", "needs_improvement", "needs_verification"):
        assert SkillGap(**base, status=status).status == status
    with pytest.raises(ValidationError):
        SkillGap(**base, status="已掌握")


@pytest.mark.contract
def test_TC_DATA_12_node_status_enum():
    """发展节点状态只接受契约 §3.7 收敛后的 3 档。

    2026-11-25 口径变更：旧的 learning / needs_improvement / needs_verification /
    completed 四值已废弃（能力状态与任务状态混用，Flutter 遇未知枚举会崩），
    本用例由 5 档改判 3 档，并与后端 schemas.py、前端 DevelopmentStatus 对齐。
    非法值拒绝同时覆盖一个旧值，防止旧枚举回流。
    """
    base = {"node_id": "n1", "skill_id": SKILL_PROGRAMMING, "name": "Programming"}
    for status in ("not_started", "in_progress", "mastered"):
        assert DevelopmentNode(**base, status=status).status == status
    for old_or_unknown in ("learning", "completed", "needs_verification", "unknown"):
        with pytest.raises(ValidationError):
            DevelopmentNode(**base, status=old_or_unknown)


@pytest.mark.contract
def test_TC_DATA_13_api_response_shape():
    """统一响应含 code / message / data / request_id，data 可为 null。"""
    resp = ApiResponse(code=200, message="success", data=None, request_id="req_001")
    payload = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
    assert set(payload) == {
        "code", "message", "data", "request_id"
    }
    with pytest.raises(ValidationError):
        ApiResponse(code=200, message="success", data=None)


@pytest.mark.contract
def test_TC_DATA_15_request_id_snake_case_not_camel_case():
    """契约规定统一用 request_id（snake_case），拒绝总体 README 里的 requestId。

    总体 README 八、数据与接口规范写的是 "requestId"，与 data_contract.md
    第 197 行冲突。本用例把契约口径钉死：出现 requestId 视为契约违规。
    """
    fields = field_names(ApiResponse)
    assert "request_id" in fields
    assert "requestId" not in fields
    assert all(not any(c.isupper() for c in name) for name in fields)
    with pytest.raises(ValidationError):
        ApiResponse(code=200, message="success", data={}, requestId="req_001")


@pytest.mark.contract
def test_TC_DATA_14_overlong_text_rejected():
    """TC-EX-05：超长文本（>1000 字）应被字段长度校验拦住。"""
    data = base_profile()
    data["career_goals"] = {"goal_description": "想" * 1001}
    with pytest.raises(ValidationError) as exc:
        UserProfile(**data)
    assert any("goal_description" in loc for loc in error_locations(exc.value))
