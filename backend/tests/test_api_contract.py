"""接口契约测试（代旭 · 验收单第 2 行「接口保障」）

只补 main 上还没有的覆盖，避免和已有用例重复：
  tests/test_health.py            → /health、/ready 存活探针
  tests/test_recommend.py         → 推荐算法、self_level 校验、未知 skill_id
  tests/test_response_envelope.py → 404/405/422/500 的信封格式

本文件专盯验收单那三条：
  ① 核心接口 200（recommendations / skills / tree）
  ② 技能列表字段完整、无空值遗漏
  ③ 树结构合法、可正常解析

上一版这三条都只做到"能解析"，复检时被判成：
  ① recommendations、skills 是真实数据，tree 是 mock；
  ② 字段没空值，但 used_in_kb 恒为 True、description 没透出；
  ③ 树是一层平铺，不构成层级。
所以这里改成对着"真实数据"和"结构"断言，而不是对着"字段存在"断言：
  - 技能 35 条、其中 33 条 used_in_kb=true，零引用那 2 条必须是 false；
  - 每条技能 description 非空，且与 reference/skill_description.csv 一致；
  - 树按 occupation_id 变化，技能节点数等于该职业的关联记录数；
  - 树只有一个根、父节点存在、层级不跳、同级 order 连续、无环。

只断言接口返回，不碰算法内部，所以调权重、改排序时不会误报。
"""

import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from packages.service.knowledge import DATA_DIR, PROCESSED_DIR, REFERENCE_DIR, validate_tree
from packages.service.main import app

client = TestClient(app)

DATA_SCIENCE_ID = "OCC-ONET-15-2051.00"
ANALYST_ID = "OCC-ONET-15-1211.00"
ZERO_REFERENCE_IDS = {"SKILL-ONET-2.B.3.c", "SKILL-ONET-2.B.3.d"}


def _first_skill_id() -> str:
    return client.get("/api/v1/skills").json()["data"][0]["skill_id"]


def _read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_skills_fields_complete():
    """验收第②条：技能列表字段完整、无空值遗漏。

    填报页的技能选项全来自这个接口，任何一个字段空着前端就会出空白项。
    description 是本次新透出的字段——技能说明以前只躺在数据侧，接口不给，
    前端就算想显示也没有东西可用。
    """
    response = client.get("/api/v1/skills")
    assert response.status_code == 200

    body = response.json()
    assert body["code"] == 200
    skills = body["data"]
    assert isinstance(skills, list)
    assert len(skills) == 35, "技能表 35 条应全量返回，用于核对口径"

    required_fields = ["skill_id", "name", "name_zh", "category", "used_in_kb", "description"]
    for skill in skills:
        for field in required_fields:
            assert field in skill, f"技能 {skill.get('skill_id')} 缺字段 {field}"
            assert skill[field] not in (None, ""), f"技能 {skill.get('skill_id')} 的 {field} 是空值"

    ids = [skill["skill_id"] for skill in skills]
    assert len(ids) == len(set(ids)), "skill_id 有重复"


def test_used_in_kb_is_computed_not_hardcoded():
    """验收第②条：used_in_kb 必须是算出来的，不能恒为 True。

    词表 35 条里有 2 条没关联任何职业。恒定 True 等于告诉前端"这 35 条都能选"，
    选上后推荐分数一分不涨，查起来会以为是算法算错了。
    """
    skills = client.get("/api/v1/skills").json()["data"]
    used = {skill["skill_id"] for skill in skills if skill["used_in_kb"]}
    unused = {skill["skill_id"] for skill in skills if not skill["used_in_kb"]}

    relation_ids = {row["skill_id"] for row in _read_rows(PROCESSED_DIR / "occupation_skills.csv")}
    assert used == relation_ids, "used_in_kb=true 的集合必须等于关联表里出现过的技能"
    assert unused == ZERO_REFERENCE_IDS, f"零引用技能应为 {ZERO_REFERENCE_IDS}，实际 {unused}"
    assert len(used) == 33 and len(unused) == 2


def test_used_only_query_still_returns_33():
    """api_spec §3.5 写的"前端可选项 33 条"仍要一步拿到，不能逼前端自己过滤。"""
    items = client.get("/api/v1/skills?used_only=true").json()["data"]
    assert len(items) == 33
    assert all(item["used_in_kb"] for item in items)


def test_skill_description_matches_reference_table():
    """description 取自 reference/skill_description.csv（O*NET 31.0 原文）。

    不做"非空就行"的弱断言：换成占位符也能过。这里要求逐条对得上参考表，
    数据换版本时用例会先报错，而不是等前端看到说明才知道文案变了。
    """
    expected = {
        row["skill_id"]: row["description_en"]
        for row in _read_rows(REFERENCE_DIR / "skill_description.csv")
    }
    skills = client.get("/api/v1/skills").json()["data"]

    assert {skill["skill_id"] for skill in skills} == set(expected), "参考表与技能词表条目不一致"
    for skill in skills:
        assert skill["description"] == expected[skill["skill_id"]], (
            f"技能 {skill['skill_id']} 的 description 与参考表不一致"
        )


def test_request_id_uses_spec_prefix():
    """request_id 格式与 docs/api_spec.md 的 req_xxx 对齐。

    改 schemas.py 之前这里是裸 UUID，和文档对不上。
    """
    body = client.get("/api/v1/skills").json()
    request_id = body["request_id"]
    assert request_id.startswith("req_"), f"request_id 前缀不对: {request_id}"
    assert len(request_id) == 12, f"request_id 长度不对（应为 req_ + 8 位）: {request_id}"


def test_recommendations_fields_and_score_range():
    """验收第①条：推荐接口 200 且关键字段齐全、匹配度在有效区间。"""
    payload = {
        "profile": {
            "user_id": "tester@careeros.com",
            "learning_stage": {
                "education_level": "本科",
                "major": "软件工程",
                "current_stage": "大三",
            },
            "preferences": {},
            "skills": [{"skill_id": _first_skill_id(), "self_level": 1}],
            "constraints": {},
            "career_goals": {},
        }
    }
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["code"] == 200
    assert body["data"]["user_id"] == "tester@careeros.com"

    recommendations = body["data"]["recommendations"]
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0

    for item in recommendations:
        for field in [
            "occupation_id",
            "occupation_name",
            "match_score",
            "skill_gaps",
            "recommendation_reasons",
            "matched_skills",
            "skills_to_improve",
            "skills_to_verify",
        ]:
            assert field in item, f"推荐缺字段 {field}"

        assert 0 <= item["match_score"] <= 1, f"match_score 越界: {item['match_score']}"

        for gap in item["skill_gaps"]:
            for field in ["skill_id", "gap", "status", "current_level", "required_level"]:
                assert field in gap, f"技能缺口缺字段 {field}"
            assert gap["status"] in ("mastered", "needs_improvement", "needs_verification")
            assert 0 <= gap["current_level"] <= 4
            assert 0 <= gap["required_level"] <= 4


def _tree(occupation_id: str) -> dict:
    response = client.get(f"/api/v1/tree/{occupation_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 200
    return body["data"]


def test_skill_description_reference_is_traceable():
    """参考表必须在 manifest 里登记来源、生成脚本与 sha256，否则就是"来历不明的数据文件"。

    冻结三表有 sha256 却没有校验，等于没登记；这里把新加的参考表也纳入对账。
    哈希按 LF 归一化后再比：Windows 克隆会把 CSV 检成 CRLF，
    直接对原始字节做哈希会让这条用例只在 Linux 上绿。
    """
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    meta = manifest["derived_skill_descriptions"]

    assert meta["row_count"] == 35
    assert meta["generated_by"].endswith("build_skill_descriptions.py")
    assert meta["join_key"].startswith("skills.csv.source_id")

    raw = (REFERENCE_DIR / "skill_description.csv").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == meta["sha256"], (
        "skill_description.csv 与 manifest 登记的 sha256 不一致（改过内容没同步 manifest）"
    )


def test_tree_is_built_from_real_relations():
    """验收第③条（上）：树必须按 occupation_id 从关联表现拼，不能是写死的节点。

    上一版的 3 个节点（Python / SQL / 业务分析）对任何 ID 都返回同一份，
    连 mock 都算不上"发展树"。这一版要求：技能节点数 = 该职业的关联记录数。
    """
    relations = _read_rows(PROCESSED_DIR / "occupation_skills.csv")
    relation_counts: dict[str, int] = {}
    for row in relations:
        relation_counts[row["occupation_id"]] = relation_counts.get(row["occupation_id"], 0) + 1

    for occupation_id in (DATA_SCIENCE_ID, ANALYST_ID):
        nodes = _tree(occupation_id)["nodes"]
        skill_nodes = [node for node in nodes if node["node_type"] == "skill"]
        assert len(skill_nodes) == relation_counts[occupation_id], (
            f"{occupation_id} 的技能节点数与关联表不符"
        )
        assert {node["skill_id"] for node in skill_nodes} == {
            row["skill_id"] for row in relations if row["occupation_id"] == occupation_id
        }

    # 不同职业必须给出不同的树（上一版这里完全相同）
    assert _tree(DATA_SCIENCE_ID)["nodes"] != _tree(ANALYST_ID)["nodes"]


def test_tree_structure_is_legal():
    """验收第③条（下）：层级结构合法、可正常解析。

    逐条校验"能不能被当成树解析"：唯一根、父节点存在、层级不跳、同级 order
    连续、无环。前端按 parent_id 建树时，任何一条不成立都会画出断树或死循环。
    """
    for occupation_id in (DATA_SCIENCE_ID, ANALYST_ID):
        data = _tree(occupation_id)
        nodes = data["nodes"]
        by_id = {node["node_id"]: node for node in nodes}

        assert len(by_id) == len(nodes), "node_id 有重复"
        assert data["node_count"] == len(nodes)
        assert data["root_id"] in by_id

        roots = [node for node in nodes if node["parent_id"] is None]
        assert len(roots) == 1, "树必须只有一个根"
        assert roots[0]["node_id"] == data["root_id"]
        assert roots[0]["level"] == 0
        assert roots[0]["node_type"] == "occupation"

        siblings: dict[str, list[int]] = {}
        for node in nodes:
            assert node["node_type"] in ("occupation", "category", "skill")
            assert node["status"] in ("not_started", "in_progress", "mastered")
            if node["parent_id"] is None:
                continue
            parent = by_id[node["parent_id"]]
            assert node["level"] == parent["level"] + 1, f"{node['node_id']} 层级跳级"
            # 只查层级不够：把技能直接挂到根上（level 1）也能过层级校验，但那不是这棵树
            expected_child = {"occupation": "category", "category": "skill"}.get(parent["node_type"])
            assert node["node_type"] == expected_child, (
                f"{node['node_id']}（{node['node_type']}）不能挂在 {parent['node_type']} 下"
            )
            siblings.setdefault(node["parent_id"], []).append(node["order"])

        for parent_id, orders in siblings.items():
            assert sorted(orders) == list(range(1, len(orders) + 1)), (
                f"{parent_id} 下同级 order 不连续：{sorted(orders)}"
            )

        # 每个节点都能上溯到根（有环会在这里走不完）
        for node in nodes:
            cursor, steps = node, 0
            while cursor["parent_id"] is not None:
                cursor = by_id[cursor["parent_id"]]
                steps += 1
                assert steps <= len(nodes), f"{node['node_id']} 的父链成环"
            assert cursor["node_id"] == data["root_id"]

        assert data["max_depth"] == max(node["level"] for node in nodes)


def test_tree_nodes_carry_skill_facts():
    """技能节点上的数字必须来自关联表，不能是编的。

    required_level / importance 是前端排序与赵帝臣算法同源的两个值，
    接口再算一遍容易走偏，这里直接和 occupation_skills.csv 对账。
    两个职业都过一遍：只测一个，换个职业走错分支也发现不了。
    """
    relations = {
        (row["occupation_id"], row["skill_id"]): row
        for row in _read_rows(PROCESSED_DIR / "occupation_skills.csv")
    }
    for occupation_id in (DATA_SCIENCE_ID, ANALYST_ID):
        for node in _tree(occupation_id)["nodes"]:
            if node["node_type"] != "skill":
                assert node["skill_id"] is None
                assert node["required_level"] is None and node["importance"] is None
                continue
            row = relations[(occupation_id, node["skill_id"])]
            assert node["required_level"] == int(row["required_level"])
            assert abs(node["importance"] - float(row["importance"])) < 1e-9
            assert node["skill_name"], "技能节点必须有显示名"
            assert node["description"], "技能节点必须有说明"


def test_validate_tree_rejects_illegal_shapes():
    """校验函数本身要能用：坏树必须抛错，否则它就是一段没人验证过的装饰代码。

    这里不经过 HTTP，直接喂三种典型坏树——接口层能过、结构层必须挡住的那些。
    """
    root = {"node_id": "R", "parent_id": None, "node_type": "occupation", "level": 0, "order": 0, "skill_id": None}
    category = {"node_id": "C", "parent_id": "R", "node_type": "category", "level": 1, "order": 1, "skill_id": None}
    skill = {"node_id": "S", "parent_id": "C", "node_type": "skill", "level": 2, "order": 1, "skill_id": "X"}

    assert validate_tree([root, category, skill], "R")["skill_count"] == 1

    # 技能直接挂在根上：层级没跳，但父子类型不对
    with pytest.raises(ValueError, match="不能挂在"):
        validate_tree([root, {**skill, "parent_id": "R", "level": 1}], "R")

    # 两个根
    with pytest.raises(ValueError, match="只有一个根"):
        validate_tree([root, {**root, "node_id": "R2"}], "R")

    # 同级 order 跳号
    with pytest.raises(ValueError, match="order"):
        validate_tree([root, {**category, "order": 2}, skill], "R")

    # 父节点不存在
    with pytest.raises(ValueError, match="父节点不存在"):
        validate_tree([root, {**category, "parent_id": "GONE"}], "R")


def test_tree_unknown_occupation_returns_404():
    """职业 ID 写错要 404，不能返回空树——空树会被当成「该职业没有技能要求」。"""
    response = client.get("/api/v1/tree/occ_eng")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 404
    assert body["data"] is None
    assert body["request_id"].startswith("req_")


def test_legacy_tree_path_kept_with_deprecation_header():
    """旧路径 /v1/tree/{id} 还要能用（前端 api_service.dart 仍在请求），
    但响应头必须声明弃用，否则没人知道该迁。"""
    response = client.get(f"/v1/tree/{DATA_SCIENCE_ID}")

    assert response.status_code == 200
    assert response.headers.get("deprecation") == "true"
    assert "successor-version" in response.headers.get("link", "")
    assert response.json()["data"] == _tree(DATA_SCIENCE_ID)
