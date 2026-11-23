import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// 本地持久化。只存三样东西：
/// 1. 用户填过的画像（profile），下次进来不用重填；
/// 2. 每个职业的发展树里，哪些节点已经勾成「已掌握」；
/// 3. 最近一次查看的职业 ID，方便从发展树页直接恢复。
///
/// key 里都带 _v1 版本号：将来结构变了，改成 _v2 就能让旧数据自然失效，
/// 不会因为读到旧格式而白屏。
class StorageService {
  static const String _profileKey = 'careeros_profile_v1';
  static const String _progressPrefix = 'careeros_progress_v1_';
  static const String _lastOccupationKey = 'careeros_last_occupation_v1';

  static Future<void> saveProfile(Map<String, dynamic> profile) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_profileKey, jsonEncode(profile));
  }

  static Future<Map<String, dynamic>?> loadProfile() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_profileKey);
    if (raw == null || raw.isEmpty) {
      return null;
    }
    try {
      final dynamic decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      return null;
    } catch (_) {
      // 本地数据损坏就当作没存过，不要让整个应用起不来。
      return null;
    }
  }

  static Future<void> clearProfile() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_profileKey);
  }

  /// 进度按职业分开存：不同职业的技能节点本来就不是一套。
  static Future<Set<String>> loadProgress(String occupationId) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getStringList('$_progressPrefix$occupationId');
    if (raw == null) {
      return <String>{};
    }
    return raw.toSet();
  }

  static Future<void> saveProgress(
    String occupationId,
    Set<String> masteredNodeIds,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final sorted = masteredNodeIds.toList()..sort();
    await prefs.setStringList('$_progressPrefix$occupationId', sorted);
  }

  static Future<void> saveLastOccupation(String occupationId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastOccupationKey, occupationId);
  }

  static Future<String?> loadLastOccupation() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_lastOccupationKey);
    if (raw == null || raw.isEmpty) {
      return null;
    }
    return raw;
  }
}
