import 'package:flutter/material.dart';

import 'career_navigation.dart';
import 'career_profile.dart';

class SkillTreePage extends StatefulWidget {
	const SkillTreePage({required this.profile, super.key});

	final CareerProfile profile;

	@override
	State<SkillTreePage> createState() => _SkillTreePageState();
}

class _SkillTreePageState extends State<SkillTreePage> {
	late final List<_Milestone> _milestones;

	@override
	void initState() {
		super.initState();
		final opportunity = careerOpportunities.firstWhere(
			(item) => item.category == widget.profile.targetRole,
			orElse: () => careerOpportunities.first,
		);
		_milestones = _buildMilestones(opportunity);
	}

	List<_Milestone> _buildMilestones(CareerOpportunity opportunity) {
		final isDesign = opportunity.category == '产品设计';
		final isData = opportunity.category == '数据分析';
		final foundations = isDesign
				? ['设计基础', 'Figma', '用户研究']
				: isData
						? ['数据思维', 'SQL', 'Python 分析']
						: opportunity.category == '后端开发'
								? ['编程基础', 'Python', '数据库与 API']
								: ['编程基础', 'Dart', 'Flutter'];
		final steps = [
			_Milestone('foundation', '打好基础', '核心概念与工具熟悉', foundations[0]),
			_Milestone('practice', '完成专项练习', '通过小任务巩固核心技能', foundations[1]),
			_Milestone('project', '做出完整作品', '从需求到交付，完成一个真实项目', foundations[2]),
			_Milestone('portfolio', '整理作品集', '复盘过程、展示成果并准备面试', '作品集'),
		];
		for (final step in steps) {
			step.completed = widget.profile.skills.any(
				(skill) => skill.toLowerCase() == step.skill.toLowerCase(),
			);
		}
		return steps;
	}

	@override
	Widget build(BuildContext context) {
		final completedCount = _milestones.where((item) => item.completed).length;
		final progress = completedCount / _milestones.length;
		return Scaffold(
			appBar: AppBar(title: const Text('发展路径')),
			body: Center(
				child: ConstrainedBox(
					constraints: const BoxConstraints(maxWidth: 820),
					child: ListView(
						padding: const EdgeInsets.fromLTRB(20, 12, 20, 30),
						children: [
							Text('${widget.profile.targetRole} 成长路线', style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w700)),
							const SizedBox(height: 8),
							Text(
								'按每周 ${widget.profile.weeklyHours} 小时安排，分阶段积累能力与作品。',
								style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, height: 1.5),
							),
							const SizedBox(height: 20),
							Card(child: Padding(
								padding: const EdgeInsets.all(18),
								child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
									Row(children: [
										const Expanded(child: Text('当前进度', style: TextStyle(fontWeight: FontWeight.w700))),
										Text('$completedCount / ${_milestones.length} 阶段'),
									]),
									const SizedBox(height: 12),
									LinearProgressIndicator(value: progress, minHeight: 8),
									const SizedBox(height: 10),
									Text('${(progress * 100).round()}% 已完成'),
								]),
							)),
							const SizedBox(height: 12),
							..._milestones.asMap().entries.map((entry) => _MilestoneTile(
										index: entry.key + 1,
										milestone: entry.value,
										isLast: entry.key == _milestones.length - 1,
										onChanged: (value) => setState(() => entry.value.completed = value ?? false),
									)),
							const SizedBox(height: 10),
							FilledButton.icon(
								onPressed: () => Navigator.pushNamed(context, '/recommendation', arguments: widget.profile),
								icon: const Icon(Icons.explore_outlined),
								label: const Text('回到方向推荐'),
								style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
							),
						],
					),
				),
			),
			bottomNavigationBar: CareerNavigationBar(currentIndex: 2, profile: widget.profile),
		);
	}
}

class _Milestone {
	_Milestone(this.id, this.title, this.description, this.skill);

	final String id;
	final String title;
	final String description;
	final String skill;
	bool completed = false;
}

class _MilestoneTile extends StatelessWidget {
	const _MilestoneTile({
		required this.index,
		required this.milestone,
		required this.isLast,
		required this.onChanged,
	});

	final int index;
	final _Milestone milestone;
	final bool isLast;
	final ValueChanged<bool?> onChanged;

	@override
	Widget build(BuildContext context) {
		final color = milestone.completed ? Theme.of(context).colorScheme.primary : const Color(0xFF9BA7A0);
		return IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
			SizedBox(width: 42, child: Column(children: [
				Container(
					width: 34,
					height: 34,
					alignment: Alignment.center,
					decoration: BoxDecoration(
						shape: BoxShape.circle,
						color: milestone.completed ? color : Colors.white,
						border: Border.all(color: color, width: 1.5),
					),
					child: milestone.completed ? const Icon(Icons.check, color: Colors.white, size: 19) : Text('$index', style: TextStyle(color: color)),
				),
				if (!isLast) Expanded(child: Container(width: 2, margin: const EdgeInsets.symmetric(vertical: 4), color: const Color(0xFFD9DFDA))),
			])),
			const SizedBox(width: 8),
			Expanded(child: Card(
				margin: const EdgeInsets.only(bottom: 12),
				child: Padding(
					padding: const EdgeInsets.fromLTRB(12, 10, 8, 10),
					child: Row(children: [
						Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
							Text(milestone.title, style: const TextStyle(fontWeight: FontWeight.w700)),
							const SizedBox(height: 4),
							Text(milestone.description, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, height: 1.35)),
							const SizedBox(height: 7),
							Text('重点：${milestone.skill}', style: TextStyle(color: Theme.of(context).colorScheme.primary, fontSize: 12, fontWeight: FontWeight.w600)),
						])),
						Checkbox(value: milestone.completed, onChanged: onChanged, semanticLabel: '标记${milestone.title}完成'),
					]),
				),
			)),
		]));
	}
}
