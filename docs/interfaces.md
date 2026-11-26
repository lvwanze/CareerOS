# CareerOS 接口契约快照

> 本文件由 `scripts/snapshot_openapi.py` 自动生成，**请勿手改**。
> 生成时间：2026-11-26 10:22
> 来源：`GET /openapi.json`（FastAPI 自动生成）
> OpenAPI 版本：3.1.0　服务版本：0.1.0

## 1 接口目录

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | Show Route Index |
| `GET` | `/api/v1/occupations` | List Occupations |
| `GET` | `/api/v1/occupations/{occupation_id}` | Get Occupation |
| `POST` | `/api/v1/recommendations` | Recommend |
| `GET` | `/api/v1/skills` | List Skills |
| `GET` | `/api/v1/tree/{occupation_id}` | 获取指定职业的发展树（职业根 → 技能类别 → 技能） |
| `GET` | `/health` | Health Check |
| `GET` | `/ready` | Readiness Check |

共 8 条路径。

## 2 关键模型字段

### ProfileInput

| 字段 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `user_id` | `object` |  |  | 用户ID |
| `skills` | `array<SkillInput>` |  |  | 技能自评列表 |

### RecommendationRequest

| 字段 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `profile` | `ProfileInput` |  |  |  |

### ApiResponse

| 字段 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `code` | `integer` |  | `200` | 状态码 |
| `message` | `string` |  | `success` | 提示信息 |
| `data` | `object` | 是 |  | 业务数据 |
| `request_id` | `string` |  |  | 请求唯一标识 |

## 3 与 api_spec.md 的关系

- `docs/api_spec.md` 是**人写的约定**：为什么这么设计、错误码怎么定、字段口径怎么来。
- 本文件是**机器给的现状**：服务实际暴露了哪些路径、每个模型有哪些字段。
- 两者冲突时以本文件为准——契约要防的就是「文档说这样、实现是那样」。
