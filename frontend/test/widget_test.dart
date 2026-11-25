import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/main.dart';
import 'package:frontend/questionnaire_page.dart';

void main() {
  testWidgets('应用启动后先加载职业与技能知识库', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await tester.pumpWidget(const MyApp());

    expect(find.text('CareerOS'), findsWidgets);
    expect(find.byType(QuestionnairePage), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
