"""TC-API / TC-EX：FastAPI 接口与异常边界测试。

通过 client fixture 自动选择真实后端或参考 stub。
异常用例编号与报告骨架表 5-3 对齐：
  TC-EX-01 等级越界 / 02 空技能 / 03 可选字段缺省 / 04 未知技能
  TC-EX-05 超长文本 / 06 类型错误 / 07 连续请求 / 08 知识库文件缺失（待后端）
  TC-EX-09 为本项目补充的必填字段缺失用例。
  TC-EX-10 证据枚举越界（2026-11-27 新增，随 evidence_level 冻结一并落地）。

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
    此断言锁定该口径防回归。已在 a36acd6（PR#18 合入后）真实后端全量中验证通过。
    本用例依赖 client；自检模式（无真实 app）下由 conftest 统一 skip——
    不再对参考 stub 自证通过（清单 P0-2 关闭假绿灯）。
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
def test_TC_API_05_development_paths_structure(client, recommend_path):
    """发展路径由后端构树：每组与推荐职业对应，节点字段齐全、priority 从 1 递增。

    后端 2026-11-20 口径：发展树由后端返回（算法只给缺口/等级/权重，不构树），
    /recommendations 的 development_paths 已按此实现（gap>0、priority 从 1 递增），
    故按 200 + 严格结构断言。此前自检 stub 无 priority 时曾退化为宽松检查，
    现按清单 P0-2 关闭假绿灯：接口用例只在真实 app 下执行，stub 模式整条 skip，
    不再保留对 stub 的降级断言。
    注意：节点 status 枚举契约(5 档)与代码 Literal(3 档)冲突待吕宛泽确认，
    此处只断言非空字符串，不写死枚举，避免写哪套都挂一边。
    """
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
        assert all(isinstance(p, int) for p in priorities)
        assert priorities == list(range(1, len(nodes) + 1)), "priority 应从 1 递增"


@pytest.mark.api
def test_TC_API_06_tree_is_real_structured_and_versioned(client, api_mode):
    """发展树：真实数据、三层结构、未知 ID 404、旧路径弃用标记（单条不涨数）。

    2026-11-25 代旭 PR#18 把 /v1/tree 从写死的 3 个 mock 节点改为按
    occupation_id 从三张表现拼：职业根(L0) → 技能类别(L1) → 技能(L2)，
    并新增正式路径 /api/v1/tree/{id}。本用例据此由"只测 mock 形状"升级：
      - 顶层：occupation_id / root_id / node_count / max_depth / nodes 齐全；
      - 结构：唯一根、parent_id 指向存在的节点、level=父+1、同级 order 连续、无环；
      - 真实：不同职业给出不同树，技能节点数 = 该职业关联表记录数；
      - 边界：未知 occupation_id 返回 404 + 统一信封（不是空树）；
      - 兼容：旧路径 /v1/tree 可用且带 Deprecation 头。

    注意：本用例需 PR#18 合并后的真实后端；合并前在本地旧后端上断言会失败，
    属预期（新口径先于实现落地），不是回归。自检模式由 conftest 统一 skip。
    """
    if api_mode != "real":
        pytest.skip("发展树接口仅真实后端提供（自检 stub 无此路由）")

    data_scientist = "OCC-ONET-15-2051.00"
    analyst = "OCC-ONET-15-1211.00"

    def get_tree(occ_id, path="/api/v1/tree"):
        resp = client.get(f"{path}/{occ_id}")
        assert resp.status_code == 200, resp.text
        body = _json(resp)
        assert body["code"] == 200
        assert body["request_id"].startswith("req_")
        return body["data"]

    tree = get_tree(data_scientist)
    for field in ("occupation_id", "root_id", "node_count", "max_depth", "nodes"):
        assert field in tree, f"发展树 data 缺字段 {field}"
    nodes = tree["nodes"]
    assert isinstance(nodes, list) and nodes
    assert tree["node_count"] == len(nodes)
    assert tree["max_depth"] == 2

    by_id = {n["node_id"]: n for n in nodes}
    assert len(by_id) == len(nodes), "node_id 重复"
    for n in nodes:
        for field in (
            "node_id", "parent_id", "node_type", "level", "order", "skill_id",
            "skill_name", "description", "status", "priority",
        ):
            assert field in n, f"树节点缺字段 {field}"
        assert n["node_type"] in ("occupation", "category", "skill")
        assert n["status"] in ("not_started", "in_progress", "mastered")
        assert n["level"] <= tree["max_depth"]
    roots = [n for n in nodes if n["parent_id"] is None]
    assert len(roots) == 1 and roots[0]["node_id"] == tree["root_id"], "必须唯一根"
    assert roots[0]["node_type"] == "occupation" and roots[0]["level"] == 0

    siblings = {}
    for n in nodes:
        if n["parent_id"] is None:
            continue
        parent = by_id[n["parent_id"]]
        assert n["level"] == parent["level"] + 1, f"{n['node_id']} 层级跳级"
        assert n["node_type"] == {"occupation": "category", "category": "skill"}.get(
            parent["node_type"]
        ), f"{n['node_id']} 父子类型不匹配"
        if n["node_type"] == "skill":
            assert n["skill_id"], "技能节点必须有 skill_id"
        else:
            assert n["skill_id"] is None, "非技能节点 skill_id 应为 null"
        siblings.setdefault(n["parent_id"], []).append(n["order"])
    for parent_id, orders in siblings.items():
        assert sorted(orders) == list(range(1, len(orders) + 1)), (
            f"{parent_id} 下 order 不连续"
        )
    for n in nodes:
        cursor, steps = n, 0
        while cursor["parent_id"] is not None:
            cursor = by_id[cursor["parent_id"]]
            steps += 1
            assert steps <= len(nodes), f"{n['node_id']} 父链成环"
        assert cursor["node_id"] == tree["root_id"], f"{n['node_id']} 无法上溯到根"

    # 真实数据：两个职业的树不同（旧 mock 对任何 ID 都返回同一份）
    other = get_tree(analyst)
    assert other["nodes"] != nodes, "不同职业应返回不同的树"

    # 未知职业：404 + 统一信封，不返回空树
    missing = client.get("/api/v1/tree/occ_eng")
    assert missing.status_code == 404, missing.text
    assert _json(missing)["code"] == 404
    assert _json(missing)["data"] is None

    # 旧路径保留但标弃用（前端仍在迁移窗口内）
    legacy = client.get(f"/v1/tree/{data_scientist}")
    assert legacy.status_code == 200, legacy.text
    assert legacy.headers.get("deprecation") == "true"
    assert "successor-version" in legacy.headers.get("link", "")


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


@pytest.mark.api
@pytest.mark.exception
def test_TC_EX_10_evidence_level_out_of_enum(client, recommend_path):
    """evidence_level 不在冻结的 7 值枚举内：422，错误定位到字段。

    2026-11-27 起（收尾清单 M2 第 1 条 / ADR-012）由 Pydantic Literal 硬校验：
    中文「课程作业」、拼写错误 projct、大写 PROJECT、旧值 verified 一律 422，
    不再静默归一为 none 后返回 200。

    末尾断言 service 层枚举与算法层 EVIDENCE_LEVELS 一致：两处各写一份
    白名单，不同步会让「接口放行、算法归 none」重新出现，必须锁死。

    两个包级 import 放在函数内：一键包自检模式没有 backend/packages，模块顶层
    import 会让整个 test_api.py collection 失败（P0-2 假绿灯回归）。本用例依赖
    client，自检模式必被 skip，函数体不执行，import 也就不会触发。
    """
    from packages.core.schemas import SkillInput
    from packages.training.matcher import EVIDENCE_LEVELS

    for bad_value in ("课程作业", "projct", "PROJECT", "verified"):
        response = client.post(
            recommend_path,
            json=payload(skill_level(3, evidence_level=bad_value)),
        )
        assert response.status_code == 422, f"{bad_value!r} 应 422：{response.text}"
        assert "evidence_level" in response.text, f"{bad_value!r} 错误未定位到字段"

    prop = SkillInput.model_json_schema()["properties"]["evidence_level"]
    service_enum = next(
        (set(item["enum"]) for item in prop.get("anyOf", [prop]) if "enum" in item),
        set(),
    )
    assert service_enum == set(EVIDENCE_LEVELS), "service 层枚举与算法层白名单不一致"
