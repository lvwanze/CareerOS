"""build_dataset.py — 职业知识库构建脚本（M1 数据负责人：高帅龙）

职责：从 data/raw/onet31_csv/ 的 O*NET 31.0 原始数据，生成 data/processed/ 下三张正式表。
      这是 M1 私有工具，只由数据负责人运行；下游（算法、后端）只读成品 CSV，不运行本脚本。

五步加工流程：
    1. 读取原始 CSV（occupation_data / essential_skills / transferable_skills）
    2. 统一 ID：加 OCC-ONET- / SKILL-ONET- 前缀，保留 source / source_id
    3. 清洗：职业白名单筛选、IM >= 3.0 过滤、去重、去孤立 ID、缺失留空字符串
    4. 换算：IM/LV 双行透视成一行；importance 存原始 IM(1~5)、required_level = round(LV*4/7)
    5. 输出：UTF-8 无 BOM、逗号分隔、LF 换行、首行表头

确认口径（2026-11-18 冻结）：
    - importance 存原始 IM(1~5)，不归一化；归一化 (IM-1)/4 由算法层在内存做（赵帝臣 A1）
    - required_level = round(LV*4/7)，映射 0→0,1→1,2→1,3→2,4→2,5→3,6→3,7→4（赵帝臣 A3）
    - 不加新列：展示名沿用契约已有 name / category 字段（用户 2026-11-18 拍板，规避代旭 B3 多列抛错）
    - 职业白名单 28 个：23 个 15- 计算机数学类 + 5 个 13- 商业金融分析类（代旭 B6）
    - 技能两来源合并、按 skill_id 去重，category 写 essential / transferable（代旭 B7）
    - 只做 IM >= 3.0 入表筛选，不做「每职业前 12 个」截断（用户转述赵帝臣口径）
    - 字段严格遵循 data_contract.md 公共契约，不擅自增删改

运行：python scripts/build_dataset.py
依赖：Python 3 标准库（csv / pathlib），无需第三方包。

原始数据获取（干净 clone 复现，对应答辩验收清单 M1-P0-2）：
    data/raw/ 未纳入 Git（原始 O*NET 数据量较大）。在全新 clone 上复现前，
    先从官方下载以下三份 CSV，放到 data/raw/onet31_csv/：
      下载地址：https://www.onetcenter.org/dl_files/database/db_31_0_csv/
        - occupation_data.csv      (sha256 a09eae1d6609686e44e05b7290993a1c8b523d8ca224bc0eedc194c855c3ee02)
        - essential_skills.csv     (sha256 68c4d31d8c55077238395dca40cc4e6d32e6a608b5474bb8264b1f98ae415bd7)
        - transferable_skills.csv  (sha256 f17d0419e818a3bf2f55076510c76c4aef01cc8f5aee2670d2f44f6f44ac60f7)
    下载后用 `sha256sum data/raw/onet31_csv/*.csv` 核对，三项须与上面一致，
    否则脚本会产出不同的表。校验通过后运行 `python scripts/build_dataset.py`，
    产出三表应与 backend/data/manifest.json 登记的 sha256 逐字节一致
    （2026-11-26 实测复现：occupations 087a2484… / skills 59ca8b64… / relations 00044bd0…）。
"""

import csv
from pathlib import Path

# ---------------- 可配置参数（规则变更只改这里） ----------------
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "onet31_csv"
OUT = ROOT / "data" / "processed"

# 职业白名单（代旭 B6：23 个 15- 计算机数学类 + 5 个 13- 商业金融分析类，全部经核查有完整 IM/LV 评分）
OCCUPATION_CODES = [
    "15-1211.00", "15-1212.00", "15-1221.00", "15-1231.00", "15-1232.00",
    "15-1241.00", "15-1242.00", "15-1243.00", "15-1244.00", "15-1251.00",
    "15-1252.00", "15-1253.00", "15-1254.00", "15-1255.00", "15-1299.04",
    "15-1299.07", "15-1299.08", "15-2011.00", "15-2031.00", "15-2041.00",
    "15-2051.00", "15-2051.01", "15-2099.01",
    "13-1082.00", "13-1111.00", "13-1161.00", "13-2031.00", "13-2099.01",
]

IM_THRESHOLD = 3.0          # 数据层入表阈值（原始 IM 尺度 1~5）
LV_TO_LEVEL = lambda lv: round(float(lv) * 4 / 7)   # 0~7 → 0~4
OCC_PREFIX = "OCC-ONET-"
SKILL_PREFIX = "SKILL-ONET-"

OCC_FIELDS = ["occupation_id", "name", "description", "category", "source", "source_id"]
SKILL_FIELDS = ["skill_id", "name", "category", "description", "source", "source_id"]
REL_FIELDS = ["occupation_id", "skill_id", "importance", "required_level"]
# ---------------------------------------------------------------


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    # 步骤 1：读取原始数据
    occ_raw = read_csv(RAW / "occupation_data.csv")
    skill_files = [
        ("essential_skills.csv", "essential"),
        ("transferable_skills.csv", "transferable"),
    ]

    # 步骤 2 + 3：职业表（白名单筛选 + 统一 ID + 分类）
    occ_by_code = {r["O*NET-SOC Code"]: r for r in occ_raw}
    occ_rows = []
    for code in OCCUPATION_CODES:
        r = occ_by_code.get(code)
        if not r:
            continue
        category = "Computer and Mathematical" if code.startswith("15-") else "Business and Financial Operations"
        occ_rows.append({
            "occupation_id": OCC_PREFIX + code,
            "name": r["Title"],
            "description": r["Description"],
            "category": category,
            "source": "ONET",
            "source_id": code,
        })
    kept_occ = {r["occupation_id"] for r in occ_rows}

    # 步骤 2 + 3：技能表（两来源合并 + 按 skill_id 去重 + 统一 ID）
    skill_rows, seen_skills = [], {}
    skill_category = {}
    for fn, cat in skill_files:
        for r in read_csv(RAW / fn):
            eid = r["Element ID"]
            sid = SKILL_PREFIX + eid
            skill_category[eid] = cat
            if sid in seen_skills:
                continue
            seen_skills[sid] = True
            skill_rows.append({
                "skill_id": sid,
                "name": r["Element Name"],
                "category": cat,                       # essential / transferable（代旭 B7）
                "description": "",                     # O*NET 无技能描述，契约非必填 → 留空字符串
                "source": "ONET",
                "source_id": eid,
            })

    # 步骤 3 + 4：关联表（透视 IM/LV + 阈值过滤 + 换算 + 去孤立）
    scores = {}   # (occ_code, element_id) -> {"IM":..., "LV":...}
    for fn, _ in skill_files:
        for r in read_csv(RAW / fn):
            code, eid, scale, val = (r["O*NET-SOC Code"], r["Element ID"],
                                     r["Scale ID"], r["Data Value"])
            if code not in OCCUPATION_CODES or not val:
                continue
            scores.setdefault((code, eid), {})[scale] = float(val)

    rel_rows = []
    for (code, eid), sc in scores.items():
        if "IM" not in sc or "LV" not in sc:
            continue                                   # 长表：只保留双评分齐全的组合
        if sc["IM"] < IM_THRESHOLD:
            continue                                   # IM >= 3.0 才入表
        oid, sid = OCC_PREFIX + code, SKILL_PREFIX + eid
        if oid not in kept_occ or sid not in seen_skills:
            continue                                   # 去孤立 ID
        rel_rows.append({
            "occupation_id": oid,
            "skill_id": sid,
            "importance": f"{sc['IM']:.2f}",           # 原始 IM(1~5)，不做归一化
            "required_level": LV_TO_LEVEL(sc["LV"]),   # 0~4 整数
        })

    # 步骤 5：输出三张表
    write_csv(OUT / "occupations.csv", OCC_FIELDS, occ_rows)
    write_csv(OUT / "skills.csv", SKILL_FIELDS, skill_rows)
    write_csv(OUT / "occupation_skills.csv", REL_FIELDS, rel_rows)

    print(f"生成完成：occupations={len(occ_rows)}, skills={len(skill_rows)}, relations={len(rel_rows)}")
    print(f"importance 范围: {min(float(r['importance']) for r in rel_rows):.2f} ~ "
          f"{max(float(r['importance']) for r in rel_rows):.2f} (原始 IM 1~5)")
    print(f"required_level 分布: {sorted(set(r['required_level'] for r in rel_rows))}")


if __name__ == "__main__":
    main()
