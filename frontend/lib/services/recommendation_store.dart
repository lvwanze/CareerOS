import 'package:frontend/models/recommendation.dart';

/// 推荐结果的进程内缓存。
///
/// 发展树节点来自推荐响应的 `development_paths`，而发展树页与推荐页是两个路由，
/// 用这份缓存避免为了拿节点再发一次完全相同的推荐请求。
class RecommendationStore {
  RecommendationStore._();

  static final RecommendationStore instance = RecommendationStore._();

  RecommendationResult? _result;

  void cache(RecommendationResult result) => _result = result;

  void clear() => _result = null;

  String get modelVersion => _result?.modelVersion ?? '';

  DevelopmentPathResult? pathFor(String? occupationId) {
    final paths = _result?.developmentPaths;
    if (paths == null || occupationId == null) return null;
    for (final path in paths) {
      if (path.occupationId == occupationId) return path;
    }
    return null;
  }
}
