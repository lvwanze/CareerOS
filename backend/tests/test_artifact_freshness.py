"""接住两个「写了没跑」的校验脚本，让产物过期即令质量门变红（M5 收尾第 4 条）。

- `check_feature_catalog.py`：校验 configs/feature_catalog.yaml 的三表列名与
  data/processed 表头一致。这里直接调它的 main()，返回非 0 即失败。
- `snapshot_openapi.py`：把 /openapi.json 渲染成 docs/interfaces.md。这里复用它的
  `_render()` 在内存重生成，与入库文件逐字节比对，不一致即失败（不写盘）。
  这样「接口改了但快照没重生成」会在 pytest 步骤被拦住，而不是悄悄过期。

两个脚本都属他人交付物（M1/M3），本文件只读调用，不改它们的源码。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SNAPSHOT = ROOT / "scripts" / "snapshot_openapi.py"
INTERFACES = ROOT / "docs" / "interfaces.md"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_feature_catalog_matches_processed_tables() -> None:
    """特征目录三表列名与 data/processed 表头必须一一对应。"""
    script = BACKEND / "scripts" / "check_feature_catalog.py"
    module = _load(script, "_check_feature_catalog")
    assert module.main() == 0, "feature_catalog.yaml 与成品表列名不一致"


def test_openapi_snapshot_not_stale() -> None:
    """docs/interfaces.md 必须等于当前 app 的 /openapi.json 渲染结果。"""
    # 让 snapshot 脚本的 backend 路径注入生效（它 import packages.service.main）
    for path in (str(BACKEND), str(ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    module = _load(SNAPSHOT, "_snapshot_openapi_for_test")

    from fastapi.testclient import TestClient

    client = TestClient(module.app)
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    rendered = module._render(response.json())  # noqa: SLF001 - 稳定内部函数，测试内存比对

    assert INTERFACES.exists(), "docs/interfaces.md 不存在，请先跑 snapshot_openapi.py"
    on_disk = INTERFACES.read_text(encoding="utf-8")

    # 生成时间戳每次运行都会变，比对时剔除该行；其余内容（路径、模型字段）必须逐字一致。
    def strip_timestamp(text: str) -> str:
        return "\n".join(
            line for line in text.splitlines() if not line.startswith("> 生成时间：")
        )

    assert strip_timestamp(on_disk) == strip_timestamp(rendered), (
        "docs/interfaces.md 已过期：接口变更未同步快照，"
        "请在仓库根运行 `python scripts/snapshot_openapi.py` 后随 PR 提交"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
