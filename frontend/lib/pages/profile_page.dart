// ignore: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:frontend/core/app_layout.dart';
import 'package:frontend/core/model_labels.dart';
import 'package:frontend/models/skill_option.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/storage_service.dart';

/// 填报页：用户信息 + 技能自评。
///
/// 产出结构严格对齐 docs/data_contract.md §3.1 的 UserProfile：
/// {
///   user_id, learning_stage{education_level, major, current_stage},
///   preferences, skills[{skill_id, self_level}], constraints, career_goals
/// }
class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key, required this.onSubmitted});

  /// 提交成功后通知外层切到推荐页。
  final VoidCallback onSubmitted;

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  // 联调统一账号：当前版本没有登录模块，先用 user_id 承载账号标识。
  static const String _defaultUserId = 'tester@careeros.com';

  static const List<String> _educationOptions = ['专科', '本科', '硕士', '博士'];
  static const List<String> _stageOptions = [
    '大一',
    '大二',
    '大三',
    '大四',
    '研一',
    '研二',
    '研三',
    '应届',
    '在职',
  ];
  static const List<String> _levelLabels = [
    '未掌握',
    '了解概念',
    '能做基础',
    '能独立做',
    '熟练应用',
  ];

  final TextEditingController _userIdController =
      TextEditingController(text: _defaultUserId);
  final TextEditingController _majorController =
      TextEditingController(text: '软件工程');
  final TextEditingController _searchController = TextEditingController();

  String _education = '本科';
  String _stage = '大三';

  bool _loading = true;
  String? _errorMessage;
  List<SkillOption> _skills = <SkillOption>[];

  /// skill_id -> 自评等级 0~4
  final Map<String, int> _selectedLevels = <String, int>{};
  String _keyword = '';

  @override
  void initState() {
    super.initState();
    _restoreAndLoad();
  }

  @override
  void dispose() {
    _userIdController.dispose();
    _majorController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  /// 先把上次存过的画像回填，再去后端拉技能字典。
  Future<void> _restoreAndLoad() async {
    final saved = await StorageService.loadProfile();
    if (saved != null && mounted) {
      setState(() {
        _userIdController.text = (saved['user_id'] as String?) ?? _defaultUserId;
        final dynamic stage = saved['learning_stage'];
        if (stage is Map<String, dynamic>) {
          _education = (stage['education_level'] as String?) ?? _education;
          _stage = (stage['current_stage'] as String?) ?? _stage;
          _majorController.text = (stage['major'] as String?) ?? _majorController.text;
        }
        final dynamic skills = saved['skills'];
        if (skills is List) {
          for (final dynamic item in skills) {
            if (item is Map<String, dynamic>) {
              final id = item['skill_id'];
              final level = item['self_level'];
              if (id is String && level is int) {
                _selectedLevels[id] = level;
              }
            }
          }
        }
      });
    }
    await _loadSkills();
  }

  Future<void> _loadSkills() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });
    try {
      final result = await ApiService.fetchSkills();
      if (!mounted) {
        return;
      }
      setState(() {
        _skills = result.data;
        _loading = false;
        if (_skills.isEmpty) {
          _errorMessage = '技能列表为空，请检查后端 /api/v1/skills 是否正常返回';
        }
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

  List<SkillOption> get _filteredSkills {
    final keyword = _keyword.trim().toLowerCase();
    if (keyword.isEmpty) {
      return _skills;
    }
    return _skills.where((skill) {
      final zh = skill.nameZh.toLowerCase();
      final en = skill.name.toLowerCase();
      final id = skill.skillId.toLowerCase();
      return zh.contains(keyword) || en.contains(keyword) || id.contains(keyword);
    }).toList();
  }

  Map<String, dynamic> _buildProfile() {
    final skills = _selectedLevels.entries
        .map((entry) => <String, dynamic>{
              'skill_id': entry.key,
              'self_level': entry.value,
            })
        .toList();
    return <String, dynamic>{
      'user_id': _userIdController.text.trim(),
      'learning_stage': <String, dynamic>{
        'education_level': _education,
        'major': _majorController.text.trim(),
        'current_stage': _stage,
      },
      'preferences': <String, dynamic>{},
      'skills': skills,
      'constraints': <String, dynamic>{},
      'career_goals': <String, dynamic>{},
    };
  }

  Future<void> _submit() async {
    if (_userIdController.text.trim().isEmpty) {
      _showHint('请先填写账号 / User ID');
      return;
    }
    if (_selectedLevels.isEmpty) {
      _showHint('至少勾选一项技能并给出自评等级');
      return;
    }

    final profile = _buildProfile();
    await StorageService.saveProfile(profile);
    if (!mounted) {
      return;
    }
    _showHint('已保存 ${_selectedLevels.length} 项技能，开始生成推荐');
    widget.onSubmitted();
  }

  void _showHint(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    // 左信息右技能的双栏至少需要 900 逻辑像素，不然两边都会被挤扁。
    final isWide = MediaQuery.of(context).size.width >= 900;
    return Scaffold(
      appBar: AppBar(
        title: const Text('技能填报'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: Text(
                '已选 ${_selectedLevels.length} / ${_skills.length}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ),
        ],
      ),
      body: _buildBody(context, isWide),
    );
  }

  Widget _buildBody(BuildContext context, bool isWide) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorMessage != null) {
      return _buildError(context);
    }

    final padding = pagePaddingOf(context);
    final basicCard = _buildBasicCard(context);
    final skillCard = _buildSkillCard(context);

    return SingleChildScrollView(
      padding: padding,
      child: ContentWidth(
        child: isWide
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(width: 340, child: basicCard),
                  const SizedBox(width: 20),
                  Expanded(child: skillCard),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [basicCard, const SizedBox(height: 16), skillCard],
              ),
      ),
    );
  }

  Widget _buildError(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 40),
            const SizedBox(height: 12),
            Text(
              '技能列表加载失败',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              _errorMessage!,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _loadSkills,
              icon: const Icon(Icons.refresh),
              label: const Text('重试'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBasicCard(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('基本信息', style: textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              '账号 tester@careeros.com / P@ssw0rd123（当前版本无鉴权，仅作标识）',
              style: textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _userIdController,
              decoration: const InputDecoration(
                labelText: '账号 / User ID',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _majorController,
              decoration: const InputDecoration(
                labelText: '专业',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Text('学历', style: textTheme.labelLarge),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _educationOptions.map((option) {
                return ChoiceChip(
                  label: Text(option),
                  selected: _education == option,
                  onSelected: (selected) {
                    if (selected) {
                      setState(() => _education = option);
                    }
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 16),
            Text('当前阶段', style: textTheme.labelLarge),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _stageOptions.map((option) {
                return ChoiceChip(
                  label: Text(option),
                  selected: _stage == option,
                  onSelected: (selected) {
                    if (selected) {
                      setState(() => _stage = option);
                    }
                  },
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSkillCard(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final filtered = _filteredSkills;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('技能自评（0~4 级）', style: textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              '勾选你会或想学的技能，拖动滑块给出当前水平。等级口径：0 未掌握 / 1 了解概念 / 2 能做基础 / 3 能独立做 / 4 熟练应用',
              style: textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _searchController,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: '搜索技能中文名 / 英文名 / ID',
                border: OutlineInputBorder(),
                isDense: true,
              ),
              onChanged: (value) => setState(() => _keyword = value),
            ),
            const SizedBox(height: 8),
            Text('共 ${filtered.length} 项', style: textTheme.bodySmall),
            const SizedBox(height: 4),
            // 技能条目直接用 Column 铺开，跟着外层页面一起滚动，
            // 不要在 Column 里再塞可滚动列表，否则会互相抢手势。
            ...filtered.map((skill) => _buildSkillRow(context, skill)),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _submit,
                icon: const Icon(Icons.send),
                label: const Text('保存并生成推荐'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSkillRow(BuildContext context, SkillOption skill) {
    final level = _selectedLevels[skill.skillId];
    final isSelected = level != null;
    final subtitle = skill.subtitleName;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Checkbox(
                value: isSelected,
                onChanged: (checked) {
                  setState(() {
                    if (checked == true) {
                      _selectedLevels[skill.skillId] = 1;
                    } else {
                      _selectedLevels.remove(skill.skillId);
                    }
                  });
                },
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(skill.displayName),
                    if (subtitle.isNotEmpty)
                      Text(
                        subtitle,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                  ],
                ),
              ),
              if (level != null)
                Text(
                  '$level 级 · ${_levelLabels[level]}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
            ],
          ),
          if (level != null)
            Padding(
              padding: const EdgeInsets.only(left: 40, right: 8),
              child: Slider(
                value: level.toDouble(),
                min: 0,
                max: 4,
                divisions: 4,
                label: '${level} 级',
                onChanged: (value) {
                  setState(() {
                    _selectedLevels[skill.skillId] = value.round();
                  });
                },
              ),
            ),
        ],
      ),
    );
  }
}
