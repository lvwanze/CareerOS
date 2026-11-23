// ignore: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:frontend/core/app_layout.dart';
import 'package:frontend/core/model_labels.dart';
import 'package:frontend/models/development_path.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/storage_service.dart';

/// 发展树页：按职业展示学习节点，勾选即记为已掌握，进度存本地。
///
/// 说明：当前后端 /v1/tree/{occupation_id} 返回的是扁平 nodes 数组，
/// 没有 parent_id / level，表达不了真正的父子层级，
/// 所以这里先按「学习顺序」线性渲染。等后端补了层级字段，
/// 只要把 _buildNodeList 换成递归构造就能升级成树，其余逻辑不用动。
class TreePage extends StatefulWidget {
  const TreePage({
    super.key,
    required this.reloadToken,
    required this.onGoRecommend,
    this.occupationId,
  });

  final int reloadToken;
  final VoidCallback onGoRecommend;

  /// 由推荐页点进来的职业 ID。
  /// 为空时（冷启动）回退到本地存的上一次选择，避免首屏空着。
  final String? occupationId;

  @override
  State<TreePage> createState() => _TreePageState();
}

class _TreePageState extends State<TreePage> {
  bool _loading = true;
  String? _errorMessage;
  String _occupationId = '';
  String _requestId = '';
  List<TreeNode> _nodes = <TreeNode>[];
  Set<String> _masteredNodeIds = <String>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant TreePage oldWidget) {
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

    final occupationId =
        widget.occupationId ?? await StorageService.loadLastOccupation();
    if (occupationId == null || occupationId.isEmpty) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _errorMessage = '还没有选择职业，先去推荐页点一个职业的「查看发展树」';
      });
      return;
    }

    try {
      final result = await ApiService.fetchCareerTree(occupationId);
      final progress = await StorageService.loadProgress(occupationId);
      if (!mounted) {
        return;
      }
      setState(() {
        _occupationId = occupationId;
        _nodes = result.data;
        _requestId = result.requestId;
        // 只保留仍然存在的节点 ID，后端删节点后本地脏数据不会算进进度。
        final aliveIds = result.data.map((node) => node.nodeId).toSet();
        _masteredNodeIds = progress.intersection(aliveIds);
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

  Future<void> _toggleNode(TreeNode node, bool mastered) async {
    setState(() {
      if (mastered) {
        _masteredNodeIds.add(node.nodeId);
      } else {
        _masteredNodeIds.remove(node.nodeId);
      }
    });
    // 每次勾选立刻落盘，不等用户点保存，避免杀进程丢进度。
    await StorageService.saveProgress(_occupationId, _masteredNodeIds);
  }

  Future<void> _resetProgress() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('清空本职业进度'),
        content: Text('会把「$_occupationId」下已勾选的 ${_masteredNodeIds.length} 个节点全部重置。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('确认清空'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }
    setState(() => _masteredNodeIds = <String>{});
    await StorageService.saveProgress(_occupationId, <String>{});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('发展树'),
        actions: [
          IconButton(
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
            tooltip: '重新拉取发展树',
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
      final needsOccupation = _errorMessage!.contains('推荐页');
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.route_outlined, size: 40),
              const SizedBox(height: 12),
              Text('发展树加载失败', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: needsOccupation ? widget.onGoRecommend : _load,
                icon: Icon(needsOccupation ? Icons.explore : Icons.refresh),
                label: Text(needsOccupation ? '去推荐页选职业' : '重试'),
              ),
            ],
          ),
        ),
      );
    }

    if (_nodes.isEmpty) {
      return Center(
        child: Text(
          '该职业还没有可展示的学习节点',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      );
    }

    return SingleChildScrollView(
      padding: pagePaddingOf(context),
      child: ContentWidth(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildProgressCard(context),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Column(
                  children: _buildNodeList(context),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressCard(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final total = _nodes.length;
    final done = _masteredNodeIds.length;
    final ratio = total == 0 ? 0.0 : done / total;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('职业 $_occupationId', style: textTheme.titleMedium),
                ),
                Text(
                  '${(ratio * 100).round()}%',
                  style: textTheme.titleLarge?.copyWith(color: scheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text('$done / $total 个节点已掌握', style: textTheme.bodySmall),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(value: ratio, minHeight: 8),
            ),
            if (_requestId.isNotEmpty) ...[
              const SizedBox(height: 8),
              SelectableText(
                'request_id: $_requestId',
                style: textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: _masteredNodeIds.isEmpty ? null : _resetProgress,
                icon: const Icon(Icons.restart_alt),
                label: const Text('清空进度'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildNodeList(BuildContext context) {
    final widgets = <Widget>[];
    for (var index = 0; index < _nodes.length; index++) {
      final node = _nodes[index];
      final mastered = _masteredNodeIds.contains(node.nodeId);
      widgets.add(
        CheckboxListTile(
          value: mastered,
          onChanged: (checked) => _toggleNode(node, checked == true),
          controlAffinity: ListTileControlAffinity.leading,
          secondary: CircleAvatar(
            radius: 14,
            child: Text(
              '${index + 1}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          title: Text(
            node.displayName,
            style: mastered
                ? const TextStyle(decoration: TextDecoration.lineThrough)
                : null,
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (node.description.isNotEmpty) Text(node.description),
              const SizedBox(height: 2),
              Text(
                '后端状态 ${node.status.label} · 本地进度 ${mastered ? '已掌握' : '未掌握'}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      );
    }
    return widgets;
  }
}
