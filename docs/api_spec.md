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

## 3. 第一阶段核心接口

### 3.1 职业推荐

POST /api/v1/recommendations

用途：

接收用户画像，调用职业匹配算法，返回职业推荐结果、能力差距及发展路径。

请求示例：

```json
{
  "profile": {
    "user_id": "user_001",
    "learning_stage": {},
    "preferences": {},
    "skills": [],
    "constraints": {},
    "career_goals": {}
  }
}
```

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

获取当前知识库中至少关联一个职业的技能，前端技能选择和展示仅使用 `used_in_kb=true` 的条目。零引用词表项不返回。

响应数据项：

- skill_id
- name（英文原始名称）
- name_zh（中文名称，映射缺失时回退为 name）
- category
- used_in_kb（当前返回项均为 true）

## 4. 推荐结果字段

recommendations：

- occupation_id
- occupation_name
- match_score
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
- name
- status
- priority
- description

具体字段以 data_contract.md 为准。

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

- 必填字段是否存在。
- 字段类型是否正确。
- 技能等级是否在 0～4 范围。
- 职业和技能 ID 是否有效。
- 列表字段是否符合要求。
- 数值字段是否处于合理范围。

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