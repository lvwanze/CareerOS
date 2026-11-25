// 临时联调脚本（不进入默认测试集）：对着真实后端跑一遍 问卷→推荐→发展树。
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/career_profile.dart';
import 'package:frontend/main.dart';
import 'package:frontend/models/evidence_level.dart';
import 'package:frontend/recommendation_page.dart';
import 'package:frontend/services/api_service.dart';
import 'package:frontend/services/profile_storage.dart';
import 'package:frontend/services/recommendation_store.dart';
import 'package:frontend/skill_tree_page.dart';

const String _baseUrl = 'http://127.0.0.1:8000';

void _useTallScreen(WidgetTester tester) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1280, 2600);
  addTearDown(tester.view.reset);
}

void main() {
  setUp(() {
    HttpOverrides.global = null;
    dotenv.testLoad(fileInput: 'BASE_URL=$_baseUrl');
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('问卷页：真实职业与技能知识库渲染', (tester) async {
    _useTallScreen(tester);
    await tester.runAsync(() async {
      await tester.pumpWidget(const MyApp());
      await _settle(tester, find.text('先认识一下你'));

      expect(find.text('先认识一下你'), findsOneWidget);
      final helper = tester.widgetList<Text>(find.byType(Text))
          .map((t) => t.data ?? '')
          .where((s) => s.contains('个职业来自后端知识库'));
      print('KB >>> ${helper.join()}');
      expect(helper.join(), contains('个职业来自后端知识库'));
    });
  });

  testWidgets('推荐页与发展树：真实响应字段可视化', (tester) async {
    _useTallScreen(tester);
    await tester.runAsync(() async {
      final skills = await ApiService.fetchSkills();
      expect(skills.length, greaterThanOrEqualTo(3));
      final profile = CareerProfile(
        name: '吕宛泽',
        targetRole: '数据分析',
        experience: '有项目经验',
        weeklyHours: 8,
        occupationId: null,
        skills: <ProfileSkill>[
          ProfileSkill(
              skillId: skills[0].skillId,
              name: skills[0].displayName,
              selfLevel: 4,
              evidenceLevel: 'project'),
          ProfileSkill(
              skillId: skills[1].skillId,
              name: skills[1].displayName,
              selfLevel: 3,
              evidenceLevel: 'none'),
          ProfileSkill(
              skillId: skills[2].skillId,
              name: skills[2].displayName,
              selfLevel: 1,
              evidenceLevel: 'self'),
        ],
      );

      final result = await ApiService.fetchRecommendations(profile.toJson());
      expect(result.recommendations, isNotEmpty);
      final first = result.recommendations.first;
      print('REC >>> ${first.occupationNameZh} score=${first.matchScore} '
          'reasons=${first.recommendationReasons.length} gaps=${first.skillGaps.length} '
          'paths=${result.developmentPaths.length}');
      expect(first.recommendationReasons, isNotEmpty);
      expect(first.skillsToImprove, isNotEmpty);
      final statuses = first.skillGaps.map((g) => g.status).toSet();
      print('STATUS >>> $statuses');

      RecommendationStore.instance.cache(result);
      final treeProfile = CareerProfile(
        name: profile.name,
        targetRole: first.occupationNameZh,
        experience: profile.experience,
        skills: profile.skills,
        weeklyHours: profile.weeklyHours,
        occupationId: first.occupationId,
      );

      await tester.pumpWidget(MaterialApp(
        home: RecommendationPage(profile: treeProfile),
        onGenerateRoute: (settings) => MaterialPageRoute<void>(
          builder: (_) => settings.name == '/skill-tree'
              ? SkillTreePage(profile: treeProfile)
              : RecommendationPage(profile: treeProfile),
        ),
      ));
      await _settle(tester, find.text('匹配依据'));
      expect(find.text('匹配依据'), findsWidgets);
      expect(find.textContaining('% 匹配'), findsWidgets);
      expect(find.text('优先补的能力差距'), findsWidgets);
      expect(find.textContaining('已掌握 '), findsWidgets);

      await tester.tap(find.text('查看发展路径').first);
      await tester.pump();
      await _settle(tester, find.textContaining('成长路线'));
      expect(find.textContaining('成长路线'), findsOneWidget);
      expect(find.textContaining('后端状态：'), findsWidgets);
      expect(find.textContaining('SK00'), findsNothing);
      print('TREE >>> ${tester.widgetList<Text>(find.byType(Text)).map((t) => t.data ?? '').where((s) => s.contains('个节点')).join()}');
    });
  });

  test('进度持久化：画像/收藏/节点写读一致', () async {
    HttpOverrides.global = null;
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final storage = await ProfileStorage.open();
    expect(storage.loadProfile(), isNull);
    expect(storage.hasCompletedNodes('occ_x'), isFalse);

    final profile = CareerProfile(
      name: '吕宛泽',
      targetRole: '算法工程师',
      experience: '有项目经验',
      weeklyHours: 9,
      occupationId: 'occ_a',
      skills: const [
        ProfileSkill(
            skillId: 'sk_1', name: 'Python', selfLevel: 3, evidenceLevel: 'project'),
      ],
    );
    await storage.saveProfile(profile);
    final restored = storage.loadProfile()!;
    expect(restored.name, '吕宛泽');
    expect(restored.weeklyHours, 9);
    expect(restored.occupationId, 'occ_a');
    expect(restored.skills.single.selfLevel, 3);
    expect(restored.skills.single.evidenceLevel, 'project');

    await storage.saveOccupation('occ_b', saved: true);
    expect(storage.loadSavedOccupations(), contains('occ_b'));

    await storage.saveCompletedNode('occ_a', 'node_1', completed: true);
    expect(storage.hasCompletedNodes('occ_a'), isTrue);
    expect(storage.loadCompletedNodes('occ_a'), contains('node_1'));
    expect(EvidenceLevel.defaultLevel, 'self');
  });

  testWidgets('异常态：BASE_URL 缺失与后端不可达', (tester) async {
    _useTallScreen(tester);
    HttpOverrides.global = null;
    dotenv.testLoad(fileInput: 'OTHER=1');
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await tester.runAsync(() async {
      await tester.pumpWidget(const MyApp());
      await _settle(tester, find.textContaining('无法读取职业与技能知识库'));
      expect(find.text('无法读取职业与技能知识库：请在 .env 中配置 BASE_URL'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    dotenv.testLoad(fileInput: 'BASE_URL=http://127.0.0.1:9');
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.runAsync(() async {
      await tester.pumpWidget(const MyApp());
      await _settle(tester, find.textContaining('连不上服务'));
      final unreachable = tester
          .widgetList<Text>(find.byType(Text))
          .map((t) => t.data ?? '')
          .firstWhere((s) => s.startsWith('无法读取职业与技能知识库'));
      expect(unreachable, startsWith('无法读取职业与技能知识库：连不上服务：'));
      expect(find.text('重试'), findsOneWidget);
    });
  });

  testWidgets('重进填报页：已存画像自动回填', (tester) async {
    _useTallScreen(tester);
    await tester.runAsync(() async {
      final skills = await ApiService.fetchSkills();
      final occupations = await ApiService.fetchOccupations();
      final storage = await ProfileStorage.open();
      await storage.saveProfile(CareerProfile(
        name: '吕宛泽',
        targetRole: '数据分析',
        experience: '有项目经验',
        weeklyHours: 11,
        occupationId: occupations.first.occupationId,
        skills: <ProfileSkill>[
          ProfileSkill(
            skillId: skills.first.skillId,
            name: skills.first.displayName,
            selfLevel: 3,
            evidenceLevel: 'course',
          ),
        ],
      ));

      await tester.pumpWidget(const MyApp());
      await _settle(tester, find.text('先认识一下你'));
      expect(find.text('先认识一下你'), findsOneWidget);
      final filled = tester
          .widgetList<TextFormField>(find.byType(TextFormField))
          .map((f) => f.controller?.text ?? f.initialValue ?? '')
          .toList();
      print('RESTORE >>> $filled');
      expect(filled, contains('吕宛泽'));
      expect(find.text('已选 1 项'), findsOneWidget);
      expect(find.textContaining('11 小时 / 周'), findsOneWidget);
      expect(find.textContaining('证据：课程或培训'), findsOneWidget);
      expect(find.textContaining('做过完整项目'), findsOneWidget);
      expect(find.textContaining('有项目经验'), findsWidgets);
    });
  });
}

Future<void> _settle(WidgetTester tester, Finder finder,
    {int maxPumps = 40}) async {
  for (var i = 0; i < maxPumps; i++) {
    if (finder.evaluate().isNotEmpty) return;
    await Future<void>.delayed(const Duration(milliseconds: 150));
    await tester.pump(const Duration(milliseconds: 150));
  }
  final texts = tester
      .widgetList<Text>(find.byType(Text))
      .map((t) => t.data ?? '')
      .where((s) => s.isNotEmpty)
      .take(12)
      .join(' | ');
  final errors = tester.takeException();
  print('SETTLE-FAIL >>> $texts');
  print('EXCEPTION >>> $errors');
}
