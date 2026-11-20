# 算法侧验收口径说明（matcher-v1）

> 供测试侧复测与报告引用。本文所有数值均为本地实测，非估算。
> 对应分支 `feature/model`，以 `main` 合并后的最新提交为准。

---

## 一、版本号

| 项 | 值 |
| --- | --- |
| `model_version` | **`matcher-v1`** |
| 唯一来源 | `backend/packages/training/matcher.py` → `MODEL_VERSION` |
| 对外出口 | `POST /api/v1/recommendations` 响应 `data.model_version` |
| 算法接入提交 | `a631abf`（`inference.py` 改为调用 `matcher`） |
| 口径修订提交 | `1bf2817`（版本号单点化）、`5d258da`（`evidence_level` 透传）、`8de7ce2`（`self_level` 越界改为 422） |

**注意（此前存在不一致，已修）**：路由层曾把 `model_version` 硬编码为 `weighted-knowledge-base-v1`，与 `matcher.MODEL_VERSION`、`d4_cases.json` 三处不一致。现已统一为单一来源，接口返回与算法层、回归基线三者一致。

**确认方法**（任意一次调用即可）：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/recommendations \
  -H 'Content-Type: application/json' \
  -d '{"profile":{"user_id":"u1","skills":[{"skill_id":"SKILL-ONET-2.B.3.e","self_level":4}]}}' \
  | python -c "import json,sys; print(json.load(sys.stdin)['data']['model_version'])"
# 期望输出：matcher-v1
```

---

## 二、画像定义

### 2.1 我方已固化的基准画像（仓库内，带回归基线）

这两组定义在 `backend/tests/profiles/d4_cases.json`，含 `expected` 基线，容差 `tolerance = 0.01`。

**画像 A（`high_match`）：12 项技能**

| 技能 | 自评等级 | 证据 |
| --- | --- | --- |
| `SKILL-ONET-2.B.3.e`（Programming） | 4 | project |
| `SKILL-ONET-2.A.1.e`（Mathematics） | 4 | project |
| `SKILL-ONET-2.A.2.a` / `2.B.4.g` / `2.B.4.h` | 3 | course |
| `SKILL-ONET-2.B.2.i` / `2.B.3.b` | 3 | project |
| `SKILL-ONET-2.B.3.a` / `2.B.4.e` | 2 | course |
| `SKILL-ONET-2.A.1.a` | 3 | course |
| `SKILL-ONET-2.A.2.b` / `2.B.5.a` | 3 | self |

期望 Top-5（`occupation_id` / `match_score`）：

| 排名 | occupation_id | match_score |
| --- | --- | --- |
| 1 | `OCC-ONET-15-1252.00` | 0.751 |
| 2 | `OCC-ONET-15-2051.00` | 0.714 |
| 3 | `OCC-ONET-15-1255.00` | 0.705 |
| 4 | `OCC-ONET-15-1243.00` | 0.647 |
| 5 | `OCC-ONET-15-2099.01` | 0.631 |

**画像 B（`low_match`）：5 项通用技能**

| 技能 | 自评等级 | 证据 |
| --- | --- | --- |
| `SKILL-ONET-2.A.1.a`（Reading Comprehension） | 2 | course |
| `SKILL-ONET-2.A.1.c`（Writing） | 2 | course |
| `SKILL-ONET-2.A.1.b`（Active Listening） | 2 | self |
| `SKILL-ONET-2.B.5.a` | 2 | self |
| `SKILL-ONET-2.A.1.d`（Speaking） | 2 | **none** |

期望 Top-5：

| 排名 | occupation_id | match_score |
| --- | --- | --- |
| 1 | `OCC-ONET-15-1255.00` | 0.383 |
| 2 | `OCC-ONET-15-2051.00` | 0.334 |
| 3 | `OCC-ONET-15-1212.00` | 0.312 |
| 4 | `OCC-ONET-15-2051.01` | 0.307 |
| 5 | `OCC-ONET-15-2099.01` | 0.297 |

> 画像 B 第 5 项证据为 `none`，用于验证第三档 `needs_verification`：Top-5 每条各含 1 条待验证记录。

### 2.2 关于「画像 C、D」

**我方仓库中不存在编号为 C、D 的画像定义。** 固化的只有上述两组（A 高匹配、B 低匹配）。

请按以下任一方式明确，否则双方无法保证同一口径：

1. 提供 C、D 的具体构成（技能 ID + 自评等级 + 证据）；
2. 或确认 C、D 即指 2.1 的 A、B；
3. 或确认 C、D 为你方自建的边界画像，则只需我方确认期望行为（见第五节边界表）。

若 C、D 属边界类，可直接采用下列两组标准边界画像复测：

| 画像 | 构成 | 实测行为 |
| --- | --- | --- |
| 空画像 | `skills: []` | HTTP 200，`recommendations` 返回 **0 条** |
| 满覆盖画像 | 全部 35 项技能均填 `self_level = 2` | 28 个职业分数 0.867~1.000，中位数 **1.000** |

---

## 三、`match_score` 取值范围

### 3.1 公式

```
match_score = Σ(w_i × 达成度_i) / Σ w_i
```

- `w_i = ((importance_i − 1) / 4) × idf_i`，`idf_i = ln((1 + 28) / (1 + df_i)) + 1`
- 达成度 = `min(self_level / required_level, 1.0)`
- **分母取该职业全部挂载技能的权重和**，不是「用户已填技能」的权重和

### 3.2 取值范围

| 口径 | 值 |
| --- | --- |
| 数学区间 | **[0.000, 1.000]**，闭区间 |
| 实测下界 | 全员 `self_level = 0` → 28 个职业全部 **0.000** |
| 实测上界 | 全员 `self_level = 4` → 28 个职业全部 **1.000** |
| 画像 A 实测 | Top-5 0.631~0.751；`top_k=28` 时 25 条，全区间 0.242~0.751 |
| 画像 B 实测 | Top-5 0.297~0.383；`top_k=28` 时 26 条，全区间 0.136~0.383 |
| 字段类型 | Python `float` |
| 输出精度 | 保留 3 位小数；内部排序使用全精度，不在排序前 `round` |

### 3.3 两个必须避免的误判

**① 「填满所有技能」会得到接近 1.000，这不是 bug**

`required_level` 的实际分布是：1 级 3 条、**2 级 454 条（92%）**、3 级 35 条。因为绝大多数技能只要求 2 级，用户把 35 项技能全填 2 级就能满足九成以上的要求，分数自然接近满分。

实测：全员 2 级 → 28 个职业 0.867~1.000，中位数 1.000。

**② `match_score` 不是概率，不能表述为百分比**

它是「内部相对匹配度」，用于同一用户在不同职业之间排序。不能写成「匹配度 75%」「录取概率 0.751」。任何对外文案都不得将其解释为概率或通过率。

### 3.4 为什么高分画像也只有 0.751

因为分母包含该职业**全部**挂载技能，用户没填的技能按 0 级计入达成度 0。画像 A 的 12 项技能并未覆盖 `Software Developers` 的全部 16 项要求，未覆盖部分持续压低分数。这是设计意图：分母若改为「只算用户已填技能」，则人人接近 1.0，失去区分度。

---

## 四、字段映射最终口径

### 4.1 推荐条目（`data.recommendations[]`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `occupation_id` | `str` | 职业 ID，如 `OCC-ONET-15-1252.00` |
| `occupation_name` | `str` | 英文名 |
| `occupation_name_zh` | `str \| null` | 中文名，仅展示，**不参与计算** |
| `match_score` | `float` | 取值 [0.0, 1.0]，3 位小数 |
| `skill_gaps` | `array` | 技能差距明细，见 4.2 |
| `recommendation_reasons` | `array[str]` | 推荐依据，中文技能名拼装 |
| `matched_skills` | `array[str]` | 已达标技能 ID |
| `skills_to_improve` | `array[str]` | 待提升技能 ID |
| `skills_to_verify` | `array[str]` | 待验证技能 ID |

### 4.2 `skill_gaps[]`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `skill_id` | `str` | 技能 ID |
| `skill_name` | `str` | 英文名 |
| `skill_name_zh` | `str \| null` | 中文名 |
| `gap` | **`int`** | `max(0, required_level - current_level)`，**整数，非 float** |
| `importance` | `float` | 原始 O*NET 重要度（1~5） |
| `status` | `str` | 三档枚举，见 4.3 |
| `current_level` | `int` | 用户自评等级 |
| `required_level` | `int` | 职业要求等级 |

排序：按 `importance` 降序（展示口径）；内部算分按 `weight` 降序，两者不同，差异在 `inference` 层转换。

### 4.3 枚举

**`status`（三档）**

| 值 | 触发条件（按此顺序判定，顺序不可换） |
| --- | --- |
| `needs_improvement` | `current_level <= 0`，或 `current_level < required_level` |
| `needs_verification` | `current_level > 0` 且 `evidence_level == "none"` |
| `mastered` | `current_level >= required_level` 且有证据 |

**`evidence_level`（入参，7 值）**

`none` / `self` / `course` / `project` / `work` / `certificate` / `test`

| 入参情况 | 实际处理（HTTP 路径实测） |
| --- | --- |
| 不传该字段 / 传 `null` / 传空串 | 按 `self` 处理（不判待验证），HTTP 200 |
| 显式传 `none` | 按「无证据」处理，产出 `needs_verification` |
| 传大小写混杂（如 `PROJECT`） | 归一为 `project`，正常判 `mastered` |
| 传未知值（如 `projct`） | 算法层告警并归为 `none`，产出 `needs_verification`，**HTTP 仍 200**（当前不做枚举硬校验，原因见下） |

**证据只影响 `status`，不影响 `match_score`。** 实测同一画像 6 种证据输入（不传 / `null` / 空串 / `none` / `projct` / `PROJECT`），最高分恒为 `0.1170`，仅 `status` 在 `mastered` 与 `needs_verification` 间变化。复测时不要用「分数随证据变化」做断言。

> 契约 §2.2 的 `evidence_level` 枚举至今标注「待确认」，因此本轮**未**把它收敛为 `Literal` 硬校验，避免契约冻结时误伤新增合法值。`self_level` 因契约已明确 `int 0~4`，本轮已改为越界 422（见第五节）。建议下一版契约同时冻结证据枚举，届时再补 API 层校验。

### 4.4 返回条数

- 算法层区间：**[0, top_k]**，**不保证等于 `top_k`**
- HTTP 入口：`skills` 少于 1 项直接 422，因此正常请求最少返回 **1 条**
- 原因：相似职业去重（Jaccard > 0.90 剔除）
- 实测：`top_k=28` 时，画像 A 返回 25 条、画像 B 返回 26 条
- 前端必须按「最多 top_k 张卡片」渲染，不能写死 5

### 4.5 已废弃的别名（复测时请勿使用）

| 旧写法（已失效） | 正确写法 |
| --- | --- |
| `gaps` | `skill_gaps` |
| `top_factors` | `recommendation_reasons` |

原实现把 alias 方向写反，导致按契约名构造直接校验失败、序列化输出旧名，前端读 `skill_gaps` 会拿到 `null`。现已删除两个 alias，只接受契约名。

---

## 五、边界行为（实测）

| 场景 | 请求 | 实际行为 |
| --- | --- | --- |
| 空画像 | `skills: []` | **HTTP 422**，`field = profile.skills`，提示「至少填报 1 项技能」（冻结单要求 ≥1 项） |
| 技能不存在 | `skill_id: "SKILL-FAKE-999"` | HTTP 200，该技能被忽略，正常返回 5 条 |
| 未知证据值 | `evidence_level: "projct"` | HTTP 200，按 `none` 处理 |
| `self_level` 缺失 | 不传该字段 | HTTP 200，按 **0 级**处理（与显式传 0 结果逐字段一致） |
| `self_level = 5` / `-1` / `99` | 越界值 | **HTTP 422**，`field = profile.skills.0.self_level` |
| 缺少 `skill_id` | 只传 `self_level` | **HTTP 422**，`field = profile.skills.0.skill_id`，提示「为必填项」 |
| `top_k = 0` | 算法层直接调用 | 返回空列表 |
| 超过去重上限的 `top_k` | `top_k=100` | 返回去重后实际可选条数（25~28），不报错 |

### 5.1 越界与空画像统一返回 422

早期版本在路由层用 `0 <= self_level <= 4` 做过滤，越界条目被**静默丢弃**且仍返回 200，调用方无从察觉该技能没有参与计算，极端情况下会拿到 0 条推荐却看不到任何错误。

现已将请求体收敛为 pydantic 模型（`packages/core/schemas.py` 的 `SkillInput` / `ProfileInput`），越界在进入业务逻辑前即被拦下。

### 5.2 422 响应格式（统一一种，复测按此断言）

三种 422（越界 / 空画像 / 缺必填字段）返回**同一结构**，不要按 FastAPI 原生 `{"detail": [...]}` 断言：

```json
HTTP 422
{
  "code": 422,
  "message": "请求参数不符合要求",
  "data": {"errors": [{"field": "profile.skills.0.self_level", "message": "不能大于 4"}]},
  "request_id": "..."
}
```

| 字段 | 说明 |
| --- | --- |
| `code` | 固定 422 |
| `message` | 固定「请求参数不符合要求」 |
| `data.errors[].field` | 出错的字段路径，点分格式；数组下标用数字（`skills.0`） |
| `data.errors[].message` | 中文原因：`不能大于 4` / `不能小于 0` / `为必填项` / `至少填报 1 项技能` |

约定不变的部分：字段缺失仍按 0 级处理；未知 `skill_id` 仍告警并忽略；`evidence_level` 非法值仍归一为 `none`（HTTP 200）。

---

## 六、关于把「自检」改为「真实验收」

可如实声称的范围：

| 能声称 | 依据 |
| --- | --- |
| 契约字段一致 | 接口实测返回 9 个顶层字段、8 个差距字段，名称与类型逐项核对 |
| 三档判定有效 | 显式传 `evidence_level: "none"` 时产出 `needs_verification`（实测 `skills_to_verify` 非空） |
| 相似职业去重有效 | `top_k=28` 仅返回 25/26 条；被剔职业与保留职业 Jaccard > 0.90 |
| 结果确定性 | 同一输入多次调用，排序与分数完全一致 |
| 边界行为 | 上表 8 个场景逐项实测，三种 422 结构一致 |
| 中文名不影响分数 | 全部 `name_zh` 置空 / 替换为乱码各跑一次，28 个职业排序与分数 6 位小数一致 |

**不能声称**：

| 不能声称 | 原因 |
| --- | --- |
| 准确率 / 召回率 / NDCG | 无标注数据，无法计算 |
| 「推荐得准」 | 无 ground truth，只能验证确定性与契约一致性 |
| `match_score` 是匹配概率 | 内部相对指标，非概率 |

**当前验证的性质**：契约一致性 + 确定性 + 边界行为。这属于「工程验收」，不等于「算法效果评估」。若报告需要效果结论，须先有标注集，属 D4 范畴，目前未完成。

---

## 七、复测入口

```bash
# 单元测试（7 项）
cd backend && python -m pytest tests/ -q

# 冒烟测试（10 项，含回归基线与分数区间）
python backend/tests/smoke_test.py

# 回归基线（容差 0.01）
backend/tests/profiles/d4_cases.json
```

模型卡：`docs/model_card.md`（含算法细节、固定参数、已知局限、版本变更）
