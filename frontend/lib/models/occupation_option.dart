class OccupationOption {
  const OccupationOption({
    required this.occupationId,
    required this.name,
    required this.nameZh,
    required this.category,
    required this.skillCount,
  });

  final String occupationId;
  final String name;
  final String nameZh;
  final String category;
  final int skillCount;

  factory OccupationOption.fromJson(Map<String, dynamic> json) {
    return OccupationOption(
      occupationId: json['occupation_id'] as String,
      name: json['name'] as String,
      nameZh: json['name_zh'] as String? ?? json['name'] as String,
      category: json['category'] as String? ?? '',
      skillCount: json['skill_count'] as int? ?? 0,
    );
  }
}
