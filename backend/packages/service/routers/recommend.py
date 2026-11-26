import logging

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

# 相对导入（.. 即 packages.service）：写成 from packages.service import knowledge 时，
# ruff 的 first-party 探测会把 packages.service 判成本地包、把 packages.training 判成三方包，
# 两个导入因此被要求分组加空行；而这个探测依赖运行目录，CI 与本机给出相反结论。
# 相对导入固定归入 local 组，不受探测影响，两边判断一致。
from .. import knowledge

router = APIRouter(prefix="/api/v1", tags=["recommend"])
logger = logging.getLogger(__name__)


def _load_skill_catalog(used_only: bool = False) -> list[SkillOption]:
	"""技能列表。默认全量 35 条并逐条标注 used_in_kb；used_only=True 只给可选项。

	读表与中文名回退统一走 knowledge.py——技能列表、职业详情、发展树三处
	各读各的，迟早会出现同一技能在三个接口里三种写法。
	"""
	return knowledge.load_skill_options(used_only=used_only)


@router.get("/skills", response_model=ApiResponse)
async def list_skills(used_only: bool = False):
	"""可用技能列表，对齐 api_spec §3.5。

	为什么默认返回 35 条而不是 33 条：used_in_kb 以前写死 True，两条零引用技能
	（Equipment Selection、Installation）被直接过滤掉，字段恒真等于没有信息量，
	前端也无从知道这两条为什么不在列表里。现在全量返回、逐条现算标注，
	前端照旧按 used_in_kb=true 过滤即可还原成 33 条可选项。
	"""
	return ApiResponse(code=200, message="success", data=_load_skill_catalog(used_only=used_only))


def _load_known_skill_ids() -> set[str]:
	"""知识库技能表全量 ID（35 条），不是只认被职业引用的 33 条。

	零引用技能传进来不会得出错误结论，只是不贡献分数；「技能表里根本没有」
	才是请求错误。前端可选项以 GET /api/v1/skills?used_only=true 为准。
	"""
	return knowledge.load_skill_ids()


def _load_occupation_requirements() -> list[dict]:
	"""推荐算法输入：每个职业 + 它的技能要求（含 IM 与要求等级）。"""
	return knowledge.load_occupation_requirements()



def _reject_unknown_skill_ids(profile: ProfileInput) -> JSONResponse | None:
	"""技能 ID 必须存在于知识库。

	模型层只能保证 skill_id 是字符串，拼错的 ID 会一路进到算法，因匹配不到任何
	职业要求而贡献 0 分，接口却返回 200 —— 与「越界等级被静默丢弃」是同一类问题：
	调用方以为数据生效了，实际没有。这里按条目定位，一次列出全部无效 ID。
	"""
	known_skill_ids = _load_known_skill_ids()
	errors = [
		{
			"field": f"profile.skills.{index}.skill_id",
			"message": f"技能 ID 不存在：{item.skill_id}",
		}
		for index, item in enumerate(profile.skills)
		if item.skill_id not in known_skill_ids
	]
	if not errors:
		return None
	return JSONResponse(
		status_code=422,
		content=ApiResponse(
			code=422,
			message="请求参数不符合要求",
			data={"errors": errors},
		).model_dump(),
	)


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
	invalid = _reject_unknown_skill_ids(profile)
	if invalid is not None:
		return invalid
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