"""check_feature_catalog.py — 校验特征目录与成品表列名一致（M1-P0-3）

用途：
    1. 作为「至少被一处代码或测试读取 feature_catalog.yaml」的落点；
    2. 保证 configs/feature_catalog.yaml 声明的列名与 data/processed/ 三张 CSV 表头一一对应，
       避免字段元数据出现第二个来源。

依赖：Python 3 标准库。若环境已装 PyYAML 则优先用它；否则用内置极简解析（仅支持本文件结构）。
运行：python scripts/check_feature_catalog.py
退出码：全部一致 0；不一致或非空错误 1。
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "configs" / "feature_catalog.yaml"
PROCESSED = ROOT / "data" / "processed"

TABLES = ("occupations.csv", "skills.csv", "occupation_skills.csv")


def load_catalog(path):
    """优先 PyYAML；无则用极简解析提取表格段落里的 - name: 字段（按出现顺序）。"""
    try:
        import yaml  # type: ignore

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except ImportError:
        pass

    text = path.read_text(encoding="utf-8")
    # 只取 tables: 段落到下一个顶层键（forbidden_columns:）之间
    m = re.search(r"^tables:\s*$(.*?)^forbidden_columns:", text, re.M | re.S)
    if not m:
        raise ValueError("feature_catalog.yaml 缺少 tables: 段落")
    block = m.group(1)
    result = {}
    cur_table = None
    for line in block.splitlines():
        tm = re.match(r"^  ([\w.]+\.csv):\s*$", line)
        if tm:
            cur_table = tm.group(1)
            result[cur_table] = {"columns": []}
            continue
        cm = re.match(r"^\s+- name:\s*(\S+)", line)
        if cm and cur_table:
            result[cur_table]["columns"].append({"name": cm.group(1)})
    return {"tables": result}


def csv_header(path):
    with path.open(encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


def main():
    if not CATALOG.exists() or CATALOG.stat().st_size == 0:
        print(f"[FAIL] 特征目录缺失或为空：{CATALOG}")
        return 1
    try:
        catalog = load_catalog(CATALOG)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] 解析特征目录失败：{exc}")
        return 1

    tables = catalog.get("tables") or {}
    ok = True
    for name in TABLES:
        declared = [c["name"] for c in (tables.get(name) or {}).get("columns", [])]
        header = csv_header(PROCESSED / name)
        if declared == header:
            print(f"[OK] {name}: 目录列 {len(declared)} 个，与表头一一对应")
        else:
            ok = False
            print(f"[FAIL] {name}: 目录列 {declared}")
            print(f"       表头列 {header}")
    if ok:
        print("特征目录校验通过：三张成品表列名与 configs/feature_catalog.yaml 完全一致。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
