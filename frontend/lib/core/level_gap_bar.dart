// ignore: deprecated_member_use
import 'package:flutter/material.dart';

/// 技能水平可视化：画 4 格代表 0~4 级。
/// 主色 = 已达到，错误色 = 缺口，描边色 = 还没要求的更高等级。
/// 推荐页的缺口清单和填报页的技能条目共用它，保证两处口径一致。
class LevelGapBar extends StatelessWidget {
  const LevelGapBar({
    super.key,
    required this.currentLevel,
    required this.requiredLevel,
  });

  final int currentLevel;
  final int requiredLevel;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List<Widget>.generate(4, (index) {
        final level = index + 1;
        Color color;
        if (level <= currentLevel) {
          color = scheme.primary;
        } else if (level <= requiredLevel) {
          color = scheme.error;
        } else {
          color = scheme.outlineVariant;
        }
        return Padding(
          padding: const EdgeInsets.only(left: 2),
          child: Container(
            width: 14,
            height: 8,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        );
      }),
    );
  }
}
