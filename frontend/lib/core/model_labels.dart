import 'package:frontend/core/display_name.dart';
import 'package:frontend/models/development_path.dart';
import 'package:frontend/models/recommendation.dart';
import 'package:frontend/models/skill_option.dart';

/// 给各个数据模型挂一个统一的 displayName，
/// 页面里直接写 skill.displayName 就行，不用关心回退逻辑。

extension SkillOptionLabel on SkillOption {
  String get displayName => preferredName(nameZh, name, fallback: skillId);
  String get subtitleName => secondaryName(nameZh, name);
}

extension CareerRecommendationLabel on CareerRecommendation {
  String get displayName =>
      preferredName(occupationNameZh, occupationName, fallback: occupationId);
  String get subtitleName => secondaryName(occupationNameZh, occupationName);
}

extension SkillGapResultLabel on SkillGapResult {
  String get displayName =>
      preferredName(skillNameZh, skillName, fallback: skillId);
  String get subtitleName => secondaryName(skillNameZh, skillName);
}

extension TreeNodeLabel on TreeNode {
  // 发展树接口目前只给 skill_name 一个字段，没有中文名，先按英文名展示。
  String get displayName => preferredName(null, skillName, fallback: skillId);
}

extension DevelopmentStatusLabel on DevelopmentStatus {
  String get label {
    switch (this) {
      case DevelopmentStatus.notStarted:
        return '未开始';
      case DevelopmentStatus.inProgress:
        return '进行中';
      case DevelopmentStatus.mastered:
        return '已掌握';
    }
  }
}
