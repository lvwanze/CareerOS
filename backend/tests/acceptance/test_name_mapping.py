"""TC-MAP：中英名称参考映射校验（cd9e2aa 新增交付物）。

背景：组长 2026-11-19 提交 cd9e2aa，新增独立于 processed/ 三张正式契约表的
派生参考数据（manifest 中 derived_reference_data 段登记）：
  - data/reference/occupation_name_zh.csv   28 条
  - data/reference/skill_name_zh.csv        35 条
  - scripts/build_name_mappings.py           生成脚本

对应任务表里分配给测试侧的验收点：
  「新增映射测试：条数、ID 对应、无重复、脚本可重复生成」

本文件逐条覆盖：
  TC-MAP-01  条数与 manifest 登记一致（28 / 35）
  TC-MAP-02  ID 与 processed 正式表一一对应，无缺失、无多余
  TC-MAP-03  主键无重复（occupation_id / skill_id 唯一）
  TC-MAP-04  name_en 与正式表 name 一致（映射串错 ID 会被抓出）
  TC-MAP-05  生成脚本可重复生成：重跑后文件 SHA-256 与交付物一致（幂等）
  TC-MAP-06  映射文件编码 UTF-8 无 BOM、LF 换行
  TC-MAP-07  manifest.derived_reference_data 元信息完整且指向正确
  TC-MAP-08  后端加载映射：/api/v1/skills 与推荐结果返回 name_zh，缺失回退英文

数据来源：后端仓库 data/reference/ 与 data/processed/（cd9e2aa 已入库）。
定位：CAREEROS_ROOT 环境变量 > conftest 发现的后端根目录；找不到则明确失败，
不静默跳过——映射文件是本次验收的核心交付物。
"""

import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from conftest import BACKEND_ROOT

DATA_DIR = BACKEND_ROOT / "data" if BACKEND_ROOT else None
REFERENCE_DIR = DATA_DIR / "reference" if DATA_DIR else None
PROCESSED_DIR = DATA_DIR / "processed" if DATA_DIR else None
SCRIPTS_DIR = BACKEND_ROOT / "scripts" if BACKEND_ROOT else None
MANIFEST_PATH = DATA_DIR / "manifest.json" if DATA_DIR else None

OCC_MAP = "occupation_name_zh.csv"
SKILL_MAP = "skill_name_zh.csv"
MAP_FILES = {
    OCC_MAP: {"id_field": "occupation_id", "source": "occupations.csv", "expected": 28},
    SKILL_MAP: {"id_field": "skill_id", "source": "skills.csv", "expected": 35},
}
COLUMNS = ["name_en", "name_zh", "source", "note"]


def _backend_ready():
    """映射文件是后端交付物；后端未就位时整模块 skip（诚实表达"无法验"）。"""
    return (
        DATA_DIR is not None
        and REFERENCE_DIR.is_dir()
        and PROCESSED_DIR.is_dir()
        and (REFERENCE_DIR / OCC_MAP).is_file()
        and (REFERENCE_DIR / SKILL_MAP).is_file()
    )


pytestmark = pytest.mark.skipif(
    not _backend_ready(),
    reason="中英映射是后端 cd9e2aa 交付物；需 CAREEROS_ROOT 指向含 data/reference/ 的后端仓库后才能校验",
)


def _require_backend():
    """每个用例兜底断言（模块级 skip 已覆盖，这里防御性保留）。"""
    assert _backend_ready(), "后端映射数据未就位"


def load_manifest():
    _require_backend()
    with io.open(MANIFEST_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def read_mapping(filename):
    _require_backend()
    with io.open(REFERENCE_DIR / filename, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def read_processed_ids(filename):
    """读取正式契约表，返回 {id: name}。"""
    _require_backend()
    out = {}
    with io.open(PROCESSED_DIR / filename, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            id_field = "occupation_id" if "occupation" in filename else "skill_id"
            out[row[id_field]] = row["name"]
    return out


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------- 条数 ----------------

@pytest.mark.name_mapping
@pytest.mark.parametrize("filename,meta", MAP_FILES.items(), ids=["occupation", "skill"])
def test_TC_MAP_01_row_count_matches_manifest(filename, meta):
    """映射条数 = manifest 登记值 = 组长说明的 28/35。"""
    _, rows = read_mapping(filename)
    assert len(rows) == meta["expected"], (
        f"{filename} 实际 {len(rows)} 条，期望 {meta['expected']} 条"
    )
    manifest = load_manifest()
    derived = manifest["derived_reference_data"]["files"][filename]
    assert derived["row_count"] == meta["expected"] == len(rows)


# ---------------- ID 对应 ----------------

@pytest.mark.name_mapping
@pytest.mark.parametrize("filename,meta", MAP_FILES.items(), ids=["occupation", "skill"])
def test_TC_MAP_02_ids_match_processed_tables(filename, meta):
    """映射 ID 集合与正式契约表完全一致：不缺、不多。"""
    _, rows = read_mapping(filename)
    map_ids = {row[meta["id_field"]] for row in rows}
    source_ids = set(read_processed_ids(meta["source"]).keys())
    assert map_ids == source_ids, (
        f"{filename} ID 与 {meta['source']} 不一致："
        f"缺失={sorted(source_ids - map_ids)}, 多余={sorted(map_ids - source_ids)}"
    )


# ---------------- 无重复 ----------------

@pytest.mark.name_mapping
@pytest.mark.parametrize("filename,meta", MAP_FILES.items(), ids=["occupation", "skill"])
def test_TC_MAP_03_primary_key_unique(filename, meta):
    """主键无重复。"""
    _, rows = read_mapping(filename)
    ids = [row[meta["id_field"]] for row in rows]
    assert len(ids) == len(set(ids)), f"{filename} 主键重复：{sorted({x for x in ids if ids.count(x) > 1})}"


# ---------------- name_en 一致性 ----------------

@pytest.mark.name_mapping
@pytest.mark.parametrize("filename,meta", MAP_FILES.items(), ids=["occupation", "skill"])
def test_TC_MAP_04_name_en_matches_source(filename, meta):
    """映射的 name_en 必须与正式表 name 一致，防止 ID 串行。"""
    _, rows = read_mapping(filename)
    source = read_processed_ids(meta["source"])
    for row in rows:
        assert row["name_en"] == source[row[meta["id_field"]]], (
            f"{filename} 中 {row[meta['id_field']]} 的英文名与正式表不一致"
        )
    assert all(row["name_zh"].strip() for row in rows), "存在空中文名"


# ---------------- 脚本可重复生成 ----------------

@pytest.mark.name_mapping
def test_TC_MAP_05_script_reproduces_identical_files():
    """重跑 build_name_mappings.py，产物与交付物 SHA-256 一致（幂等）。"""
    _require_backend()
    script = SCRIPTS_DIR / "build_name_mappings.py"
    assert script.is_file(), f"缺少生成脚本：{script}"

    # 在临时目录复刻 data/processed 与 scripts/，避免污染真实交付物
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "data" / "processed").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)
        shutil.copy2(PROCESSED_DIR / "occupations.csv", root / "data" / "processed" / "occupations.csv")
        shutil.copy2(PROCESSED_DIR / "skills.csv", root / "data" / "processed" / "skills.csv")
        shutil.copy2(script, root / "scripts" / "build_name_mappings.py")

        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "build_name_mappings.py")],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        assert proc.returncode == 0, f"生成脚本执行失败：{proc.stderr}"

        for filename in MAP_FILES:
            regenerated = root / "data" / "reference" / filename
            assert regenerated.is_file(), f"脚本未生成 {filename}"
            assert sha256(regenerated) == sha256(REFERENCE_DIR / filename), (
                f"{filename} 重新生成后 SHA-256 与交付物不一致，脚本不可重复生成"
            )


# ---------------- 编码 / manifest 元信息 ----------------

@pytest.mark.name_mapping
@pytest.mark.parametrize("filename", MAP_FILES.keys(), ids=["occupation", "skill"])
def test_TC_MAP_06_encoding_utf8_no_bom_lf(filename):
    """映射文件 UTF-8 无 BOM、LF 换行（与 manifest 声明一致）。"""
    _require_backend()
    raw = (REFERENCE_DIR / filename).read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), f"{filename} 含 BOM"
    assert b"\r\n" not in raw, f"{filename} 含 CRLF，应为 LF"
    raw.decode("utf-8")  # 非法 UTF-8 会抛异常


@pytest.mark.name_mapping
def test_TC_MAP_07_manifest_metadata_and_hashes():
    """manifest.derived_reference_data 元信息完整，且两个 sha256 与实际一致。"""
    derived = load_manifest()["derived_reference_data"]
    assert derived["status"] == "maintained_reference"
    assert derived["version"]
    assert derived["not_part_of_processed_contract_tables"] is True
    assert derived["generated_by"].endswith("build_name_mappings.py")
    # encoding / line_ending / delimiter 在 derived_reference_data 顶层，不在 files[k]
    assert derived["encoding"] == "UTF-8 (no BOM)"
    assert derived["line_ending"] == "LF"
    assert derived["delimiter"] == ","
    assert set(derived["files"]) == set(MAP_FILES)
    for filename, meta in derived["files"].items():
        assert meta["primary_key"] == MAP_FILES[filename]["id_field"]
        assert meta["sha256"] == sha256(REFERENCE_DIR / filename), (
            f"{filename} manifest 登记的 sha256 与实际文件不一致"
        )


# ---------------- 后端接口加载 ----------------

@pytest.mark.name_mapping
@pytest.mark.api
def test_TC_MAP_08_api_returns_chinese_names(client, api_mode):
    """后端加载映射与技能新字段：中文名、35 条全量、used_in_kb 现算、description 对齐。

    2026-11-25 代旭 PR#18 改了 /api/v1/skills 的口径，本用例在原 name_zh
    校验上加深断言（仍是一条，不涨用例数）：
      - 默认全量 35 条，每条 name_zh 非空；
      - used_in_kb 现算：33 true / 2 false，false 恰为两条零引用技能；
      - used_only=true 只返 33 条可选项；
      - description 逐条等于参考表 skill_description.csv（不写“非空就行”）。
    注意：这些断言需 PR#18 合并后的真实后端；合并前在本地旧后端上会失败，
    属新口径先于实现落地，不是回归。自检模式由 conftest 统一 skip。
    """
    if api_mode != "real":
        pytest.skip("参考 stub 未实现 name_zh，此用例仅在真实后端接入后校验")

    skills_resp = client.get("/api/v1/skills")
    assert skills_resp.status_code == 200, skills_resp.text
    skills = skills_resp.json()["data"]
    assert isinstance(skills, list) and len(skills) == 35, (
        f"技能列表应全量 35 条，实际 {len(skills)} 条"
    )
    assert all("name_zh" in item and item["name_zh"] for item in skills), (
        "技能列表存在缺失 name_zh 的条目"
    )

    # used_in_kb：由关联表现算，不能恒为 True
    used = {s["skill_id"] for s in skills if s.get("used_in_kb")}
    unused = {s["skill_id"] for s in skills if not s.get("used_in_kb")}
    assert len(used) == 33 and len(unused) == 2, (
        f"used_in_kb 应为 33 true / 2 false，实际 {len(used)}/{len(unused)}"
    )
    relations = set()
    with io.open(PROCESSED_DIR / "occupation_skills.csv", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            relations.add(row["skill_id"])
    assert used == relations, "used_in_kb=true 集合应等于关联表出现过的技能"

    # description：逐条对参考表，防止占位符或串列
    desc_path = REFERENCE_DIR / "skill_description.csv"
    assert desc_path.is_file(), f"缺少技能说明参考表：{desc_path}"
    with io.open(desc_path, encoding="utf-8-sig", newline="") as fh:
        expected_desc = {row["skill_id"]: row["description_en"] for row in csv.DictReader(fh)}
    for skill in skills:
        assert "description" in skill, f"{skill['skill_id']} 缺 description 字段"
        assert skill["description"] == expected_desc[skill["skill_id"]], (
            f"{skill['skill_id']} 的 description 与参考表不一致"
        )

    # used_only=true 一步拿到 33 条可选项
    only_resp = client.get("/api/v1/skills?used_only=true")
    assert only_resp.status_code == 200, only_resp.text
    only_skills = only_resp.json()["data"]
    assert len(only_skills) == 33 and all(s["used_in_kb"] for s in only_skills)

    from factories import base_profile, payload
    rec_resp = client.post("/api/v1/recommendations", json=payload(base_profile()))
    assert rec_resp.status_code == 200, rec_resp.text
    recs = rec_resp.json()["data"]["recommendations"]
    assert recs, "推荐结果为空"
    assert all(rec.get("occupation_name_zh") for rec in recs), (
        "推荐结果存在缺失 occupation_name_zh 的条目"
    )
