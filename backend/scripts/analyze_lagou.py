# -*- coding: utf-8 -*-
"""拉勾 JD 可用性体检：样本量分布、JD 重复率、长度分布、职业覆盖。"""

import csv
import hashlib
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data" / "processed"

with (BASE / "job_postings.csv").open(encoding="utf-8", newline="") as handle:
    postings = [row for row in csv.DictReader(handle) if row["platform"] == "lagou"]

with (BASE / "job_descriptions.csv").open(encoding="utf-8", newline="") as handle:
    details = {row["job_id"]: row["position_detail"] for row in csv.DictReader(handle)}

print(f"拉勾岗位: {len(postings):,}  JD 条数: {len(details):,}")

print("\n--- 细分方向（bigcategory）---")
for name, count in Counter(row["job_subcategory"] for row in postings).most_common():
    print(f"  {name:<8} {count:>6,}")

print("\n--- 城市前 12 ---")
for name, count in Counter(row["city"] for row in postings).most_common(12):
    print(f"  {name:<8} {count:>6,}")

print("\n--- 经验要求 ---")
for name, count in Counter(row["work_year"] for row in postings).most_common():
    print(f"  {name:<10} {count:>6,}")

lengths = sorted(len(text) for text in details.values())
n = len(lengths)
print(f"\n--- JD 长度 ---")
print(f"  最短 {lengths[0]}  中位 {lengths[n // 2]}  均值 {sum(lengths) // n}  最长 {lengths[-1]}")
print(f"  <100 字: {sum(1 for x in lengths if x < 100):,}  <200 字: {sum(1 for x in lengths if x < 200):,}")

hashes = Counter(hashlib.md5(text.encode("utf-8")).hexdigest() for text in details.values())
unique = len(hashes)
print(f"\n--- JD 重复情况 ---")
print(f"  唯一 JD: {unique:,} / {n:,}（重复率 {(n - unique) / n:.1%}）")
print(f"  最高重复次数: {hashes.most_common(1)[0][1]}")

total_chars = sum(lengths)
print(f"  语料总量: {total_chars:,} 字（约 {total_chars / 10000:.0f} 万字）")

print("\n--- 城市 × 细分方向 的小样本格子（<100 条）---")
cross = Counter((row["city"], row["job_subcategory"]) for row in postings)
thin = [(k, v) for k, v in cross.items() if v < 100 and k[0] in {"北京", "上海", "深圳", "杭州", "广州", "成都"}]
for (city, sub), count in sorted(thin, key=lambda x: -x[1])[:10]:
    print(f"  {city} × {sub}: {count}")
