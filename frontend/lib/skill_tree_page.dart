import 'package:flutter/material.dart';

import 'career_navigation.dart';
import 'career_profile.dart';
import 'models/career_tree.dart';
import 'models/evidence_level.dart';
import 'services/api_service.dart';
import 'services/profile_storage.dart';

/// 发展树页：数据来自 `GET /api/v1/tree/{occupation_id}`（api_spec §3.6）。
///
/// 之前这里读的是推荐响应里的 `development_paths`，靠进程内单例跨页传——
/// 冷启动即空、且只有"待提升"的缺口节点，看不到该职业完整的技能要求。
/// 真实树接口按 occupation_id 现拼三层结构，个人勾选进度仍只存本地。
class SkillTreePage extends StatefulWidget {
	const SkillTreePage({required this.profile, super.key});

	final CareerProfile profile;

	@override
	State<SkillTreePage> createState() => _SkillTreePageState();
}

class _SkillTreePageState extends State<SkillTreePage> {
	final Set<String> _completed = <String>{};
	ProfileStorage? _storage;
	CareerTree? _tree;
	late final Future<void> _restore;

	@override
	void initState() {
		super.initState();
		_restore = _load();
	}

	Future<void> _load() async {
		final storage = await ProfileStorage.open();
		final occupationId = widget.profile.occupationId;
		CareerTree? tree;
		if (occupationId != null) {
			tree = await ApiService.fetchCareerTree(occupationId);
			final stored = storage.loadCompletedNodes(occupationId);
			_completed.clear();
			_completed.addAll(tree.skillNodes
					.map((node) => node.nodeId)
					.where(stored.contains));
		}
		if (!mounted) return;
		setState(() {
			_storage = storage;
			_tree = tree;
		});
	}

	Future<void> _toggle(String nodeId, bool completed) async {
		final occupationId = widget.profile.occupationId;
		setState(() => completed ? _completed.add(nodeId) : _completed.remove(nodeId));
		if (occupationId == null) return;
		await _storage?.saveCompletedNode(occupationId, nodeId, completed: completed);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('发展树')),
			body: FutureBuilder<void>(
				future: _restore,
				builder: (context, snapshot) {
					if (snapshot.connectionState != ConnectionState.done) {
						return const Center(child: CircularProgressIndicator());
					}
					if (snapshot.hasError) {
						return _LoadFailure(
							message: '${snapshot.error}',
							onRetry: () => setState(() => _restore = _load()),
						);
					}
					final tree = _tree;
					if (tree == null) {
						return _EmptyState(profile: widget.profile);
					}
					return _buildTree(tree);
				},
			),
			bottomNavigationBar: CareerNavigationBar(
					currentIndex: 2, profile: widget.profile),
		);
	}

	Widget _buildTree(CareerTree tree) {
		final skills = tree.skillNodes;
		final completedCount = skills.where((node) => _completed.contains(node.nodeId)).length;
		final progress = skills.isEmpty ? 0.0 : completedCount / skills.length;
		final muted = Theme.of(context).colorScheme.onSurfaceVariant;
		final root = tree.root;

		return Center(
			child: ConstrainedBox(
				constraints: const BoxConstraints(maxWidth: 820),
				child: ListView(
					padding: const EdgeInsets.fromLTRB(20, 12, 20, 30),
					children: [
						Text('${tree.occupationNameZh} 发展树',
								style: const TextStyle(
										fontSize: 27, fontWeight: FontWeight.w700)),
						const SizedBox(height: 8),
						Text(
							'职业要求 ${skills.length} 项技能，分属 ${tree.categories.length} 个类别；'
							'同级按 O*NET 重要度排列，编号是全树学习顺序。',
							style: TextStyle(color: muted, height: 1.5),
						),
						const SizedBox(height: 4),
						Text('节点 ${root.skillName}（${root.nameEn ?? root.skillName}）'
								'来自知识库 ${tree.nodeCount} 节点 · ${tree.maxDepth + 1} 层',
								style: TextStyle(fontSize: 12, color: muted)),
						const SizedBox(height: 16),
						Card(child: Padding(
							padding: const EdgeInsets.all(18),
							child: Column(crossAxisAlignment: CrossAxisAlignment.start,
									children: [
								Row(children: [
									const Expanded(
											child: Text('我的进度',
													style: TextStyle(
															fontWeight: FontWeight.w700))),
									Text('$completedCount / ${skills.length} 项技能'),
								]),
								const SizedBox(height: 12),
								LinearProgressIndicator(value: progress, minHeight: 8),
								const SizedBox(height: 10),
								Text('已勾选 ${(progress * 100).round()}%'),
								const SizedBox(height: 4),
								Text('接口只描述"这个职业要求什么"，勾选进度保存在本机。',
										style: TextStyle(fontSize: 12, color: muted)),
							]),
						)),
						const SizedBox(height: 8),
						for (final category in tree.categories) ...[
							_CategoryHeader(
								category: category,
								total: tree.skillsOf(category.nodeId).length,
							),
							...tree.skillsOf(category.nodeId).map(
								(node) => _SkillTile(
									node: node,
									statusLabel: node.statusLabel,
									completed: _completed.contains(node.nodeId),
									onChanged: (value) =>
										_toggle(node.nodeId, value ?? false),
								),
							),
						],
						const SizedBox(height: 10),
						FilledButton.icon(
							onPressed: () => Navigator.pushNamed(
								context,
								'/recommendation',
								arguments: widget.profile,
							),
							icon: const Icon(Icons.explore_outlined),
							label: const Text('回到方向推荐'),
							style: FilledButton.styleFrom(
									minimumSize: const Size.fromHeight(50)),
						),
					],
				),
			),
		);
	}
}

class _CategoryHeader extends StatelessWidget {
	const _CategoryHeader({required this.category, required this.total});

	final CareerTreeNode category;
	final int total;

	@override
	Widget build(BuildContext context) {
		final muted = Theme.of(context).colorScheme.onSurfaceVariant;
		return Padding(
			padding: const EdgeInsets.fromLTRB(2, 18, 2, 8),
			child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
				Row(children: [
					Icon(Icons.folder_open_outlined, size: 18, color: muted),
					const SizedBox(width: 6),
					Text('${category.skillName}（$total 项）',
							style: const TextStyle(
									fontSize: 17, fontWeight: FontWeight.w700)),
					const SizedBox(width: 8),
					Text(category.nameEn ?? '', style: TextStyle(fontSize: 12, color: muted)),
				]),
				const SizedBox(height: 4),
				Text(category.description, style: TextStyle(fontSize: 12, color: muted, height: 1.4)),
			]),
		);
	}
}

class _SkillTile extends StatelessWidget {
	const _SkillTile({
		required this.node,
		required this.statusLabel,
		required this.completed,
		required this.onChanged,
	});

	final CareerTreeNode node;
	final String statusLabel;
	final bool completed;
	final ValueChanged<bool?> onChanged;

	@override
	Widget build(BuildContext context) {
		final muted = Theme.of(context).colorScheme.onSurfaceVariant;
		final color = completed
				? Theme.of(context).colorScheme.primary
				: const Color(0xFF9BA7A0);
		return IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
			SizedBox(width: 42, child: Column(children: [
				Container(
					width: 34,
					height: 34,
					alignment: Alignment.center,
					decoration: BoxDecoration(
						shape: BoxShape.circle,
						color: completed ? color : Colors.white,
						border: Border.all(color: color, width: 1.5),
					),
					child: Text('${node.priority}', style: TextStyle(color: color)),
				),
				Expanded(
					child: Container(
						width: 2,
						margin: const EdgeInsets.symmetric(vertical: 4),
						color: const Color(0xFFD9DFDA),
					),
				),
			])),
			const SizedBox(width: 8),
			Expanded(child: Card(
				margin: const EdgeInsets.only(bottom: 12),
				child: Padding(
					padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
					child: Row(children: [
						Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
							Text(node.skillName,
									style: const TextStyle(fontWeight: FontWeight.w700)),
							if (node.nameEn != null && node.nameEn!.isNotEmpty) ...[
								const SizedBox(height: 2),
								Text(node.nameEn!,
										style: TextStyle(fontSize: 12, color: muted)),
							],
							if (node.description.isNotEmpty) ...[
								const SizedBox(height: 4),
								Text(node.description,
										style: TextStyle(color: muted, height: 1.35)),
							],
							const SizedBox(height: 6),
							Text(
								'要求 ${SkillLevel.labelOf(node.requiredLevel ?? 0)}'
								'  ·  重要度 ${node.importance?.toStringAsFixed(2) ?? '-'}'
								'  ·  后端状态：$statusLabel',
								style: TextStyle(
										color: Theme.of(context).colorScheme.primary,
										fontSize: 12,
										fontWeight: FontWeight.w600)),
						])),
						Checkbox(
							value: completed,
							onChanged: onChanged,
							semanticLabel: '标记 ${node.skillName} 完成',
						),
					]),
				),
			)),
		]));
	}
}

class _LoadFailure extends StatelessWidget {
	const _LoadFailure({required this.message, required this.onRetry});

	final String message;
	final VoidCallback onRetry;

	@override
	Widget build(BuildContext context) {
		final muted = Theme.of(context).colorScheme.onSurfaceVariant;
		return Center(child: Padding(
			padding: const EdgeInsets.all(24),
			child: Column(mainAxisSize: MainAxisSize.min, children: [
				const Icon(Icons.cloud_off_outlined, size: 42),
				const SizedBox(height: 12),
				Text('发展树读取失败',
						style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
				const SizedBox(height: 6),
				Text(message,
						style: TextStyle(color: muted, height: 1.4), textAlign: TextAlign.center),
				const SizedBox(height: 6),
				Text('发展树按职业 ID 现拼，接口不会用空树代替失败，所以这里能看到具体原因。',
						style: TextStyle(fontSize: 12, color: muted), textAlign: TextAlign.center),
				const SizedBox(height: 16),
				OutlinedButton(onPressed: onRetry, child: const Text('重试')),
			]),
		));
	}
}

class _EmptyState extends StatelessWidget {
	const _EmptyState({required this.profile});

	final CareerProfile profile;

	@override
	Widget build(BuildContext context) {
		final muted = Theme.of(context).colorScheme.onSurfaceVariant;
		return Center(
			child: Padding(
				padding: const EdgeInsets.all(24),
				child: Column(mainAxisSize: MainAxisSize.min, children: [
					const Icon(Icons.account_tree_outlined, size: 42),
					const SizedBox(height: 12),
					const Text('还没有选定职业方向'),
					const SizedBox(height: 6),
					Text('发展树需要一个职业 ID，先在推荐页从 Top-5 结果里选一个方向。',
							style: TextStyle(color: muted), textAlign: TextAlign.center),
					const SizedBox(height: 16),
					FilledButton.icon(
						onPressed: () => Navigator.pushReplacementNamed(
								context, '/recommendation', arguments: profile),
						icon: const Icon(Icons.explore_outlined),
						label: const Text('回到方向推荐'),
					),
				]),
			),
		);
	}
}
