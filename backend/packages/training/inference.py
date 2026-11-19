from typing import Any

from packages.core.schemas import CareerRecommendation, SkillGap

def generate_recommendations(
	user_skills: dict[str, int],
	occupation_requirements: list[dict[str, Any]],
	limit: int = 5,
) -> list[CareerRecommendation]:
	if not user_skills:
		return []

	results: list[CareerRecommendation] = []
	for occupation in occupation_requirements:
		requirements = occupation["skills"]
		total_importance = sum(float(item["importance"]) for item in requirements)
		if total_importance <= 0:
			continue

		weighted_match = 0.0
		skill_gaps: list[SkillGap] = []
		matched_skills: list[str] = []
		skills_to_improve: list[str] = []
		for requirement in requirements:
			skill_id = requirement["skill_id"]
			current_level = user_skills.get(skill_id, 0)
			required_level = int(requirement["required_level"])
			importance = float(requirement["importance"])
			weighted_match += importance * min(current_level, required_level) / max(required_level, 1)
			gap = max(required_level - current_level, 0)
			status = "mastered" if gap == 0 else "needs_improvement"
			skill_gaps.append(SkillGap(
				skill_id=skill_id,
				skill_name=requirement["skill_name"],
				gap=gap,
				importance=importance,
				status=status,
				current_level=current_level,
				required_level=required_level,
			))
			if gap == 0:
				matched_skills.append(skill_id)
			else:
				skills_to_improve.append(skill_id)

		match_score = weighted_match / total_importance
		if match_score <= 0:
			continue
		skill_gaps.sort(key=lambda item: item.importance or 0, reverse=True)
		results.append(CareerRecommendation(
			occupation_id=occupation["occupation_id"],
			occupation_name=occupation["occupation_name"],
			match_score=match_score,
			skill_gaps=skill_gaps,
			recommendation_reasons=["技能匹配度基于职业技能重要度加权计算"],
			matched_skills=matched_skills,
			skills_to_improve=skills_to_improve,
			skills_to_verify=[],
		))

	results.sort(key=lambda item: item.match_score, reverse=True)
	return results[:max(0, min(limit, 5))]