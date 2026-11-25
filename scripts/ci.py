#!/usr/bin/env python3
"""CareerOS 唯一质量门（方案 A1 / 组长清单 P0-1）。

一条命令依次跑：ruff → mypy → architecture → pytest → coverage，任一步失败即以非零码退出。
本地与 CI（GitHub Actions）调用同一个脚本，杜绝"本地绿灯、CI 红灯"。

用法（仓库根目录）：
    python scripts/ci.py                 # 全量五步
    python scripts/ci.py --skip-coverage # 只跑前四步（lint/type/architecture/test）

设计说明：
    * ruff：抓真缺陷（E4/E7/E9/F/I），他人存量文件在 pyproject 精确豁免。
    * mypy：生产代码类型检查，存量类型债在 pyproject overrides 豁免。
    * architecture：架构测试（清单 P1）。AST 扫描生产代码，检查分层依赖、
      sys.path/os.chdir、数据目录推算与数据指纹。已登记现状在 baseline.py 放行，
      新增越界即失败；先于 pytest 拦截架构违规。
    * pytest：真实后端全量测试（含 architecture）。CI/仓库内有 packages/service，
      自动用真实 app；独立自检（无后端）时依赖 client 的接口用例按清单 P0-2
      一律 skip，不对参考 stub 自证通过。
      数据 CSV 行尾由 .gitattributes 固定为 LF；验收测试另走 git blob 读规范字节，
      因此 Windows core.autocrlf 的 CRLF 不会造成假失败。
    * coverage：输出覆盖率报告用于追踪，不设硬阈值（当前基线约 92%）。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PY = sys.executable


def step(title: str) -> None:
    print(f"\n{'=' * 68}\n>>> {title}\n{'=' * 68}", flush=True)


def run(args: list[str]) -> int:
    print(f"$ {' '.join(args)}", flush=True)
    return subprocess.run(args, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="CareerOS 唯一质量门")
    parser.add_argument("--skip-coverage", action="store_true", help="跳过覆盖率步骤")
    args = parser.parse_args()

    # 让 Python 把 backend/ 当源码根，保证 packages.* / factories 等可导入
    env_pythonpath = str(BACKEND)
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = (
        env_pythonpath + os.pathsep + existing if existing else env_pythonpath
    )
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    results: list[tuple[str, int]] = []

    step("1/5  Ruff — 静态检查")
    results.append(("ruff", run([PY, "-m", "ruff", "check", "backend", "scripts/ci.py"])))

    step("2/5  Mypy — 类型检查")
    results.append(("mypy", run([PY, "-m", "mypy", "backend/packages"])))

    step("3/5  Architecture — 架构约束")
    results.append((
        "architecture",
        run([PY, "-m", "pytest", "backend/tests/architecture", "-q"]),
    ))

    step("4/5  Pytest — 全量测试（含架构）")
    results.append(("pytest", run([PY, "-m", "pytest", "backend/tests", "-q"])))

    if not args.skip_coverage:
        step("5/5  Coverage — 覆盖率")
        run([PY, "-m", "coverage", "erase"])
        run([
            PY, "-m", "coverage", "run", "--source=backend/packages",
            "-m", "pytest", "backend/tests", "-q",
        ])
        results.append(("coverage", run([PY, "-m", "coverage", "report"])))

    step("结果汇总")
    failed = [(name, code) for name, code in results if code != 0]
    for name, code in results:
        print(f"  {'PASS' if code == 0 else 'FAIL'}  {name} (exit={code})")

    if failed:
        print(f"\n质量门失败：{', '.join(n for n, _ in failed)}")
        return 1
    print("\n质量门全绿 ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
