# -*- coding: utf-8 -*-
"""职业-技能匹配算法：数据加载、加权打分、Top-K 推荐。

本模块只依赖 pandas / numpy，不依赖 FastAPI，符合 docs/development.md
「training 通过稳定的算法调用接口向 service 提供推理能力」的约定。

对外入口
--------
recommend(profile, top_k=5, diversity_theta=0.90) -> list[dict]
    输入用户画像，返回按 match_score 降序排列的推荐结果列表。
    返回条数在 [0, top_k] 之间，不保证等于 top_k。

输出字段严格遵循 docs/data_contract.md：
    3.5 Recommendation：occupation_id / occupation_name / match_score /
        matched_skills / skills_to_improve / skills_to_verify /
        recommendation_reasons
    3.6 SkillGap：skill_id / current_level / required_level / gap / status
        （额外附带 skill_name，仅为前端展示，不改变契约）
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# backend/data/processed
# parents[0]=training  parents[1]=packages  parents[2]=backend
# 不硬编码绝对路径，换机器或换人 clone 都能跑
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# 模型版本号，供 service 层写入 RecommendResponse.model_version
MODEL_VERSION = "matcher-v1"

# ---- 算法超参：集中在这里，方便回归实验时调 ----
TOP_K_DEFAULT = 5
DIVERSITY_THETA = 0.90   # 两职业技能集合 Jaccard 超过该值，只保留分数高的那个
LEVEL_MIN = 0            # 用户自评等级下限
LEVEL_MAX = 4            # 用户自评等级上限（data_contract 2.2）

# 状态枚举，与 data_contract.md 3.6 一致
STATUS_MASTERED = "mastered"
STATUS_IMPROVE = "needs_improvement"
STATUS_VERIFY = "needs_verification"

# 能力证据枚举。契约 3.1 只写了 str、第 8 节把具体枚举列为待确认，
# 本模块先按下面这一版执行，等服务层定稿后同步。
#
# 归一化规则：先 strip + lower，再查白名单；
# 缺失 / null / 空串 / 纯空白 / 未知值，一律按 EVIDENCE_NONE 处理。
# 方向是「宁可判待验证」——无效值不能把技能误判成 mastered，
# 否则前端拼错一个词，用户就凭空多出一批「已达标」。
EVIDENCE_NONE = "none"
EVIDENCE_LEVELS = frozenset(
    {
        EVIDENCE_NONE,   # 无证据（默认）
        "self",          # 用户自述
        "course",        # 课程 / 培训
        "project",       # 项目经历
        "work",          # 工作 / 实习
        "certificate",   # 证书 / 认证
        "test",          # 客观测试
    }
)

# 模块级缓存：首次调用时装载，之后直接复用，避免每个请求都读盘
_CACHE: dict | None = None


# --------------------------------------------------------------------------
# 一、数据加载与预处理
# --------------------------------------------------------------------------
def _build_index(relations: pd.DataFrame, names: dict, skill_names: dict) -> dict:
    """从关联表构建打分索引，不读盘。

    抽出来的目的：service 层已经把三张表组装成 occupation_requirements 了，
    再让算法自己读一遍 CSV 就重复了。有了这个入口，两条路径共用同一套
    权重计算和切片逻辑，不会出现「离线评估一套、在线服务另一套」。

    Args:
        relations: 至少含 occupation_id / skill_id / importance / required_level
        names: occupation_id -> 职业名
        skill_names: skill_id -> 技能名
    """
    relations = relations.copy()
    relations["importance"] = relations["importance"].astype(float)
    relations["required_level"] = relations["required_level"].astype(int)
    relations["skill_name"] = relations["skill_id"].map(skill_names)

    # ---- 权重 w = importance_norm × idf ----
    # importance 归一化到 0~1：原始 O*NET IM 是 1~5，按 (IM-1)/4 压缩
    relations["importance_norm"] = (relations["importance"] - 1.0) / 4.0

    # IDF 用平滑写法 log((1+N)/(1+df))+1。
    # 若直接用 log(N/(1+df))，覆盖全部职业的通用技能会得到负值（约 -0.035），
    # 意味着"掌握这项技能反而扣分"，逻辑上不成立。
    n_occupation = relations["occupation_id"].nunique()
    skill_occurrence = relations.groupby("skill_id")["occupation_id"].nunique()
    idf = np.log((1 + n_occupation) / (1 + relations["skill_id"].map(skill_occurrence))) + 1.0

    relations["weight"] = relations["importance_norm"] * idf

    # 按重要度降序排一次，保证 reasons 优先取重要的技能
    relations = relations.sort_values(
        ["occupation_id", "weight"], ascending=[True, False]
    ).reset_index(drop=True)

    by_occupation = {oid: g for oid, g in relations.groupby("occupation_id")}
    skill_sets = {oid: set(g["skill_id"]) for oid, g in by_occupation.items()}

    return {
        "relations": relations,
        "by_occupation": by_occupation,
        "skill_sets": skill_sets,
        "names": names,
        "skill_names": skill_names,
    }

def _load_data() -> dict:
    """读入三张表并完成权重预计算，结果缓存在模块级变量 _CACHE 中。

    必须声明 global，否则函数内对 _CACHE 的赋值只会创建一个局部变量，
    模块级的 _CACHE 永远是 None，缓存形同虚设（且不会报错）。

    返回 dict：
        occupations  DataFrame  职业表
        skills       DataFrame  技能表
        relations    DataFrame  关联表（已附加 weight 列）
        by_occupation dict[str, DataFrame]  按职业预切分，避免每次重新 groupby
        skill_sets   dict[str, set[str]]    职业技能集合，用于 Jaccard 去重
        names        dict[str, str]         occupation_id -> 职业名
        skill_names  dict[str, str]         skill_id -> 技能名
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    logger.info("首次加载职业技能知识库：%s", DATA_DIR)

    # 职业表和技能表整表按字符串读，避免 SOC 码、ElementID 被数值化
    occupations = pd.read_csv(DATA_DIR / "occupations.csv", dtype=str)
    skills = pd.read_csv(DATA_DIR / "skills.csv", dtype=str)

    # 关联表只把两个 ID 列设为 str，数值列让 pandas 自行推断
    relations = pd.read_csv(
        DATA_DIR / "occupation_skills.csv",
        dtype={"occupation_id": str, "skill_id": str},
    )
    relations["importance"] = relations["importance"].astype(float)
    relations["required_level"] = relations["required_level"].astype(int)

    # 把技能名挂到关联表上，打分循环里直接取用，避免每行再去查字典
    skill_name_map = dict(zip(skills["skill_id"], skills["name"]))
    names_map = dict(zip(occupations["occupation_id"], occupations["name"]))

    _CACHE = _build_index(relations, names_map, skill_name_map)
    # 这两张原始表只有冒烟测试用来看 shape，算法本身不依赖，补在索引上
    _CACHE["occupations"] = occupations
    _CACHE["skills"] = skills

    logger.info(
        "知识库加载完成：%d 个职业 / %d 个技能 / %d 条关联",
        len(occupations),
        len(skills),
        len(_CACHE["relations"]),
    )
    return _CACHE


# --------------------------------------------------------------------------
# 二、单项技能的判定与达标度
# --------------------------------------------------------------------------
def _normalize_evidence(value) -> str:
    """把任意 evidence_level 入参归一成白名单里的值。

    Args:
        value: 原始入参，可能是 None、空串、带空白、大小写混杂或未知字符串。

    Returns:
        EVIDENCE_LEVELS 中的某一个值，无法识别时返回 EVIDENCE_NONE。

    未识别值只告警、不抛异常，这是本模块作为「被直接调用」时的防御：
    matcher 可能被脚本、离线任务、单元测试直接使用，不该因为一个证据字段
    就让整批计算中断。告警用于留痕，避免前端传错枚举值静默变成「无证据」。

    注意与 API 层的分工：self_level 的范围由 service 层 SkillInput 拦成 422，
    不会走到本函数；evidence_level 因契约枚举尚未冻结，API 层暂不做硬校验，
    未知值会落到这里归一为 none（HTTP 仍 200），因此本函数的宽容对外可见。
    待契约冻结后应在 schemas 层补 Literal，届时本函数只服务直接调用场景。
    """
    if value is None:
        return EVIDENCE_NONE
    text = str(value).strip().lower()
    if not text:
        return EVIDENCE_NONE
    if text in EVIDENCE_LEVELS:
        return text
    logger.warning("未知 evidence_level=%r，按无证据处理", value)
    return EVIDENCE_NONE


def _achievement(self_level: int, required_level: int) -> float:
    """技能达成度，取值 [0, 1]。

    超过要求时封顶为 1.0——多出来的能力不给额外加分，避免"刷级"刷高匹配度。
    """
    if required_level <= 0:
        return 1.0
    return min(self_level / required_level, 1.0)


def _status_of(self_level: int, required_level: int, evidence_level: str) -> str:
    """三档状态判定，注意顺序。

    1. 等级为 0（含未填写）：needs_improvement —— 无论有没有证据，能力都不够
    2. 有等级但证据缺失：needs_verification —— 「Self 说会，但拿不出东西」
    3. 等级达标：mastered
    4. 其余：needs_improvement

    若先判等级再判证据，则"自评 4 级但无证据"会落到 mastered，
    needs_verification 这一档几乎永远不会触发。
    """
    if self_level <= 0:
        return STATUS_IMPROVE
    if evidence_level == "none":
        return STATUS_VERIFY
    if self_level >= required_level:
        return STATUS_MASTERED
    return STATUS_IMPROVE


# --------------------------------------------------------------------------
# 三、单个职业打分
# --------------------------------------------------------------------------
def _score_occupation(group: pd.DataFrame, user_skills: dict) -> tuple[float, list]:
    """对一个职业的全部要求技能做加权求和，返回 (匹配分数, 差距明细列表)。

    match_score = Σ(w × 达标度) / Σw
    分母用「该职业挂载技能的权重和」，因此 1.0 是可达的（全部达标即为满分）。
    """
    numerator = 0.0
    denominator = 0.0
    gaps = []

    for row in group.itertuples(index=False):
        weight = row.weight
        denominator += weight

        self_level, evidence_level = user_skills.get(row.skill_id, (0, "none"))
        numerator += weight * _achievement(self_level, row.required_level)

        gaps.append(
            {
                "skill_id": row.skill_id,
                "skill_name": row.skill_name,
                "current_level": int(self_level),
                "required_level": int(row.required_level),
                "gap": int(max(0, row.required_level - self_level)),
                "status": _status_of(int(self_level), int(row.required_level), evidence_level),
            }
        )

    score = numerator / denominator if denominator > 0 else 0.0
    return score, gaps


def _jaccard(occupation_a: str, occupation_b: str, skill_sets: dict) -> float:
    """两个职业技能集合的 Jaccard 相似度，用于剔除高度同质的职业。"""
    set_a = skill_sets.get(occupation_a, set())
    set_b = skill_sets.get(occupation_b, set())
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _build_reasons(gaps: list, limit: int = 4) -> list:
    """生成推荐依据：优先说已达标的，其次说缺口大的。"""
    reasons = []
    for item in gaps:
        if item["status"] == STATUS_MASTERED and len(reasons) < 2:
            reasons.append(f"{item['skill_name']} 已达标")
    for item in gaps:
        if item["status"] == STATUS_IMPROVE and item["gap"] >= 2 and len(reasons) < limit:
            reasons.append(f"{item['skill_name']} 还差 {item['gap']} 级")
    return reasons


# --------------------------------------------------------------------------
# 四、对外入口
# --------------------------------------------------------------------------
def _normalize_profile(profile: dict, index: dict | None = None) -> dict:
    """把画像里的技能列表转成 {skill_id: (self_level, evidence_level)}。

    同时做三件事：等级校验、未知技能过滤、重复技能后写覆盖。

    index 由调用方传入时用它的技能白名单，避免为了校验再读一次盘；
    不传则回落到本地缓存。
    """
    data = index if index is not None else _load_data()
    known_skill_ids = set(data["skill_names"])

    raw_skills = profile.get("skills") or []
    user_skills = {}
    for item in raw_skills:
        skill_id = item.get("skill_id")
        if not skill_id:
            logger.warning("技能条目缺少 skill_id，已忽略：%r", item)
            continue
        if skill_id not in known_skill_ids:
            logger.warning("未知 skill_id，已忽略：%s", skill_id)
            continue

        self_level = int(item.get("self_level", 0))
        if not LEVEL_MIN <= self_level <= LEVEL_MAX:
            raise ValueError(
                f"技能 {skill_id} 的自评等级 {self_level} 超出允许范围 "
                f"[{LEVEL_MIN}, {LEVEL_MAX}]"
            )
        user_skills[skill_id] = (
            self_level,
            _normalize_evidence(item.get("evidence_level")),
        )

    return user_skills


def recommend_from_index(
    index: dict,
    profile: dict,
    top_k: int = TOP_K_DEFAULT,
    diversity_theta: float = DIVERSITY_THETA,
) -> list:
    """在给定索引上计算推荐，不读盘。

    index 由 _build_index 生成；service 层已把三张表组装好时，自己构一个
    同样的结构传进来即可，不必让算法再读一遍 CSV。
    返回结构与 recommend 完全一致。
    """
    data = index
    user_skills = _normalize_profile(profile, index)

    if top_k <= 0:
        return []

    scored = []
    for occupation_id, group in data["by_occupation"].items():
        score, gaps = _score_occupation(group, user_skills)
        scored.append((score, occupation_id, gaps))

    # 全精度排序，最后才 round，避免四舍五入后并列导致顺序不稳定
    scored.sort(key=lambda x: (-x[0], x[1]))

    picked_ids = []
    results = []
    for score, occupation_id, gaps in scored:
        if len(results) >= top_k:
            break
        # 相似职业去重：与已入选的任一职业 Jaccard 过高则跳过，
        # 否则 Software Developers 与 Blockchain Engineers 会同时占据前二
        if any(
            _jaccard(occupation_id, picked, data["skill_sets"]) > diversity_theta
            for picked in picked_ids
        ):
            continue

        picked_ids.append(occupation_id)
        results.append(
            {
                "occupation_id": occupation_id,
                "occupation_name": data["names"][occupation_id],
                "match_score": round(float(score), 3),
                "matched_skills": [
                    g["skill_id"] for g in gaps if g["status"] == STATUS_MASTERED
                ],
                "skills_to_improve": [
                    g["skill_id"] for g in gaps if g["status"] == STATUS_IMPROVE
                ],
                "skills_to_verify": [
                    g["skill_id"] for g in gaps if g["status"] == STATUS_VERIFY
                ],
                "recommendation_reasons": _build_reasons(gaps),
                "skill_gaps": gaps,
            }
        )

    logger.info(
        "推荐完成：输入 %d 项技能，返回 %d 个职业，最高分 %s",
        len(user_skills),
        len(results),
        results[0]["match_score"] if results else "N/A",
    )
    return results


def recommend(
    profile: dict,
    top_k: int = TOP_K_DEFAULT,
    diversity_theta: float = DIVERSITY_THETA,
) -> list:
    """根据用户画像推荐 Top-K 职业（读本地 data/processed，供离线使用）。

    参数
    ----
    profile : dict
        形如 {"user_id": "...", "skills": [{"skill_id": ..., "self_level": 3,
        "evidence_level": "project"}, ...]}
    top_k : int
        期望返回条数，默认 5。上界由调用方控制，算法内部不写死常量。
    diversity_theta : float
        相似职业剔除阈值，Jaccard 超过该值的职业只保留分数高的一个。
        默认 0.90。设为 >= 1.0 即关闭去重（任何两职业都不会超过 1.0）。

    返回
    ----
    list[dict]，每项包含 data_contract 3.5 规定的七个字段，外加 skill_gaps。

    条数约定：返回长度在 [0, top_k] 之间，**不保证等于 top_k**。
    去重后可选出的职业数量是有限的（theta=0.90 时最多 25 个），
    若 top_k 超过该上限则实际返回更少。调用方与前端必须按
    「最多 top_k 张卡片」渲染，不能写死 top_k。

    排序：按 match_score 降序；分数相同时按 occupation_id 升序，保证结果确定。

    在线服务请走 recommend_from_index，把已组装好的数据传进去，
    避免同一份数据被读两次。
    """
    return recommend_from_index(_load_data(), profile, top_k, diversity_theta)


# 公开别名：service 层要自己构建索引时用这个，不要直接 import 带下划线的名字
build_index = _build_index


__all__ = [
    "recommend",
    "recommend_from_index",
    "build_index",
    "MODEL_VERSION",
    "TOP_K_DEFAULT",
    "DIVERSITY_THETA",
    "EVIDENCE_LEVELS",
    "EVIDENCE_NONE",
]
