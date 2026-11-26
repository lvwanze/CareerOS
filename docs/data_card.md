# CareerOS 职业—技能知识库 Data Card

| 项目 | 内容 |
| --- | --- |
| 数据集 | CareerOS Occupation-Skill Knowledge Base |
| 版本 | 0.5.0（frozen） |
| 负责人 | 高帅龙（成员1 / M1 · 职业与技能知识库建设） |
| 生成日期 | 2026-11-18 |
| 数据来源 | O*NET 31.0（2026-08 发布） |
| 许可证 | CC BY 4.0，使用时需保留来源标注 |
| 契约版本 | data_contract.md V1.0 |
| 状态 | 已通过赵帝臣算法验收 + 代旭后端验收（2026-11-18），冻结 |

---

## 一、数据集用途

本知识库是 CareerOS 推荐系统的基础数据，描述"有哪些职业、有哪些技能、每个职业要求哪些技能到什么程度"。供算法层（M3/M4）计算职业匹配与技能差距，供后端（M5）读取展示。不支持用户画像数据——用户自评等级由前端采集，与职业要求等级同量表（0~4）但来源不同。

完整业务链路：`用户画像 → 技能画像 → 职业匹配 → Top-5 推荐 → 能力差距 → 发展路径 → Flutter 展示`。本数据集覆盖其中"职业技能知识库"一环。

---

## 二、数据来源与许可

唯一数据源为 **O*NET 31.0**（美国劳工部职业信息数据库），不引入 ESCO。

- 官方页：https://www.onetcenter.org/database.html
- CSV 目录：https://www.onetcenter.org/dl_files/database/db_31_0_csv/
- 许可页：https://www.onetcenter.org/license_db.html

选择理由：O*NET 是唯一同时提供"技能重要性（IM，1~5）"和"要求等级（LV，0~7）"两套数值评分的开放数据，与契约的 `importance` / `required_level` 一一对应，无需自行编造权重。

**地域局限**：O*NET 是美国就业市场数据，不代表中国就业市场。匹配分仅为模型内部相对适配指标，不可解释为进入某职业的统计概率。

原始数据保留在 `data/raw/onet31_csv/`：

| 文件 | 记录数 | 用途 |
| --- | --- | --- |
| `occupation_data.csv` | 1,016 职业 | 职业基础信息 |
| `essential_skills.csv` | 18,200 行 | 10 种核心技能 + IM/LV 双评分 |
| `transferable_skills.csv` | 45,500 行 | 25 种可迁移技能 + IM/LV 双评分 |

---

## 三、数据规模与结构

| 成品表 | 行数 | 主键 | 说明 |
| --- | --- | --- | --- |
| `data/processed/occupations.csv` | 28 | `occupation_id` | 23 个 `15-` 计算机数学类 + 5 个 `13-` 商业金融类 |
| `data/processed/skills.csv` | 35 | `skill_id` | 10 essential + 25 transferable，两来源无交集 |
| `data/processed/occupation_skills.csv` | 492 | (`occupation_id`, `skill_id`) | 职业—技能关联，长表 |

职业范围是有意划定的 MVP 子集，聚焦 IT 与金融分析岗位，非 O*NET 全量（1,016 职业中 910 个有完整双评分）。28 个职业全部经核查有完整 IM/LV 双评分，含后端点名的 5 个职业。

### 字段说明

**occupations.csv**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `occupation_id` | str | 统一职业 ID，格式 `OCC-ONET-<原始SOC码>` |
| `name` | str | 职业名称（英文原始名） |
| `description` | str | 职业描述（O*NET 原文） |
| `category` | str | 职业类别 |
| `source` | str | 固定 `ONET` |
| `source_id` | str | 原始 SOC 码 |

**skills.csv**

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `skill_id` | str | 统一技能 ID，格式 `SKILL-ONET-<原始ElementID>` |
| `name` | str | 技能名称（英文原始名） |
| `category` | str | 来源分组：`essential` / `transferable` |
| `description` | str | 本期全部留空（前端不做技能详情展示） |
| `source` | str | 固定 `ONET` |
| `source_id` | str | 原始 Element ID |

**occupation_skills.csv**（最关键）

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `occupation_id` | str | 关联职业，外键 → occupations |
| `skill_id` | str | 关联技能，外键 → skills |
| `importance` | float | 存 O*NET 原始 IM（1~5），**未归一化**；实际 3.00~4.88 |
| `required_level` | int | `round(LV×4/7)` 映射的 0~4 级；实际值域 **1~3** |

---

## 四、数据处理与清洗规则

由 `scripts/build_dataset.py` 从 `data/raw/onet31_csv/` 加工生成，五步流程：读取 → 统一 ID → 清洗 → 评分换算 → 输出。规则已参数化，变更时改参数重跑即可。

1. **职业白名单**：28 个，23 个 `15-` + 5 个 `13-`，全部有完整 IM/LV 双评分。
2. **技能合并**：essential + transferable 合并，按 skill_id 去重（实测无交集，共 35 种）。
3. **关联表**：只保留 IM 与 LV 双评分齐全的组合（长表），缺失不按 0 填充；不做每职业前 N 个截断（交由算法层按 importance 降序处理，N 可配初值 12）。
4. **入表阈值**：IM ≥ 3.0（原始 1~5 尺度），低于阈值不入表。
5. **ID**：`OCC-ONET-` / `SKILL-ONET-` 前缀 + 原始 ID，全程按字符串处理，不经 Excel。
6. **去重与孤立清理**：关联表按 (`occupation_id`, `skill_id`) 唯一，两端 ID 必须能在主表找到。
7. **缺失值**：留空字符串，不写 `null` / `NA` / `-`；UTF-8 无 BOM、逗号分隔、LF 换行、首行表头。
8. **字段**：严格遵循 data_contract.md V1.0，未新增列。

### 评分口径（经算法负责人确认）

| 契约字段 | O*NET 来源 | 处理方式 |
| --- | --- | --- |
| `importance` | `Scale ID=IM` 的 `Data Value` | 存原始 1~5，归一化 `(IM-1)/4` 由算法层读入内存后执行 |
| `required_level` | `Scale ID=LV` 的 `Data Value` | `round(LV×4/7)`，即 0→0,1→1,2→1,3→2,4→2,5→3,6→3,7→4 |

`required_level` 契约定义 0~4 五级，实际数据只出现 1~3：`IM≥3.0` 筛掉低重要度技能，这些技能的 LV 也偏低。O*NET 这批数据原始 LV 上限约 6，映射后本就没有 4 级。前端/测试勿按 0~4 做全档位断言。

---

## 五、已知局限与后续项

1. **技能粒度偏粗**：35 种技能多为通用认知技能（阅读理解、批判性思维等），缺专业技术技能。实测 28 职业两两 Jaccard 相似度平均 **0.665**，Software Developers 与 Blockchain Engineers 达 **0.941**——算法层用 importance 加权 + 技能稀缺度（IDF）加权解决区分度。后续若区分度不足，从 O*NET Technology Skills 扩充，优先补设计类、运维类、硬件类等技能差异大的职业。
2. **两个孤立技能**：`SKILL-ONET-2.B.3.c`（Equipment Selection）、`SKILL-ONET-2.B.3.d`（Installation）在当前 28 职业下无关联记录。保留在技能表中作词表，用户填写这两项不影响推荐；后续扩职业范围时可能启用。
3. **技能描述为空**：本期不做技能详情展示，前端如需展示再从 O*NET 补列并重生成。
4. **无 `required_level_raw`**：曾讨论保留 LV 原始 0~7，算法负责人已收回该需求（值域集中 1~3、gap 计算不需原始刻度、变更成本大于收益）。
5. **中文名**：本期三表不含中文字段，由后端维护映射兜底。
6. **招聘市场数据（本期不接入）**：招聘数据两表（`job_postings` 等）的 manifest 标记为 `0.2.0-draft`，注明确认前不得作为正式契约读入，目前无代码读取。**结论：第一阶段不接入招聘数据**，不进入知识库三表、不参与匹配与排序。原因：MVP 以可解释的基础算法和可现场指认的数据为准，招聘数据尚未完成来源许可与口径确认。接入计划放在第二阶段（个人毕设迭代），由 M3 代旭负责采集清洗与口径确认、M2 赵帝臣负责数据驱动权重；接入前需更新公共契约与本节结论。本数据集（O*NET 职业—技能知识库）是第一阶段唯一正式输入。
7. **时点断言（as-of）**：本项目**不实现时点断言**。数据无时序标签、无快照时间轴，不存在「按某个历史时点重放推荐」的语义；用户画像快照即请求时点，匹配与差距计算只基于当前快照，不做跨时点对比。这是有记录的「不做」决策，而非遗漏。未来引入招聘市场数据后，该结论变化为：岗位需求带采集时间，可按 as-of 做时间旅行评估（某历史时点的技能需求与推荐），届时需为招聘数据表增加时间字段并单独设计快照读取逻辑，本职业—技能知识库本身仍不含时点语义。

---

## 六、版本与验收

| 时间 | 事件 |
| --- | --- |
| 2026-11-18 08:45 | 按 A1-A6 / B1-B8 确认口径用 `build_dataset.py` 生成正式三表，manifest 升 0.4.0 |
| 2026-11-18 09:06 | 赵帝臣《数据验收报告-v0.4.0》：通过，同意冻结；required_level_raw 收回不加 |
| 2026-11-18 09:06 | manifest 补 scope / 孤立技能标注 / 描述策略 / 值域说明，状态改为 frozen，三表数据零改动 |
| 2026-11-18 11:00 | 代旭后端读入验收通过：sha256/row_count/contract_version 全对、无 BOM/LF、列名与顺序符契约、dtype=str 读 ID 点号不丢、0 孤立/0 重复、description 真空单元格；三表对契约 V1.0 一列不差 |
| 2026-11-18 17:30 | 组长确认修正方案后正式打包 v0.5.0：manifest 增量升级（保留全部验收记录、source 纠正为 O*NET 31.0、补 collection_date/record_counts），三表数据零改动、sha256 不变；组长清单中的 echo 覆盖 manifest 与改 CSV 字段两步已作废 |

验收通过的检查项（算法侧赵帝臣 + 后端侧代旭）：三表 `pd.read_csv(dtype=str)` 可读；row_count 与 manifest 一致（28/35/492）；sha256 逐文件重算一致；ID 无孤立引用；主键与关联对无重复；长表无缺失、未做 0 填充；UTF-8 无 BOM、LF 换行；列名与顺序与契约 V1.0 完全一致、一列不差。

后端接口层：`schemas.py` 模型字段与数据列名不同名（`name→occupation_name`、`skills.name→skill_name`、`importance→match_score`），由后端加一层映射解决，数据侧不改。中文名按 B4 由后端映射表转中文，`skills.csv` 不加 `name_zh` 列。注意 `importance`（技能重要程度，数据输入）与 `match_score`（算法对用户的匹配度，算法输出）语义不同，接口 `match_score` 应取算法输出而非本表 `importance` 列。

`manifest.json` 记录三表 sha256、row_count、contract_version、字段含义、ID 映射、清洗规则、确认决策与处理日志，是数据溯源与复现的依据。

---

## 七、复现方式

**从干净 clone 复现**（对应答辩验收清单 M1-P0-2）：

`data/raw/` 因原始数据量大未纳入 Git，全新 clone 里没有它。按下面四步操作即可复现出与仓库逐字节一致的三表：

```bash
# 1. 下载原始数据（O*NET 官方，无需注册）：
#    https://www.onetcenter.org/dl_files/database/db_31_0_csv/
#    下载 occupation_data.csv / essential_skills.csv / transferable_skills.csv 三份

# 2. 放到 backend/data/raw/onet31_csv/ 后，核对校验和：
cd backend
sha256sum data/raw/onet31_csv/*.csv

# 3. 校验通过后生成三表：
python scripts/build_dataset.py

# 4. 比对产物与 manifest 登记值：
sha256sum data/processed/*.csv
```

三份原始数据的 sha256（下载后必须核对一致）：

| 原始数据文件 | sha256 |
| --- | --- |
| `occupation_data.csv` | `a09eae1d6609686e44e05b7290993a1c8b523d8ca224bc0eedc194c855c3ee02` |
| `essential_skills.csv` | `68c4d31d8c55077238395dca40cc4e6d32e6a608b5474bb8264b1f98ae415bd7` |
| `transferable_skills.csv` | `f17d0419e818a3bf2f55076510c76c4aef01cc8f5aee2670d2f44f6f44ac60f7` |

生成三表的目标 sha256（应与 `backend/data/manifest.json` 一致）：

| 成品表 | sha256 |
| --- | --- |
| `occupations.csv` | `087a2484e1a6db12497dda2bbbadf8bc37bfe50adb741c18334d0b5e00cc2512` |
| `skills.csv` | `59ca8b64bb1c295cc6fb4a5e84ba3429cb21e20d3a6d09c671132e19825a12db` |
| `occupation_skills.csv` | `00044bd0943fd019b7805633f0b6412258c71dd4c1fa6b11997020e75e02f8bb` |

> 2026-11-26 实测：用上述原始数据 + 本脚本在干净目录复现，三表 sha256 与 manifest 登记值逐字节一致（28/35/492 行）。

脚本从 `data/raw/onet31_csv/` 读取 O*NET 原始数据，按固化规则（职业白名单 28 个、IM≥3.0、两来源合并去重、ID 统一、评分换算）生成 `data/processed/` 三张表。规则变更时修改脚本顶部参数后重跑，并同步更新 `manifest.json` 的 sha256 与版本号。

**分析**（只读成品表，任何成员可运行，复现本报告中的关键数字）：

```bash
python scripts/analyze_dataset.py
```

对三张成品表做统计与质量分析：数据规模与主键/孤立检查、每职业剩余技能数分布（min12/中位17/均值17.57/max24）、importance 与 required_level 实际值域、职业间 Jaccard 相似度（平均 0.665、最高 Software Developers↔Blockchain Engineers 0.941）、孤立技能检测。这些是「阈值 0.90 去重」「技能粒度够用」等结论的量化依据，答辩可直接跑此脚本复现。

---

> 数据来源：O*NET 31.0，U.S. Department of Labor / Employment and Training Administration，CC BY 4.0。
