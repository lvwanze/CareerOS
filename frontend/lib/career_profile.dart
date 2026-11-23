class CareerProfile {
  const CareerProfile({
    required this.name,
    required this.targetRole,
    required this.experience,
    required this.skills,
    required this.weeklyHours,
  });

  final String name;
  final String targetRole;
  final String experience;
  final List<String> skills;
  final int weeklyHours;
}

class CareerOpportunity {
  const CareerOpportunity({
    required this.title,
    required this.category,
    required this.description,
    required this.skills,
    required this.duration,
    required this.icon,
    required this.color,
  });

  final String title;
  final String category;
  final String description;
  final List<String> skills;
  final String duration;
  final String icon;
  final int color;

  int matchScore(CareerProfile profile) {
    final targetMatch = profile.targetRole == category ? 28 : 0;
    final matchingSkills = profile.skills
        .map((skill) => skill.toLowerCase())
        .where((skill) => skills.any((item) => item.toLowerCase() == skill))
        .length;
    final experienceBonus = switch (profile.experience) {
      '有项目经验' => 8,
      '有工作经验' => 12,
      _ => 0,
    };
    return (48 + targetMatch + matchingSkills * 6 + experienceBonus).clamp(0, 98);
  }
}

const careerOpportunities = [
  CareerOpportunity(
    title: 'Flutter 应用开发',
    category: '移动开发',
    description: '从 Dart 基础到完整跨平台应用，构建可展示的作品集。',
    skills: ['Flutter', 'Dart', '移动开发', 'Git'],
    duration: '建议 8 周',
    icon: 'phone_iphone',
    color: 0xFF167D78,
  ),
  CareerOpportunity(
    title: 'Python 后端工程',
    category: '后端开发',
    description: '掌握 API、数据库与服务部署，独立交付一个后端项目。',
    skills: ['Python', 'SQL', 'API', 'Git'],
    duration: '建议 10 周',
    icon: 'dns',
    color: 0xFFCB6847,
  ),
  CareerOpportunity(
    title: '产品体验设计',
    category: '产品设计',
    description: '用研究、信息架构和原型设计，把想法转化为清晰体验。',
    skills: ['Figma', '用户研究', '原型设计', '产品设计'],
    duration: '建议 6 周',
    icon: 'design_services',
    color: 0xFF7E6C45,
  ),
  CareerOpportunity(
    title: '数据分析与洞察',
    category: '数据分析',
    description: '用 SQL 与可视化分析真实数据，练习把发现讲清楚。',
    skills: ['SQL', 'Python', '数据分析', 'Excel'],
    duration: '建议 7 周',
    icon: 'query_stats',
    color: 0xFF547B50,
  ),
];