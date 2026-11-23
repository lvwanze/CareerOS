/// 中文名称优先渲染的统一入口。
///
/// 规则：有中文名就用中文名；中文名为空（null / 空字符串 / 纯空格）
/// 时回退英文名；英文名也没有，再回退调用方给的兜底值（一般是 ID）。
/// 全站展示名称都必须走这里，不要在页面里自己写 a ?? b，
/// 否则某个接口少一个 name_zh 就会在界面上留下空白。
String preferredName(String? nameZh, String? name, {String fallback = '未命名'}) {
  final zh = nameZh?.trim();
  if (zh != null && zh.isNotEmpty) {
    return zh;
  }
  final en = name?.trim();
  if (en != null && en.isNotEmpty) {
    return en;
  }
  return fallback;
}

/// 副标题用的英文原名。
/// 只有「中文名和英文名都存在、且两者不相等」时才返回英文名，
/// 避免界面上出现「Python / Python」这种重复。
String secondaryName(String? nameZh, String? name) {
  final zh = nameZh?.trim() ?? '';
  final en = name?.trim() ?? '';
  if (zh.isEmpty || en.isEmpty) {
    return '';
  }
  if (zh == en) {
    return '';
  }
  return en;
}

/// 匹配度转百分比文本，限制在 0% ~ 100%，防止后端越界把界面撑坏。
String formatMatchScore(double score) {
  var value = score;
  if (value.isNaN) {
    value = 0;
  }
  if (value < 0) {
    value = 0;
  }
  if (value > 1) {
    value = 1;
  }
  return '${(value * 100).round()}%';
}

/// 技能状态的中文标签，后端返回的英文枚举统一在这里翻译。
String skillStatusLabel(String status) {
  switch (status) {
    case 'mastered':
      return '已掌握';
    case 'needs_improvement':
      return '待提升';
    case 'needs_verification':
      return '待验证';
    case 'not_started':
      return '未开始';
    case 'in_progress':
      return '进行中';
    default:
      return status;
  }
}
