"""TC-DATAV / FR-09：数据版本可追溯与完整性校验。

依据高帅龙 M1 交付包（dataset/M1_职业知识库_数据交付_v0.5.0_20261118/）
的 manifest.json 与三张 CSV，把"数据版本可追溯"从文档承诺变成可执行检查。

覆盖点：manifest 元信息、frozen 状态、三表声明、文件存在与编码、sha256、
row_count、列名顺序、主键唯一、无孤立引用、ID 格式、值域、缺失值策略、
以及两个已拍板保留的孤立技能（不判为缺陷）。

数据尚未放入共享目录时，这些用例会明确失败并提示设置 CAREEROS_DATASET_ROOT，
不会静默跳过——这正是 FR-09 要盯的事。
"""

import csv
import hashlib
import io
import json
import re
import subprocess

import pytest

from reference.real_data import DATASET_ROOT, MANIFEST_PATH

FILE_KEYS = ("occupations.csv", "skills.csv", "occupation_skills.csv")

OCC_ID_RE = re.compile(r"^OCC-ONET-\d{2}-\d{4}(?:\.\d{2})?$")
SKILL_ID_RE = re.compile(r"^SKILL-ONET-2\.[A-B]\.\d\.[a-z]$")
PLACEHOLDERS = {"null", "na", "n/a", "none", "-", "nan"}


def load_manifest():
    with io.open(MANIFEST_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def file_path(filename, manifest):
    """按 manifest 声明的 path 定位文件，顺带验证 path 字段本身。"""
    return DATASET_ROOT / manifest["files"][filename]["path"]


def canonical_bytes(filename, manifest):
    """取文件的规范字节（git blob 口径，恒为 LF）用于换行/哈希校验。

    Windows 上 core.autocrlf 会把 checkout 的 CSV 变成 CRLF，工作区字节与
    manifest 登记的 sha256（按 LF 计算）不符，属环境问题非数据缺陷。
    因此在 git 仓库内优先用 `git show HEAD:<repo-relative>` 读 blob 原文；
    非 git 环境（独立交付包）回退工作区文件。校验语义不变：仍是"数据未被改动"。
    """
    path = file_path(filename, manifest)
    try:
        # 从数据根向上找 .git，得到仓库根，再算文件相对仓库根的路径
        repo_root = None
        for base in [DATASET_ROOT] + list(DATASET_ROOT.parents)[:6]:
            if (base / ".git").exists():
                repo_root = base
                break
        if repo_root is not None:
            rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
            out = subprocess.run(
                ["git", "show", f"HEAD:{rel}"],
                capture_output=True, check=True, cwd=str(repo_root),
            ).stdout
            if out:
                return out
    except (subprocess.CalledProcessError, OSError, ValueError):
        pass
    return path.read_bytes()


def read_rows(filename, manifest):
    with io.open(file_path(filename, manifest), encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


@pytest.mark.data_version
def test_TC_DATAV_01_manifest_parses_with_required_metadata():
    """manifest 可解析，且版本追溯所需元信息齐全。"""
    manifest = load_manifest()
    required = (
        "dataset", "version", "status", "generated_at", "owner",
        "contract_version", "source", "files", "processing_log",
    )
    for key in required:
        assert key in manifest, f"manifest 缺少 {key}"
    assert manifest["version"]
    assert manifest["generated_at"]
    assert manifest["processing_log"], "处理记录为空，无法追溯数据集演进"


@pytest.mark.data_version
def test_TC_DATAV_02_dataset_is_frozen():
    """数据集必须处于 frozen 状态，且契约版本为 V1.0。"""
    manifest = load_manifest()
    assert manifest["status"] == "frozen"
    assert manifest["contract_version"] == "V1.0"


@pytest.mark.data_version
def test_TC_DATAV_03_three_files_declared_with_full_metadata():
    """三张表都在 manifest 中声明，且校验所需字段齐全。"""
    manifest = load_manifest()
    assert set(manifest["files"]) == set(FILE_KEYS)
    needed = (
        "path", "encoding", "primary_key", "columns", "row_count",
        "row_status", "sha256", "delimiter", "line_ending",
    )
    for filename in FILE_KEYS:
        meta = manifest["files"][filename]
        for key in needed:
            assert key in meta, f"{filename} 的 manifest 声明缺少 {key}"
        assert len(meta["sha256"]) == 64, f"{filename} 的 sha256 长度不对"


@pytest.mark.data_version
@pytest.mark.parametrize("filename", FILE_KEYS)
def test_TC_DATAV_04_file_exists_with_declared_encoding(filename):
    """文件存在，UTF-8 无 BOM，LF 换行，逗号分隔。"""
    manifest = load_manifest()
    meta = manifest["files"][filename]
    path = file_path(filename, manifest)
    assert path.is_file(), f"manifest 声明的文件不存在: {path}"
    raw = canonical_bytes(filename, manifest)
    assert not raw.startswith(b"\xef\xbb\xbf"), f"{filename} 含 BOM"
    assert b"\r\n" not in raw, f"{filename} 不是 LF 换行"
    assert meta["encoding"] == "UTF-8 (no BOM)"
    assert meta["line_ending"] == "LF"
    assert meta["delimiter"] == ","


@pytest.mark.data_version
@pytest.mark.parametrize("filename", FILE_KEYS)
def test_TC_DATAV_05_sha256_matches_actual_file(filename):
    """manifest 里的数据指纹必须和文件实际哈希一致。"""
    manifest = load_manifest()
    expected = manifest["files"][filename]["sha256"]
    actual = hashlib.sha256(canonical_bytes(filename, manifest)).hexdigest()
    assert actual == expected, f"{filename} 的 sha256 与文件不符：数据被改动过"


@pytest.mark.data_version
@pytest.mark.parametrize("filename", FILE_KEYS)
def test_TC_DATAV_06_row_count_matches_actual_rows(filename):
    """manifest 声明的行数与实际数据行数一致（不含表头）。"""
    manifest = load_manifest()
    _, rows = read_rows(filename, manifest)
    expected = manifest["files"][filename]["row_count"]
    assert len(rows) == expected, f"{filename} 实际 {len(rows)} 行，manifest 声明 {expected} 行"


@pytest.mark.data_version
@pytest.mark.parametrize("filename", FILE_KEYS)
def test_TC_DATAV_07_columns_match_declared_order(filename):
    """列名与顺序必须和契约/manifest 完全一致，不许多列少列。"""
    manifest = load_manifest()
    header, _ = read_rows(filename, manifest)
    assert header == manifest["files"][filename]["columns"]


@pytest.mark.data_version
def test_TC_DATAV_08_primary_keys_are_unique():
    """主键唯一：两主表 ID 唯一，关联表复合主键不重复。"""
    manifest = load_manifest()
    _, occupations = read_rows("occupations.csv", manifest)
    _, skills = read_rows("skills.csv", manifest)
    _, relations = read_rows("occupation_skills.csv", manifest)

    occ_ids = [r["occupation_id"] for r in occupations]
    skill_ids = [r["skill_id"] for r in skills]
    pairs = [(r["occupation_id"], r["skill_id"]) for r in relations]
    assert len(occ_ids) == len(set(occ_ids)), "occupations 主键重复"
    assert len(skill_ids) == len(set(skill_ids)), "skills 主键重复"
    assert len(pairs) == len(set(pairs)), "关联表存在重复的 (occupation_id, skill_id)"


@pytest.mark.data_version
def test_TC_DATAV_09_no_orphan_references():
    """关联表两端 ID 都要在主表中存在，0 孤立引用。"""
    manifest = load_manifest()
    _, occupations = read_rows("occupations.csv", manifest)
    _, skills = read_rows("skills.csv", manifest)
    _, relations = read_rows("occupation_skills.csv", manifest)

    occ_ids = {r["occupation_id"] for r in occupations}
    skill_ids = {r["skill_id"] for r in skills}
    for row in relations:
        assert row["occupation_id"] in occ_ids, f"孤立职业 ID: {row['occupation_id']}"
        assert row["skill_id"] in skill_ids, f"孤立技能 ID: {row['skill_id']}"


@pytest.mark.data_version
def test_TC_DATAV_10_id_format_and_source_id_preserved():
    """统一 ID 符合 OCC-/SKILL- 前缀格式，source_id 点号未被数值化。"""
    manifest = load_manifest()
    _, occupations = read_rows("occupations.csv", manifest)
    _, skills = read_rows("skills.csv", manifest)

    for row in occupations:
        assert OCC_ID_RE.match(row["occupation_id"]), row["occupation_id"]
        assert row["source_id"] in row["occupation_id"], "职业 source_id 未保留"
        assert row["source"] == "ONET"
    for row in skills:
        assert SKILL_ID_RE.match(row["skill_id"]), row["skill_id"]
        assert row["source_id"] in row["skill_id"], "技能 source_id 未保留"
        assert row["source"] == "ONET"


@pytest.mark.data_version
def test_TC_DATAV_11_importance_and_required_level_ranges():
    """importance 存原始 IM(1~5)，required_level 在契约 0~4 范围内。

    注意：经 IM>=3.0 筛选后 required_level 实际值域只有 1~3，
    这是数据方明确提醒的，本用例不要求"覆盖 0~4 全档位"。
    """
    manifest = load_manifest()
    _, relations = read_rows("occupation_skills.csv", manifest)
    importance = [float(r["importance"]) for r in relations]
    required = [int(r["required_level"]) for r in relations]
    assert importance and min(importance) >= 1.0 and max(importance) <= 5.0
    assert required and min(required) >= 0 and max(required) <= 4
    assert set(required) <= {1, 2, 3}, "实际值域超出数据方声明的 1~3"


@pytest.mark.data_version
def test_TC_DATAV_12_missing_values_are_empty_not_placeholder():
    """缺失值留空字符串，不写 null / NA / - 之类占位串。"""
    manifest = load_manifest()
    for filename in FILE_KEYS:
        _, rows = read_rows(filename, manifest)
        for row in rows:
            for value in row.values():
                assert (value or "").strip().lower() not in PLACEHOLDERS, (
                    f"{filename} 出现占位缺失值: {value!r}"
                )


@pytest.mark.data_version
def test_TC_DATAV_13_declared_exceptions_are_documented_not_defects():
    """2 个未关联技能与 description 全空是已拍板策略，不算数据缺陷。"""
    manifest = load_manifest()
    _, skills = read_rows("skills.csv", manifest)
    _, relations = read_rows("occupation_skills.csv", manifest)

    declared = {item["skill_id"] for item in manifest["unused_skills"]["skills"]}
    assert len(declared) == 2, "已声明的未关联技能数量变化，需重新确认"
    all_skill_ids = {r["skill_id"] for r in skills}
    linked_skill_ids = {r["skill_id"] for r in relations}
    assert declared <= all_skill_ids, "声明的未关联技能不在 skills.csv 中"
    assert not (declared & linked_skill_ids), "声明为未关联的技能实际有关联记录"

    assert "description_policy" in manifest
    assert all(r["description"] == "" for r in skills), "本期 description 应全部留空"
