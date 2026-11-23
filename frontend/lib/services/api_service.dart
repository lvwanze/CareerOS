import 'dart:async';
import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:frontend/models/development_path.dart';
import 'package:frontend/models/recommendation.dart';
import 'package:frontend/models/skill_option.dart';
import 'package:http/http.dart' as http;

/// 带 request_id 的结果包装。
/// 统一响应信封里的 request_id 要一路带到界面上：
/// 联调时出问题，直接在报错提示里把它念给后端负责人听，比截图有效得多。
class ApiResult<T> {
  const ApiResult({required this.data, required this.requestId});

  final T data;
  final String requestId;
}

/// 接口异常。request_id 可能为空（FastAPI 默认的 422 校验错误不带信封）。
class ApiException implements Exception {
  const ApiException(this.message, {this.requestId, this.statusCode});

  final String message;
  final String? requestId;
  final int? statusCode;

  @override
  String toString() {
    if (requestId == null || requestId!.isEmpty) {
      return message;
    }
    return '$message（request_id: $requestId）';
  }
}

class ApiService {
  static const Duration _timeout = Duration(seconds: 10);

  static String get baseUrl {
    final configuredUrl = dotenv.env['BASE_URL']?.trim();
    if (configuredUrl == null || configuredUrl.isEmpty) {
      throw const ApiException('请在 .env 中配置 BASE_URL');
    }
    // 去掉结尾多余的斜杠，避免拼出 //api/v1 这种路径。
    return configuredUrl.replaceFirst(RegExp(r'/+$'), '');
  }

  /// 技能字典：GET /api/v1/skills
  /// 返回里带中文名 name_zh，填报页的选项就靠它。
  static Future<ApiResult<List<SkillOption>>> fetchSkills() async {
    final response = await _send(
      http.get(
        Uri.parse('$baseUrl/api/v1/skills'),
        headers: {'Accept': 'application/json'},
      ),
    );

    final body = _decodeEnvelope(response);
    final dynamic rawSkills = body['data'];
    if (rawSkills is! List) {
      throw ApiException('技能数据格式错误：data 不是数组', requestId: _requestIdOf(body));
    }

    final skills = <SkillOption>[];
    for (final dynamic item in rawSkills) {
      if (item is! Map<String, dynamic>) {
        continue;
      }
      skills.add(SkillOption.fromJson(item));
    }
    // 只保留知识库里真正用到的技能，和 used_in_kb 字段保持一致。
    final usedSkills = skills.where((skill) => skill.usedInKb).toList();
    return ApiResult(
      data: usedSkills.isEmpty ? skills : usedSkills,
      requestId: _requestIdOf(body),
    );
  }

  /// 职业推荐：POST /api/v1/recommendations
  /// 注意请求体是 {"profile": {...}}，不是扁平的 user_skills / target_occupation。
  static Future<ApiResult<RecommendationResult>> fetchRecommendations(
    Map<String, dynamic> profile,
  ) async {
    final response = await _send(
      http.post(
        Uri.parse('$baseUrl/api/v1/recommendations'),
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'profile': profile}),
      ),
    );

    final body = _decodeEnvelope(response);
    final dynamic rawData = body['data'];
    if (rawData is! Map<String, dynamic>) {
      throw ApiException('推荐数据格式错误：data 不是对象', requestId: _requestIdOf(body));
    }
    return ApiResult(
      data: RecommendationResult.fromJson(rawData),
      requestId: _requestIdOf(body),
    );
  }

  /// 发展树：GET /v1/tree/{occupation_id}
  /// 这个接口不带 /api 前缀，和另外两个接口不一致，已写进接口问题清单。
  static Future<ApiResult<List<TreeNode>>> fetchCareerTree(
    String occupationId,
  ) async {
    if (occupationId.trim().isEmpty) {
      throw const ApiException('缺少 occupation_id');
    }
    final response = await _send(
      http.get(
        Uri.parse('$baseUrl/v1/tree/${Uri.encodeComponent(occupationId)}'),
        headers: {'Accept': 'application/json'},
      ),
    );

    final body = _decodeEnvelope(response);
    final dynamic rawData = body['data'];
    if (rawData is! Map<String, dynamic>) {
      throw ApiException('发展树数据格式错误：data 不是对象', requestId: _requestIdOf(body));
    }
    final dynamic rawNodes = rawData['nodes'];
    if (rawNodes is! List) {
      throw ApiException('发展树数据格式错误：nodes 不是数组', requestId: _requestIdOf(body));
    }

    final nodes = <TreeNode>[];
    for (final dynamic item in rawNodes) {
      if (item is! Map<String, dynamic>) {
        continue;
      }
      nodes.add(TreeNode.fromJson(item));
    }
    return ApiResult(data: nodes, requestId: _requestIdOf(body));
  }

  /// 统一加超时，并把网络层异常翻译成人话。
  static Future<http.Response> _send(Future<http.Response> request) async {
    try {
      return await request.timeout(_timeout);
    } on TimeoutException {
      throw const ApiException('请求超时：后端没起来，或 BASE_URL 指向不对');
    } on http.ClientException catch (error) {
      throw ApiException('网络错误：${error.message}');
    }
  }

  /// 拆统一信封 {code, message, data, request_id}。
  /// 每一步都先判类型再取值，防止后端少一个字段就抛 TypeError 白屏。
  static Map<String, dynamic> _decodeEnvelope(http.Response response) {
    Map<String, dynamic>? body;
    try {
      final dynamic decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        body = decoded;
      }
    } catch (_) {
      body = null;
    }

    if (body == null) {
      throw ApiException(
        '响应不是合法 JSON（HTTP ${response.statusCode}）',
        statusCode: response.statusCode,
      );
    }

    final requestId = _requestIdOf(body);

    if (response.statusCode != 200) {
      final message = body['message']?.toString() ?? 'HTTP ${response.statusCode}';
      throw ApiException(message, requestId: requestId, statusCode: response.statusCode);
    }

    if (body['code'] != 200) {
      throw ApiException(
        body['message']?.toString() ?? '业务处理失败',
        requestId: requestId,
        statusCode: response.statusCode,
      );
    }

    return body;
  }

  static String _requestIdOf(Map<String, dynamic> body) {
    final dynamic value = body['request_id'];
    if (value == null) {
      return '';
    }
    return value.toString();
  }
}
