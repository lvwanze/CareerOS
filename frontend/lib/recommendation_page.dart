import 'package:flutter/material.dart';

import 'career_navigation.dart';
import 'career_profile.dart';
import 'models/recommendation.dart';
import 'services/api_service.dart';
import 'services/profile_storage.dart';

class RecommendationPage extends StatefulWidget {
	const RecommendationPage({required this.profile, super.key});

	final CareerProfile profile;

	@override
	State<RecommendationPage> createState() => _RecommendationPageState();
}

class _RecommendationPageState extends State<RecommendationPage> {
	final Set<String> _saved = <String>{};
	ProfileStorage? _storage;
	late Future<RecommendationResult> _recommendations;

	@override
	void initState() {
		super.initState();
		_recommendations = _load();
		_restoreBookmarks();
	}

	Future<void> _restoreBookmarks() async {
		final storage = await ProfileStorage.open();
		if (!mounted) return;
		setState(() {
			_storage = storage;
			_saved.addAll(storage.loadSavedOccupations());
		});
	}

	Future<RecommendationResult> _load() =>
		ApiService.fetchRecommendations(widget.profile.toJson());

	Future<void> _toggleSaved(String occupationId, bool saved) async {
		setState(() => saved ? _saved.add(occupationId) : _saved.remove(occupationId));
		await _storage?.saveOccupation(occupationId, saved: saved);
	}

	void _openPath(CareerRecommendation item) {
		Navigator.pushNamed(
			context,
			'/skill-tree',
			arguments: widget.profile.copyWith(occupationId: item.occupationId),
		);
	}

	@override
	Widget build(BuildContext context) {
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
			body: !widget.profile.hasSkills
					? const _NoSkillsHint()
					: FutureBuilder<RecommendationResult>(
						future: _recommendations,
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
										Text('无法获取推荐：${snapshot.error}',
												textAlign: TextAlign.center),
										if (snapshot.error is ApiException)
											const SizedBox(height: 6),
										const SizedBox(height: 16),
										OutlinedButton(
											onPressed: () => setState(
													() => _recommendations = _load()),
											child: const Text('重试'),
										),
									]),
								));
							}
							final result = snapshot.data!;
							if (result.recommendations.isEmpty) {
								return const Center(
										child: Text('暂无可推荐的职业，请补充技能画像后重试。'));
							}
							return _buildList(result);
						},
					),
			bottomNavigationBar: CareerNavigationBar(currentIndex: 1, profile: widget.profile),
		);
	}

	Widget _buildList(RecommendationResult result) {
		return Center(
			child: ConstrainedBox(
				constraints: const BoxConstraints(maxWidth: 820),
				child: ListView(
					padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
					children: [
						Text('${widget.profile.name}，下一步可以这样走。',
								style: const TextStyle(fontSize: 27, fontWeight: FontWeight.w700)),
						const SizedBox(height: 8),
						Text(
							'匹配分、能力差距与发展路径均由后端 ${result.modelVersion} 依据 ${widget.profile.skills.length} 项技能自评算出。',
							style: TextStyle(
									color: Theme.of(context).colorScheme.onSurfaceVariant,
									height: 1.5),
						),
						const SizedBox(height: 20),
						...result.recommendations.asMap().entries.map((entry) =>
								_RecommendationCard(
									index: entry.key,
									item: entry.value,
									saved: _saved.contains(entry.value.occupationId),
									onSaveChanged: (saved) =>
											_toggleSaved(entry.value.occupationId, saved),
									onOpenPath: () => _openPath(entry.value),
								)),
					],
				),
			),
		);
	}
}

class _RecommendationCard extends StatelessWidget {
	const _RecommendationCard({
		required this.index,
		required this.item,
		required this.saved,
		required this.onSaveChanged,
		required this.onOpenPath,
	});

	final int index;
	final CareerRecommendation item;
	final bool saved;
	final ValueChanged<bool> onSaveChanged;
	final VoidCallback onOpenPath;

	static const Map<String, String> _statusLabels = <String, String>{
		'mastered': '已掌握',
		'needs_improvement': '待提升',
		'needs_verification': '待验证',
	};

	int _countOf(String status) =>
			item.skillGaps.where((gap) => gap.status == status).length;

	List<SkillGapResult> get _topGaps => item.skillGaps
			.where((gap) => gap.status == 'needs_improvement')
			.toList()
		  ..sort((a, b) {
				final byGap = b.gap.compareTo(a.gap);
				return byGap != 0
						? byGap
						: (b.importance ?? 0).compareTo(a.importance ?? 0);
		  });

	@override
	Widget build(BuildContext context) {
		final muted = Theme.of(context).colorScheme.onSurfaceVariant;
		return Card(
			margin: const EdgeInsets.only(bottom: 12),
			child: Padding(
				padding: const EdgeInsets.all(16),
				child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
					Row(children: [
						Expanded(
							child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
								Text(
									index == 0
											? '优先探索 · ${item.occupationNameZh}'
											: item.occupationNameZh,
									style: const TextStyle(
											fontSize: 17, fontWeight: FontWeight.w700),
								),
								Text(item.occupationName, style: TextStyle(color: muted)),
							]),
						),
						IconButton(
							tooltip: saved ? '取消收藏' : '收藏方向',
							onPressed: () => onSaveChanged(!saved),
							icon: Icon(saved ? Icons.bookmark : Icons.bookmark_border),
						),
					]),
					const SizedBox(height: 10),
					Row(children: [
						Expanded(
							child: ClipRRect(
								borderRadius: BorderRadius.circular(4),
								child: LinearProgressIndicator(
										value: item.matchScore, minHeight: 7),
							),
						),
						const SizedBox(width: 12),
						Text('${(item.matchScore * 100).round()}% 匹配',
								style: const TextStyle(fontWeight: FontWeight.w700)),
					]),
					const SizedBox(height: 14),
					Wrap(spacing: 8, runSpacing: 8, children: [
						for (final entry in _statusLabels.entries)
							Chip(
								label: Text('${entry.value} ${_countOf(entry.key)}'),
								visualDensity: VisualDensity.compact,
							),
					]),
					const SizedBox(height: 14),
					const Text('匹配依据', style: TextStyle(fontWeight: FontWeight.w700)),
					const SizedBox(height: 6),
					...item.recommendationReasons.take(3).map((reason) => Padding(
								padding: const EdgeInsets.only(bottom: 4),
								child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
									Text('· ', style: TextStyle(color: muted)),
									Expanded(child: Text(reason, style: const TextStyle(height: 1.4))),
								]),
							)),
					if (_topGaps.isNotEmpty) ...<Widget>[
						const SizedBox(height: 10),
						const Text('优先补的能力差距',
								style: TextStyle(fontWeight: FontWeight.w700)),
						const SizedBox(height: 6),
						..._topGaps.take(4).map((gap) => Padding(
									padding: const EdgeInsets.only(bottom: 4),
									child: Row(children: [
										Expanded(
											child: Text(gap.skillNameZh ?? gap.skillName ?? gap.skillId,
													overflow: TextOverflow.ellipsis),
										),
										Text('${gap.currentLevel} → ${gap.requiredLevel} 级',
												style: TextStyle(color: muted, fontSize: 13)),
										const SizedBox(width: 8),
										Text('差 ${gap.gap} 级',
												style: const TextStyle(
														fontWeight: FontWeight.w600, fontSize: 13)),
									]),
								)),
					],
					if (_countOf('needs_verification') > 0) ...<Widget>[
						const SizedBox(height: 10),
						Text(
							'有 ${_countOf('needs_verification')} 项技能自评已达等级但缺少证据，补一次课程、项目或证书记录即可转为已掌握。',
							style: TextStyle(color: muted, fontSize: 13, height: 1.45),
						),
					],
					const SizedBox(height: 14),
					Align(
						alignment: Alignment.centerRight,
						child: OutlinedButton.icon(
							onPressed: onOpenPath,
							icon: const Icon(Icons.account_tree_outlined, size: 18),
							label: const Text('查看发展路径'),
						),
					),
				]),
			),
		);
	}
}

class _NoSkillsHint extends StatelessWidget {
	const _NoSkillsHint();

	@override
	Widget build(BuildContext context) {
		return Center(
			child: Padding(
				padding: const EdgeInsets.all(24),
				child: Column(mainAxisSize: MainAxisSize.min, children: [
					const Icon(Icons.how_to_reg_outlined, size: 42),
					const SizedBox(height: 12),
					const Text('还没有填写任何技能，先去填报页选几项已接触过的技能。',
							textAlign: TextAlign.center),
					const SizedBox(height: 16),
					FilledButton.icon(
						onPressed: () => Navigator.pushReplacementNamed(
								context, '/questionnaire'),
						icon: const Icon(Icons.arrow_forward),
						label: const Text('去填报画像'),
					),
				]),
			),
		);
	}
}
