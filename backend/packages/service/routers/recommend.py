import csv
import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from packages.core.schemas import (
	ApiResponse,
	DevelopmentNode,
	DevelopmentPath,
	ProfileInput,
	RecommendationRequest,
	RecommendationsResponse,
	RecommendationsResponseData,
	SkillOption,
)
from packages.training.inference import MODEL_VERSION, generate_recommendations

router = APIRouter(prefix="/api/v1", tags=["recommend"])
logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
REFERENCE_DIR = DATA_DIR / "reference"


def _load_name_mapping(filename: str, id_field: str) -> dict[str, str]:
	"""读参考映射。文件缺失或某行没中文名时返回空表，调用方回退英文名，
	不让服务因为少一个翻译文件就整体 500。"""
	path = REFERENCE_DIR / filename
	if not path.is_file():
		logger.warning("中文名映射缺失，回退英文名：%s", path)
		return {}
	with path.open(encoding="utf-8-sig", newline="") as file:
		return {
			row[id_field]: row["name_zh"]
			for row in csv.DictReader(file)
			if row.get(id_field) and row.get("name_zh")
		}


def _load_used_skills() -> list[SkillOption]:
	skill_names_zh = _load_name_mapping("skill_name_zh.csv", "skill_id")
	with (DATA_DIR / "processed" / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
		used_skill_ids = {row["skill_id"] for row in csv.DictReader(file)}

	with (DATA_DIR / "processed" / "skills.csv").open(encoding="utf-8", newline="") as file:
		return [
			SkillOption(
				skill_id=row["skill_id"],
				name=row["name"],
				name_zh=skill_names_zh.get(row["skill_id"], row["name"]),
				category=row["category"],
				used_in_kb=True,
			)
			for row in csv.DictReader(file)
			if row["skill_id"] in used_skill_ids
		]


def _load_occupation_requirements() -> list[dict]:
	skill_names = {}
	with (DATA_DIR / "processed" / "skills.csv").open(encoding="utf-8", newline="") as file:
		skill_names = {row["skill_id"]: row["name"] for row in csv.DictReader(file)}
	skill_names_zh = _load_name_mapping("skill_name_zh.csv", "skill_id")
	occupation_names_zh = _load_name_mapping("occupation_name_zh.csv", "occupation_id")

	occupations = {}
	with (DATA_DIR / "processed" / "occupations.csv").open(encoding="utf-8", newline="") as file:
		for row in csv.DictReader(file):
			occupations[row["occupation_id"]] = {
				"occupation_id": row["occupation_id"],
				"occupation_name": row["name"],
				"occupation_name_zh": occupation_names_zh.get(row["occupation_id"], row["name"]),
				"skills": [],
			}

	with (DATA_DIR / "processed" / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
		for row in csv.DictReader(file):
			occupation = occupations.get(row["occupation_id"])
			if occupation is not None:
				occupation["skills"].append({
					"skill_id": row["skill_id"],
					"skill_name": skill_names.get(row["skill_id"], row["skill_id"]),
					"skill_name_zh": skill_names_zh.get(
						row["skill_id"], skill_names.get(row["skill_id"], row["skill_id"])
					),
					"importance": float(row["importance"]),
					"required_level": int(row["required_level"]),
				})

	return list(occupations.values())


@router.get("/skills", response_model=ApiResponse)
async def list_skills():
	return ApiResponse(code=200, message="success", data=_load_used_skills())

def _reject_empty_skills(profile: ProfileInput) -> JSONResponse | None:
	"""skills 少于 1 条直接拒绝。冻结单要求至少 1 项。

	本函数只管条数；单条技能的 self_level 越界由 ProfileInput → SkillInput
	的 ge=0/le=4 在进入路由前拦成 422，不再走过滤式静默丢弃。
	"""
	skills = profile.skills
	if isinstance(skills, list) and len(skills) >= 1:
		return None
	return JSONResponse(
		status_code=422,
		content=ApiResponse(
			code=422,
			message="请求参数不符合要求",
			data={"errors": [{"field": "profile.skills", "message": "至少填报 1 项技能"}]},
		).model_dump(),
	)


@router.post("/recommendations", response_model=RecommendationsResponse)
async def recommend(request: RecommendationRequest):
	profile = request.profile
	rejected = _reject_empty_skills(profile)
	if rejected is not None:
		return rejected
	# 等级范围由 SkillInput 保证（0～4），越界请求在进入本函数前已被 422 拦下，
	# 因此这里不再做过滤，避免"越界条目被静默丢弃、接口仍返回 200"。
	user_skills = {
		item.skill_id: {
			"level": item.self_level,
			"evidence": item.evidence_level,
		}
		for item in profile.skills
	}
	recommendations = generate_recommendations(user_skills, _load_occupation_requirements())
	development_paths = []
	for recommendation in recommendations:
		gaps = [gap for gap in recommendation.skill_gaps if gap.gap > 0]
		development_paths.append(DevelopmentPath(
			path_id=f"PATH-{recommendation.occupation_id}",
			occupation_id=recommendation.occupation_id,
			nodes=[
				DevelopmentNode(
					node_id=f"{recommendation.occupation_id}-{gap.skill_id}",
					skill_id=gap.skill_id,
					name=gap.skill_name_zh or gap.skill_name or gap.skill_id,
					status="not_started",
					priority=index,
					description=f"将技能水平从 {gap.current_level} 提升至 {gap.required_level}",
				)
				for index, gap in enumerate(gaps, start=1)
			],
		))
	return RecommendationsResponse(
		data=RecommendationsResponseData(
			user_id=profile.user_id if profile.user_id is not None else "anonymous",
			model_version=MODEL_VERSION,
			recommendations=recommendations,
			development_paths=development_paths,
		)
	)