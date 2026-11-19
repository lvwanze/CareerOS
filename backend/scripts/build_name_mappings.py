"""Generate derived Chinese name mappings from the frozen processed tables."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
REFERENCE = ROOT / "data" / "reference"

OCCUPATION_NAMES_ZH = {
    "Computer Systems Analysts": "计算机系统分析师",
    "Information Security Analysts": "信息安全分析师",
    "Computer and Information Research Scientists": "计算机与信息研究科学家",
    "Computer Network Support Specialists": "计算机网络支持专员",
    "Computer User Support Specialists": "计算机用户支持专员",
    "Computer Network Architects": "计算机网络架构师",
    "Database Administrators": "数据库管理员",
    "Database Architects": "数据库架构师",
    "Network and Computer Systems Administrators": "网络与计算机系统管理员",
    "Computer Programmers": "计算机程序员",
    "Software Developers": "软件开发人员",
    "Software Quality Assurance Analysts and Testers": "软件质量保证分析师与测试人员",
    "Web Developers": "Web开发人员",
    "Web and Digital Interface Designers": "Web与数字界面设计师",
    "Penetration Testers": "渗透测试工程师",
    "Blockchain Engineers": "区块链工程师",
    "Computer Systems Engineers/Architects": "计算机系统工程师/架构师",
    "Actuaries": "精算师",
    "Operations Research Analysts": "运筹分析师",
    "Statisticians": "统计学家",
    "Data Scientists": "数据科学家",
    "Business Intelligence Analysts": "商业智能分析师",
    "Bioinformatics Technicians": "生物信息技术员",
    "Project Management Specialists": "项目管理专员",
    "Management Analysts": "管理分析师",
    "Market Research Analysts and Marketing Specialists": "市场研究分析师与营销专员",
    "Budget Analysts": "预算分析师",
    "Financial Quantitative Analysts": "金融量化分析师",
}

SKILL_NAMES_ZH = {
    "Reading Comprehension": "阅读理解",
    "Active Listening": "积极倾听",
    "Writing": "写作",
    "Speaking": "口头表达",
    "Mathematics": "数学",
    "Science": "科学",
    "Critical Thinking": "批判性思维",
    "Active Learning": "主动学习",
    "Learning Strategies": "学习策略",
    "Monitoring": "监控",
    "Social Perceptiveness": "社会洞察力",
    "Coordination": "协调",
    "Persuasion": "说服",
    "Negotiation": "谈判",
    "Instructing": "指导",
    "Service Orientation": "服务导向",
    "Complex Problem Solving": "复杂问题解决",
    "Operations Analysis": "运营分析",
    "Technology Design": "技术设计",
    "Equipment Selection": "设备选型",
    "Installation": "安装",
    "Programming": "编程",
    "Operations Monitoring": "运营监控",
    "Operation and Control": "操作与控制",
    "Equipment Maintenance": "设备维护",
    "Troubleshooting": "故障排查",
    "Repairing": "维修",
    "Quality Control Analysis": "质量控制分析",
    "Judgment and Decision Making": "判断与决策",
    "Systems Analysis": "系统分析",
    "Systems Evaluation": "系统评估",
    "Time Management": "时间管理",
    "Management of Financial Resources": "财务资源管理",
    "Management of Material Resources": "物资资源管理",
    "Management of Personnel Resources": "人力资源管理",
}

OCCUPATION_FIELDS = ["occupation_id", "name_en", "name_zh", "source", "note"]
SKILL_FIELDS = ["skill_id", "name_en", "name_zh", "source", "note"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_mapping(filename: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with (REFERENCE / filename).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create_rows(
    source_rows: list[dict[str, str]],
    id_field: str,
    translations: dict[str, str],
) -> list[dict[str, str]]:
    missing = sorted({row["name"] for row in source_rows} - translations.keys())
    if missing:
        raise ValueError(f"Missing Chinese translations: {', '.join(missing)}")

    return [
        {
            id_field: row[id_field],
            "name_en": row["name"],
            "name_zh": translations[row["name"]],
            "source": "O*NET 31.0",
            "note": "人工整理中文译名",
        }
        for row in source_rows
    ]


def main() -> None:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    occupations = create_rows(
        read_csv(PROCESSED / "occupations.csv"), "occupation_id", OCCUPATION_NAMES_ZH
    )
    skills = create_rows(read_csv(PROCESSED / "skills.csv"), "skill_id", SKILL_NAMES_ZH)
    write_mapping("occupation_name_zh.csv", OCCUPATION_FIELDS, occupations)
    write_mapping("skill_name_zh.csv", SKILL_FIELDS, skills)
    print(f"生成完成：occupation_name_zh={len(occupations)}, skill_name_zh={len(skills)}")


if __name__ == "__main__":
    main()