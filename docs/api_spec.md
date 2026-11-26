# CareerOS API 接口规范 V1.0

## 1. 基本约定

后端框架：FastAPI

接口版本：V1

基础路径：

/api/v1

数据格式：JSON

字符编码：UTF-8

请求方式：RESTful 风格。

## 2. 统一响应结构

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "request_id": "req_xxx"
}
```

失败响应：

```json
{
  "code": 422,
  "message": "请求参数不符合要求",
  "data": null,
  "request_id": "req_xxx"
}
```

注意：

- HTTP 状态码表示 HTTP 请求处理状态。
- code 表示业务处理状态。
- Flutter 必须同时检查 HTTP 状态码和业务 code。
- request_id 用于问题追踪。
- FastAPI 自动生成的错误响应需要根据统一规范进行封装。
- 已统一：参数校验 422、未匹配路由 404、方法不允许 405、未捕获异常 500 均返回上述信封，不再出现 `{"detail": ...}`。例外只有探针 `/health` 与 `/ready`，它们按运维约定保持裸结构（见 3.4、3.8）。
- 校验失败时 `data.errors` 为数组，每项形如 `{"field": "profile.skills.0.skill_id", "message": "..."}`。`field` 使用点分路径，数组下标单独作为一段。

## 3. 第一阶段核心接口

### 3.1 职业推荐

POST /api/v1/recommendations

用途：

接收用户画像，调用职业匹配算法，返回职业推荐结果、能力差距及发展路径。

请求示例（`skills` 至少 1 项，`skill_id` 必须取自 `GET /api/v1/skills`）：

```json
{
  "profile": {
    "user_id": "user_001",
    "learning_stage": {},
    "preferences": {},
    "skills": [
      {"skill_id": "SKILL-ONET-2.A.1.a", "self_level": 2, "evidence_level": "课程作业"},
      {"skill_id": "SKILL-ONET-2.B.3.e", "self_level": 3, "evidence_level": "实习"}
    ],
    "constraints": {},
    "career_goals": {}
  }
}
```

`learning_stage` / `preferences` / `constraints` / `career_goals` 目前原样接收但不参与计算，保留在示例里是为了说明前端画像字段不会被丢弃。

校验失败示例（HTTP 422，`data.errors` 按字段逐条定位）：

```json
{
  "code": 422,
  "message": "请求参数不符合要求",
  "data": {
    "errors": [
      {"field": "profile.skills.0.skill_id", "message": "技能 ID 不存在：SKILL-XXX"},
      {"field": "profile.skills.1.self_level", "message": "不能大于 4"}
    ]
  },
  "request_id": "req_002"
}
```

同一层校验内的错误一次返回全部，前端按 `field` 定位到对应输入框即可。校验分两层：先由 Pydantic 检查结构、类型与等级范围（0～4），全部通过后才查技能 ID 是否存在于知识库；因此两类错误同时出现时会先报前者，改完再提交才会看到后者。

成功响应示例：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "recommendations": [],
    "development_paths": []
  },
  "request_id": "req_001"
}
```

### 3.2 职业列表

GET /api/v1/occupations

用途：

获取系统当前支持的职业列表。

响应数据：

- occupation_id
- name
- name_zh（中文名称，映射缺失时回退为 name）
- category
- skill_count

列表响应形状为 `{"items": [...], "total": 28}`。为控制响应体积，列表项不含 description 与 skills，详细信息走 3.3。

是否第一阶段实现：已实现。

### 3.3 职业详情

GET /api/v1/occupations/{occupation_id}

用途：

获取职业详情和关联技能要求。

响应数据：

- 职业基本信息（occupation_id / name / name_zh / description / category / skill_count）。
- 关联技能（skill_id / name / name_zh / category）。
- 技能重要程度（importance，O\*NET 原始 IM 值，1~5 不归一化）。
- 技能要求等级（required_level，0~4）。
- 关联技能按 importance 降序排列。
- 职业不存在时返回 HTTP 404，响应体仍为统一信封（code=404、data=null），不返回 `{"detail": ...}`。

是否第一阶段实现：已实现。

### 3.4 健康检查

GET /health

用途：

检查后端服务是否正常启动。

响应示例：

```json
{
  "status": "ok"
}
```

### 3.5 可用技能

GET /api/v1/skills

用途：

获取知识库技能词表。默认返回**全量 35 条**，每条的 `used_in_kb` 由后端按
`occupation_skills.csv` 现算，表示该技能是否至少关联一个职业。

查询参数：

- `used_only`（可选，布尔，默认 `false`）：`true` 时只返回 `used_in_kb=true` 的 33 条，
  前端技能选择可直接用这个参数，不必自己再过滤。

响应数据项：

- skill_id
- name（英文原始名称）
- name_zh（中文显示名称，由后端参考映射提供，缺失时回退 name）
- category（essential / transferable）
- used_in_kb（现算：词表 35 条中 33 条为 true，Equipment Selection、Installation 两条为 false）
- description（技能英文说明，O\*NET 31.0 Content Model Reference 原文，
  取自 `data/reference/skill_description.csv`）

口径说明：

- `used_in_kb` 以前写死 `true` 并把零引用技能直接过滤掉，字段恒真、信息量为零。
  现在改为全量返回 + 逐条标注：前端照旧按 `used_in_kb=true` 过滤即可还原 33 条可选项，
  也能看到"这两条为什么不在我这边"。
- `description` 不在冻结表 `skills.csv` 里补（该表已冻结，description 列按 manifest
  的 description_policy 留空），改由参考层提供，与中文名映射同一种做法。
- 中文技能说明不在本期范围（2026-11-26 组内确认）：该字段仅用于详情展示、不参与匹配
  打分，翻译需术语审校与数据责任人，改由前端用 `name_zh` 承担中文呈现。

### 3.6 发展树

GET /api/v1/tree/{occupation_id}

用途：

按职业返回可解释的学习发展树：**职业根节点 → 技能类别 → 技能**，三层（level 0~2）。

结构规则：

- 只有一个根节点，`parent_id` 为 `null`，`node_id` 形如 `TREE-OCC-ONET-15-2051.00`。
- 第二层按 O\*NET 的技能两分法分组：`essential`（基本技能）、`transferable`（跨职能技能）；
  只保留该职业实际有技能的组。
- 父子关系固定为 occupation → category → skill，技能节点是叶子（不会再带子节点）；
- 第三层是技能节点，父节点为该组；同级按 importance 降序、required_level 降序、skill_id 升序排列，
  `order` 从 1 连续递增；`priority` 是全树学习顺序（1 开始）。
- 技能节点数量等于 `occupation_skills.csv` 中该职业的关联记录数，不放任何写死的节点。
- `status` 统一为 `not_started`：本接口描述"这个职业要求什么"，个人进度由前端本地持久化，
  不写进知识库（两边都存会出现"接口说已掌握、用户说没学过"的冲突）。

响应数据（`data`）：

- occupation_id / occupation_name / occupation_name_zh
- root_id（根节点 ID）
- node_count（含根与类别节点的总数）
- max_depth（当前为 2）
- nodes：节点数组，字段见 data_contract.md §3.8

节点字段：

- node_id / parent_id / node_type（occupation / category / skill）
- level（0/1/2）、order（同级从 1）、priority（全树学习顺序）
- skill_id（仅技能节点有值，根与类别节点为 `null`）
- skill_name（显示名，技能节点为中文名）、name_en（英文原名）
- description（技能节点为 O\*NET 原文说明，类别节点为分组说明）
- status（not_started / in_progress / mastered）
- category、required_level（0~4）、importance（O\*NET 原始 IM 1~5）

异常：

- 职业不存在返回 HTTP 404，统一信封（`code=404`、`data=null`），不返回空树——
  空树会被前端当成"该职业没有技能要求"，与"ID 写错"分不清。

旧路径：

- `GET /v1/tree/{occupation_id}` 保留可用（缺 `/api` 前缀的历史写法），响应体与正式路径
  一致，响应头带 `Deprecation: true` 与 `Link: </api/v1/tree/{id}>; rel="successor-version"`；
  下个版本摘除。
- 标注原因与现状（2026-11-26 复核）：该路径是历史遗留，**前端已不再调用**
  （`frontend/lib/services/api_service.dart` 现只请求 `/api/v1/recommendations`、
  `/api/v1/skills`、`/api/v1/occupations`），保留一个版本仅为兼容早期调用方。
  本路径 `include_in_schema=False`，不进 `/openapi.json` 与 `docs/interfaces.md`，
  避免前端照着旧路径写代码。

### 3.7 服务索引

GET /

用途：

浏览器直接打开服务地址时给出可用路由清单，避免看到 404 误判服务没启动。

响应为统一信封，`data` 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "service": "CareerOS API",
    "docs": "/docs",
    "routes": ["GET  /health", "GET  /ready", "POST /api/v1/recommendations", "..."]
  },
  "request_id": "req_003"
}
```

根路径不是业务接口，但会出现在 `/docs` 里被当成接口调用，因此同样遵守统一信封。

### 3.8 就绪探针

GET /ready

用途：

判断知识库三张表是否可读（文件在、列齐、行数非空、关联表无孤儿外键）。

- 就绪：HTTP 200，`status=ready`，附三表行数。
- 未就绪：HTTP 503，`status=not_ready`，附 `reason`。
- 与 `/health` 一致，按运维探针约定保持裸结构，不套统一信封。
- `?refresh=1` 跳过 10 秒缓存强制重查。

## 4. 推荐结果字段

recommendations：

- occupation_id
- occupation_name
- occupation_name_zh（中文显示名称，由后端参考映射提供）
- match_score
- skill_name_zh（技能差距中的中文显示名称，由后端参考映射提供）
- matched_skills
- skills_to_improve
- skills_to_verify
- recommendation_reasons

development_paths：

- path_id
- occupation_id
- nodes

nodes：

- node_id
- skill_id
- name（优先返回中文显示名）
- status
- priority
- description

具体字段以 data_contract.md 为准。

注意：`development_paths` 是"这一次推荐结果里的缺口顺序"，随画像变化；
`GET /api/v1/tree/{occupation_id}`（§3.6）是"这个职业要求什么"的完整三层树，与画像无关。
两者不要混用：前端画发展树用 §3.6，画本次推荐的缺口清单用 `development_paths`。

## 5. 错误处理

建议统一处理：

| HTTP 状态码 | 场景 |
|---|---|
| 200 | 请求成功 |
| 400 | 请求业务条件不满足 |
| 404 | 目标资源不存在 |
| 422 | 参数格式或数据校验失败 |
| 500 | 服务器内部异常 |

错误响应不得直接暴露服务器内部堆栈、密钥或敏感信息。

## 6. 参数校验

后端使用 Pydantic 定义请求模型。

至少校验：

- 必填字段是否存在：缺失时 422，`field` 指向缺字段。
- 字段类型是否正确。
- 技能等级是否在 0～4 范围：越界即 422（`profile.skills.{下标}.self_level`），不再静默按 0 处理。
- 技能 ID 是否有效：`skill_id` 必须存在于知识库技能表（当前 35 条）；空串、或技能表里没有的 ID 返回 422（`profile.skills.{下标}.skill_id`）。前端可选项以 `GET /api/v1/skills?used_only=true` 返回的 33 条为准（不带参数返回全量 35 条）。
- 技能列表是否非空：`skills` 至少 1 项，空数组返回 422。
- 列表字段是否符合要求。
- 数值字段是否处于合理范围。

以上校验统一按第 2 节的信封格式返回。同一层内的错误一次列出全部，不逐条试错；层级顺序见 3.1（Pydantic 结构与范围 → 知识库 ID 存在性）。

## 7. 前后端交接约定

后端负责人代旭：

- 提供可访问的 API 地址。
- 提供请求和响应示例。
- 提供启动说明。
- 说明接口是否已部署。
- 提供测试数据。

前端负责人吕宛泽：

- 根据接口规范编写请求模型。
- 处理加载、成功、失败状态。
- 检查 HTTP 状态码和业务 code。
- 不擅自修改字段名称。
- 接口未部署时使用 Mock 数据。

## 8. 接口版本管理

第一阶段统一使用 /api/v1。

公共字段发生不兼容变化时，需要同步通知前后端成员，并更新接口文档。

## 9. 待确认事项

- 推荐接口最终请求结构。
- 推荐结果是否需要单独返回 SkillGap。
- 发展路径由后端组织还是算法直接返回。
- 是否需要用户画像独立保存接口。
- 是否需要职业列表与详情接口。
- request_id 的生成方式。
- 统一错误响应的具体实现方式。