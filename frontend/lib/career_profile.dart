import 'models/evidence_level.dart';

/// 单项技能的用户自评，字段与 data_contract.md 的 `skills[]` 一致。
class ProfileSkill {
  const ProfileSkill({
    required this.skillId,
    required this.name,
    required this.selfLevel,
    required this.evidenceLevel,
  });

  final String skillId;
  final String name;
  final int selfLevel;
  final String evidenceLevel;

  ProfileSkill copyWith({int? selfLevel, String? evidenceLevel}) => ProfileSkill(
        skillId: skillId,
        name: name,
        selfLevel: selfLevel ?? this.selfLevel,
        evidenceLevel: evidenceLevel ?? this.evidenceLevel,
      );

  Map<String, dynamic> toJson() => <String, dynamic>{
        'skill_id': skillId,
        'self_level': selfLevel,
        'evidence_level': evidenceLevel,
      };

  factory ProfileSkill.fromJson(Map<String, dynamic> json) => ProfileSkill(
        skillId: json['skill_id'] as String,
        name: json['name'] as String,
        selfLevel: json['self_level'] as int,
        evidenceLevel: json['evidence_level'] as String? ??
            EvidenceLevel.defaultLevel,
      );
}

class CareerProfile {
  const CareerProfile({
    required this.name,
    required this.targetRole,
    required this.experience,
    required this.skills,
    required this.weeklyHours,
    this.occupationId,
  });

  final String name;
  final String targetRole;
  final String experience;
  final List<ProfileSkill> skills;
  final int weeklyHours;
  final String? occupationId;

  bool get hasSkills => skills.isNotEmpty;

  CareerProfile copyWith({String? occupationId}) => CareerProfile(
        name: name,
        targetRole: targetRole,
        experience: experience,
        skills: skills,
        weeklyHours: weeklyHours,
        occupationId: occupationId ?? this.occupationId,
      );

  /// 推荐接口请求体里的 `profile`，字段顺序与 data_contract.md 对齐。
  Map<String, dynamic> toJson() => <String, dynamic>{
        'user_id': name,
        'learning_stage': <String, dynamic>{'experience': experience},
        'preferences': <String, dynamic>{'target_role': targetRole},
        'skills': skills.map((skill) => skill.toJson()).toList(),
        'constraints': <String, dynamic>{'weekly_hours': weeklyHours},
        'career_goals': <String, dynamic>{'target_role': targetRole},
      };

  factory CareerProfile.fromJson(Map<String, dynamic> json) => CareerProfile(
        name: json['name'] as String? ?? '',
        targetRole: json['target_role'] as String? ?? '',
        experience: json['experience'] as String? ?? '刚刚起步',
        skills: (json['skills'] as List<dynamic>? ?? <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .map(ProfileSkill.fromJson)
            .toList(),
        weeklyHours: json['weekly_hours'] as int? ?? 6,
        occupationId: json['occupation_id'] as String?,
      );
}
