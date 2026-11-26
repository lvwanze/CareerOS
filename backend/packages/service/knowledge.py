#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : knowledge.py
# @Path       : backend/packages/service/knowledge.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-25 14:40:00
# @Version    : v2.0.0
"""知识库读取层：技能词表、职业、职业-技能关联、发展树。

为什么单独抽一层，而不是继续写在路由里：
1. 原来技能列表在 recommend.py 读一遍 skills.csv，职业详情在 occupations.py
   又读一遍，发展树再接上就是第三份。三份代码各写各的中文名回退、各排各的
   序，时间一长同一技能在不同接口的显示名就可能不一样。
2. 发展树不是一张表能查出来的：职业 → 技能类别 → 技能，父子关系、同级排序、
   全局学习顺序都是规则。规则和数据读取放在一起，路由里只剩 HTTP 的事。

数据来源（都是仓库内已冻结的文件，不新增外部依赖）：
- data/processed/occupations.csv       职业 28 条，含 description
- data/processed/skills.csv            技能词表 35 条
- data/processed/occupation_skills.csv 职业-技能关联 492 条，含 IM / 要求等级
- data/reference/*_zh.csv              中文名，映射缺失时回退英文名
- data/reference/skill_description.csv 技能英文说明（O*NET 31.0 原文）
"""

import csv
import logging
from pathlib import Path

from packages.core.name_text import clean_name
from packages.core.schemas import SkillOption

logger = logging.getLogger(__name__)

# knowledge.py -> service -> packages -> backend
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"

# 发展树的第一层分组。用 O*NET 自己的两分法（2.A 基本技能 / 2.B 跨职能技能），
# 不自造"初级/中级/高级"——那需要难度数据，我们没有，硬分会变成编数据。
# 顺序即学习顺序：基本技能是所有目标职业的公共底座，先补；跨职能技能在其后。
# 每个分组四件事：数据里的 category 值、中文标签、英文标签、分组说明。
# 英文标签不能直接用 essential/transferable 这种小写枚举值——前端若显示 name_en，
# 用户看到的是 "essential" 而不是一句话，等于把内部枚举漏到界面上。
CATEGORY_STAGES = (
    ("essential", "基本技能", "Essential Skills",
     "O*NET 2.A 基本技能：读写、数学、批判性思维等，所有目标职业都要求"),
    ("transferable", "跨职能技能", "Transferable Skills",
     "O*NET 2.B 跨职能技能：编程、系统分析、资源管理等，可迁移到不同岗位"),
)


def load_name_mapping(filename: str, id_field: str) -> dict[str, str]:
    """读参考中文名映射。文件缺失或某行没中文名时返回空表，调用方回退英文名，
    不让服务因为少一个翻译文件就整体 500。清洗口径见 core.name_text。"""
    path = REFERENCE_DIR / filename
    if not path.is_file():
        logger.warning("中文名映射缺失，回退英文名：%s", path)
        return {}
    table: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            key_value = clean_name(row.get(id_field))
            name_zh = clean_name(row.get("name_zh"))
            if key_value and name_zh:
                table[key_value] = name_zh
    return table


def load_skill_rows() -> dict[str, dict]:
    """技能词表 35 条，{skill_id: 原始行}。"""
    with (PROCESSED_DIR / "skills.csv").open(encoding="utf-8", newline="") as file:
        return {row["skill_id"]: row for row in csv.DictReader(file)}


def load_skill_ids() -> set[str]:
    """技能词表全量 ID。

    请求校验用它而不是"被职业引用的 33 条"：Equipment Selection、Installation
    两条零引用技能传进来不会算错（只是不贡献分数），"技能表里根本没有"才是错。
    """
    return set(load_skill_rows())


def load_skill_descriptions() -> dict[str, str]:
    """技能英文说明，{skill_id: description}。

    为什么不直接读 skills.csv 的 description 列：那一列在三表冻结时按
    manifest 的 description_policy 全部留空（当时前端不展示技能详情），
    冻结表不再改动。说明改由参考层提供，做法与中文名映射一致——
    reference 是"维护型参考数据"，processed 是"冻结契约表"，两者不混。
    """
    path = REFERENCE_DIR / "skill_description.csv"
    if not path.is_file():
        logger.warning("技能说明参考表缺失，description 回退空串：%s", path)
        return {}
    table: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            skill_id = clean_name(row.get("skill_id"))
            description = clean_name(row.get("description_en"))
            if skill_id and description:
                table[skill_id] = description
    return table


def load_occupation_skill_rows() -> list[dict]:
    """职业-技能关联 492 条（原样，未排序）。"""
    with (PROCESSED_DIR / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def load_occupations() -> dict[str, dict]:
    """职业基础信息，{occupation_id: {name, name_zh, description, category}}。"""
    names_zh = load_name_mapping("occupation_name_zh.csv", "occupation_id")
    occupations: dict[str, dict] = {}
    with (PROCESSED_DIR / "occupations.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            occupation_id = row["occupation_id"]
            occupations[occupation_id] = {
                "occupation_id": occupation_id,
                "name": row["name"],
                "name_zh": names_zh.get(occupation_id) or clean_name(row["name"]) or occupation_id,
                "description": row["description"],
                "category": row["category"],
            }
    return occupations


def load_skill_options(used_only: bool = False) -> list[SkillOption]:
    """技能列表，按 skills.csv 原顺序（35 条）。

    used_in_kb 现在由 occupation_skills.csv 现算，不再写死 True：
    词表 35 条里有 2 条（Equipment Selection、Installation）没有关联任何职业，
    恒为 True 等于告诉前端"这 35 条都能选"，前端把这 2 条选上后推荐分数一分不涨，
    排查时会以为是算法问题。默认返回全量并逐条标注，前端按 used_in_kb=true 过滤
    即可还原成原来的 33 条；used_only=True 供只需要可选项的调用方一步到位。
    """
    used_skill_ids = {row["skill_id"] for row in load_occupation_skill_rows()}
    names_zh = load_name_mapping("skill_name_zh.csv", "skill_id")
    descriptions = load_skill_descriptions()

    options: list[SkillOption] = []
    for skill_id, row in load_skill_rows().items():
        used_in_kb = skill_id in used_skill_ids
        if used_only and not used_in_kb:
            continue
        options.append(
            SkillOption(
                skill_id=skill_id,
                name=row["name"],
                name_zh=names_zh.get(skill_id) or clean_name(row["name"]) or skill_id,
                category=row["category"],
                used_in_kb=used_in_kb,
                description=descriptions.get(skill_id) or clean_name(row.get("description")),
            )
        )
    return options


def load_occupation_requirements() -> list[dict]:
    """推荐算法要的那种结构：每个职业 + 它要求的技能列表（含 IM 与要求等级）。"""
    skill_rows = load_skill_rows()
    names_zh = load_name_mapping("skill_name_zh.csv", "skill_id")

    occupations = {
        occupation_id: {
            "occupation_id": occupation_id,
            "occupation_name": occupation["name"],
            "occupation_name_zh": occupation["name_zh"],
            "skills": [],
        }
        for occupation_id, occupation in load_occupations().items()
    }

    for row in load_occupation_skill_rows():
        occupation = occupations.get(row["occupation_id"])
        if occupation is None:
            continue
        skill_id = row["skill_id"]
        skill = skill_rows.get(skill_id, {})
        occupation["skills"].append({
            "skill_id": skill_id,
            "skill_name": skill.get("name", skill_id),
            "skill_name_zh": names_zh.get(skill_id) or skill.get("name") or skill_id,
            "importance": float(row["importance"]),
            "required_level": int(row["required_level"]),
        })

    return list(occupations.values())


def _skill_sort_key(row: dict) -> tuple:
    """同级技能的顺序：重要程度降序 → 要求等级降序 → ID 升序。

    为什么不按 ID 排：发展树是给人照着学的，先学 O*NET 认为更重要、要求更高的，
    学完再往下走。ID 只作最后的兜底，保证每次请求顺序一致（可复现）。
    """
    return (-float(row["importance"]), -int(row["required_level"]), row["skill_id"])


def validate_tree(nodes: list[dict], root_id: str) -> dict:
    """校验树的合法性，不合法直接抛 ValueError（宁可 500 也不返回坏树）。

    校验的是"能不能被解析成树"，不是"内容对不对"：
    - node_id 唯一（重复了前端 key 会撞、React/Flutter 列表会丢节点）
    - 只有一个根，且就是 root_id、类型为 occupation、level 为 0
    - 除根以外的 parent_id 都指向本树里真实存在的节点（无孤儿）
    - level 必须等于父节点 level + 1（层级不能跳）
    - 父子类型必须对得上：occupation 只带 category，category 只带 skill，skill 不能再带子节点
      （只查 level 的话，把技能直接挂到根上也能过——那棵树前端画出来是错的）
    - 同级 order 从 1 连续递增（前端按 order 排，跳号说明排序逻辑有洞）
    - 任何节点沿 parent_id 上溯都能到达根（无环）
    - 技能节点必须有 skill_id，分组节点必须没有（避免前端把分组当技能提交）

    返回 {"node_count", "max_depth", "skill_count"} 供响应体直接使用。
    """
    by_id = {}
    for node in nodes:
        node_id = node["node_id"]
        if node_id in by_id:
            raise ValueError(f"节点 ID 重复：{node_id}")
        by_id[node_id] = node

    roots = [node for node in nodes if node["parent_id"] is None]
    if len(roots) != 1 or roots[0]["node_id"] != root_id:
        raise ValueError(f"树必须只有一个根，且根为 {root_id}，实际 {[r['node_id'] for r in roots]}")
    if roots[0]["node_type"] != "occupation" or roots[0]["level"] != 0:
        raise ValueError(f"根节点必须是 occupation 且 level=0，实际 {roots[0]['node_type']}/{roots[0]['level']}")

    # 父子类型白名单：技能节点是叶子，不再带子节点
    allowed_child = {"occupation": "category", "category": "skill"}

    siblings: dict[str, list[int]] = {}
    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id is None:
            continue
        parent = by_id.get(parent_id)
        if parent is None:
            raise ValueError(f"节点 {node['node_id']} 的父节点不存在：{parent_id}")
        if node["level"] != parent["level"] + 1:
            raise ValueError(
                f"节点 {node['node_id']} 层级跳级：自身 {node['level']}，父节点 {parent['level']}"
            )
        expected_child = allowed_child.get(parent["node_type"])
        if node["node_type"] != expected_child:
            raise ValueError(
                f"节点 {node['node_id']}（{node['node_type']}）不能挂在 "
                f"{parent['node_type']} 下，应为 {expected_child or '无（技能是叶子）'}"
            )
        if node["node_type"] == "skill" and not node["skill_id"]:
            raise ValueError(f"技能节点缺 skill_id：{node['node_id']}")
        if node["node_type"] != "skill" and node["skill_id"] is not None:
            raise ValueError(f"非技能节点不应带 skill_id：{node['node_id']}")
        siblings.setdefault(parent_id, []).append(node["order"])

    for parent_id, orders in siblings.items():
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise ValueError(f"父节点 {parent_id} 下的同级 order 不是从 1 连续递增：{sorted(orders)}")

    # 无环：逐节点上溯，步数不超过节点总数（有环必然走不完）
    for node in nodes:
        cursor, steps = node, 0
        while cursor["parent_id"] is not None:
            cursor = by_id[cursor["parent_id"]]
            steps += 1
            if steps > len(nodes):
                raise ValueError(f"节点 {node['node_id']} 的父链存在环")

    return {
        "node_count": len(nodes),
        "max_depth": max(node["level"] for node in nodes),
        "skill_count": sum(1 for node in nodes if node["node_type"] == "skill"),
    }


def build_career_tree(occupation_id: str) -> dict | None:
    """按真实数据拼出发展树；职业不存在返回 None（路由层转 404）。

    结构（三层，深度 0~2）：
        职业根节点（level 0）
        └── 技能类别（level 1）：基本技能 / 跨职能技能
            └── 技能节点（level 2，按重要程度排序）

    节点里的数字全部来自三张表：importance / required_level 取关联表，
    说明取 reference/skill_description.csv，中文名取 reference/*_zh.csv。
    status 一律 not_started：这个接口描述的是"这个职业要求什么"，
    个人进度由前端本地持久化（吕宛泽那条线），不写进知识库。
    """
    occupation = load_occupations().get(occupation_id)
    if occupation is None:
        return None

    skill_rows = load_skill_rows()
    names_zh = load_name_mapping("skill_name_zh.csv", "skill_id")
    descriptions = load_skill_descriptions()

    relations: dict[str, list[dict]] = {}
    for row in load_occupation_skill_rows():
        if row["occupation_id"] == occupation_id:
            relations.setdefault(row["skill_id"], []).append(row)

    root_id = f"TREE-{occupation_id}"
    nodes: list[dict] = [
        {
            "node_id": root_id,
            "parent_id": None,
            "node_type": "occupation",
            "level": 0,
            "order": 0,
            "skill_id": None,
            "skill_name": occupation["name_zh"],
            "name_en": occupation["name"],
            "description": occupation["description"],
            "status": "not_started",
            "priority": 0,
            "category": occupation["category"],
            "required_level": None,
            "importance": None,
        }
    ]

    learning_order = 0
    for category_key, category_label, category_label_en, category_note in CATEGORY_STAGES:
        members = [
            rows[0]
            for skill_id, rows in relations.items()
            if skill_rows.get(skill_id, {}).get("category") == category_key
        ]
        if not members:
            continue
        members.sort(key=_skill_sort_key)

        category_id = f"{occupation_id}-CAT-{category_key}"
        nodes.append(
            {
                "node_id": category_id,
                "parent_id": root_id,
                "node_type": "category",
                "level": 1,
                "order": len([n for n in nodes if n["parent_id"] == root_id]) + 1,
                "skill_id": None,
                "skill_name": category_label,
                "name_en": category_label_en,
                "description": f"{category_note}（本职业要求 {len(members)} 项）",
                "status": "not_started",
                "priority": 0,
                "category": category_key,
                "required_level": None,
                "importance": None,
            }
        )

        for order, row in enumerate(members, start=1):
            skill_id = row["skill_id"]
            skill = skill_rows.get(skill_id, {})
            learning_order += 1
            nodes.append(
                {
                    "node_id": f"{occupation_id}-{skill_id}",
                    "parent_id": category_id,
                    "node_type": "skill",
                    "level": 2,
                    "order": order,
                    "skill_id": skill_id,
                    "skill_name": names_zh.get(skill_id) or skill.get("name") or skill_id,
                    "name_en": skill.get("name", skill_id),
                    "description": descriptions.get(skill_id)
                    or clean_name(skill.get("description"))
                    or f"目标职业要求该技能达到 {row['required_level']} 级（0~4）",
                    "status": "not_started",
                    "priority": learning_order,
                    "category": category_key,
                    "required_level": int(row["required_level"]),
                    "importance": float(row["importance"]),
                }
            )

    stats = validate_tree(nodes, root_id)

    # 拼接数必须等于关联表里的技能数。少一个就说明有技能没落到任何分组里
    # （典型场景：skills.csv 出现第三种 category，而 CATEGORY_STAGES 只登记了两种）。
    # 不校验的话，接口会安静地少返回几个技能节点，缺陷一路漂到用户面前才被发现。
    if stats["skill_count"] != len(relations):
        covered = {node["skill_id"] for node in nodes if node["node_type"] == "skill"}
        missing = sorted(set(relations) - covered)
        raise ValueError(
            f"{occupation_id} 技能节点数 {stats['skill_count']} 与关联表去重后的 "
            f"{len(relations)} 项不一致，未落组：{missing}"
        )

    return {
        "occupation_id": occupation_id,
        "occupation_name": occupation["name"],
        "occupation_name_zh": occupation["name_zh"],
        "root_id": root_id,
        "node_count": stats["node_count"],
        "max_depth": stats["max_depth"],
        "nodes": nodes,
    }
