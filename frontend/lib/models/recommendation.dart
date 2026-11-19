class RecommendationResult {
  final String userId;
  final String modelVersion;
  final List<CareerRecommendation> recommendations;
  final List<DevelopmentPathResult> developmentPaths;

  const RecommendationResult({
    required this.userId,
    required this.modelVersion,
    required this.recommendations,
    required this.developmentPaths,
  });

  factory RecommendationResult.fromJson(Map<String, dynamic> json) {
    return RecommendationResult(
      userId: json['user_id'] as String,
      modelVersion: json['model_version'] as String,
      recommendations: (json['recommendations'] as List<dynamic>)
          .map((item) => CareerRecommendation.fromJson(item as Map<String, dynamic>))
          .toList(),
      developmentPaths: (json['development_paths'] as List<dynamic>)
          .map((item) => DevelopmentPathResult.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class CareerRecommendation {
  final String occupationId;
  final String occupationName;
  final String occupationNameZh;
  final double matchScore;
  final List<SkillGapResult> skillGaps;

  const CareerRecommendation({
    required this.occupationId,
    required this.occupationName,
    required this.occupationNameZh,
    required this.matchScore,
    required this.skillGaps,
  });

  factory CareerRecommendation.fromJson(Map<String, dynamic> json) {
    return CareerRecommendation(
      occupationId: json['occupation_id'] as String,
      occupationName: json['occupation_name'] as String,
        occupationNameZh: json['occupation_name_zh'] as String? ??
          json['occupation_name'] as String,
      matchScore: (json['match_score'] as num).toDouble(),
      skillGaps: (json['skill_gaps'] as List<dynamic>)
          .map((item) => SkillGapResult.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class SkillGapResult {
  final String skillId;
  final String? skillName;
  final String? skillNameZh;
  final int gap;
  final double? importance;
  final String status;
  final int currentLevel;
  final int requiredLevel;

  const SkillGapResult({
    required this.skillId,
    required this.skillName,
    required this.skillNameZh,
    required this.gap,
    required this.importance,
    required this.status,
    required this.currentLevel,
    required this.requiredLevel,
  });

  factory SkillGapResult.fromJson(Map<String, dynamic> json) {
    return SkillGapResult(
      skillId: json['skill_id'] as String,
      skillName: json['skill_name'] as String?,
      skillNameZh: json['skill_name_zh'] as String?,
      gap: json['gap'] as int,
      importance: (json['importance'] as num?)?.toDouble(),
      status: json['status'] as String,
      currentLevel: json['current_level'] as int,
      requiredLevel: json['required_level'] as int,
    );
  }
}

class DevelopmentPathResult {
  final String pathId;
  final String occupationId;
  final List<DevelopmentNodeResult> nodes;

  const DevelopmentPathResult({
    required this.pathId,
    required this.occupationId,
    required this.nodes,
  });

  factory DevelopmentPathResult.fromJson(Map<String, dynamic> json) {
    return DevelopmentPathResult(
      pathId: json['path_id'] as String,
      occupationId: json['occupation_id'] as String,
      nodes: (json['nodes'] as List<dynamic>)
          .map((item) => DevelopmentNodeResult.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class DevelopmentNodeResult {
  final String nodeId;
  final String skillId;
  final String name;
  final String status;
  final int priority;
  final String description;

  const DevelopmentNodeResult({
    required this.nodeId,
    required this.skillId,
    required this.name,
    required this.status,
    required this.priority,
    required this.description,
  });

  factory DevelopmentNodeResult.fromJson(Map<String, dynamic> json) {
    return DevelopmentNodeResult(
      nodeId: json['node_id'] as String,
      skillId: json['skill_id'] as String,
      name: json['name'] as String,
      status: json['status'] as String,
      priority: json['priority'] as int,
      description: json['description'] as String,
    );
  }
}