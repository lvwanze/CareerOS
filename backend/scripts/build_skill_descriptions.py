"""Generate the English skill descriptions from O*NET's content model reference.

为什么单独生成一份参考表，而不是直接填进 skills.csv 的 description 列：
- processed/ 三张表是冻结契约表（manifest 有 sha256、赵帝臣已验收），
  改一列就得整体重新验收，为了"接口能展示一句说明"不值当；
- reference/ 本来就是"维护型参考数据"（中文名映射就在这儿），
  技能说明放同一层，改的是同一类东西，契约表一行不动。

数据来源：O*NET 31.0 Content Model Reference（Element ID 2.A.x / 2.B.x 即本项目的
35 条技能），官方下载页 https://www.onetcenter.org/database.html
拿到 content_model_reference.csv 后按下面用法执行：

    python scripts/build_skill_descriptions.py data/raw/onet_content_model_reference.csv
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
REFERENCE = ROOT / "data" / "reference"

FIELDS = ["skill_id", "name_en", "description_en", "source", "note"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "onet_content_model_reference.csv"
    if not source_path.is_file():
        raise SystemExit(f"找不到 O*NET 内容模型参考表：{source_path}")

    descriptions = {
        row["Element ID"]: row["Description"].strip()
        for row in read_csv(source_path)
        if row.get("Description")
    }

    rows, missing = [], []
    for skill in read_csv(PROCESSED / "skills.csv"):
        description = descriptions.get(skill["source_id"], "")
        if not description:
            missing.append(f"{skill['skill_id']}({skill['source_id']})")
            continue
        rows.append({
            "skill_id": skill["skill_id"],
            "name_en": skill["name"],
            "description_en": description,
            "source": "O*NET 31.0",
            "note": "Content Model Reference 原文，按 Element ID 对齐",
        })

    if missing:
        raise SystemExit(f"以下技能在 O*NET 参考表里查不到说明：{', '.join(missing)}")

    REFERENCE.mkdir(parents=True, exist_ok=True)
    with (REFERENCE / "skill_description.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"生成完成：skill_description={len(rows)} 条，来源 {source_path.name}")


if __name__ == "__main__":
    main()
