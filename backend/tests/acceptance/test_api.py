"""TC-API / TC-EX：FastAPI 接口与异常边界测试。

通过 client fixture 自动选择真实后端或参考 stub。
异常用例编号与报告骨架表 5-3 对齐：
  TC-EX-01 等级越界 / 02 空技能 / 03 可选字段缺省 / 04 未知技能
  TC-EX-05 超长文本 / 06 类型错误 / 07 连续请求 / 08 知识库文件缺失（待后端）
  TC-EX-09 为本项目补充的必填字段缺失用例。

异常用例统一要求：不能返回 500，且校验错误要能定位到具体字段。
"""

import pytest

from factories import (
    base_profile,
    empty_skills_profile,
    minimal_profile,
    payload,
    skill_level,
    unknown_skill_profile,
)


def _json(response):
    return response.json()


def _body(response):
    return _json(response).get("data") or {}


# ---------------- 接口正常流程 ----------------

@pytest.mark.api
def test_TC_API_01_health_check(client):
    """GET /health 应返回 status=ok。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert _json(response)["status"] == "ok"


@pytest.mark.api
def test_TC_API_02_recommend_success(client, recommend_path):
    """正常请求：HTTP 200 且业务 code=200。"""
    response = client.post(recommend_path, json=payload())
    assert response.status_code == 200, response.text
    body = _json(response)
    assert body["code"] == 200
    assert body["message"] == "success"
    assert "recommendations" in _body(response)
    assert "development_paths" in _body(response)


@pytest.mark.api
def test_TC_API_03_top5_count_and_fields(client, recommend_path):
    """核心契约：恰好 Top-5，按分数降序，字段齐全。"""
    data = _body(client.post(recommend_path, json=payload()))
    recs = data["recommendations"]
    assert len(recs) == 5
    scores = [item["match_score"] for item in recs]
    assert scores == sorted(scores, reverse=True)
    required = {
        "occupation_id", "occupation_name", "match_score", "matched_skills",
        "skills_to_improve", "skills_to_verify", "recommendation_reasons",
    }
    for item in recs:
        assert required <= set(item.keys())
        assert 0 <= item["match_score"] <= 1


@pytest.mark.api
def test_TC_API_04_unified_response_fields(client, recommend_path):
    """统一响应四字段齐全，request_id 为 req_ 前缀（api_spec.md 口径）。

    代旭在 feat/api-contract-v2 将 request_id 由裸 UUID 统一为 req_ 前缀，
    此断言锁定该口径防回归。自检 stub 已是 req_ 前缀；真实后端需该 PR
    合入后才通过，旧 commit（如 d24e6f4）仍返回裸 UUID。
    """
    body = _json(client.post(recommend_path, json=payload()))
    for field in ("code", "message", "data", "request_id"):
        assert field in body
    request_id = body["request_id"]
    assert request_id, "request_id 不得为空"
    assert request_id.startswith("req_"), (
        f"request_id 须为 req_ 前缀（api_spec.md），实际为 {request_id!r}"
    )


# ---------------- 发展树结构（后端 2026-11-20 口径：责任归后端，可实测）----------------

@pytest.mark.api
def test_TC_API_05_development_paths_structure(client, recommend_path, api_mode):
    """发展路径由后端构树：每组与推荐职业对应，节点字段齐全、priority 从 1 递增。

    后端 2026-11-20 口径：发展树由后端返回（算法只给缺口/等级/权重，不构树），
    /recommendations 的 development_paths 已按此实现（gap>0、priority 从 1 递增），
    故按 200 + 结构断言，不再当作兜底。自检 stub 的 development_paths 无 priority，
    故自检模式退化为字段齐全检查（不强求 priority）。
    注意：节点 status 枚举契约(5 档)与代码 Literal(3 档)冲突待吕宛泽确认，
    此处只断言非空字符串，不写死枚举，避免写哪套都挂一边。
    """
    strict = api_mode == "real"
    data = _body(client.post(recommend_path, json=payload()))
    paths = data.get("development_paths")
    assert isinstance(paths, list) and paths
    rec_ids = {r["occupation_id"] for r in data["recommendations"]}
    assert {p["occupation_id"] for p in paths} <= rec_ids
    for path in paths:
        assert path["path_id"]
        nodes = path["nodes"]
        assert nodes
        priorities = []
        for node in nodes:
            for field in ("node_id", "skill_id", "name", "status"):
                assert field in node, f"发展节点缺字段 {field}"
            assert isinstance(node["status"], str) and node["status"]
            priorities.append(node.get("priority"))
        if strict:
            assert all(isinstance(p, int) for p in priorities)
            assert priorities == list(range(1, len(nodes) + 1)), "priority 应从 1 递增"


@pytest.mark.api
def test_TC_API_06_tree_endpoint_shape(client, api_mode):
    """/v1/tree/{occupation_id} 形状校验：后端标注为 mock，形状即最终形状，只测形状不测内容。

    实际返回节点字段：node_id / skill_id / skill_name / status / description；
    顶层 data 含 occupation_id / nodes。自检 stub 无该路由，真实后端才测。
    status 值同样不写死（契约/代码枚举冲突待确认）。
    """
    if api_mode != "real":
        pytest.skip("/v1/tree 仅真实后端提供（自检 stub 无此路由）")
    resp = client.get("/v1/tree/OCC-ONET-15-2051.00")
    assert resp.status_code == 200, resp.text
    data = _json(resp)
    assert "request_id" in data
    payload_data = data["data"]
    assert "occupation_id" in payload_data
    nodes = payload_data["nodes"]
    assert isinstance(nodes, list) and nodes
    for node in nodes:
        for field in ("node_id", "skill_id", "skill_name", "status", "description"):
            assert field in node, f"tree 节点缺字段 {field}"


# ---------------- 异常与边界（编号对齐报告骨架表 5-3）----------------

@pytest.mark.api
@pytest.mark.exception
@pytest.mark.parametrize("bad_level", [5, -1])
def test_TC_EX_01_skill_level_out_of_range(client, recommend_path, bad_level):
    """技能等级填 5 或 -1（超出 0~4）：422，提示等级取值范围。"""
    response = client.post(recommend_path, json=payload(skill_level(bad_level)))
    assert response.status_code == 422, response.text
    assert "self_level" in response.text


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_02_empty_skill_list(client, recommend_path):
    """技能列表为空：给出明确提示，不返回 500。"""
    response = client.post(recommend_path, json=payload(empty_skills_profile()))
    assert response.status_code != 500, response.text
    assert response.status_code in (200, 400, 422)
    if response.status_code == 200:
        assert _json(response)["code"] in (200, 400)


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_03_optional_sections_absent(client, recommend_path):
    """不填 career_goals / constraints（非必填）：正常返回推荐结果。"""
    response = client.post(recommend_path, json=payload(minimal_profile()))
    assert response.status_code == 200, response.text
    assert len(_body(response)["recommendations"]) == 5


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_04_unknown_skill_does_not_crash(client, recommend_path):
    """技能名不在知识库中：忽略或提示未知技能，不崩溃。"""
    response = client.post(recommend_path, json=payload(unknown_skill_profile()))
    assert response.status_code != 500, response.text
    assert response.status_code in (200, 400, 422)


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_05_overlong_text(client, recommend_path):
    """超长文本（1001 字）：不得崩溃（非 500）。

    口径说明：后端 2026-11-20 已定规则——goal_description 选填，上限 2000 字符，
    按 Python len() 码点计（中文按 1，不按字节），超限 422，
    loc = profile.career_goals.goal_description。但代码尚未落地（pending，
    后端要动前端与存量用例，走完契约确认再改），明确要求测试侧暂按 422 跑。
    故本用例仍按"健壮性"验收——不 500 即可（200 兜底或 422 拒绝都算通过），
    且不写死"1001 字必 422"。等后端提交号到位、代码落地后，
    再把本用例升级为严格断言（用 2001 字触发 422，并校验 loc）。
    """
    profile = base_profile()
    profile["career_goals"] = {"goal_description": "想" * 1001}
    response = client.post(recommend_path, json=payload(profile))
    assert response.status_code != 500, response.text
    assert response.status_code in (200, 400, 422), response.text


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_06_wrong_field_type(client, recommend_path):
    """字段类型错误（等级非整数）：422，错误定位到字段。

    2026-11-23 起 main `d24e6f4` 恢复 StrictInt：self_level 必须是真正的整数，
    字符串（含数字字符串 "3"）、浮点数 3.0、布尔 true 一律 422，
    不再被宽松转换成 3 级或 1 级。四种值在同一用例内逐一校验，
    不新增 pytest 收集数，避免影响既定的 89 条口径。
    """
    for bad_level in ("high", "3", 3.0, True):
        response = client.post(recommend_path, json=payload(skill_level(bad_level)))
        assert response.status_code == 422, f"{bad_level!r} 应 422: {response.text}"
        assert "self_level" in response.text, f"{bad_level!r} 错误未定位到 self_level"


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_07_repeated_requests_stable(client, recommend_path):
    """连续请求 20 次：响应稳定，结果数量一致。"""
    results = [client.post(recommend_path, json=payload()) for _ in range(20)]
    assert all(r.status_code == 200 for r in results)
    counts = {len(_body(r)["recommendations"]) for r in results}
    assert counts == {5}


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_09_missing_required_field(client, recommend_path):
    """补充：user_id 缺失时不得崩溃（口径待团队确认）。

    口径说明：后端 2026-11-20 已定规则——user_id 必填（契约 §3.1 原本就是"是"），
    规则为 str 且 strip() 后长度 1～64，缺失或空白 → 422，loc = profile.user_id。
    但代码尚未落地（pending，要动前端与存量用例，后端走完契约确认再改），
    明确要求测试侧暂不按 422 跑。故本用例仍接受 200（anonymous 兜底）或 422，
    只排除 500。等后端提交号到位、代码落地后，再升级为严格断言：
    覆盖缺失 / 空白 / 超 64 字符三类 422，并校验 loc = profile.user_id。
    """
    profile = base_profile()
    profile.pop("user_id")
    response = client.post(recommend_path, json=payload(profile))
    assert response.status_code != 500, response.text
    assert response.status_code in (200, 422), response.text
