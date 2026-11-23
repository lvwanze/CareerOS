import 'package:flutter/material.dart';

import 'career_profile.dart';

class QuestionnairePage extends StatefulWidget {
	const QuestionnairePage({super.key});

	@override
	State<QuestionnairePage> createState() => _QuestionnairePageState();
}

class _QuestionnairePageState extends State<QuestionnairePage> {
	final _formKey = GlobalKey<FormState>();
	final _nameController = TextEditingController();
	final _skillController = TextEditingController();
	final Set<String> _selectedSkills = {'Flutter', 'Dart'};
	String _targetRole = '移动开发';
	String _experience = '刚刚起步';
	double _weeklyHours = 6;

	static const _skillOptions = ['Flutter', 'Dart', 'Python', 'SQL', 'Figma', 'Git'];

	@override
	void dispose() {
		_nameController.dispose();
		_skillController.dispose();
		super.dispose();
	}

	void _addSkill(String value) {
		final skill = value.trim();
		if (skill.isEmpty) return;
		setState(() {
			_selectedSkills.add(skill);
			_skillController.clear();
		});
	}

	void _continue() {
		if (!_formKey.currentState!.validate()) return;
		final profile = CareerProfile(
			name: _nameController.text.trim(),
			targetRole: _targetRole,
			experience: _experience,
			skills: _selectedSkills.toList(),
			weeklyHours: _weeklyHours.round(),
		);
		Navigator.pushNamed(context, '/recommendation', arguments: profile);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('CareerOS'),
				actions: [
					TextButton.icon(
						onPressed: () => Navigator.pushNamed(
							context,
							'/recommendation',
							arguments: const CareerProfile(
								name: '访客',
								targetRole: '移动开发',
								experience: '刚刚起步',
								skills: ['Flutter', 'Dart'],
								weeklyHours: 6,
							),
						),
						icon: const Icon(Icons.arrow_forward, size: 18),
						label: const Text('先看看'),
					),
					const SizedBox(width: 8),
				],
			),
			body: Center(
				child: ConstrainedBox(
					constraints: const BoxConstraints(maxWidth: 760),
					child: Form(
						key: _formKey,
						child: ListView(
							padding: const EdgeInsets.fromLTRB(20, 14, 20, 36),
							children: [
								const Text('先认识一下你',
										style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700)),
								const SizedBox(height: 8),
								Text(
									'几项简单信息，帮你找到下一步的职业方向。',
									style: TextStyle(
										color: Theme.of(context).colorScheme.onSurfaceVariant,
										fontSize: 15,
									),
								),
								const SizedBox(height: 28),
								const _SectionHeading(number: '01', title: '基本信息'),
								const SizedBox(height: 14),
								TextFormField(
									controller: _nameController,
									textInputAction: TextInputAction.next,
									decoration: const InputDecoration(
										labelText: '怎么称呼你',
										hintText: '例如：林同学',
										prefixIcon: Icon(Icons.person_outline),
									),
									validator: (value) => value == null || value.trim().isEmpty
											? '请填写称呼'
											: null,
								),
								const SizedBox(height: 14),
								DropdownButtonFormField<String>(
									value: _targetRole,
									decoration: const InputDecoration(
										labelText: '感兴趣的方向',
										prefixIcon: Icon(Icons.explore_outlined),
									),
									items: const [
										DropdownMenuItem(value: '移动开发', child: Text('移动开发')),
										DropdownMenuItem(value: '后端开发', child: Text('后端开发')),
										DropdownMenuItem(value: '产品设计', child: Text('产品设计')),
										DropdownMenuItem(value: '数据分析', child: Text('数据分析')),
									],
									onChanged: (value) => setState(() => _targetRole = value!),
								),
								const SizedBox(height: 28),
								const _SectionHeading(number: '02', title: '目前的起点'),
								const SizedBox(height: 14),
								Wrap(
									spacing: 10,
									runSpacing: 10,
									children: ['刚刚起步', '有项目经验', '有工作经验'].map((level) {
										return ChoiceChip(
											label: Text(level),
											selected: _experience == level,
											onSelected: (_) => setState(() => _experience = level),
										);
									}).toList(),
								),
								const SizedBox(height: 20),
								const Text('已经接触过的技能',
										style: TextStyle(fontWeight: FontWeight.w600)),
								const SizedBox(height: 10),
								Wrap(
									spacing: 8,
									runSpacing: 8,
									children: [
										..._skillOptions.map((skill) => FilterChip(
													label: Text(skill),
													selected: _selectedSkills.contains(skill),
													onSelected: (selected) => setState(() {
														if (selected) {
															_selectedSkills.add(skill);
														} else {
															_selectedSkills.remove(skill);
														}
													}),
												)),
										..._selectedSkills
												.where((skill) => !_skillOptions.contains(skill))
												.map((skill) => InputChip(
															label: Text(skill),
															onDeleted: () => setState(
																() => _selectedSkills.remove(skill),
															),
														)),
									],
								),
								const SizedBox(height: 10),
								TextField(
									controller: _skillController,
									decoration: InputDecoration(
										hintText: '添加其他技能后按回车',
										prefixIcon: const Icon(Icons.add),
										suffixIcon: IconButton(
											tooltip: '添加技能',
											onPressed: () => _addSkill(_skillController.text),
											icon: const Icon(Icons.add_circle_outline),
										),
									),
									textInputAction: TextInputAction.done,
									onSubmitted: _addSkill,
								),
								const SizedBox(height: 28),
								const _SectionHeading(number: '03', title: '每周可投入时间'),
								Row(
									children: [
										Expanded(
											child: Slider(
												value: _weeklyHours,
												min: 2,
												max: 20,
												divisions: 9,
												label: '${_weeklyHours.round()} 小时',
												onChanged: (value) => setState(() => _weeklyHours = value),
											),
										),
										SizedBox(
											width: 82,
											child: Text('${_weeklyHours.round()} 小时 / 周',
													textAlign: TextAlign.end,
													style: const TextStyle(fontWeight: FontWeight.w600)),
										),
									],
								),
								const SizedBox(height: 24),
								FilledButton.icon(
									onPressed: _continue,
									icon: const Icon(Icons.arrow_forward),
									label: const Text('生成我的方向建议'),
									style: FilledButton.styleFrom(
										minimumSize: const Size.fromHeight(54),
										shape: RoundedRectangleBorder(
											borderRadius: BorderRadius.circular(10),
										),
									),
								),
							],
						),
					),
				),
			),
		);
	}
}

class _SectionHeading extends StatelessWidget {
	const _SectionHeading({required this.number, required this.title});

	final String number;
	final String title;

	@override
	Widget build(BuildContext context) {
		return Row(
			children: [
				Text(number, style: TextStyle(
					color: Theme.of(context).colorScheme.primary,
					fontWeight: FontWeight.w700,
				)),
				const SizedBox(width: 10),
				Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
			],
		);
	}
}
