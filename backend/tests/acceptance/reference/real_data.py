"""真实数据加载层：从高帅龙的 M1 交付包读取职业-技能知识库。

数据口径（来自 manifest.json 的 confirmed_decisions / cleaning_rules）：
  - importance 存 O*NET 原始 IM(1~5)，算法层归一化 (IM-1)/4（赵帝臣 A1）
  - required_level 由 LV 按 round(LV*4/7) 映射，实际值域 1~3
  - ID 全程按字符串读取（OCC-ONET- / SKILL-ONET- 前缀）

本模块让参考算法跑在真实数据上，从而让测试样本换成真实 ID 后仍然有效。
它仍不是赵帝臣的正式算法——只替代了原来硬编码的虚拟知识库。
"""

import csv
import io
import os
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TESTS_DIR.parent


# manifest 相对数据根的位置：
#   - 独立 M1 交付包：manifest 与 data/ 同级，"manifest.json"
#   - 后端仓库：backend/ 为根，manifest 在 data/ 下，"data/manifest.json"
#     （manifest 内部 path 字段均相对该根，故 DATASET_ROOT 取 backend/）
MANIFEST_REL = "manifest.json"


def discover_dataset_root():
    """按优先级定位数据根，返回使 manifest 内 path 字段可相对解析的目录。

    支持两种布局：
      1. 独立 M1 交付包：根目录含 manifest.json + data/processed/；
      2. CareerOS 后端仓库：backend/ 含 data/manifest.json + packages/，
         manifest 与三表都在 backend/data/ 下，path 字段相对 backend/。
    优先级：环境变量 > 后端仓库 data/ > 向上找 dataset/M1_*。
    """
    global MANIFEST_REL
    env_root = os.environ.get("CAREEROS_DATASET_ROOT")
    if env_root:
        root = Path(env_root).expanduser()
        if (root / "manifest.json").is_file():
            MANIFEST_REL = "manifest.json"
            return root
        if (root / "data" / "manifest.json").is_file():
            MANIFEST_REL = "data/manifest.json"
            return root
        raise FileNotFoundError(
            f"CAREEROS_DATASET_ROOT 指向的目录缺少 manifest.json: {root}"
        )
    start = Path(__file__).resolve().parents[1]
    parents = [start] + list(start.parents)[:6]
    # 布局 2：后端仓库（测试位于 backend/tests/acceptance/ 时，向上找 backend/）
    for base in parents:
        if (base / "data" / "manifest.json").is_file() and (base / "packages").is_dir():
            MANIFEST_REL = "data/manifest.json"
            return base
    # 布局 1：独立 M1 交付包
    for base in parents:
        candidates = sorted(
            (base / "dataset").glob("M1_职业知识库_数据交付_v*"),
            reverse=True,
        )
        for root in candidates:
            if (root / "manifest.json").is_file():
                MANIFEST_REL = "manifest.json"
                return root
    raise FileNotFoundError(
        "未找到数据交付包：向上 6 级内既无后端仓库 backend/data/manifest.json，"
        "也无 dataset/M1_职业知识库_数据交付_v*/manifest.json。"
        "请设置 CAREEROS_DATASET_ROOT 指向数据根。"
    )


DATASET_ROOT = discover_dataset_root()
MANIFEST_PATH = DATASET_ROOT / MANIFEST_REL
PROCESSED_DIR = DATASET_ROOT / "data" / "processed"


def _read_csv(filename):
    """按契约口径读 CSV：UTF-8 无 BOM、ID 列保持字符串。"""
    path = PROCESSED_DIR / filename
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_knowledge_base():
    """构建 {职业ID: {技能ID: (required_level, normalized_importance)}}。"""
    occupations = _read_csv("occupations.csv")
    skills = _read_csv("skills.csv")
    relations = _read_csv("occupation_skills.csv")

    occupation_skills = {row["occupation_id"]: {} for row in occupations}
    for row in relations:
        occ_id = row["occupation_id"]
        if occ_id not in occupation_skills:
            continue
        # A1：原始 IM(1~5) 在算法层归一化为 (IM-1)/4
        importance = round((float(row["importance"]) - 1.0) / 4.0, 4)
        occupation_skills[occ_id][row["skill_id"]] = (
            int(row["required_level"]), importance
        )

    occupation_names = {row["occupation_id"]: row["name"] for row in occupations}
    skill_names = {row["skill_id"]: row["name"] for row in skills}
    return occupation_skills, occupation_names, skill_names


OCCUPATION_SKILLS, OCCUPATION_NAMES, SKILL_NAMES = load_knowledge_base()
