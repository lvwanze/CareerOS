import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'career_profile.dart';
import 'questionnaire_page.dart';
import 'recommendation_page.dart';
import 'skill_tree_page.dart';

Future<void> main() async {
	WidgetsFlutterBinding.ensureInitialized();
	await dotenv.load(fileName: '.env');
	runApp(const MyApp());
}

class MyApp extends StatelessWidget {
	const MyApp({super.key});

	@override
	Widget build(BuildContext context) {
		return MaterialApp(
			title: 'CareerOS',
			debugShowCheckedModeBanner: false,
			theme: ThemeData(
				useMaterial3: true,
				colorScheme: ColorScheme.fromSeed(
					seedColor: const Color(0xFF167D78),
					surface: const Color(0xFFF7F7F2),
				),
				scaffoldBackgroundColor: const Color(0xFFF7F7F2),
				appBarTheme: const AppBarTheme(
					backgroundColor: Color(0xFFF7F7F2),
					surfaceTintColor: Colors.transparent,
				),
				inputDecorationTheme: InputDecorationTheme(
					filled: true,
					fillColor: Colors.white,
					border: OutlineInputBorder(
						borderRadius: BorderRadius.circular(10),
						borderSide: const BorderSide(color: Color(0xFFD9DFDA)),
					),
					enabledBorder: OutlineInputBorder(
						borderRadius: BorderRadius.circular(10),
						borderSide: const BorderSide(color: Color(0xFFD9DFDA)),
					),
				),
				cardTheme: CardTheme(
					color: Colors.white,
					elevation: 0,
					shape: RoundedRectangleBorder(
						borderRadius: BorderRadius.circular(8),
						side: const BorderSide(color: Color(0xFFE2E6E1)),
					),
				),
			),
			home: const QuestionnairePage(),
			onGenerateRoute: (settings) {
				final profile = settings.arguments is CareerProfile
						? settings.arguments! as CareerProfile
						: const CareerProfile(
								name: '访客',
								targetRole: '',
								experience: '刚刚起步',
								skills: <ProfileSkill>[],
								weeklyHours: 6,
							);
				return switch (settings.name) {
					'/questionnaire' => MaterialPageRoute<void>(
							builder: (_) => const QuestionnairePage(),
							settings: settings,
						),
					'/recommendation' => MaterialPageRoute<void>(
							builder: (_) => RecommendationPage(profile: profile),
							settings: settings,
						),
					'/skill-tree' => MaterialPageRoute<void>(
							builder: (_) => SkillTreePage(profile: profile),
							settings: settings,
						),
					_ => null,
				};
			},
		);
	}
}
