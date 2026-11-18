import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:frontend/models/development_path.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:8000';

  static Future<List<TreeNode>> fetchCareerTree(String occupationId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/v1/tree/$occupationId'),
      headers: {'Accept': 'application/json'},
    );

    if (response.statusCode != 200) {
      throw Exception('请求失败: ${response.statusCode}');
    }

    final dynamic decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception('响应格式错误');
    }

    final Map<String, dynamic> body = decoded;
    if (body['code'] != 200) {
      throw Exception('业务失败: ${body['message']}');
    }

    final dynamic rawData = body['data'];
    if (rawData is! Map<String, dynamic>) {
      throw Exception('响应数据为空');
    }

    final dynamic rawNodes = rawData['nodes'];
    if (rawNodes is! List) {
      throw Exception('节点数据格式错误');
    }

    return rawNodes.map<TreeNode>((dynamic jsonNode) {
      if (jsonNode is! Map<String, dynamic>) {
        throw Exception('节点数据格式错误');
      }
      return TreeNode.fromJson(jsonNode);
    }).toList();
  }
}