# CareerOS 公共数据契约 V1.0

## 1. 文档目的

本文档定义 CareerOS 各模块共同使用的数据模型、字段名称、数据类型、业务含义及数据交接规则。

所有模块必须遵循统一的数据结构。未经沟通，不得擅自修改公共字段名称、数据类型和业务含义。

当前版本为第一阶段 MVP。原「待确认事项」（§8）已于 2026-11-27 全部定稿，结论见第 8 节；后续新增字段仍需相关负责人确认后才能冻结。

## 2. 全局数据规范

### 2.1 命名规范

- JSON 字段统一使用 snake_case。
- Python 变量和函数使用 snake_case。
- Python 类名使用 PascalCase。
- 每个职业和技能均使用唯一 ID。
- ID 不应依赖中文显示名称。
- 时间字段统一使用 ISO 8601 格式。
- 缺失值使用 null，不使用字符串 "null"。

### 2.2 技能等级规范

第一阶段暂定使用 0～4 级：

| 等级 | 含义 |
|---|---|
| 0 | 未掌握 |
| 1 | 了解基础概念 |
| 2 | 能完成基础任务 |
| 3 | 能独立完成常见任务 |
| 4 | 能处理复杂任务并熟练应用 |

用户自评等级与职业要求等级可以采用相同量表，但必须区分数据来源。

用户自评不等于客观能力证明。

## 3. 核心数据模型

### 3.1 UserProfile：用户画像

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| user_id | str | 是 | 用户唯一标识 |
| learning_stage | object | 是 | 学习阶段 |
| preferences | object | 是 | 兴趣与偏好 |
| skills | list | 是 | 用户技能列表 |
| constraints | object | 否 | 现实条件 |
| career_goals | object | 否 | 职业目标 |

learning_stage：

| 字段 | 类型 | 说明 |
|---|---|---|
| education_level | str | 学历阶段 |
| major | str | 当前专业 |
| current_stage | str | 当前学习或工作阶段 |

preferences：

| 字段 | 类型 | 说明 |
|---|---|---|
| interest_areas | list[str] | 感兴趣的领域 |
| work_style | list[str] | 偏好的工作方式 |

skills：

| 字段 | 类型 | 说明 |
|---|---|---|
| skill_id | str | 技能唯一标识 |
| self_level | int | 用户自评等级，0～4 |
| evidence_level | str | 能力证据状态 |

constraints：

| 字段 | 类型 | 说明 |
|---|---|---|
| available_hours_per_week | int | 每周可投入时间 |
| preferred_regions | list[str] | 偏好就业地域 |
| relocation_willingness | bool | 是否接受异地发展 |

career_goals：

| 字段 | 类型 | 说明 |
|---|---|---|
| target_occupations | list[str] | 用户主动选择的职业方向 |
| goal_description | str | 个人目标描述 |

注意：以上为 MVP 建议字段；推荐链路的最终必填规则已定（`skills` 至少 1 项、`user_id` 可选缺省 anonymous），结论见 §8。

### 3.2 Skill：技能定义

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| skill_id | str | 是 | 技能唯一 ID |
| name | str | 是 | 技能名称 |
| category | str | 是 | 技能分类 |
| description | str | 否 | 技能描述 |
| source | str | 否 | 数据来源 |
| source_id | str | 否 | 原始数据源 ID |

### 3.3 Occupation：职业定义

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| occupation_id | str | 是 | 职业唯一 ID |
| name | str | 是 | 职业名称 |
| description | str | 否 | 职业描述 |
| category | str | 否 | 职业分类 |
| source | str | 否 | 数据来源 |
| source_id | str | 否 | 原始数据源 ID |

### 3.4 OccupationSkill：职业技能关联

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| occupation_id | str | 是 | 职业 ID |
| skill_id | str | 是 | 技能 ID |
| importance | float | 是 | 技能重要程度 |
| required_level | integer | 是 | 职业对技能的最低要求等级,实际值域：经过数据清洗后实际值为1-3
说明：理论值域0-4，当前数据集经IM>=3.0筛选后仅出现1-3级 |

importance 的具体取值范围和归一化方式已定（存原始 IM，值域 3.00～4.88，算法层归一化），结论见 §8。

### 3.5 Recommendation：职业推荐结果

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| occupation_id | str | 是 | 推荐职业 ID |
| occupation_name | str | 是 | 职业显示名称 |
| match_score | float | 是 | 匹配分数 |
| matched_skills | list[str] | 是 | 已匹配技能 ID |
| skills_to_improve | list[str] | 是 | 待加强技能 ID |
| skills_to_verify | list[str] | 是 | 待验证技能 ID |
| recommendation_reasons | list[str] | 是 | 推荐依据 |

match_score 的范围、计算方法及解释已定（[0.000, 1.000]，相对匹配指标），结论见 §8。

该分数是模型内部的相对匹配指标，不代表就业概率或录取概率。

### 3.6 SkillGap：能力差距

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| skill_id | str | 是 | 技能 ID |
| skill_name | str | 否 | 技能名称；第一阶段使用英文原始名称 |
| current_level | int | 是 | 用户当前能力等级 |
| required_level | int | 是 | 职业要求等级 |
| gap | int | 是 | 能力差距 |
| importance | float | 否 | O*NET 原始 IM 重要程度，非归一化百分比 |
| status | str | 是 | 能力状态 |

status 第一阶段建议采用：

- mastered：已具备
- needs_improvement：待加强
- needs_verification：待验证

gap 的计算规则需要由算法负责人确认。

### 3.7 DevelopmentPath：发展路径

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| path_id | str | 是 | 路径 ID |
| occupation_id | str | 是 | 目标职业 ID |
| nodes | list | 是 | 技能节点列表 |

DevelopmentNode：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| node_id | str | 是 | 节点 ID |
| skill_id | str | 是 | 对应技能 ID |
| name | str | 是 | 节点名称 |
| status | str | 是 | 当前状态 |
| priority | int | 否 | 优先级 |
| description | str | 否 | 学习建议 |

节点状态（2026-11-25 统一，与 schemas.py、前端 DevelopmentStatus 对齐）：

- not_started：未开始
- in_progress：进行中
- mastered：已掌握

原文列过 learning / needs_improvement / needs_verification / completed 五个值，但代码与前端
都只实现三个，且 Flutter 侧对未知枚举直接抛 ArgumentError，收到 learning 会整页崩。
故契约收敛为上述三个值：learning → in_progress，completed → mastered；
needs_improvement / needs_verification 属于能力状态（SkillGap.status），
不是学习任务状态，不再混用在同一枚举里。

已具备的能力与已完成的学习任务不是同一个概念，必要时应通过能力状态和任务状态分别表达。

### 3.8 CareerTree：发展树

`GET /api/v1/tree/{occupation_id}` 的 data 结构。三层：职业根节点 → 技能类别 → 技能。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| occupation_id | str | 是 | 职业 ID |
| occupation_name | str | 是 | 职业英文名 |
| occupation_name_zh | str | 是 | 职业中文名，缺失回退英文名 |
| root_id | str | 是 | 根节点 ID |
| node_count | int | 是 | 节点总数（含根与类别节点） |
| max_depth | int | 是 | 最大层级，当前为 2 |
| nodes | list | 是 | 节点数组 |

TreeNode：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| node_id | str | 是 | 节点 ID；技能节点为 `{occupation_id}-{skill_id}` |
| parent_id | str/null | 是 | 父节点 ID，根节点为 null |
| node_type | str | 是 | occupation / category / skill |
| level | int | 是 | 0 根、1 类别、2 技能 |
| order | int | 是 | 同一父节点下从 1 连续递增，根为 0 |
| priority | int | 是 | 全树学习顺序，从 1 递增；根与类别为 0 |
| skill_id | str/null | 是 | 仅技能节点有值 |
| skill_name | str | 是 | 显示名，技能节点为中文名（缺失回退英文） |
| name_en | str/null | 否 | 英文原名，便于与 O*NET 对照 |
| description | str | 是 | 技能节点为 O*NET 原文说明；类别节点为分组说明 |
| status | str | 是 | not_started / in_progress / mastered |
| category | str/null | 否 | essential / transferable；根节点为职业类别 |
| required_level | int/null | 否 | 0~4，仅技能节点 |
| importance | float/null | 否 | O*NET 原始 IM 1~5，仅技能节点 |

约束：只有一个根（类型 occupation、level 0）；除根外 parent_id 必须指向本树中存在的节点；
level 等于父节点 +1；父子类型必须是 occupation→category→skill（技能节点是叶子）；
同级 order 连续；任何节点沿 parent_id 上溯可达根（无环）。
技能节点数量等于 `occupation_skills.csv` 中该职业的关联记录数。

注意 `skill_id` 是"字段必填、值可为 null"：根与类别节点必须是 null，
前端解析时要按可空处理（Dart 用 `json['skill_id'] as String? ?? ''`），
否则遇到根节点会抛类型错误。

### 3.9 ApiResponse：统一接口响应

| 字段 | 类型 | 说明 |
|---|---|---|
| code | int | 业务状态码 |
| message | str | 响应说明 |
| data | object/null | 业务数据 |
| request_id | str | 请求追踪 ID |

说明：JSON 字段统一使用 snake_case，因此统一采用 request_id。

## 4. 数据关系

- 一个 UserProfile 可以包含多个 Skill。
- 一个 Occupation 可以关联多个 Skill。
- 一个 Skill 可以被多个 Occupation 使用。
- 一个 Recommendation 对应一个 Occupation。
- 一个 Recommendation 可以包含多个 SkillGap。
- 一个 DevelopmentPath 可以包含多个 DevelopmentNode。
- DevelopmentNode 通过 skill_id 关联公共 Skill。

职业和技能之间采用多对多关系。

## 5. 数据来源与可信度

不同数据来源必须保留来源信息：

- 用户自评：用户主动填写。
- 客观测试：系统测试结果。
- 项目经历：用户提供的项目成果或经历。
- 职业知识库：O*NET等公开数据。
- 招聘市场：经过许可获取的招聘岗位样本。

不能将用户自评、测试结果和项目经历直接视为相同可信度的数据。

## 6. 后续扩展模型

以下模型不作为第一阶段强制开发内容：

- SkillEvidence：能力证据。
- JobPosting：招聘岗位。
- JobSkill：岗位与技能关系。
- MarketSnapshot：市场快照。
- SkillDemand：技能需求统计。
- SkillRelation：技能前置及共享关系。
- GrowthRecord：用户成长记录。
- RecommendationHistory：历史推荐。
- UserFeedback：用户反馈。

## 7. 变更管理

公共数据结构发生修改时，需要：

1. 提出修改原因。
2. 说明受影响模块。
3. 与相关负责人确认。
4. 更新本文档。
5. 同步修改 schemas.py 和相关接口。
6. 通知所有受影响成员。

## 8. 事项结论（已定）

> 2026-11-27 收口：以下 7 条原为「待确认事项」，经 M2 赵帝臣给出结论、数据侧逐条对照代码与实测数据核实、组长确认后定稿。每条标注结论与代码依据，供测试与答辩直接引用。字段定义仍在前文各节，本节只记录口径结论。

- [x] **用户画像各字段的最终必填规则**：推荐链路的画像输入为 `ProfileInput`（`backend/packages/core/schemas.py:129`），其中 `skills` 至少 1 项，空数组或非 list 由 `_reject_empty_skills` 返回 422（`backend/packages/service/routers/recommend.py`）；`user_id` 为 `Optional[str]`，缺省时路由填 `"anonymous"`（`recommend.py:149`）。单条技能的 `self_level` 越界由 `SkillInput` 的 `ge=0/le=4` 拦成 422，不静默丢弃。§3.1 表格中的 `user_id` 必填指持久化用户模型，与推荐链路的匿名入参不是同一场景。
- [x] **技能等级量表及职业要求等级**：名义量表 0～4（§2.2）；`required_level` 经 `IM>=3.0` 清洗后当前数据集**实际值域 1～3**（1 级 3 条 / 2 级 454 条 / 3 级 35 条，共 492 条），无 0、无 4。测试造数按实际 1～3，勿按 0 造用例。
- [x] **evidence_level 的具体枚举**：共 7 值——`none / self / course / project / work / certificate / test`，定义于 `backend/packages/training/matcher.py` 的 `EVIDENCE_LEVELS` 常量。
- [x] **importance 的取值和归一化方式**：数据侧存 O\*NET 原始 IM，**实际值域 3.00～4.88**（名义 1～5，但 1、2 级无记录），不做归一化；算法层按 `(IM-1)/4` 归一化后乘 IDF 得权重（`weight = importance_norm × IDF`，`IDF = ln((1+N)/(1+df))+1`，N 为职业总数、df 为要求该技能的职业数），全程内存计算，不回写数据文件。归一化阈值 3.0 对应权重下界 0.5000，与模型卡一致。
- [x] **match_score 的计算范围**：`[0.000, 1.000]`（`schemas.py` 中 `ge=0, le=1`），全 0 级 = 0.000、全 4 级 = 1.000；是模型内部相对匹配指标，不代表就业概率或录取概率。
- [x] **DevelopmentPath 的具体生成责任**：归**后端服务层**，由路由 `backend/packages/service/routers/recommend.py:129-152` 拼装；算法层只返回 `recommendations[].skill_gaps`（含 `skill_id / gap / current_level / required_level / importance / status`），不产出路径。节点规则：仅取 `gap > 0` 的技能，`path_id = PATH-{occupation_id}`，`node_id = {occupation_id}-{skill_id}`，`priority` 按差距顺序从 1 递增，`status` 恒为 `not_started`。**注意**：当前路径是按差距排序的技能列表，不是「初级→中级→高级」的分阶段树，勿作树形阶段解读。
- [x] **原始职业数据与统一 ID 的映射方式**：统一 ID = 类型前缀 `OCC-` / `SKILL-` + `ONET-` + 原始码（如 `OCC-ONET-15-1211.00`、`SKILL-ONET-2.A.1.a`）；三表均有 `source` 与 `source_id` 保留原始 SOC / Element ID 可回溯。ID 含 `15-1211.00` 这类带小数点段，**全程按字符串处理，禁止转数值**（转 float 会丢精度）。

变更记录：2026-11-27 由 M1 高帅龙按 M2 赵帝臣结论收口，经组长确认。