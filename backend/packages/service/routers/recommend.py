import csv
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from packages.core.schemas import (
	ApiResponse,
	DevelopmentNode,
	DevelopmentPath,
	RecommendationRequest,
	RecommendationsResponse,
	RecommendationsResponseData,
	SkillOption,
)
from packages.service.name_mapping import skill_zh
from packages.training.inference import generate_recommendations

router = APIRouter(prefix="/api/v1", tags=["recommend"])
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _load_used_skills() -> list[SkillOption]:
	with (DATA_DIR / "processed" / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
		used_skill_ids = {row["skill_id"] for row in csv.DictReader(file)}

	with (DATA_DIR / "processed" / "skills.csv").open(encoding="utf-8", newline="") as file:
		return [
			SkillOption(
				skill_id=row["skill_id"],
				name=row["name"],
				name_zh=skill_zh(row["skill_id"], row["name"]),
				category=row["category"],
				used_in_kb=True,
			)
			for row in csv.DictReader(file)
			if row["skill_id"] in used_skill_ids
		]


def _load_occupation_requirements() -> list[dict]:
	with (DATA_DIR / "processed" / "skills.csv").open(encoding="utf-8", newline="") as file:
		skill_names = {row["skill_id"]: row["name"] for row in csv.DictReader(file)}

	occupations = {}
	with (DATA_DIR / "processed" / "occupations.csv").open(encoding="utf-8", newline="") as file:
		for row in csv.DictReader(file):
			occupations[row["occupation_id"]] = {
				"occupation_id": row["occupation_id"],
				"occupation_name": row["name"],
				"skills": [],
			}

	with (DATA_DIR / "processed" / "occupation_skills.csv").open(encoding="utf-8", newline="") as file:
		for row in csv.DictReader(file):
			occupation = occupations.get(row["occupation_id"])
			if occupation is not None:
				occupation["skills"].append({
					"skill_id": row["skill_id"],
					"skill_name": skill_names.get(row["skill_id"], row["skill_id"]),
					"importance": float(row["importance"]),
					"required_level": int(row["required_level"]),
				})

	return list(occupations.values())


@router.get("/skills", response_model=ApiResponse)
async def list_skills():
	return ApiResponse(code=200, message="success", data=_load_used_skills())

def _reject_empty_skills(profile: dict) -> JSONResponse | None:
	"""skills 少于 1 条直接拒绝。冻结单要求至少 1 项，越界值仍走静默过滤。"""
	skills = profile.get("skills")
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
	user_skills = {
		item["skill_id"]: item["self_level"]
		for item in profile.get("skills", [])
		if isinstance(item, dict)
		and isinstance(item.get("skill_id"), str)
		and isinstance(item.get("self_level"), int)
		and 0 <= item["self_level"] <= 4
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
					name=gap.skill_name or gap.skill_id,
					status="not_started",
					priority=index,
					description=f"将技能水平从 {gap.current_level} 提升至 {gap.required_level}",
				)
				for index, gap in enumerate(gaps, start=1)
			],
		))
	return RecommendationsResponse(
		data=RecommendationsResponseData(
			user_id=profile.get("user_id", "anonymous"),
			model_version="weighted-knowledge-base-v1",
			recommendations=recommendations,
			development_paths=development_paths,
		)
	)