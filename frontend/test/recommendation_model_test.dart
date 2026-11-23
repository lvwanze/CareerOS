import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/models/recommendation.dart';

/// 用 2026-11-23 从 /api/v1/recommendations 抓到的真实结构做解析测试。
/// 真实 ID 是 `SKILL-ONET-2.A.1.a` 这种，别用文档里的 SK001。
void main() {
  Map<String, dynamic> buildPayload() {
    return <String, dynamic>{
      'user_id': 'tester@careeros.com',
      'model_version': 'weighted-knowledge-base-v1',
      'recommendations': [
        {
          'occupation_id': 'OCC-ONET-15-1255.00',
          'occupation_name': 'Web and Digital Interface Designers',
          'occupation_name_zh': 'Web与数字界面设计师',
          'match_score': 0.133,
          'skill_gaps': [
            {
              'skill_id': 'SKILL-ONET-2.A.1.a',
              'skill_name': 'Reading Comprehension',
              'skill_name_zh': '阅读理解',
              'gap': 2,
              'importance': 3.5,
              'status': 'needs_improvement',
              'current_level': 1,
              'required_level': 3,
            },
            {
              'skill_id': 'SKILL-ONET-2.A.1.b',
              'skill_name': 'Active Listening',
              'skill_name_zh': '积极倾听',
              'gap': 0,
              'importance': 3.0,
              'status': 'mastered',
              'current_level': 2,
              'required_level': 2,
            },
          ],
          'recommendation_reasons': ['技能匹配度基于职业技能重要度加权计算'],
          'matched_skills': ['SKILL-ONET-2.A.1.b'],
          'skills_to_improve': ['SKILL-ONET-2.A.1.a', 'SKILL-ONET-2.A.1.c'],
          'skills_to_verify': <String>[],
        },
      ],
      'development_paths': <Map<String, dynamic>>[],
    };
  }

  test('解析真实推荐响应：职业中文名、匹配度、缺口字段齐全', () {
    final result = RecommendationResult.fromJson(buildPayload());
    expect(result.userId, 'tester@careeros.com');
    expect(result.recommendations.length, 1);

    final recommendation = result.recommendations.first;
    expect(recommendation.occupationNameZh, 'Web与数字界面设计师');
    expect(recommendation.matchScore, 0.133);
    expect(recommendation.skillGaps.length, 2);

    final gap = recommendation.skillGaps.first;
    expect(gap.skillNameZh, '阅读理解');
    expect(gap.currentLevel, 1);
    expect(gap.requiredLevel, 3);
    expect(gap.gap, 2);
    expect(gap.status, 'needs_improvement');
  });

  test('推荐理由与三组技能 ID 都能读出来', () {
    final recommendation =
        RecommendationResult.fromJson(buildPayload()).recommendations.first;
    expect(recommendation.recommendationReasons, ['技能匹配度基于职业技能重要度加权计算']);
    expect(recommendation.matchedSkills, ['SKILL-ONET-2.A.1.b']);
    expect(recommendation.skillsToImprove.length, 2);
    expect(recommendation.skillsToVerify, isEmpty);
  });

  test('后端少给字段时退化成空列表，不抛异常', () {
    final payload = buildPayload();
    final first = (payload['recommendations'] as List).first as Map<String, dynamic>;
    first.remove('recommendation_reasons');
    first.remove('skills_to_improve');
    first.remove('occupation_name_zh');

    final recommendation =
        RecommendationResult.fromJson(payload).recommendations.first;
    expect(recommendation.recommendationReasons, isEmpty);
    expect(recommendation.skillsToImprove, isEmpty);
    // 中文名缺失时回退英文名
    expect(recommendation.occupationNameZh, 'Web and Digital Interface Designers');
  });
}
