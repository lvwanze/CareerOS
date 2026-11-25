# 质量门与 CI 交付说明（M5 / 组长清单 P0-1）

对照基准：`origin/main` `d0ea59a`。本文件说明"唯一质量门 + CI"这项 P0 的交付内容、实测证据、以及他人存量代码的处理边界。
依据新发的《CareerOS 答辩验收清单》（2026-11-25 整理稿），P0-1 除质量门与 CI 外，还要求补 `AGENTS.md`，且其中构建/测试命令须与 `ci.py` 一致——已一并交付。

## 一、新增文件（都在仓库根，本地未提交）

| 文件 | 作用 |
|---|---|
| `scripts/ci.py` | 唯一质量门：一条命令依次跑 ruff → mypy → pytest → coverage，任一步失败非零退出 |
| `pyproject.toml` | ruff / mypy / pytest / coverage 的统一配置，含他人存量文件的精确豁免及归属注释 |
| `.github/workflows/ci.yml` | GitHub Actions：push / PR 到 main、feature、hotfix 分支时跑同一个 `scripts/ci.py` |
| `.editorconfig` | 统一缩进/换行/编码，避免多人机器格式漂移 |
| `.gitattributes` | 强制文本 LF、数据 CSV/JSON 为 LF、`*.bat` 为 CRLF；根治 Windows `core.autocrlf` 造成的 CRLF 假失败 |
| `.gitignore` | 补 `.coverage` / `.coverage.*`（覆盖率报告产物不入库） |
| `AGENTS.md` | 仓库协作规范：结构、环境、构建与测试命令（与 ci.py 逐字一致）、验收两模式口径、提交前检查；对应老师能力矩阵「规格卡·ADR·AGENTS.md」直接复用项 |

## 二、实测证据（2026-11-25，本地 `backend/.venv`，Python 3.13）

命令（仓库根目录）：

```
python scripts/ci.py
```

输出汇总：

```
PASS  ruff      (exit=0)     # E4/E7/E9/F/I，全 backend + ci.py 自身
PASS  mypy      (exit=0)     # 11 个源文件，Success: no issues found
PASS  pytest    (exit=0)     # 131 passed, 1 warning（真实后端）
PASS  coverage  (exit=0)     # TOTAL 538 stmts, 92% cover
质量门全绿 ✅
```

- pytest 在两步里各跑一次（测试步骤 + 覆盖率步骤），都是 131 passed。
- 唯一 warning 是 Starlette 的 httpx 弃用提示，与本项目无关。
- CI 侧 workflow 用 `ubuntu-latest` + Python 3.11，Linux 下 CSV 天然 LF，`scripts/ci.py` 不依赖任何 Windows 特化处理。

## 三、"全绿"不是放水：规则设计与存量边界

质量门要能真挡缺陷，所以规则集选的是会抓出真实问题的项：

- **ruff** `E4/E7/E9/F/I`：E9 语法错、F821 未定义名、F811 重名这类会直接挡住所有文件（包括他人文件）；只把 F401（未用导入）、I001（导入顺序）、F541、E731 这几类纯格式/无行为影响的问题，对**他人存量文件**按文件豁免。
- **mypy**：对 4 个存在存量类型债的生产模块（schemas / matcher / recommend / health）设 `ignore_errors`，其余模块真实检查；注释写明"负责人修好后删除 override"。
- 豁免清单逐条写在 `pyproject.toml`，全部标注了归属成员（M1/M2/M3），不是无声跳过。

**M5 自有的 `backend/tests/acceptance/` 没有豁免**，6 个测试文件的导入顺序/未用导入已实际修复，89 条验收用例在修复后仍全过。

越界防护：过程中 ruff `--fix` 曾自动改动他人生产/测试文件，已全部 `git checkout` 还原；最终 `git status` 里除 `pyproject.toml` 的豁免配置外，没有他人生产代码的改动。

## 四、与组长清单其他项的关系

- `.gitattributes` 同时覆盖 M1-P0-1「固定 CSV 行尾」的基础设施需求：新 clone 后 CSV 为 LF，`sha256sum` 与 manifest 一致。M1 若已单独提交同类文件，合并时保留其一即可。
- pytest 的 131 passed 与清单附录"106 个 test_ 函数"是同一批测试的不同数法：106 是函数数，参数化展开后为 131 个用例（其中验收套件 89 条）。
- P0-2「关闭假绿灯」已按组长清单完成（详见 `docs/测试执行结果.md` 2.3.1）：自检模式下依赖 `client` 的接口/端到端用例统一 skip（59 passed / 30 skipped），不再对参考 stub 自证通过；真实后端模式仍 89 passed、全量 131 passed，质量门不受影响。该项独立于本质量门。

## 五、待用户操作

1. 本轮全部改动为本地未提交状态，由用户决定 commit / push。
2. push 后 GitHub Actions 会在 PR 上跑出绿色检查，即完成组长"PR 显示绿色检查"的验收；这一步需要在 GitHub 上确认。
3. CI 用 Python 3.11，本地实测用 3.13；两端依赖版本范围一致（requirements.txt），若 CI 首次跑出版本相关问题，按 workflow 日志微调后重跑。
