"""clean_recruitment.py — 招聘岗位样本清洗与合并脚本（市场分析数据）

职责：把两个来源的招聘样本清洗成统一 schema，合并输出 data/processed/job_postings.csv，
      并把拉勾的 JD 正文单独存一份 job_descriptions.csv（后续抽技能用）。

数据来源（两个，互补）：
    一、拉勾招聘技术岗（21,320 条，技术岗社招，薪资/学历/经验/JD 正文全满）
        来源：和鲸社区数据集「【拉勾招聘】2万多条技术岗位的招聘数据」，作者 Blues，
        id=659e362916c9b1fb045bf0d8，单文件 24.9 MB，原文件为论坛公开附件转载。
        时间跨度 2022-08-05 ~ 2024-01-07。
    二、校招宝 recruit-hub（24,000 条原始，全行业校招，时间较新）
        来源：github.com/kknee-dev/recruit-hub 的 data/ 目录，三期快照
        2026-09-03 / 2026-10-01 / 2026-11-01，已脱敏、不含个人信息。

    两者互补：拉勾字段全但年份偏旧、只覆盖技术岗；recruit-hub 时间新但无技能无经验。
    合并后按 platform 字段区分，统计时可以分开算，也可以合起来算总量。

清洗步骤（每步 log_step 留痕）：
    1. 读两源原始 CSV
    2. 各自去重：recruit-hub 按岗位链接；拉勾按 positionId，保留最新一条
    3. 剔除抓取错位脏行（岗位名落成「工作地址」「公司信息」）
    4. 统一字段：城市、学历、薪资、岗位大类、地域、批次
    5. 合并两源
    6. 输出主表 + JD 表 + manifest

字段口径说明：
    data_contract.md V1.0 只列了 JobPosting 这个名字（§6 后续扩展模型），没有定义字段。
    本表字段是建议稿，需走 ADR-006 变更流程由契约负责人确认后才能冻结。
    在确认前，本表标记为 draft，不得被算法或后端当正式契约读入。

运行：python scripts/clean_recruitment.py
依赖：仅 Python 3 标准库（csv / json / hashlib / re / pathlib），无需第三方包。
"""

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

# ---------------- 可配置参数（规则变更只改这里） ----------------
ROOT = Path(__file__).resolve().parent.parent
RECRUIT_DIR = ROOT / "data" / "raw" / "recruit_hub"
LAGOU_DIR = ROOT / "data" / "raw" / "lagou"
OUT = ROOT / "data" / "processed"
OUT_FILE = OUT / "job_postings.csv"
DESCRIPTIONS_FILE = OUT / "job_descriptions.csv"
MANIFEST_FILE = OUT / "job_postings.manifest.json"
CONTRACT_VERSION = "V1.0"
DATASET_VERSION = "0.2.0-draft"

RECRUIT_FILES = [
    "jobs-2026-09-03.csv",
    "jobs-2026-10-01.csv",
    "jobs-1101.csv",
]
LAGOU_FILE = "lagou_raw.csv"

# 输出列顺序即契约顺序，下游按位置校验，不得随意调整
COLUMNS = [
    "job_id",
    "platform",
    "source_ref",
    "position_name",
    "job_category",
    "job_subcategory",
    "company_name",
    "company_size",
    "industry",
    "city",
    "region",
    "education",
    "work_year",
    "salary_min",
    "salary_max",
    "batch",
    "publish_date",
    "has_jd",
]

DETAIL_COLUMNS = ["job_id", "position_detail"]

# 抓取错位产生的伪岗位名，不是真实岗位
DIRTY_POSITIONS = {"", "工作地址", "公司信息", "公司简介", "职位描述", "岗位职责"}

OVERSEAS_MARKERS = (
    "新加坡", "马来西亚", "澳大利亚", "菲律宾", "印度尼西亚", "印尼",
    "日本", "韩国", "美国", "英国", "德国", "越南", "泰国", "香港", "澳门", "台北",
)

PROVINCE_PREFIXES = (
    "黑龙江省", "内蒙古自治区", "广西壮族自治区", "宁夏回族自治区", "新疆维吾尔自治区", "西藏自治区",
    "四川省", "广东省", "江苏省", "浙江省", "山东省", "河南省", "湖北省", "湖南省", "陕西省",
    "安徽省", "福建省", "江西省", "河北省", "山西省", "辽宁省", "吉林省", "甘肃省", "青海省",
    "云南省", "贵州省", "海南省",
)

# recruit-hub 的岗位大类：按顺序命中，先数据后技术、先管培后职能
CATEGORY_RULES = [
    ("数据", ("数据分析", "数据开发", "大数据", "数据挖掘", "数据仓库", "数仓", "bi", "算法", "机器学习", "人工智能")),
    ("技术", ("开发", "工程师", "程序员", "前端", "后端", "全栈", "测试", "运维", "架构", "软件", "嵌入式", "硬件", "电子", "电气", "机械", "结构", "工艺",
             "技术员", "信息技术", "机电", "设备", "维修", "自动化", "通信", "it")),
    ("产品", ("产品经理", "产品专员", "产品管培")),
    ("设计", ("设计", "美术", "视觉", "ui", "ux")),
    ("管培生", ("管培", "培训生", "储备干部", "trainee", "intern", "实习生", "校园大使")),
    ("职能", ("人力", "hr", "人事", "财务", "会计", "审计", "法务", "法律", "合规", "行政", "采购", "供应链", "物流", "仓储", "品控", "质量",
             "安全", "环保", "党建", "纪检", "文员", "统计", "劳资", "综合管理")),
    ("市场运营", ("市场", "运营", "营销", "销售", "品牌", "商务", "客户", "业务经理", "购销")),
]

# 拉勾的 bigcategory 本身就是细分方向，直接映射到统一大类
LAGOU_CATEGORY_MAP = {
    "后端开发": "技术",
    "前端开发": "技术",
    "移动开发": "技术",
    "测试": "技术",
    "运维": "技术",
    "人工智能": "数据",
    "大数据": "数据",
    "数据分析": "数据",
}

SALARY_FLOOR = 1000        # 月薪下限，低于此视为解析异常
SALARY_CEILING = 200000    # 月薪上限，高于此视为解析异常
WORK_DAYS_PER_MONTH = 22   # 日薪折算月薪的天数


def log_step(step: str, before: int, after: int) -> None:
    """打印一步清洗的前后行数，让清洗过程留痕可复核。变化为负表示这一步丢了行。"""
    changed = after - before
    print(f"[{step}] {before:,} -> {after:,}（变化 {changed:+,}）")


def read_csv_file(path: Path) -> list:
    """读一个 CSV，返回字典列表。原始文件可能带 BOM，用 utf-8-sig 读。"""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_job_id(platform: str, key: str) -> str:
    """用来源前缀 + 去重键哈希做稳定 ID，重跑脚本 ID 不变。"""
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    prefix = "JP-LG" if platform == "lagou" else "JP-RH"
    return f"{prefix}-{digest}"


def normalize_city(raw: str) -> str:
    """城市标准化：去省名前缀、多城市取首个、· 分隔取末段。"""
    text = (raw or "").strip()
    if not text:
        return ""
    text = text.replace("，", ",").split(",")[0].strip()
    if "·" in text:
        text = text.split("·")[-1].strip()
    for prefix in PROVINCE_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    return text


def detect_region(city: str, raw_city: str = "") -> str:
    """标出大陆还是境外。境外样本保留，但不混进大陆口径的统计。"""
    combined = f"{city}{raw_city}"
    if any(marker in combined for marker in OVERSEAS_MARKERS):
        return "overseas"
    return "mainland"


def normalize_education(raw: str) -> str:
    """学历收敛到 博士/硕士/本科/大专/不限 五档，认不出的留空。"""
    text = (raw or "").strip()
    if not text:
        return ""
    if "博士" in text:
        return "博士"
    if "硕士" in text or "研究生" in text:
        return "硕士"
    if "本科" in text:
        return "本科"
    if "大专" in text or "专科" in text or "高职" in text:
        return "大专"
    if "不限" in text or "无要求" in text:
        return "不限"
    return ""


def parse_salary(raw: str) -> tuple:
    """薪资折算成月薪（元），解析不出返回 (None, None)，不做猜测性补值。"""
    text = (raw or "").strip().lower().replace(" ", "").replace("，", "-")
    text = text.split("·")[0]          # 拉勾的「20k-40k·13薪」只取月薪部分
    if not text or text in {"面议", "薪资面议", "待遇面议", "-", "/"}:
        return None, None

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(k|千|万)?\s*[-~至到]\s*(\d+(?:\.\d+)?)\s*(k|千|万)?",
        text,
    )
    if not match:
        return None, None

    low = float(match.group(1))
    high = float(match.group(3))
    unit = match.group(2) or match.group(4) or ""

    if unit in {"k", "千"}:
        low, high = low * 1000, high * 1000
    elif unit == "万":
        low, high = low * 10000, high * 10000

    if "天" in text:
        low, high = low * WORK_DAYS_PER_MONTH, high * WORK_DAYS_PER_MONTH
    elif "年" in text:
        low, high = low / 12, high / 12

    low, high = int(round(low)), int(round(high))
    if low < SALARY_FLOOR or high > SALARY_CEILING or low > high:
        return None, None
    return low, high


def classify_position(title: str) -> str:
    """按岗位名关键词映射到岗位大类，未命中的归「其他」。"""
    text = (title or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return "其他"


def clean_recruit_row(row: dict) -> dict:
    """recruit-hub 一行 → 统一 schema 一行。"""
    raw_city = (row.get("city") or "").strip()
    city = normalize_city(raw_city)
    salary_min, salary_max = parse_salary(row.get("salary"))
    url = (row.get("source_url") or "").strip()
    key = url or f"{(row.get('company') or '').strip()}|{(row.get('position') or '').strip()}|{raw_city}"
    position = (row.get("position") or "").strip()
    return {
        "job_id": build_job_id("recruit_hub", key),
        "platform": "recruit_hub",
        "source_ref": key,
        "position_name": position,
        "job_category": classify_position(position),
        "job_subcategory": "",
        "company_name": (row.get("company") or "").strip(),
        "company_size": "",
        "industry": (row.get("industry") or "").strip(),
        "city": city,
        "region": detect_region(city, raw_city),
        "education": normalize_education(row.get("education")),
        "work_year": "",
        "salary_min": "" if salary_min is None else salary_min,
        "salary_max": "" if salary_max is None else salary_max,
        "batch": (row.get("batch") or "").strip(),
        "publish_date": (row.get("publish_date") or "").strip(),
        "has_jd": "0",
    }


def clean_lagou_row(row: dict) -> dict:
    """拉勾一行 → 统一 schema 一行。"""
    city = normalize_city(row.get("city"))
    salary_min, salary_max = parse_salary(row.get("salary"))
    position_id = (row.get("positionId") or "").strip()
    bigcategory = (row.get("bigcategory") or "").strip()
    created = (row.get("createTime") or "").strip()
    return {
        "job_id": build_job_id("lagou", position_id),
        "platform": "lagou",
        "source_ref": position_id,
        "position_name": (row.get("positionName") or "").strip(),
        "job_category": LAGOU_CATEGORY_MAP.get(bigcategory, "其他"),
        "job_subcategory": bigcategory,
        "company_name": (row.get("companyFullName") or "").strip(),
        "company_size": (row.get("companySize") or "").strip(),
        "industry": (row.get("industryField") or "").strip(),
        "city": city,
        "region": detect_region(city),
        "education": normalize_education(row.get("education")),
        "work_year": (row.get("workYear") or "").strip(),
        "salary_min": "" if salary_min is None else salary_min,
        "salary_max": "" if salary_max is None else salary_max,
        "batch": (row.get("jobNature") or "").strip(),
        "publish_date": created[:10],
        "has_jd": "1",
    }


def write_csv(path: Path, columns: list, rows: list) -> None:
    """写成品表：UTF-8 无 BOM、逗号分隔、LF 换行。"""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_of(path: Path) -> str:
    """算文件指纹，供 manifest 溯源。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_recruit_hub() -> list:
    """读 recruit-hub 三期并去重、剔脏行，返回统一 schema 行。"""
    raw_rows = []
    for name in RECRUIT_FILES:
        part = read_csv_file(RECRUIT_DIR / name)
        print(f"  读取 {name}: {len(part):,} 行")
        raw_rows.extend(part)
    print(f"[来源一 recruit-hub] 三期合计 {len(raw_rows):,} 行")

    seen = {}
    for row in raw_rows:
        url = (row.get("source_url") or "").strip()
        key = url or f"{(row.get('company') or '').strip()}|{(row.get('position') or '').strip()}"
        seen.setdefault(key, row)
    log_step("  按岗位链接去重", len(raw_rows), len(seen))

    rows = [row for row in seen.values() if (row.get("position") or "").strip() not in DIRTY_POSITIONS]
    log_step("  剔除抓取错位脏行", len(seen), len(rows))
    return [clean_recruit_row(row) for row in rows]


def load_lagou() -> tuple:
    """读拉勾并去重，返回（统一 schema 行，JD 正文行）。"""
    raw_rows = read_csv_file(LAGOU_DIR / LAGOU_FILE)
    print(f"[来源二 lagou] 原始 {len(raw_rows):,} 行")

    latest = {}
    for row in raw_rows:
        key = (row.get("positionId") or "").strip()
        if not key:
            continue
        current = latest.get(key)
        if current is None or (row.get("createTime") or "") > (current.get("createTime") or ""):
            latest[key] = row
    log_step("  按 positionId 去重（保留最新）", len(raw_rows), len(latest))

    cleaned = [clean_lagou_row(row) for row in latest.values()]
    descriptions = [
        {"job_id": build_job_id("lagou", (row.get("positionId") or "").strip()),
         "position_detail": (row.get("positionDetail") or "").strip()}
        for row in latest.values()
    ]
    return cleaned, descriptions


def main() -> None:
    """串起全部清洗步骤，输出主表、JD 表和 manifest。"""
    recruit_rows = load_recruit_hub()
    lagou_rows, descriptions = load_lagou()

    merged = recruit_rows + lagou_rows
    log_step("3 合并两源", len(merged), len(merged))

    assert len({row["job_id"] for row in merged}) == len(merged), "job_id 必须唯一"

    mainland = [row for row in merged if row["region"] == "mainland"]
    salary_ok = [row for row in merged if row["salary_min"] != ""]
    edu_ok = [row for row in merged if row["education"] != ""]
    year_ok = [row for row in merged if row["work_year"] != ""]
    jd_ok = [row for row in merged if row["has_jd"] == "1"]
    print(
        f"[4 合并后统计] 总 {len(merged):,}（大陆 {len(mainland):,} / 境外 {len(merged) - len(mainland):,}）；"
        f"薪资 {len(salary_ok):,}（{len(salary_ok) / len(merged):.1%}）、"
        f"学历 {len(edu_ok):,}（{len(edu_ok) / len(merged):.1%}）、"
        f"年限 {len(year_ok):,}（{len(year_ok) / len(merged):.1%}）、"
        f"JD {len(jd_ok):,}（{len(jd_ok) / len(merged):.1%}）"
    )

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_FILE, COLUMNS, merged)
    write_csv(DESCRIPTIONS_FILE, DETAIL_COLUMNS, descriptions)
    print(f"写出 {OUT_FILE.name}: {len(merged):,} 行 / {len(COLUMNS)} 列")
    print(f"写出 {DESCRIPTIONS_FILE.name}: {len(descriptions):,} 行")

    by_platform = Counter(row["platform"] for row in merged)
    manifest = {
        "dataset": "CareerOS Job Postings Sample",
        "version": DATASET_VERSION,
        "status": "draft",
        "contract_version": CONTRACT_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sources": [
            {
                "platform": "recruit_hub",
                "name": "校招宝 recruit-hub 开源数据集",
                "repo": "https://github.com/kknee-dev/recruit-hub",
                "files": RECRUIT_FILES,
                "time_range": "2026-08-28 ~ 2026-10-30",
                "license_note": "聚合自企业公开校招公告与招聘平台，已脱敏；原仓库声明仅作技术演示与检索研究",
            },
            {
                "platform": "lagou",
                "name": "和鲸社区「【拉勾招聘】2万多条技术岗位的招聘数据」",
                "url": "https://www.heywhale.com/mw/dataset/659e362916c9b1fb045bf0d8",
                "author": "Blues",
                "files": [LAGOU_FILE],
                "time_range": "2022-08-05 ~ 2024-01-07",
                "license_note": "公开数据集，原页面注明可自由下载使用，建议标注来源（和鲸社区 / 拉勾招聘）",
            },
        ],
        "row_counts": {
            "recruit_hub": by_platform.get("recruit_hub", 0),
            "lagou": by_platform.get("lagou", 0),
            "total": len(merged),
            "mainland": len(mainland),
            "overseas": len(merged) - len(mainland),
            "with_salary": len(salary_ok),
            "with_education": len(edu_ok),
            "with_work_year": len(year_ok),
            "with_jd": len(jd_ok),
            "descriptions": len(descriptions),
        },
        "columns": COLUMNS,
        "sha256": {
            OUT_FILE.name: sha256_of(OUT_FILE),
            DESCRIPTIONS_FILE.name: sha256_of(DESCRIPTIONS_FILE),
        },
        "known_gaps": [
            "两源时间不重叠：拉勾 2022-08~2024-01、recruit-hub 2026-08~2026-10，跨源趋势对比需按平台分组",
            "拉勾无技能标签字段，但 JD 正文 100% 有值，可做关键词抽取",
            "recruit-hub 无工作经验字段，合并后该列仅拉勾源有值",
            "字段为建议稿，待 data_contract.md 走 ADR-006 确认",
        ],
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写出 {MANIFEST_FILE.name}")

    print("\n--- 维度分布（大陆样本）---")
    print("平台:", by_platform.most_common())
    print("城市前 10:", Counter(row["city"] for row in mainland).most_common(10))
    print("岗位大类:", Counter(row["job_category"] for row in mainland).most_common())
    print("学历:", Counter(row["education"] for row in mainland).most_common())
    print("经验:", Counter(row["work_year"] for row in mainland).most_common())


if __name__ == "__main__":
    main()
