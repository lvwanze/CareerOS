import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:frontend/models/career_tree.dart';
import 'package:frontend/models/occupation_option.dart';
import 'package:frontend/models/recommendation.dart';
import 'package:frontend/models/skill_option.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiService {
  static String get baseUrl {
    final configuredUrl = dotenv.env['BASE_URL']?.trim();
    if (configuredUrl == null || configuredUrl.isEmpty) {
      throw StateError('请在 .env 中配置 BASE_URL');
    }
    return configuredUrl.replaceFirst(RegExp(r'/+$'), '');
  }

  static Future<Map<String, dynamic>> _requestJson(
    Uri uri, {
    Map<String, dynamic>? body,
  }) async {
    final http.Response response;
    try {
      response = body == null
          ? await http.get(uri, headers: const <String, String>{
              'Accept': 'application/json',
            })
          : await http.post(uri, headers: const <String, String>{
              'Accept': 'application/json',
              'Content-Type': 'application/json',
            }, body: jsonEncode(body));
    } on Exception catch (error) {
      throw ApiException('连不上服务：$uri（$error）');
    }

    final dynamic decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw ApiException('响应不是 JSON 对象', statusCode: response.statusCode);
    }
    final code = decoded['code'];
    if (response.statusCode != 200 || code != 200) {
      final message = decoded['message'] is String
          ? decoded['message'] as String
          : '接口返回 code=$code, HTTP ${response.statusCode}';
      throw ApiException(message, statusCode: response.statusCode);
    }
    return decoded;
  }

  static Future<RecommendationResult> fetchRecommendations(
    Map<String, dynamic> profile,
  ) async {
    final decoded = await _requestJson(
      Uri.parse('$baseUrl/api/v1/recommendations'),
      body: <String, dynamic>{'profile': profile},
    );
    final rawData = decoded['data'];
    if (rawData is! Map<String, dynamic>) {
      throw ApiException('推荐数据格式错误');
    }
    return RecommendationResult.fromJson(rawData);
  }

  static Future<List<SkillOption>> fetchSkills() async {
    final decoded = await _requestJson(Uri.parse('$baseUrl/api/v1/skills'));
    final rawSkills = decoded['data'];
    if (rawSkills is! List) {
      throw ApiException('技能数据格式错误');
    }
    return rawSkills
        .whereType<Map<String, dynamic>>()
        .map(SkillOption.fromJson)
        .where((skill) => skill.usedInKb)
        .toList();
  }

  /// `GET /api/v1/tree/{occupation_id}`：该职业的三层发展树（api_spec §3.6）。
  ///
  /// 职业 ID 写错时后端返 404 + 统一信封，`_requestJson` 已把它转成
  /// [ApiException]（message 即「职业不存在：xxx」），不会退化成空树，
  /// 所以界面能区分「ID 错了」和「这个职业没要求」。
  static Future<CareerTree> fetchCareerTree(String occupationId) async {
    final decoded = await _requestJson(
      Uri.parse('$baseUrl/api/v1/tree/${Uri.encodeComponent(occupationId)}'),
    );
    final rawData = decoded['data'];
    if (rawData is! Map<String, dynamic>) {
      throw ApiException('发展树数据格式错误');
    }
    return CareerTree.fromJson(rawData);
  }

  static Future<List<OccupationOption>> fetchOccupations() async {    final decoded = await _requestJson(Uri.parse('$baseUrl/api/v1/occupations'));
    final rawData = decoded['data'];
    if (rawData is! Map<String, dynamic> || rawData['items'] is! List) {
      throw ApiException('职业数据格式错误');
    }
    return (rawData['items'] as List<dynamic>)
        .whereType<Map<String, dynamic>>()
        .map(OccupationOption.fromJson)
        .toList();
  }
}
