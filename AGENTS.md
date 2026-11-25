# CareerOS 仓库协作规范（AGENTS.md）

> 对应老师《diabetes-risk 项目架构设计方案》能力矩阵首行「规格卡 · ADR · AGENTS.md」（标「直接复用」）、
> 组长《CareerOS 答辩验收清单》M5 P0-1。本文件与 `scripts/ci.py` 配套：
> **下面写的构建与测试命令，与质量门脚本实际执行的命令逐字一致**，改脚本 must 同步改这里。

## 1. 仓库结构

```
backend/
├── packages/
│   ├── core/         契约层：schemas.py、name_text.py
│   ├── training/     算法层：matcher.py、inference.py（matcher-v1 加权规则）
│   └── service/      服务层：main.py + routers/{health,occupations,recommend}.py
├── data/
│   ├── manifest.json   M1 冻结包元数据（status=frozen, v0.5.0, 28/35/492 行 + sha256）
│   ├── processed/      occupations.csv / skills.csv / occupation_skill.csv
│   └── reference/      中英映射两表（28 + 35 行）
├── configs/            feature_catalog.yaml（待 M1 补）
├── scripts/            数据构建/清洗脚本，train.py 待 M2 补
└── tests/
    ├── acceptance/     六层 89 条验收测试（M5 交付）
    │   └── reference/  契约模型、参考算法、stub、真实数据加载
    ├── architecture/   架构测试 4 条 + baseline.py 放行清单（M5 P1）
    └── test_*.py       后端原有单元与 smoke 测试
frontend/               Flutter 三页 + models + services
docs/                   契约、数据卡、模型卡、ADR、测试报告
scripts/ci.py           唯一质量门（本文件第 3 节）
pyproject.toml          ruff / mypy / pytest / coverage 统一配置
.github/workflows/ci.yml GitHub Actions，调用同一个 scripts/ci.py
```

## 2. 环境准备

- Python 3.11+（CI 用 3.11；本地实测 3.13）。依赖：`backend/requirements.txt`。
- 需要额外工具：`ruff`、`mypy`、`coverage`（本仓库 PyPI 官方源可装；清华源缺 ruff 时换官方源）。
- 本地推荐建 `backend/.venv` 并装好依赖；仓库根运行用该 venv 的 python。
- Windows 若 `core.autocrlf=true`，CSV 会被检出成 CRLF：`.gitattributes` 已固定数据 CSV 为 LF；
  验收测试的数据校验读 git blob 规范字节，不受影响，不要手动改工作区 CSV。

## 3. 构建与测试命令（与 ci.py 逐字一致）

**唯一质量门——一条命令跑全部五步**（仓库根目录执行）：

```bash
python scripts/ci.py
```

它依次执行（可用 `python scripts/ci.py --skip-coverage` 只跑前四步）：

| 步骤 | 实际命令（cwd=仓库根） | 配置位置 |
|---|---|---|
| 1 ruff 静态检查 | `python -m ruff check backend scripts/ci.py` | `pyproject.toml [tool.ruff]` |
| 2 mypy 类型检查 | `python -m mypy backend/packages` | `pyproject.toml [tool.mypy]` |
| 3 architecture 架构测试 | `python -m pytest backend/tests/architecture -q` | `backend/tests/architecture/` |
| 4 pytest 全量测试 | `python -m pytest backend/tests -q` | `pyproject.toml [tool.pytest]` |
| 5 coverage 覆盖率 | `python -m coverage erase` → `python -m coverage run --source=backend/packages -m pytest backend/tests -q` → `python -m coverage report` | `pyproject.toml [tool.coverage]` |

任一步失败，`scripts/ci.py` 以非零码退出。本地与 GitHub Actions 调用同一个脚本，
CI 的 workflow 见 `.github/workflows/ci.yml`（push/PR 到 main、feature、hotfix 分支触发）。
架构测试采用「基线 + 显式放行清单」：现状越界在 `backend/tests/architecture/baseline.py`
登记放行，新增越界即构建失败；详见 `docs/架构测试交付说明.md`。

实测基线（2026-11-25，基准 `453841f`）：ruff PASS / mypy PASS / architecture **4 passed** /
pytest **135 passed** / coverage 92% → 质量门全绿。

## 4. 验收测试的两种模式（重要口径）

`backend/tests/acceptance/` 是 M5 的 89 条验收测试：

- **真实后端模式**（仓库内自带 `packages/service`，或设 `CAREEROS_ROOT`）：
  接口与端到端用例正常执行 → **89 passed / 0 skipped**。
- **自检模式**（无后端，独立数据包）：依赖 `client` 的接口/端到端用例**一律 skip** → **59 passed / 30 skipped**。
  这是组长清单 P0-2「关闭假绿灯」的要求：不再退回 `reference/stub_app.py` 对自身断言产出通过状态。
  stub 只作参考实现保留，不作为验收通过依据；数据版本/映射/契约/算法/推荐层仍对 M1 真实数据执行。

**报告口径**：接口与端到端的验收结论一律以真实后端 89 passed 为准；自检模式的接口 skip 不算通过。

## 5. 提交前检查

1. 在仓库根跑 `python scripts/ci.py`，确认五步全 PASS。
2. 不要改动他人文件（生产代码 `packages/*`、数据 `data/*`）；若 ruff/mypy 报他人存量问题，
   在 `pyproject.toml` 按文件精确豁免并注明归属，不要用 `--fix` 自动改他人代码。
3. 报问题时附 commit hash，便于区分版本问题与环境问题。
4. 提交作者与负责人对应关系见后续 `.mailmap`（M5 P1，未做）。
