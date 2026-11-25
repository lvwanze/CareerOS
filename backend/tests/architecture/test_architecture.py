"""架构测试（清单 M5 P1 / 方案 A1「架构测试」）。

用 AST 静态扫描 backend/packages/ 生产代码，检查四类架构约束：
  1. service 不依赖 training（推理调用按 ADR-009 放行，见 baseline.py）
  2. 生产代码不使用 sys.path / os.chdir（测试引导代码不在扫描范围）
  3. 数据目录推算不散落（现状 4 处登记基线，新增即失败）
  4. 数据指纹：三表 manifest 声明的 sha256 与实际 LF 字节一致

违规判定采用「显式放行清单」：扫出的越界若不在 baseline.py 登记范围内，
测试失败（构建失败）；已登记的现状放行，并在消失时提示清理基线。
本测试只读源码、不 import 生产模块，稳定且不依赖真实后端。
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest

# 本文件位于 backend/tests/architecture/，上溯两级得到 backend/
BACKEND = Path(__file__).resolve().parents[2]
PACKAGES = BACKEND / "packages"
# baseline.py 与 reference.real_data 都是同目录/邻近的本地模块，
# pytest 默认不把测试子目录加入 sys.path（rootdir 模式），此处显式加入。
# 这只影响测试进程，不触碰生产代码的路径（架构测试约束的是 packages/）。
_TESTS_DIR = str(Path(__file__).resolve().parent)
_ACCEPTANCE_DIR = str(BACKEND / "tests" / "acceptance")
sys.path.insert(0, _TESTS_DIR)
sys.path.insert(0, _ACCEPTANCE_DIR)

from baseline import allowances_for  # noqa: E402
from reference.real_data import DATASET_ROOT, MANIFEST_PATH  # noqa: E402

TABLES = ("occupations.csv", "skills.csv", "occupation_skills.csv")


def _production_modules() -> list[Path]:
    return sorted(PACKAGES.rglob("*.py"))


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(BACKEND).with_suffix("").parts)


def _imports_in(path: Path) -> set[str]:
    """返回该模块所有 import 的模块名（绝对导入，含 from ... import ...）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


# ---------------------------------------------------------------------------
# 约束 1：service 不依赖 training
# ---------------------------------------------------------------------------
def test_service_not_import_training() -> None:
    """service 层不得新增对 training 层的依赖。

    ADR-009 放行 recommend 对 inference 的推理调用（已登记基线）；
    任何**新增**的 service→training 导入都让本测试失败。
    """
    allowed = allowances_for("service_not_import_training")
    # 放行项 target 形如 "packages.service.routers.recommend -> packages.training.inference"
    # 用完整 "模块 -> 导入" 对精确匹配，避免只看末段导致误放行。
    allowed_pairs = {a.target.replace(" ", "") for a in allowed}
    violations: list[str] = []
    for path in sorted((PACKAGES / "service").rglob("*.py")):
        mod = _module_name(path)
        for imported in _imports_in(path):
            if imported.startswith("packages.training"):
                pair = f"{mod}->{imported}"
                if pair in allowed_pairs:
                    continue
                violations.append(f"{mod} -> {imported}")

    assert not violations, (
        "service 不得依赖 training（ADR-009；推理调用除外且须登记基线）。"
        f"未登记的新依赖：{violations}。若要放行，先在 baseline.py 登记并写明依据。"
    )
    # 基线有效性：登记项若已不存在，提示清理
    still_present = any(
        "packages.training.inference" in _imports_in(p)
        for p in (PACKAGES / "service").rglob("*.py")
    )
    if allowed and not still_present:
        pytest.fail("放行清单中的 service→training 越界已消失，请在 baseline.py 删除该放行项。")


# ---------------------------------------------------------------------------
# 约束 2：生产代码禁止 sys.path / os.chdir
# ---------------------------------------------------------------------------
def test_production_no_syspath_or_chdir() -> None:
    """backend/packages/ 生产代码不得改 sys.path 或调用 os.chdir。

    测试代码（conftest.py 为结构无关定位、smoke_test.py 为脚本直跑）不在
    生产包范围内，属清单点名但已说明的例外，不作为生产架构违规。
    """
    forbidden_calls = {"insert", "append", "extend", "remove"}
    violations: list[str] = []
    for path in _production_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            owner = node.func.value
            attr = node.func.attr
            # sys.path.<mutator>(...)
            if (
                isinstance(owner, ast.Attribute)
                and owner.attr == "path"
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "sys"
                and attr in forbidden_calls
            ):
                violations.append(f"{_module_name(path)}:{node.lineno} sys.path.{attr}")
            # os.chdir(...)
            if (
                attr == "chdir"
                and isinstance(owner, ast.Name)
                and owner.id == "os"
            ):
                violations.append(f"{_module_name(path)}:{node.lineno} os.chdir")

    allowed = allowances_for("production_no_syspath_chdir")
    allowed_locs = {a.target for a in allowed}
    new_violations = [v for v in violations if v.split(":")[0] not in allowed_locs]
    assert not new_violations, (
        f"生产代码禁止修改 sys.path / 调用 os.chdir：{new_violations}。"
        "测试引导代码请用 conftest 的 PYTHONPATH 机制，不要在 packages/ 下改全局路径。"
    )


# ---------------------------------------------------------------------------
# 约束 3：数据目录推算不散落
# ---------------------------------------------------------------------------
def test_data_dir_not_scattered() -> None:
    """数据目录推算点不得新增（现状 4 处已登记基线）。

    长期应收敛到一个 data/index 入口层（清单 5.2，归 M2/M3）；
    本测试锁定现状，防止继续散落。新增第 5 处即失败。
    """
    allowed = allowances_for("data_dir_not_scattered")
    allowed_count = len(allowed)
    found: list[str] = []
    for path in _production_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            # 形如 Path(__file__).resolve().parents[n] / "data"
            if not isinstance(node, ast.Attribute) or node.attr != "parents":
                continue
            if not isinstance(node.ctx, ast.Load):
                continue
            found.append(f"{_module_name(path)}:{node.lineno} parents[...]")

    assert len(found) <= allowed_count, (
        f"数据目录推算点从基线 {allowed_count} 处增加到 {len(found)} 处：{found}。"
        "请收敛到统一 data 入口层，或在 baseline.py 登记并写明依据。"
    )


# ---------------------------------------------------------------------------
# 约束 4：数据指纹
# ---------------------------------------------------------------------------
def test_data_fingerprint_intact() -> None:
    """三张冻结表的 sha256 与 manifest 声明一致（git blob LF 规范字节）。

    复用 acceptance 的 CRLF 规避策略：以 git show HEAD:<path> 的规范字节为准，
    避免 Windows core.autocrlf 检出成 CRLF 造成假失败。
    """
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest.get("status") == "frozen", "数据集须为冻结状态"
    for name in TABLES:
        declared = manifest["files"][name]["sha256"]
        path = DATASET_ROOT / manifest["files"][name]["path"]
        raw = _canonical_bytes(path)
        actual = hashlib.sha256(raw).hexdigest()
        assert actual == declared, f"{name} 数据指纹不符：声明 {declared}，实际 {actual}"


def _canonical_bytes(path: Path) -> bytes:
    """优先取 git blob 规范字节（LF），非 git 环境回落读文件。

    与 acceptance/test_data_version.py 同口径：Windows core.autocrlf 会把
    checkout 的 CSV 变成 CRLF，直接算 sha256 会假失败；git blob 才是规范字节。
    """
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return path.read_bytes()
    repo_root = Path(result.stdout.strip())
    rel = path.resolve().relative_to(repo_root).as_posix()
    blob = subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    return blob.stdout if blob.returncode == 0 else path.read_bytes()
