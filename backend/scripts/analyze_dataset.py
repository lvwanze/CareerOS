"""analyze_dataset.py — 职业知识库数据分析脚本（M1 数据负责人：高帅龙）

职责：对 data/processed/ 的三张成品表做统计与质量分析，复现交付/答辩中引用的关键数字。
      只读成品 CSV，不修改任何数据；纯 Python 标准库，拿到包即可运行。

分析内容：
    1. 数据规模（职业/技能/关联行数、主键唯一性、孤立引用）
    2. 每个职业剩余技能数分布（min / 中位数 / 均值 / max）——回答代旭④
    3. importance / required_level 实际值域
    4. 职业间 Jaccard 相似度（平均、最相似 Top-5）——支撑「阈值 0.90 去重」的依据
    5. 孤立技能检测（在技能表中但无职业关联）

关键结论（2026-11-18 实测，供答辩引用）：
    - 每职业技能数：min=12，中位数=17，均值≈17.57，max=24
      → 不存在「只剩 2~3 个技能导致 Jaccard 虚高」的情况，阈值 0.90 无需下调、无需保下限
    - Jaccard 平均≈0.665；最高 Software Developers↔Blockchain Engineers≈0.941
      （16/17 个技能、交集 16，属两职业本身高度相似，非技能少造成）

运行：python scripts/analyze_dataset.py
依赖：Python 3 标准库（csv / pathlib / statistics），无需第三方包。
"""

import csv
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"


def load(name):
    with (DATA / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    occ = load("occupations.csv")
    skills = load("skills.csv")
    rel = load("occupation_skills.csv")
    occ_name = {r["occupation_id"]: r["name"] for r in occ}
    skill_name = {r["skill_id"]: r["name"] for r in skills}

    print("=" * 64)
    print("职业知识库数据分析报告")
    print("=" * 64)

    # 1. 规模与完整性
    occ_ids = [r["occupation_id"] for r in occ]
    skill_ids = [r["skill_id"] for r in skills]
    pairs = [(r["occupation_id"], r["skill_id"]) for r in rel]
    orphan = [p for p in pairs if p[0] not in occ_name or p[1] not in skill_name]
    print("\n【1】数据规模与完整性")
    print(f"  职业数 / 技能数 / 关联数 : {len(occ)} / {len(skills)} / {len(rel)}")
    print(f"  职业主键唯一 / 技能主键唯一: {len(set(occ_ids)) == len(occ_ids)} / {len(set(skill_ids)) == len(skill_ids)}")
    print(f"  关联对重复数              : {len(pairs) - len(set(pairs))}")
    print(f"  孤立引用数                : {len(orphan)}")

    # 2. 每职业剩余技能数分布
    by_occ = defaultdict(set)
    for r in rel:
        by_occ[r["occupation_id"]].add(r["skill_id"])
    counts = sorted(len(v) for v in by_occ.values())
    print("\n【2】IM>=3.0 筛选后每职业技能数分布")
    print(f"  min={min(counts)}  中位数={statistics.median(counts)}  均值={statistics.mean(counts):.2f}  max={max(counts)}")
    print("  技能最少的职业:")
    for oid in sorted(by_occ, key=lambda o: len(by_occ[o]))[:3]:
        print(f"    {occ_name.get(oid, oid):45s} {len(by_occ[oid])} 个")

    # 3. 评分值域
    imp = [float(r["importance"]) for r in rel]
    lvl = [int(r["required_level"]) for r in rel]
    print("\n【3】评分值域")
    print(f"  importance : {min(imp):.2f} ~ {max(imp):.2f}（O*NET 原始 IM 1~5，未归一化）")
    print(f"  required_level : {sorted(set(lvl))}（契约 0~4，实际 1~3）")

    # 4. Jaccard 相似度
    ids = list(by_occ)
    sims = []
    for a, b in combinations(ids, 2):
        sa, sb = by_occ[a], by_occ[b]
        jac = len(sa & sb) / len(sa | sb)
        sims.append((jac, a, b, len(sa), len(sb), len(sa & sb)))
    sims.sort(reverse=True)
    print("\n【4】职业间 Jaccard 相似度（基于技能集合）")
    print(f"  职业对数 : {len(sims)}")
    print(f"  平均 Jaccard : {statistics.mean(s[0] for s in sims):.3f}")
    print("  最相似 Top-5:")
    for jac, a, b, na, nb, inter in sims[:5]:
        print(f"    {occ_name.get(a, a)} ↔ {occ_name.get(b, b)}: {jac:.3f}"
              f"（技能数 {na}/{nb}，交集 {inter}）")
    print("  → 阈值 0.90 用于相似职业去重；最高相似度由职业本身相近造成，非技能少虚高。")

    # 5. 孤立技能
    linked = {r["skill_id"] for r in rel}
    unused = [(s["skill_id"], s["name"]) for s in skills if s["skill_id"] not in linked]
    print("\n【5】孤立技能（在技能表中但无职业关联）")
    for sid, name in unused:
        print(f"    {sid:28s} {name}")
    print(f"  共 {len(unused)} 个（保留作词表，用户填写不影响推荐）")

    print("\n" + "=" * 64)


if __name__ == "__main__":
    main()
