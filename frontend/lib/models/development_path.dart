enum DevelopmentStatus {
notStarted,
inProgress,
mastered,
}

class TreeNode {
final String nodeId;
final String skillId;
final String skillName;
final String description;
final DevelopmentStatus status;

TreeNode({
required this.nodeId,
required this.skillId,
required this.skillName,
required this.description,
required this.status,
});

factory TreeNode.fromJson(Map<String, dynamic> json) {
return TreeNode(
nodeId: json['node_id'] as String,
skillId: json['skill_id'] as String,
skillName: json['skill_name'] as String,
description: json['description'] as String,
status: _parseStatus(json['status'] as String),
);
}

static DevelopmentStatus _parseStatus(String status) {
switch (status) {
case 'not_started':
return DevelopmentStatus.notStarted;
case 'in_progress':
return DevelopmentStatus.inProgress;
case 'mastered':
return DevelopmentStatus.mastered;
default:
throw ArgumentError('未知状态: $status');
}
}
}

