/// 发展树节点，字段与 `docs/data_contract.md` §3.8 的 TreeNode 一致（13 个）。
///
/// `skill_id` 是「字段必填、值可为 null」：根与类别节点必须是 null，
/// 所以这里保持可空而不是 `as String? ?? ''`——空串会被后续当成真实 ID 用。
class CareerTreeNode {
  const CareerTreeNode({
    required this.nodeId,
    required this.parentId,
    required this.nodeType,
    required this.level,
    required this.order,
    required this.priority,
    required this.skillId,
    required this.skillName,
    required this.nameEn,
    required this.description,
    required this.status,
    required this.category,
    required this.requiredLevel,
    required this.importance,
  });

  factory CareerTreeNode.fromJson(Map<String, dynamic> json) {
    return CareerTreeNode(
      nodeId: json['node_id'] as String,
      parentId: json['parent_id'] as String?,
      nodeType: json['node_type'] as String,
      level: json['level'] as int,
      order: json['order'] as int,
      priority: json['priority'] as int,
      skillId: json['skill_id'] as String?,
      skillName: json['skill_name'] as String,
      nameEn: json['name_en'] as String?,
      description: json['description'] as String? ?? '',
      status: json['status'] as String? ?? 'not_started',
      category: json['category'] as String?,
      requiredLevel: (json['required_level'] as num?)?.toInt(),
      importance: (json['importance'] as num?)?.toDouble(),
    );
  }

  final String nodeId;
  final String? parentId;

  /// occupation / category / skill
  final String nodeType;

  /// 0 根、1 类别、2 技能
  final int level;

  /// 同一父节点下从 1 连续递增，根为 0
  final int order;

  /// 全树学习顺序，从 1 递增；根与类别为 0
  final int priority;
  final String? skillId;
  final String skillName;
  final String? nameEn;
  final String description;
  final String status;
  final String? category;
  final int? requiredLevel;
  final double? importance;

  bool get isRoot => parentId == null;
  bool get isCategory => nodeType == 'category';
  bool get isSkill => nodeType == 'skill';

  String get statusLabel => SkillTreeStatus.labelOf(status);
}

/// `GET /api/v1/tree/{occupation_id}` 的 data。
class CareerTree {
  const CareerTree({
    required this.occupationId,
    required this.occupationName,
    required this.occupationNameZh,
    required this.rootId,
    required this.nodeCount,
    required this.maxDepth,
    required this.nodes,
  });

  factory CareerTree.fromJson(Map<String, dynamic> json) {
    final rawNodes = json['nodes'];
    if (rawNodes is! List) {
      throw const FormatException('发展树缺少 nodes 数组');
    }
    return CareerTree(
      occupationId: json['occupation_id'] as String,
      occupationName: json['occupation_name'] as String,
      occupationNameZh: json['occupation_name_zh'] as String? ??
          json['occupation_name'] as String,
      rootId: json['root_id'] as String,
      nodeCount: json['node_count'] as int,
      maxDepth: json['max_depth'] as int,
      nodes: rawNodes
          .whereType<Map<String, dynamic>>()
          .map(CareerTreeNode.fromJson)
          .toList(),
    );
  }

  final String occupationId;
  final String occupationName;
  final String occupationNameZh;
  final String rootId;
  final int nodeCount;
  final int maxDepth;
  final List<CareerTreeNode> nodes;

  CareerTreeNode get root => nodes.firstWhere(
        (node) => node.nodeId == rootId,
        orElse: () => throw const FormatException('发展树缺少根节点'),
      );

  /// 按 `order` 排好的技能类别。
  List<CareerTreeNode> get categories => _childrenOf(rootId);

  /// 某类别下按 `order` 排好的技能节点。
  List<CareerTreeNode> skillsOf(String categoryId) => _childrenOf(categoryId);

  List<CareerTreeNode> get skillNodes =>
      nodes.where((node) => node.isSkill).toList();

  List<CareerTreeNode> _childrenOf(String parentId) => nodes
      .where((node) => node.parentId == parentId)
      .toList()
    ..sort((a, b) => a.order.compareTo(b.order));
}

/// 树节点状态词表，与后端 `TreeNode.status` 的 Literal 一致。
class SkillTreeStatus {
  const SkillTreeStatus._();

  static const Map<String, String> labels = <String, String>{
    'not_started': '未开始',
    'in_progress': '进行中',
    'mastered': '已掌握',
  };

  static String labelOf(String value) => labels[value] ?? value;
}
