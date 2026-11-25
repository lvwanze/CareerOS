import 'dart:convert';

import 'package:frontend/career_profile.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 画像、收藏与发展树完成进度的本地持久化。
class ProfileStorage {
  ProfileStorage._(this._prefs);

  static const String _profileKey = 'careeros.profile';
  static const String _savedKey = 'careeros.saved_occupations';
  static const String _completedKey = 'careeros.completed_nodes';

  final SharedPreferences _prefs;

  static Future<ProfileStorage> open() async =>
      ProfileStorage._(await SharedPreferences.getInstance());

  CareerProfile? loadProfile() {
    final raw = _prefs.getString(_profileKey);
    if (raw == null || raw.isEmpty) return null;
    final decoded = jsonDecode(raw);
    if (decoded is! Map<String, dynamic>) return null;
    return CareerProfile.fromJson(decoded);
  }

  Future<void> saveProfile(CareerProfile profile) =>
      _prefs.setString(_profileKey, jsonEncode(_profileToJson(profile)));

  Future<void> clearProfile() => _prefs.remove(_profileKey);

  List<String> loadSavedOccupations() =>
      _prefs.getStringList(_savedKey) ?? <String>[];

  Future<void> saveOccupation(String occupationId, {required bool saved}) {
    final ids = loadSavedOccupations().toList();
    if (saved) {
      if (!ids.contains(occupationId)) ids.add(occupationId);
    } else {
      ids.remove(occupationId);
    }
    return _prefs.setStringList(_savedKey, ids);
  }

  /// 该职业是否已经有过进度记录。用于区分「没存过」和「全部取消勾选」。
  bool hasCompletedNodes(String occupationId) {
    final raw = _prefs.getString(_completedKey);
    if (raw == null || raw.isEmpty) return false;
    final decoded = jsonDecode(raw);
    return decoded is Map<String, dynamic> && decoded.containsKey(occupationId);
  }

  Set<String> loadCompletedNodes(String occupationId) {
    final raw = _prefs.getString(_completedKey);
    if (raw == null || raw.isEmpty) return <String>{};
    final decoded = jsonDecode(raw);
    if (decoded is! Map<String, dynamic>) return <String>{};
    final nodes = decoded[occupationId];
    if (nodes is! List) return <String>{};
    return nodes.whereType<String>().toSet();
  }

  Future<void> saveCompletedNode(
    String occupationId,
    String nodeId, {
    required bool completed,
  }) {
    final raw = _prefs.getString(_completedKey);
    final Map<String, dynamic> all = raw == null || raw.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(raw) as Map<String, dynamic>;
    final nodes = (all[occupationId] as List<dynamic>? ?? <dynamic>[])
        .whereType<String>()
        .toSet();
    if (completed) {
      nodes.add(nodeId);
    } else {
      nodes.remove(nodeId);
    }
    all[occupationId] = nodes.toList();
    return _prefs.setString(_completedKey, jsonEncode(all));
  }

  static Map<String, dynamic> _profileToJson(CareerProfile profile) =>
      <String, dynamic>{
        'name': profile.name,
        'target_role': profile.targetRole,
        'experience': profile.experience,
        'weekly_hours': profile.weeklyHours,
        'occupation_id': profile.occupationId,
        'skills': profile.skills.map((skill) => <String, dynamic>{
              'skill_id': skill.skillId,
              'name': skill.name,
              'self_level': skill.selfLevel,
              'evidence_level': skill.evidenceLevel,
            }).toList(),
      };
}
