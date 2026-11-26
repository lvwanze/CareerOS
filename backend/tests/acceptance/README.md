# 后端验收测试套件（acceptance）

测试与报告：薛宏博。六层 89 条验收用例，**只新增本目录，不改任何生产代码和接口**。

## 一、这个目录测什么

| 层 | 文件 | 条数 | 覆盖 |
|---|---|---:|---|
| 数据版本 | `test_data_version.py` | 21 | M1 冻结包的 manifest、sha256、行数、主键唯一、无孤立引用 |
| 中英映射 | `test_name_mapping.py` | 13 | 技能/职业中英映射条数、ID 对应、接口中文字段 |
| 契约 | `test_contract.py` | 23 | 字段必填、类型、枚举、命名规范 |
| 接口与异常 | `test_api.py` | 15 | 四个接口正常流程 + 异常边界（含 `self_level` 类型、status 结构） |
| 算法与推荐 | `test_algorithm.py`、`test_recommendation.py` | 15 | 分数范围、确定性、典型画像、发展树 |
| 端到端 | `test_e2e.py` | 2 | 从画像到推荐结果、发展路径整链 |

`reference/`：契约模型、参考算法、参考 stub、真实数据加载；`conftest.py` 自动发现后端与数据；`factories.py` 造样本。

## 二、怎么跑（在 `backend/` 目录下，无需环境变量）

```bash
python -m pytest tests/acceptance -q
```

依赖见 `backend/requirements.txt`：pytest / httpx / pandas / numpy / fastapi。

- **接了真实后端**（仓库 clone 后自带 `packages/service`，或设 `CAREEROS_ROOT=<后端路径>`）：自动用真实 app，跑 **89 passed**（接口用例正常执行）。
- **没接后端**（独立数据包/自检）：跑 **59 passed / 30 skipped**。依赖 `client` 的接口与端到端用例在自检模式下**一律 skip，不对参考 stub 自证通过**（清单 P0-2 关闭假绿灯）；通过的数据版本/静态映射/契约/算法/推荐层仍对 M1 真实交付数据执行。stub 仅作为参考实现保留，不作为验收通过依据。

跑全量（`backend/` 下）确认和后端原有测试无冲突：

```bash
python -m pytest tests -q
```

## 三、实测结果（基准 main `d925839`，2026-11-24）

```
python -m pytest tests/acceptance -q   →  89 passed / 0 failed
python -m pytest tests -q              →  131 passed   （含后端原有测试）
```

自检模式（无后端）：59 passed / 30 skipped（P0-2 关闭假绿灯后，接口用例全部 skip）。

> 环境提示：Windows 若设了 `core.autocrlf=true`，CSV 会被检出成 CRLF，导致后端原有 `test_name_mapping` 出现 4 条换行假失败；本套件的数据校验读 git blob 规范字节，不受影响，CI（Linux/LF）不复现。

## 四、几个口径（改用例前先看）

- `self_level` 必须是真整数：字符串 `"3"`、浮点 `3.0`、布尔 `true` 都返回 422（TC-EX-06，同一用例内循环，不拆条数）。
- `request_id` 必须是 `req_` 前缀（TC-API-04），对齐 `api_spec.md`。
- 节点 `status` 已收口为 3 档（`not_started`/`in_progress`/`mastered`）：2026-11-25 代旭 PR#18 把 `data_contract.md §3.7` 从旧 5 档改为 3 档，与 `schemas.py` 和 Flutter 枚举一致。TC-DATA-12 与 TC-API-05/06 按 3 档断言；注意旧 5 档语义中 `needs_improvement`/`needs_verification` 属 SkillGap（能力状态），不与任务状态混用。
- 技能列表口径（PR#18）：默认全量 35 条，`used_in_kb` 现算（33 true / 2 false），`description` 逐条对 `reference/skill_description.csv`，`?used_only=true` 返 33 条。TC-MAP-08 已覆盖。
- 发展树口径（PR#18）：`/api/v1/tree/{id}` 为正式路径，旧 `/v1/tree/{id}` 保留并带 `Deprecation` 头；未知职业 404，不再返回 mock。TC-API-06 已按真实结构断言。
- `user_id` 必填、`goal_description` 上限 2000 字：规则已定、代码 pending，相关用例暂按兜底断言，落地后收紧。

> **口径先行说明**：TC-API-06 / TC-MAP-08 的新断言按 PR#18 写好，PR 合并前在本地旧后端上会失败，属新口径先于实现落地，不是回归；自检模式因无真实 app 一律 skip，不会掩盖这一差异。合并后须在真实后端复跑确认。

维护与决策理由见同目录外的《测试侧决策记录.md》。
