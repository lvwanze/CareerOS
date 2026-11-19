class SkillOption {
  final String skillId;
  final String name;
  final String nameZh;
  final String category;
  final bool usedInKb;

  const SkillOption({
    required this.skillId,
    required this.name,
    required this.nameZh,
    required this.category,
    required this.usedInKb,
  });

  factory SkillOption.fromJson(Map<String, dynamic> json) {
    return SkillOption(
      skillId: json['skill_id'] as String,
      name: json['name'] as String,
      nameZh: json['name_zh'] as String? ?? json['name'] as String,
      category: json['category'] as String,
      usedInKb: json['used_in_kb'] == true,
    );
  }
}
