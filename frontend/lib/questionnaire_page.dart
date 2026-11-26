import 'package:flutter/material.dart';

import 'career_profile.dart';
import 'models/evidence_level.dart';
import 'models/occupation_option.dart';
import 'models/skill_option.dart';
import 'services/api_service.dart';
import 'services/profile_storage.dart';

class QuestionnairePage extends StatefulWidget {
	const QuestionnairePage({super.key});

	@override
	State<QuestionnairePage> createState() => _QuestionnairePageState();
}

typedef KnowledgeBase = ({List<SkillOption> skills, List<OccupationOption> occupations});

/// `.wait` 会把两路请求的失败包成 ParallelWaitError，界面只展示第一条原因。
String _describeError(Object error) => '${error}'
        .replaceFirst(RegExp(r'ParallelWaitError\(\d+ errors\):\s*'), '')
        .split('\n')
        .first
        .replaceFirst('Bad state: ', '');

class _QuestionnairePageState extends State<QuestionnairePage> {
	final _formKey = GlobalKey<FormState>();
	final _nameController = TextEditingController();
	final Set<String> _selectedSkillIds = <String>{};
	final Map<String, int> _levels = <String, int>{};
	final Map<String, String> _evidence = <String, String>{};

	ProfileStorage? _storage;
	List<SkillOption> _skills = <SkillOption>[];
	List<OccupationOption> _occupations = <OccupationOption>[];
	String _occupationId = '';
	String _experience = '刚刚起步';
	double _weeklyHours = 6;
	String _skillQuery = '';

	late final Future<KnowledgeBase> _bootstrap;

	@override
	void initState() {
		super.initState();
		_bootstrap = _loadKnowledgeBase();
	}

	Future<KnowledgeBase> _loadKnowledgeBase() async {
		final storage = await ProfileStorage.open();
		final loaded = await (
			ApiService.fetchSkills(),
			ApiService.fetchOccupations(),
		).wait;
		final skills = loaded.$1;
		final occupations = loaded.$2;
		if (mounted) _applyLoaded(skills, occupations, storage);
		return (skills: skills, occupations: occupations);
	}

	void _applyLoaded(
		List<SkillOption> skills,
		List<OccupationOption> occupations,
		ProfileStorage storage,
	) {
		setState(() {
			_storage = storage;
			_skills = skills;
			_occupations = occupations;
			_occupationId = occupations.first.occupationId;
		});
		_restore(storage, occupations);
	}

	/// 把上次填报的画像回填到表单，用于「刷新或重进后进度不丢失」。
	void _restore(ProfileStorage storage, List<OccupationOption> occupations) {
		final saved = storage.loadProfile();
		if (saved == null) return;
		final knownOccupation = occupations
				.any((item) => item.occupationId == saved.occupationId);
		setState(() {
			_nameController.text = saved.name;
			_experience = saved.experience;
			_weeklyHours = saved.weeklyHours.toDouble();
			if (knownOccupation) _occupationId = saved.occupationId!;
			_selectedSkillIds.clear();
			_levels.clear();
			_evidence.clear();
			for (final skill in saved.skills) {
				if (!_skills.any((option) => option.skillId == skill.skillId)) {
					continue;
				}
				_selectedSkillIds.add(skill.skillId);
				_levels[skill.skillId] = skill.selfLevel;
				_evidence[skill.skillId] = skill.evidenceLevel;
			}
		});
	}

	@override
	void dispose() {
		_nameController.dispose();
		super.dispose();
	}

	CareerProfile _buildProfile() {
		final occupation = _occupations.firstWhere(
			(item) => item.occupationId == _occupationId,
		);
		final skills = _selectedSkillIds.map((skillId) {
			final option = _skills.firstWhere((item) => item.skillId == skillId);
			return ProfileSkill(
				skillId: skillId,
				name: option.displayName,
				selfLevel: _levels[skillId] ?? 0,
				evidenceLevel: _evidence[skillId] ?? EvidenceLevel.defaultLevel,
			);
		}).toList();
		return CareerProfile(
			name: _nameController.text.trim(),
			targetRole: occupation.nameZh,
			experience: _experience,
			skills: skills,
			weeklyHours: _weeklyHours.round(),
			occupationId: occupation.occupationId,
		);
	}

	Future<void> _continue() async {
		if (!_formKey.currentState!.validate()) return;
		if (_selectedSkillIds.isEmpty) {
			ScaffoldMessenger.of(context).showSnackBar(
					const SnackBar(content: Text('至少选择一项已接触过的技能')));
			return;
		}
		final profile = _buildProfile();
		await _storage?.saveProfile(profile);
		if (!mounted) return;
		Navigator.pushNamed(context, '/recommendation', arguments: profile);
	}

	Future<void> _preview() async {
		if (_skills.isEmpty || _occupations.isEmpty) {
			ScaffoldMessenger.of(context).showSnackBar(
					const SnackBar(content: Text('知识库还在加载，稍后再试')));
			return;
		}
		final profile = CareerProfile(
			name: _nameController.text.trim().isEmpty ? '访客' : _nameController.text.trim(),
			targetRole: _occupations.first.nameZh,
			experience: _experience,
			skills: _skills.take(3).map((option) => ProfileSkill(
						skillId: option.skillId,
						name: option.displayName,
						selfLevel: _levels[option.skillId] ?? 2,
						evidenceLevel: _evidence[option.skillId] ?? EvidenceLevel.defaultLevel,
					)).toList(),
			weeklyHours: _weeklyHours.round(),
			occupationId: _occupations.first.occupationId,
		);
		await _storage?.saveProfile(profile);
		if (!mounted) return;
		Navigator.pushNamed(context, '/recommendation', arguments: profile);
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(
				title: const Text('CareerOS'),
				actions: [
					TextButton.icon(
						onPressed: _preview,
						icon: const Icon(Icons.arrow_forward, size: 18),
						label: const Text('先看看'),
					),
					const SizedBox(width: 8),
				],
			),
			body: FutureBuilder<KnowledgeBase>(
				future: _bootstrap,
				builder: (context, snapshot) {
					if (snapshot.connectionState != ConnectionState.done) {
						return const Center(child: CircularProgressIndicator());
					}
					if (snapshot.hasError) {
						return _LoadFailure(
							message: _describeError(snapshot.error!),
							onRetry: () => setState(
									() => _bootstrap = _loadKnowledgeBase()),
						);
					}
					return _buildForm();
				},
			),
		);
	}

	Widget _buildForm() {
		final visibleSkills = _skills.where((option) {
			if (_skillQuery.trim().isEmpty) return true;
			final query = _skillQuery.trim().toLowerCase();
			return option.name.toLowerCase().contains(query) ||
					option.nameZh.toLowerCase().contains(query);
		}).toList();
		final selectedSkills = _selectedSkillIds
				.map((skillId) => _skills.firstWhere((item) => item.skillId == skillId))
				.toList()
			  ..sort((a, b) => a.displayName.compareTo(b.displayName));

		return Center(
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
								value: _occupationId,
								decoration: InputDecoration(
									labelText: '目标职业',
									helperText: '共 ${_occupations.length} 个职业来自后端知识库',
									prefixIcon: const Icon(Icons.explore_outlined),
								),
								items: _occupations
										.map((occupation) => DropdownMenuItem<String>(
													value: occupation.occupationId,
													child: Text(
														'${occupation.nameZh} · ${occupation.skillCount} 项技能',
														overflow: TextOverflow.ellipsis,
													),
												))
										.toList(),
								onChanged: (value) => setState(() => _occupationId = value!),
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
							Row(
								children: [
									const Expanded(
										child: Text('已经接触过的技能',
												style: TextStyle(fontWeight: FontWeight.w600)),
									),
									Text('已选 ${_selectedSkillIds.length} 项',
											style: const TextStyle(fontWeight: FontWeight.w600)),
								],
							),
							const SizedBox(height: 10),
							TextField(
								decoration: const InputDecoration(
									hintText: '搜索技能，例如 Python 或 编程',
									prefixIcon: Icon(Icons.search),
									isDense: true,
								),
								onChanged: (value) => setState(() => _skillQuery = value),
							),
							const SizedBox(height: 10),
							Wrap(
								spacing: 8,
								runSpacing: 8,
								children: visibleSkills.map((option) => FilterChip(
											label: Text(option.displayName),
											selected: _selectedSkillIds.contains(option.skillId),
											onSelected: (selected) => setState(() {
												if (selected) {
													_selectedSkillIds.add(option.skillId);
													_levels.putIfAbsent(option.skillId, () => 2);
													_evidence.putIfAbsent(
															option.skillId, () => EvidenceLevel.defaultLevel);
												} else {
													_selectedSkillIds.remove(option.skillId);
													_levels.remove(option.skillId);
													_evidence.remove(option.skillId);
												}
											}),
										)).toList(),
							),
							if (selectedSkills.isNotEmpty) ...<Widget>[
								const SizedBox(height: 18),
								const Text('逐项确认掌握程度与证据',
										style: TextStyle(fontWeight: FontWeight.w600)),
								const SizedBox(height: 6),
								...selectedSkills.map((option) => _SkillAssessmentTile(
											title: option.displayName,
											level: _levels[option.skillId] ?? 0,
											evidence: _evidence[option.skillId] ??
													EvidenceLevel.defaultLevel,
											onLevelChanged: (value) => setState(
													() => _levels[option.skillId] = value),
											onEvidenceChanged: (value) => setState(
													() => _evidence[option.skillId] = value!),
										)),
							],
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
		);
	}
}

class _SkillAssessmentTile extends StatelessWidget {
	const _SkillAssessmentTile({
		required this.title,
		required this.level,
		required this.evidence,
		required this.onLevelChanged,
		required this.onEvidenceChanged,
	});

	final String title;
	final int level;
	final String evidence;
	final ValueChanged<int> onLevelChanged;
	final ValueChanged<String?> onEvidenceChanged;

	@override
	Widget build(BuildContext context) {
		return Card(
			margin: const EdgeInsets.only(bottom: 8),
			child: Padding(
				padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
				child: Column(
					crossAxisAlignment: CrossAxisAlignment.start,
					children: [
						Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
						Row(
							children: [
								Expanded(
									child: Slider(
										value: level.toDouble(),
										min: SkillLevel.min.toDouble(),
										max: SkillLevel.max.toDouble(),
										divisions: SkillLevel.max,
										label: '$level 级',
										onChanged: (value) => onLevelChanged(value.round()),
									),
								),
								SizedBox(
									width: 118,
									child: Text(SkillLevel.labelOf(level),
											style: const TextStyle(fontSize: 12),
											textAlign: TextAlign.end),
								),
							],
						),
						DropdownButtonHideUnderline(
							child: DropdownButton<String>(
								value: evidence,
								isDense: true,
								style: const TextStyle(fontSize: 13),
								items: EvidenceLevel.labels.entries
										.map((entry) => DropdownMenuItem<String>(
													value: entry.key,
													child: Text('证据：${entry.value}'),
												))
										.toList(),
								onChanged: onEvidenceChanged,
							),
						),
					],
				),
			),
		);
	}
}

class _LoadFailure extends StatelessWidget {
	const _LoadFailure({required this.message, required this.onRetry});

	final String message;
	final VoidCallback onRetry;

	@override
	Widget build(BuildContext context) {
		return Center(
			child: Padding(
				padding: const EdgeInsets.all(24),
				child: Column(mainAxisSize: MainAxisSize.min, children: [
					const Icon(Icons.cloud_off_outlined, size: 42),
					const SizedBox(height: 12),
					Text('无法读取职业与技能知识库：$message', textAlign: TextAlign.center),
					const SizedBox(height: 16),
					OutlinedButton(onPressed: onRetry, child: const Text('重试')),
				]),
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
