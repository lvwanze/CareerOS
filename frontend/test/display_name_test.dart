import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/display_name.dart';

void main() {
  group('preferredName 中文优先', () {
    test('中英文都有时取中文', () {
      expect(preferredName('数据分析', 'Data Analysis'), '数据分析');
    });

    test('中文名为空字符串时回退英文', () {
      expect(preferredName('', 'Python'), 'Python');
    });

    test('中文名为纯空格时回退英文', () {
      expect(preferredName('   ', 'Python'), 'Python');
    });

    test('中文名为 null 时回退英文', () {
      expect(preferredName(null, 'SQL'), 'SQL');
    });

    test('中英文都缺失时回退到 ID', () {
      expect(preferredName(null, null, fallback: 'SK001'), 'SK001');
    });

    test('不去掉英文名内部的空格', () {
      expect(preferredName(null, ' Machine Learning '), 'Machine Learning');
    });
  });

  group('secondaryName 副标题去重', () {
    test('中英文不同时返回英文', () {
      expect(secondaryName('数据分析', 'Data Analysis'), 'Data Analysis');
    });

    test('中英文相同时返回空，避免界面上重复', () {
      expect(secondaryName('Python', 'Python'), '');
    });

    test('任一为空时返回空', () {
      expect(secondaryName('', 'Python'), '');
      expect(secondaryName('数据分析', null), '');
    });
  });

  group('formatMatchScore 百分比', () {
    test('0.5 显示 50%', () {
      expect(formatMatchScore(0.5), '50%');
    });

    test('1.0 显示 100%', () {
      expect(formatMatchScore(1.0), '100%');
    });

    test('越界值被夹住，不会出现 130% 或负值', () {
      expect(formatMatchScore(1.3), '100%');
      expect(formatMatchScore(-0.2), '0%');
    });
  });

  group('skillStatusLabel 状态翻译', () {
    test('已知状态翻成中文', () {
      expect(skillStatusLabel('mastered'), '已掌握');
      expect(skillStatusLabel('needs_improvement'), '待提升');
      expect(skillStatusLabel('needs_verification'), '待验证');
    });

    test('未知状态原样返回，不静默吞掉', () {
      expect(skillStatusLabel('something_new'), 'something_new');
    });
  });
}
