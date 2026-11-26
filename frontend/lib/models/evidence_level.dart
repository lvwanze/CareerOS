/// evidence_level 词表，与后端 `packages/training/matcher.py` 的 EVIDENCE_LEVELS 一致。
///
/// 后端对无法识别的值（例如 api_spec.md 示例里的中文「课程作业」）会归一成 `none`，
/// 整份画像因此全部落入「待验证」，所以这里只允许提交下表中的英文键。
class EvidenceLevel {
  const EvidenceLevel._();

  static const String defaultLevel = 'self';

  static const Map<String, String> labels = <String, String>{
    'none': '没有证据',
    'self': '只是自述',
    'course': '课程或培训',
    'project': '项目经历',
    'work': '工作或实习',
    'certificate': '证书认证',
    'test': '客观测试',
  };

  static String labelOf(String value) => labels[value] ?? labels['none']!;
}

/// 技能自评等级 0～4 的界面文案，对应 data_contract.md 的量表口径。
class SkillLevel {
  const SkillLevel._();

  static const int min = 0;
  static const int max = 4;

  static String labelOf(int level) => switch (level) {
        0 => '没接触过',
        1 => '了解概念',
        2 => '能独立完成练习',
        3 => '做过完整项目',
        _ => '可指导他人',
      };
}
