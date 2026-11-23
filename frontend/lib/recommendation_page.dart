import 'package:flutter/material.dart';

import 'career_navigation.dart';
import 'career_profile.dart';

class RecommendationPage extends StatefulWidget {
	const RecommendationPage({required this.profile, super.key});

	final CareerProfile profile;

	@override
	State<RecommendationPage> createState() => _RecommendationPageState();
}

class _RecommendationPageState extends State<RecommendationPage> {
	final Set<String> _saved = {};
	String _filter = '全部';

	@override
	Widget build(BuildContext context) {
		final results = careerOpportunities
				.where((item) => _filter == '全部' || item.category == _filter)
				.toList()
			..sort((a, b) => b.matchScore(widget.profile).compareTo(a.matchScore(widget.profile)));

		return Scaffold(
			appBar: AppBar(
				title: const Text('方向推荐'),
				actions: [
					IconButton(
						tooltip: '重新填写',
						onPressed: () => Navigator.pushReplacementNamed(
							context, '/questionnaire', arguments: widget.profile,
						),
						icon: const Icon(Icons.edit_outlined),
					),
					const SizedBox(width: 8),
				],
			),
			body: Center(
				child: ConstrainedBox(
					constraints: const BoxConstraints(maxWidth: 820),
					child: ListView(
						padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
						children: [
							Text('${widget.profile.name}，下一步可以这样走。',
									style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w700)),
							const SizedBox(height: 8),
							Text(
								'结合你的目标「${widget.profile.targetRole}」、技能和每周 ${widget.profile.weeklyHours} 小时投入排序',
								style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, height: 1.5),
							),
							const SizedBox(height: 22),
							Container(
								padding: const EdgeInsets.all(18),
								decoration: BoxDecoration(color: const Color(0xFFE5EFEB), borderRadius: BorderRadius.circular(8)),
								child: Row(children: [
									const Icon(Icons.lightbulb_outline, size: 25),
									const SizedBox(width: 14),
									Expanded(child: Text(
										'已根据 ${widget.profile.skills.isEmpty ? '你的起点' : widget.profile.skills.join('、')} 生成 ${careerOpportunities.length} 条发展方向。',
										style: const TextStyle(height: 1.45),
									)),
								]),
							),
							const SizedBox(height: 22),
							Row(children: [
								const Expanded(child: Text('适合你的路径', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w700))),
								Text('${results.length} 个方向'),
							]),
							const SizedBox(height: 12),
							SingleChildScrollView(
								scrollDirection: Axis.horizontal,
								child: Row(children: ['全部', '移动开发', '后端开发', '产品设计', '数据分析'].map((category) => Padding(
									padding: const EdgeInsets.only(right: 8),
									child: ChoiceChip(
										label: Text(category),
										selected: _filter == category,
										onSelected: (_) => setState(() => _filter = category),
									),
								)).toList()),
							),
							const SizedBox(height: 8),
							...results.asMap().entries.map((entry) {
								final index = entry.key;
								final item = entry.value;
								final score = item.matchScore(widget.profile);
								final isSaved = _saved.contains(item.title);
								return Card(
									margin: const EdgeInsets.only(bottom: 12),
									child: Padding(
										padding: const EdgeInsets.all(16),
										child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
											Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
												Container(
													width: 46,
													height: 46,
													decoration: BoxDecoration(color: Color(item.color).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
													child: Icon(_iconFor(item.icon), color: Color(item.color)),
												),
												const SizedBox(width: 13),
												Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
													Row(children: [
														if (index == 0) ...[
															const Text('优先探索', style: TextStyle(color: Color(0xFF167D78), fontSize: 12, fontWeight: FontWeight.w700)),
															const SizedBox(width: 8),
														],
														Expanded(child: Text(item.title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700))),
													]),
													const SizedBox(height: 4),
													Text('${item.category}  ·  ${item.duration}'),
												])),
												IconButton(
													tooltip: isSaved ? '取消收藏' : '收藏方向',
													onPressed: () => setState(() => isSaved ? _saved.remove(item.title) : _saved.add(item.title)),
													icon: Icon(isSaved ? Icons.bookmark : Icons.bookmark_border),
												),
											]),
											const SizedBox(height: 12),
											Text(item.description, style: const TextStyle(height: 1.45)),
											const SizedBox(height: 12),
											Wrap(spacing: 7, runSpacing: 6, children: item.skills.take(4).map((skill) => Chip(
												label: Text(skill),
												visualDensity: VisualDensity.compact,
												materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
											)).toList()),
											const SizedBox(height: 12),
											Row(children: [
												Expanded(child: ClipRRect(
													borderRadius: BorderRadius.circular(4),
													child: LinearProgressIndicator(value: score / 100, minHeight: 7, color: Color(item.color), backgroundColor: const Color(0xFFE7EBE6)),
												)),
												const SizedBox(width: 12),
												Text('$score% 匹配', style: const TextStyle(fontWeight: FontWeight.w700)),
											]),
											const SizedBox(height: 14),
											Align(
												alignment: Alignment.centerRight,
												child: OutlinedButton.icon(
													onPressed: () => Navigator.pushNamed(context, '/skill-tree', arguments: widget.profile),
													icon: const Icon(Icons.account_tree_outlined, size: 18),
													label: const Text('查看发展路径'),
												),
											),
										]),
									),
								);
							}),
						],
					),
				),
			),
			bottomNavigationBar: CareerNavigationBar(currentIndex: 1, profile: widget.profile),
		);
	}

	IconData _iconFor(String name) => switch (name) {
				'phone_iphone' => Icons.phone_iphone,
				'dns' => Icons.dns_outlined,
				'design_services' => Icons.design_services_outlined,
				_ => Icons.query_stats,
			};
}
