import 'package:flutter/material.dart';

import 'career_navigation.dart';
import 'career_profile.dart';
import 'models/recommendation.dart';
import 'services/profile_storage.dart';
import 'services/recommendation_store.dart';

class SkillTreePage extends StatefulWidget {
	const SkillTreePage({required this.profile, super.key});

	final CareerProfile profile;

	@override
	State<SkillTreePage> createState() => _SkillTreePageState();
}

class _SkillTreePageState extends State<SkillTreePage> {
	static const Map<String, String> _statusLabels = <String, String>{
		'not_started': '未开始',
		'in_progress': '进行中',
		'mastered': '已掌握',
	};

	final Set<String> _completed = <String>{};
	ProfileStorage? _storage;
	DevelopmentPathResult? _path;
	late final Future<void> _restore;

	@override
	void initState() {
		super.initState();
		_restore = _load();
	}

	Future<void> _load() async {
		final storage = await ProfileStorage.open();
		final path = RecommendationStore.instance.pathFor(widget.profile.occupationId);
		if (path != null) {
			_completed.addAll(storage.hasCompletedNodes(path.occupationId)
					? storage.loadCompletedNodes(path.occupationId)
					: path.nodes
									.where((node) => node.status == 'mastered')
									.map((node) => node.nodeId));
		}
		if (!mounted) return;
		setState(() {
			_storage = storage;
			_path = path;
		});
	}

	Future<void> _toggle(String nodeId, bool completed) async {
		final path = _path;
		setState(() => completed ? _completed.add(nodeId) : _completed.remove(nodeId));
		if (path == null) return;
		await _storage?.saveCompletedNode(path.occupationId, nodeId,
				completed: completed);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('发展路径')),
			body: FutureBuilder<void>(
				future: _restore,
				builder: (context, snapshot) {
					if (snapshot.connectionState != ConnectionState.done) {
						return const Center(child: CircularProgressIndicator());
					}
					if (snapshot.hasError) {
						return Center(child: Padding(
							padding: const EdgeInsets.all(24),
							child: Column(mainAxisSize: MainAxisSize.min, children: [
								const Icon(Icons.cloud_off_outlined, size: 42),
								const SizedBox(height: 12),
								Text('发展路径读取失败：${snapshot.error}'),
								const SizedBox(height: 16),
								OutlinedButton(
									onPressed: () => setState(() => _restore = _load()),
									child: const Text('重试'),
								),
							]),
						));
					}
					final path = _path;
					if (path == null || path.nodes.isEmpty) {
						return Center(
							child: Padding(
								padding: const EdgeInsets.all(24),
								child: Column(mainAxisSize: MainAxisSize.min, children: [
									const Icon(Icons.account_tree_outlined, size: 42),
									const SizedBox(height: 12),
									const Text('还没有生成过该职业的发展路径。'),
									const SizedBox(height: 6),
									Text('先在推荐页点「查看发展路径」，路径来自推荐响应的 development_paths。',
											style: TextStyle(
													color: Theme.of(context)
															.colorScheme
															.onSurfaceVariant),
											textAlign: TextAlign.center),
									const SizedBox(height: 16),
									FilledButton.icon(
										onPressed: () => Navigator.pushReplacementNamed(
												context, '/recommendation',
												arguments: widget.profile),
										icon: const Icon(Icons.explore_outlined),
										label: const Text('回到方向推荐'),
									),
								]),
							),
						);
					}
					return _buildTree(path);
				},
			),
			bottomNavigationBar: CareerNavigationBar(currentIndex: 2, profile: widget.profile),
		);
	}

	Widget _buildTree(DevelopmentPathResult path) {
		final nodes = path.nodes.toList()..sort((a, b) => a.priority.compareTo(b.priority));
		final completedCount = nodes.where((node) => _completed.contains(node.nodeId)).length;
		final progress = nodes.isEmpty ? 0.0 : completedCount / nodes.length;
		final occupation = widget.profile.targetRole;
		final muted = Theme.of(context).colorScheme.onSurfaceVariant;

		return Center(
			child: ConstrainedBox(
				constraints: const BoxConstraints(maxWidth: 820),
				child: ListView(
					padding: const EdgeInsets.fromLTRB(20, 12, 20, 30),
					children: [
						Text('$occupation 成长路线',
								style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w700)),
						const SizedBox(height: 8),
						Text(
							'按每周 ${widget.profile.weeklyHours} 小时安排，共 ${nodes.length} 个节点，顺序由后端按差距大小排定。',
							style: TextStyle(color: muted, height: 1.5),
						),
						const SizedBox(height: 20),
						Card(child: Padding(
							padding: const EdgeInsets.all(18),
							child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
								Row(children: [
									const Expanded(
											child: Text('当前进度',
													style: TextStyle(fontWeight: FontWeight.w700))),
									Text('$completedCount / ${nodes.length} 节点'),
								]),
								const SizedBox(height: 12),
								LinearProgressIndicator(value: progress, minHeight: 8),
								const SizedBox(height: 10),
								Text('${(progress * 100).round()}% 已完成'),
							]),
						)),
						const SizedBox(height: 12),
						...nodes.asMap().entries.map((entry) => _NodeTile(
									index: entry.key + 1,
									node: entry.value,
									statusLabel: _statusLabels[entry.value.status] ??
											entry.value.status,
									completed: _completed.contains(entry.value.nodeId),
									isLast: entry.key == nodes.length - 1,
									onChanged: (value) =>
											_toggle(entry.value.nodeId, value ?? false),
								)),
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

class _NodeTile extends StatelessWidget {
	const _NodeTile({
		required this.index,
		required this.node,
		required this.statusLabel,
		required this.completed,
		required this.isLast,
		required this.onChanged,
	});

	final int index;
	final DevelopmentNodeResult node;
	final String statusLabel;
	final bool completed;
	final bool isLast;
	final ValueChanged<bool?> onChanged;

	@override
	Widget build(BuildContext context) {
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
					child: completed
							? const Icon(Icons.check, color: Colors.white, size: 19)
							: Text('$index', style: TextStyle(color: color)),
				),
				if (!isLast)
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
							Text(node.name, style: const TextStyle(fontWeight: FontWeight.w700)),
							const SizedBox(height: 4),
							Text(node.description,
									style: TextStyle(
											color: Theme.of(context).colorScheme.onSurfaceVariant,
											height: 1.35)),
							const SizedBox(height: 6),
							Text('后端状态：$statusLabel  ·  优先级 ${node.priority}',
									style: TextStyle(
											color: Theme.of(context).colorScheme.primary,
											fontSize: 12,
											fontWeight: FontWeight.w600)),
						])),
						Checkbox(
							value: completed,
							onChanged: onChanged,
							semanticLabel: '标记 ${node.name} 完成',
						),
					]),
				),
			)),
		]));
	}
}
