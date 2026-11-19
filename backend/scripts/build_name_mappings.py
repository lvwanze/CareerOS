#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : build_name_mappings.py
# @Path       : backend/scripts/build_name_mappings.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-19 11:25:00
# @Version    : v1.0.0
"""生成并校验中英名称映射表。

用法：
    python scripts/build_name_mappings.py           # 按源表顺序重写两份 CSV
    python scripts/build_name_mappings.py --check   # 只校验，缺一条就非零退出

映射的内置在这里而不是只读 CSV，是为了「clone 下来一条命令就能重建」。
校验时用 ID 对齐，不用英文名 —— 源表改名时能立刻报出来，不会静默错配。
"""
import argparse
import csv
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BACKEND_DIR / "data" / "processed"
MAP_DIR = BACKEND_DIR / "data" / "mappings"

SKILL_NAME_ZH = {
    "SKILL-ONET-2.A.1.a": "阅读理解",
    "SKILL-ONET-2.A.1.b": "积极倾听",
    "SKILL-ONET-2.A.1.c": "写作",
    "SKILL-ONET-2.A.1.d": "口语表达",
    "SKILL-ONET-2.A.1.e": "数学",
    "SKILL-ONET-2.A.1.f": "科学",
    "SKILL-ONET-2.A.2.a": "批判性思维",
    "SKILL-ONET-2.A.2.b": "主动学习",
    "SKILL-ONET-2.A.2.c": "学习策略",
    "SKILL-ONET-2.A.2.d": "过程监控",
    "SKILL-ONET-2.B.1.a": "社会洞察力",
    "SKILL-ONET-2.B.1.b": "协调能力",
    "SKILL-ONET-2.B.1.c": "说服能力",
    "SKILL-ONET-2.B.1.d": "谈判能力",
    "SKILL-ONET-2.B.1.e": "教学指导",
    "SKILL-ONET-2.B.1.f": "服务导向",
    "SKILL-ONET-2.B.2.i": "复杂问题解决",
    "SKILL-ONET-2.B.3.a": "运营分析",
    "SKILL-ONET-2.B.3.b": "技术设计",
    "SKILL-ONET-2.B.3.c": "设备选型",
    "SKILL-ONET-2.B.3.d": "安装调试",
    "SKILL-ONET-2.B.3.e": "编程",
    "SKILL-ONET-2.B.3.g": "运营监控",
    "SKILL-ONET-2.B.3.h": "运行控制",
    "SKILL-ONET-2.B.3.j": "设备维护",
    "SKILL-ONET-2.B.3.k": "故障排查",
    "SKILL-ONET-2.B.3.l": "维修",
    "SKILL-ONET-2.B.3.m": "质量控制分析",
    "SKILL-ONET-2.B.4.e": "判断与决策",
    "SKILL-ONET-2.B.4.g": "系统分析",
    "SKILL-ONET-2.B.4.h": "系统评估",
    "SKILL-ONET-2.B.5.a": "时间管理",
    "SKILL-ONET-2.B.5.b": "财务资源管理",
    "SKILL-ONET-2.B.5.c": "物资资源管理",
    "SKILL-ONET-2.B.5.d": "人力资源调配",
}

OCCUPATION_NAME_ZH = {
    "OCC-ONET-15-1211.00": "计算机系统分析师",
    "OCC-ONET-15-1212.00": "信息安全分析师",
    "OCC-ONET-15-1221.00": "计算机与信息研究科学家",
    "OCC-ONET-15-1231.00": "计算机网络支持专员",
    "OCC-ONET-15-1232.00": "计算机用户支持专员",
    "OCC-ONET-15-1241.00": "计算机网络架构师",
    "OCC-ONET-15-1242.00": "数据库管理员",
    "OCC-ONET-15-1243.00": "数据库架构师",
    "OCC-ONET-15-1244.00": "网络与计算机系统管理员",
    "OCC-ONET-15-1251.00": "计算机程序员",
    "OCC-ONET-15-1252.00": "软件开发工程师",
    "OCC-ONET-15-1253.00": "软件质量保证分析师与测试员",
    "OCC-ONET-15-1254.00": "Web 开发工程师",
    "OCC-ONET-15-1255.00": "Web 与数字界面设计师",
    "OCC-ONET-15-1299.04": "渗透测试工程师",
    "OCC-ONET-15-1299.07": "区块链工程师",
    "OCC-ONET-15-1299.08": "计算机系统工程师/架构师",
    "OCC-ONET-15-2011.00": "精算师",
    "OCC-ONET-15-2031.00": "运筹分析师",
    "OCC-ONET-15-2041.00": "统计学家",
    "OCC-ONET-15-2051.00": "数据科学家",
    "OCC-ONET-15-2051.01": "商业智能分析师",
    "OCC-ONET-15-2099.01": "生物信息学技术员",
    "OCC-ONET-13-1082.00": "项目管理专员",
    "OCC-ONET-13-1111.00": "管理分析师",
    "OCC-ONET-13-1161.00": "市场研究分析师与营销专员",
    "OCC-ONET-13-2031.00": "预算分析师",
    "OCC-ONET-13-2099.01": "金融量化分析师",
}


def load_source_names(filename: str, key_column: str) -> dict[str, str]:
    """读源表的 {id: 英文名}，作为重建映射时的 name_en 列。"""
    with (PROCESSED_DIR / filename).open(encoding="utf-8", newline="") as file:
        return {row[key_column]: row["name"] for row in csv.DictReader(file)}


def write_mapping(filename: str, key_column: str, source_names: dict[str, str], mapping: dict[str, str]) -> str:
    path = MAP_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([key_column, "name_en", "name_zh"])
        for key_value in sorted(source_names):
            writer.writerow([key_value, source_names[key_value], mapping[key_value]])
    return f"已写入 {path.name}：{len(source_names)} 条"


def check_coverage(label: str, source_names: dict[str, str], mapping: dict[str, str]) -> bool:
    """按 ID 比对覆盖率，打印缺口，返回是否全对上。"""
    missing = sorted(set(source_names) - set(mapping))
    extra = sorted(set(mapping) - set(source_names))
    matched = len(set(source_names) & set(mapping))
    print(f"{label}: {matched}/{len(source_names)} matched")
    if missing:
        print(f"  缺少映射: {missing}")
    if extra:
        print(f"  多余条目: {extra}")
    return not missing and not extra


def main() -> None:
    parser = argparse.ArgumentParser(description="生成或校验中英名称映射表")
    parser.add_argument("--check", action="store_true", help="只校验不写文件")
    args = parser.parse_args()

    skill_names = load_source_names("skills.csv", "skill_id")
    occupation_names = load_source_names("occupations.csv", "occupation_id")

    if args.check:
        skill_ok = check_coverage("skill", skill_names, SKILL_NAME_ZH)
        occupation_ok = check_coverage("occupation", occupation_names, OCCUPATION_NAME_ZH)
        raise SystemExit(0 if (skill_ok and occupation_ok) else 1)

    print(write_mapping("skill_name_zh.csv", "skill_id", skill_names, SKILL_NAME_ZH))
    print(write_mapping("occupation_name_zh.csv", "occupation_id", occupation_names, OCCUPATION_NAME_ZH))


if __name__ == "__main__":
    main()
