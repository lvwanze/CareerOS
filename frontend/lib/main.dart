// Flutter 3.47 起 material.dart 迁到 material_ui 包，全组 SDK 版本统一前不迁：
// material_ui 不在 SDK 内，换包名会让旧版本队友编不过。
// ignore: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:frontend/core/app_layout.dart';
import 'package:frontend/pages/profile_page.dart';
import 'package:frontend/pages/recommend_page.dart';
import 'package:frontend/pages/tree_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  runApp(const CareerOsApp());
}

class CareerOsApp extends StatelessWidget {
  const CareerOsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CareerOS',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const HomeShell(),
    );
  }
}

/// 三个页面的外壳。
/// 宽屏用侧边导航，窄屏用底部导航，页面状态用 IndexedStack 保住，
/// 切回来时不会重新请求接口。
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  // 令牌：外层一改，对应页面就重新拉数据。
  int _recommendToken = 0;
  int _treeToken = 0;
  String? _occupationId;

  void _onProfileSubmitted() {
    setState(() {
      _recommendToken++;
      _index = 1;
    });
  }

  void _onOpenTree(String occupationId) {
    setState(() {
      _occupationId = occupationId;
      _treeToken++;
      _index = 2;
    });
  }

  void _onGoProfile() {
    setState(() => _index = 0);
  }

  void _onGoRecommend() {
    setState(() => _index = 1);
  }

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      ProfilePage(onSubmitted: _onProfileSubmitted),
      RecommendPage(
        reloadToken: _recommendToken,
        onOpenTree: _onOpenTree,
        onGoProfile: _onGoProfile,
      ),
      TreePage(
        reloadToken: _treeToken,
        occupationId: _occupationId,
        onGoRecommend: _onGoRecommend,
      ),
    ];

    final content = IndexedStack(index: _index, children: pages);

    if (useSideNavigation(context)) {
      return Scaffold(
        body: Row(
          children: [
            NavigationRail(
              selectedIndex: _index,
              onDestinationSelected: (value) => setState(() => _index = value),
              labelType: NavigationRailLabelType.all,
              leading: const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Icon(Icons.school_outlined),
              ),
              destinations: const [
                NavigationRailDestination(
                  icon: Icon(Icons.edit_note_outlined),
                  selectedIcon: Icon(Icons.edit_note),
                  label: Text('填报'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.insights_outlined),
                  selectedIcon: Icon(Icons.insights),
                  label: Text('推荐'),
                ),
                NavigationRailDestination(
                  icon: Icon(Icons.account_tree_outlined),
                  selectedIcon: Icon(Icons.account_tree),
                  label: Text('发展树'),
                ),
              ],
            ),
            const VerticalDivider(width: 1),
            Expanded(child: content),
          ],
        ),
      );
    }

    return Scaffold(
      body: content,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.edit_note_outlined),
            selectedIcon: Icon(Icons.edit_note),
            label: '填报',
          ),
          NavigationDestination(
            icon: Icon(Icons.insights_outlined),
            selectedIcon: Icon(Icons.insights),
            label: '推荐',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_tree_outlined),
            selectedIcon: Icon(Icons.account_tree),
            label: '发展树',
          ),
        ],
      ),
    );
  }
}
