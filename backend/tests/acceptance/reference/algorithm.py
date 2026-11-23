"""参考匹配算法：让测试管线现在就能跑通的最小可用实现。

来源：docs/problem.md 第一阶段技术路线
  技能向量化 -> 余弦相似度 -> 加权排序 -> 技能等级差值 -> 规则化发展路径

知识库已从高帅龙的 M1 交付包（28 职业 / 35 技能 / 492 关联）真实加载，
importance 按赵帝臣 A1 口径做 (IM-1)/4 归一化。

注意：这不是赵帝臣的正式算法。代旭 / 赵帝臣的代码接入后，测试会自动
切换到真实实现（见 conftest.py）。本文件的作用是：
  1. 验证测试用例本身写得对不对
  2. 给算法负责人一个可对照的输入输出示例
"""

import math

from reference.real_data import (
    OCCUPATION_NAMES,
    OCCUPATION_SKILLS,
    SKILL_NAMES,
)

VERIFIED_EVIDENCE = {"verified", "objective", "project"}


def cosine_similarity(user_vec, occ_vec):
    """余弦相似度；任一向量为零时返回 0。"""
    dot = sum(a * b for a, b in zip(user_vec, occ_vec))
    u_norm = math.sqrt(sum(a * a for a in user_vec))
    o_norm = math.sqrt(sum(b * b for b in occ_vec))
    if u_norm == 0 or o_norm == 0:
        return 0.0
    return dot / (u_norm * o_norm)


def classify_gap(current_level, required_level, evidence_level=None):
    """技能差距分级，状态取值严格遵循 data_contract.md。"""
    gap = max(0, required_level - current_level)
    if gap > 0:
        return gap, "needs_improvement"
    if evidence_level not in VERIFIED_EVIDENCE:
        return 0, "needs_verification"
    return 0, "mastered"


def match_profile(profile):
    """输入 UserProfile 字典，输出契约约定的 data 部分。"""
    user_skills = {
        item["skill_id"]: (item.get("self_level") or 0, item.get("evidence_level"))
        for item in profile.get("skills", [])
    }
    all_skill_ids = sorted({s for req in OCCUPATION_SKILLS.values() for s in req})

    scored = []
    for occ_id, requirements in OCCUPATION_SKILLS.items():
        user_vec = [user_skills.get(sid, (0, None))[0] for sid in all_skill_ids]
        occ_vec = [
            requirements[sid][0] * requirements[sid][1] if sid in requirements else 0
            for sid in all_skill_ids
        ]
        score = round(cosine_similarity(user_vec, occ_vec), 4)
        scored.append((occ_id, score))

    # 分数降序；同分时用 occupation_id 保证排序稳定
    scored.sort(key=lambda item: (-item[1], item[0]))
    top = scored[:5]

    recommendations = []
    development_paths = []
    for occ_id, score in top:
        requirements = OCCUPATION_SKILLS[occ_id]
        matched, to_improve, to_verify = [], [], []
        nodes = []

        for sid, (required, importance) in sorted(
            requirements.items(), key=lambda kv: (-kv[1][1], kv[0])
        ):
            current, evidence = user_skills.get(sid, (0, None))
            gap, status = classify_gap(current, required, evidence)
            if status == "mastered":
                matched.append(sid)
            elif status == "needs_improvement":
                to_improve.append(sid)
            else:
                to_verify.append(sid)

            if status != "mastered":
                node_status = (
                    "needs_verification" if status == "needs_verification"
                    else "needs_improvement" if gap >= 2
                    else "not_started"
                )
                nodes.append({
                    "node_id": f"{occ_id}_{sid}",
                    "skill_id": sid,
                    "name": SKILL_NAMES.get(sid, sid),
                    "status": node_status,
                    "priority": gap if gap else 0,
                    "description": f"目标等级 {required}，当前等级 {current}",
                })

        reasons = [
            f"技能匹配度 {score:.2f}",
            f"已具备 {len(matched)} 项核心技能",
            f"待加强 {len(to_improve)} 项，待验证 {len(to_verify)} 项",
        ]
        recommendations.append({
            "occupation_id": occ_id,
            "occupation_name": OCCUPATION_NAMES[occ_id],
            "match_score": score,
            "matched_skills": matched,
            "skills_to_improve": to_improve,
            "skills_to_verify": to_verify,
            "recommendation_reasons": reasons,
        })
        development_paths.append({
            "path_id": f"path_{occ_id}",
            "occupation_id": occ_id,
            "nodes": nodes,
        })

    return {"recommendations": recommendations, "development_paths": development_paths}
