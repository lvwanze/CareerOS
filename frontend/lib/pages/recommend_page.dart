// ignore: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:frontend/core/app_layout.dart';
import 'package:frontend/core/display_name.dart';
import 'package:frontend/core/level_gap_bar.dart';
import 'package:frontend/core/model_labels.dart';
import 'package:frontend/models/recommendation.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/storage_service.dart';

/// 推荐页：职业匹配结果 + 技能缺口可视化。
class RecommendPage extends StatefulWidget {
  const RecommendPage({
    super.key,
    required this.reloadToken,
    required this.onOpenTree,
    required this.onGoProfile,
  });

  /// 外层每次加一，就代表「用户刚重新提交了画像」，这里要重新拉一次。
  final int reloadToken;
  final ValueChanged<String> onOpenTree;
  final VoidCallback onGoProfile;

  @override
  State<RecommendPage> createState() => _RecommendPageState();
}

class _RecommendPageState extends State<RecommendPage> {
  bool _loading = true;
  String? _errorMessage;
  RecommendationResult? _result;
  String _requestId = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant RecommendPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.reloadToken != widget.reloadToken) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    final profile = await StorageService.loadProfile();
    if (profile == null) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _errorMessage = '还没有填写技能画像，先去填报页提交一次';
      });
      return;
    }

    try {
      final result = await ApiService.fetchRecommendations(profile);
      if (!mounted) {
        return;
      }
      final sorted = List<CareerRecommendation>.from(result.data.recommendations)
        ..sort((a, b) => b.matchScore.compareTo(a.matchScore));
      setState(() {
        _result = RecommendationResult(
          userId: result.data.userId,
          modelVersion: result.data.modelVersion,
          recommendations: sorted,
          developmentPaths: result.data.developmentPaths,
        );
        _requestId = result.requestId;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _errorMessage = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('推荐结果'),
        actions: [
          IconButton(
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
            tooltip: '重新拉取推荐',
          ),
        ],
      ),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorMessage != null) {
      return _buildError(context);
    }

    final result = _result;
    if (result == null || result.recommendations.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.search_off, size: 40),
              const SizedBox(height: 12),
              const Text('没有匹配到职业方向'),
              const SizedBox(height: 8),
              Text(
                '可以多勾几项技能再试，或确认后端 /api/v1/recommendations 是否返回了 data.recommendations',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              FilledButton(onPressed: widget.onGoProfile, child: const Text('去补技能')),
            ],
          ),
        ),
      );
    }

    return SingleChildScrollView(
      padding: pagePaddingOf(context),
      child: ContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildMetaBar(context, result),
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (context, constraints) {
                final columns = gridColumnsOf(context);
                final gap = 16.0;
                final cardWidth =
                    (constraints.maxWidth - gap * (columns - 1)) / columns;
                return Wrap(
                  spacing: gap,
                  runSpacing: gap,
                  children: result.recommendations
                      .map((item) => SizedBox(
                            width: cardWidth,
                            child: _buildRecommendationCard(context, item),
                          ))
                      .toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetaBar(BuildContext context, RecommendationResult result) {
    final textTheme = Theme.of(context).textTheme;
    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '账号 ${result.userId} · 模型 ${result.modelVersion} · 共 ${result.recommendations.length} 条推荐',
              style: textTheme.bodyMedium,
            ),
            const SizedBox(height: 4),
            SelectableText(
              _requestId.isEmpty ? 'request_id: （响应未携带）' : 'request_id: $_requestId',
              style: textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildError(BuildContext context) {
    final needsProfile = _errorMessage!.contains('填报页');
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.warning_amber_rounded, size: 40),
            const SizedBox(height: 12),
            Text('推荐加载失败', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              _errorMessage!,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              children: [
                FilledButton.icon(
                  onPressed: needsProfile ? widget.onGoProfile : _load,
                  icon: Icon(needsProfile ? Icons.edit : Icons.refresh),
                  label: Text(needsProfile ? '去填报' : '重试'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecommendationCard(
    BuildContext context,
    CareerRecommendation recommendation,
  ) {
    final textTheme = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;

    final gaps = recommendation.skillGaps;

    // 分类口径以后端为准：skills_to_improve / skills_to_verify 是算法侧算出来的，
    // 前端自己按 status 再判一遍容易和后端口径跑偏。两个列表都空时才退回 status。
    final improveIds = recommendation.skillsToImprove.toSet();
    final verifyIds = recommendation.skillsToVerify.toSet();
    final useBackendSplit = improveIds.isNotEmpty || verifyIds.isNotEmpty;

    final toImprove = gaps
        .where((gap) => useBackendSplit
            ? improveIds.contains(gap.skillId)
            : gap.status == 'needs_improvement' && gap.gap > 0)
        .toList()
      ..sort((a, b) => b.gap.compareTo(a.gap));
    final toVerify = gaps
        .where((gap) => useBackendSplit
            ? verifyIds.contains(gap.skillId)
            : gap.status == 'needs_verification')
        .toList()
      ..sort((a, b) => b.gap.compareTo(a.gap));
    final masteredCount = recommendation.matchedSkills.isNotEmpty
        ? recommendation.matchedSkills.length
        : gaps.where((gap) => gap.status == 'mastered').length;
    final subtitle = recommendation.subtitleName;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(recommendation.displayName, style: textTheme.titleMedium),
            if (subtitle.isNotEmpty)
              Text(subtitle, style: textTheme.bodySmall),
            const SizedBox(height: 12),
            Row(
              children: [
                Text(
                  formatMatchScore(recommendation.matchScore),
                  style: textTheme.headlineSmall?.copyWith(color: scheme.primary),
                ),
                const SizedBox(width: 8),
                Text('匹配度', style: textTheme.bodySmall),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: recommendation.matchScore.clamp(0, 1).toDouble(),
                minHeight: 6,
              ),
            ),
            const SizedBox(height: 16),
            _buildGapOverview(context, toImprove.length, toVerify.length, masteredCount),
            if (recommendation.recommendationReasons.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text('推荐理由', style: textTheme.labelLarge),
              const SizedBox(height: 4),
              for (final reason in recommendation.recommendationReasons)
                Padding(
                  padding: const EdgeInsets.only(bottom: 2),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('· '),
                      Expanded(
                        child: Text(reason, style: textTheme.bodySmall),
                      ),
                    ],
                  ),
                ),
            ],
            const SizedBox(height: 16),
            if (toImprove.isNotEmpty) ...[
              Text('待提升（${toImprove.length}）', style: textTheme.labelLarge),
              const SizedBox(height: 6),
              ...toImprove.take(5).map((gap) => _buildGapRow(context, gap)),
            ],
            if (toVerify.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text('待验证（${toVerify.length}）', style: textTheme.labelLarge),
              const SizedBox(height: 6),
              ...toVerify.take(3).map((gap) => _buildGapRow(context, gap)),
            ],
            if (toImprove.isEmpty && toVerify.isEmpty)
              Text('该职业要求的技能你已经全部掌握', style: textTheme.bodySmall),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: () async {
                  await StorageService.saveLastOccupation(
                    recommendation.occupationId,
                  );
                  if (!mounted) {
                    return;
                  }
                  widget.onOpenTree(recommendation.occupationId);
                },
                icon: const Icon(Icons.account_tree_outlined),
                label: const Text('查看发展树'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 三类技能占比条：已掌握 / 待提升 / 待验证。
  Widget _buildGapOverview(
    BuildContext context,
    int improving,
    int verifying,
    int mastered,
  ) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final total = improving + verifying + mastered;
    if (total == 0) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: SizedBox(
            height: 8,
            child: Row(
              children: [
                if (mastered > 0)
                  Expanded(flex: mastered, child: ColoredBox(color: scheme.primary)),
                if (improving > 0)
                  Expanded(flex: improving, child: ColoredBox(color: scheme.error)),
                if (verifying > 0)
                  Expanded(flex: verifying, child: ColoredBox(color: scheme.tertiary)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 6),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: [
            _legend(context, scheme.primary, '已掌握 $mastered'),
            _legend(context, scheme.error, '待提升 $improving'),
            _legend(context, scheme.tertiary, '待验证 $verifying'),
          ],
        ),
        const SizedBox(height: 2),
        Text('共 $total 项技能要求', style: textTheme.bodySmall),
      ],
    );
  }

  Widget _legend(BuildContext context, Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }

  Widget _buildGapRow(BuildContext context, SkillGapResult gap) {
    final textTheme = Theme.of(context).textTheme;
    final subtitle = gap.subtitleName;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(gap.displayName, style: textTheme.bodyMedium),
                if (subtitle.isNotEmpty)
                  Text(subtitle, style: textTheme.bodySmall),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              LevelGapBar(
                currentLevel: gap.currentLevel,
                requiredLevel: gap.requiredLevel,
              ),
              const SizedBox(height: 2),
              Text(
                '自评 ${gap.currentLevel} → 要求 ${gap.requiredLevel}',
                style: textTheme.bodySmall,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
