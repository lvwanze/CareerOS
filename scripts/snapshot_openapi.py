#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File       : snapshot_openapi.py
# @Path       : scripts/snapshot_openapi.py
# @Project    : CareerOS
# @Author     : 2428324206代旭
# @Date       : 2026-11-26 09:00:00
# @Version    : v1.0.0
"""把 /openapi.json 落盘成 docs/interfaces.md（清单 M3 P0-2 / 契约 ④）。

为什么要有这个脚本：
    FastAPI 会自动给出 /openapi.json，但它是"运行时产物"——前端同学不开服务就
    看不到，评审老师也没法在仓库里翻。清单第 3 章表 6 的契约 ④ 要求"OpenAPI 快照
    入库、作为前后端唯一事实来源"，所以需要一份能进入 git 的物化副本。

为什么必须脚本生成、不能手写：
    手写的接口文档一定会在第 3 次改接口时过期，而"文档与实现不一致"正是契约要
    防的事。脚本生成 + 文件头写明生成命令与时间，评委一眼能看出它是不是最新。

用法（仓库根目录）：
    python scripts/snapshot_openapi.py
输出：
    docs/interfaces.md（覆盖写）
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUTPUT = ROOT / "docs" / "interfaces.md"

# 生产代码在 backend/ 下按 packages.* 组织，脚本里要把 backend 加进搜索路径，
# 才能 from packages.service.main import app。只影响本脚本进程。
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from packages.service.main import app  # noqa: E402

# 只把这些模型展开成字段表，避免整份 schema 几百行没法看
KEY_MODELS = ("ProfileInput", "RecommendationRequest", "ApiResponse")


def _model_rows(schema: dict) -> list[str]:
    """把 JSON Schema 的 properties 转成 Markdown 表格行。"""
    rows: list[str] = []
    required = set(schema.get("required") or ())
    for name, prop in (schema.get("properties") or {}).items():
        type_name = prop.get("type") or prop.get("$ref", "").rsplit("/", 1)[-1] or "object"
        if type_name == "array":
            item = prop.get("items") or {}
            inner = item.get("$ref", "").rsplit("/", 1)[-1] or item.get("type", "")
            type_name = f"array<{inner}>" if inner else "array"
        default = prop.get("default", "")
        rows.append(
            "| `{name}` | `{type_name}` | {required} | {default} | {desc} |".format(
                name=name,
                type_name=type_name,
                required="是" if name in required else "",
                default="" if default == "" else f"`{default}`",
                desc=(prop.get("description") or "").replace("|", "\\|"),
            )
        )
    return rows


def _render(spec: dict) -> str:
    """把 OpenAPI 文档渲染成 Markdown。"""
    lines: list[str] = [
        "# CareerOS 接口契约快照",
        "",
        "> 本文件由 `scripts/snapshot_openapi.py` 自动生成，**请勿手改**。",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "> 来源：`GET /openapi.json`（FastAPI 自动生成）",
        f"> OpenAPI 版本：{spec.get('openapi', '')}　服务版本：{spec.get('info', {}).get('version', '')}",
        "",
        "## 1 接口目录",
        "",
        "| 方法 | 路径 | 说明 |",
        "| --- | --- | --- |",
    ]

    for path in sorted(spec.get("paths") or {}):
        for method, operation in sorted(spec["paths"][path].items()):
            summary = operation.get("summary") or operation.get("operationId") or ""
            lines.append(f"| `{method.upper()}` | `{path}` | {summary} |")

    lines += ["", f"共 {len(spec.get('paths') or {})} 条路径。", ""]

    schemas = (spec.get("components") or {}).get("schemas") or {}
    lines += ["## 2 关键模型字段", ""]
    for model_name in KEY_MODELS:
        schema = schemas.get(model_name)
        if not schema:
            continue
        lines += [
            f"### {model_name}",
            "",
            "| 字段 | 类型 | 必填 | 默认 | 说明 |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines += _model_rows(schema) or ["| （无字段） |  |  |  |  |"]
        lines.append("")

    lines += [
        "## 3 与 api_spec.md 的关系",
        "",
        "- `docs/api_spec.md` 是**人写的约定**：为什么这么设计、错误码怎么定、字段口径怎么来。",
        "- 本文件是**机器给的现状**：服务实际暴露了哪些路径、每个模型有哪些字段。",
        "- 两者冲突时以本文件为准——契约要防的就是「文档说这样、实现是那样」。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    # TestClient 底层是 httpx，它也会走 root logger，把每个请求打成 JSON 行。
    # 这里只取一次 schema，不需要那条噪声，压到 WARNING 让终端只剩结果。
    logging.getLogger("httpx").setLevel(logging.WARNING)
    client = TestClient(app)
    response = client.get("/openapi.json")
    if response.status_code != 200:
        print(f"取 /openapi.json 失败：HTTP {response.status_code}")
        return 1

    spec = response.json()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(_render(spec), encoding="utf-8")
    print(f"已写入 {OUTPUT.relative_to(ROOT)}（路径 {len(spec.get('paths') or {})} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
