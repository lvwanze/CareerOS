import 'package:flutter/material.dart';

import 'career_profile.dart';

class CareerNavigationBar extends StatelessWidget {
  const CareerNavigationBar({
    required this.currentIndex,
    required this.profile,
    super.key,
  });

  final int currentIndex;
  final CareerProfile profile;

  @override
  Widget build(BuildContext context) {
    return NavigationBar(
      selectedIndex: currentIndex,
      onDestinationSelected: (index) {
        if (index == currentIndex) return;
        final route = switch (index) {
          0 => '/questionnaire',
          1 => '/recommendation',
          _ => '/skill-tree',
        };
        Navigator.pushReplacementNamed(context, route, arguments: profile);
      },
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.assignment_outlined),
          selectedIcon: Icon(Icons.assignment_rounded),
          label: '填报',
        ),
        NavigationDestination(
          icon: Icon(Icons.explore_outlined),
          selectedIcon: Icon(Icons.explore_rounded),
          label: '推荐',
        ),
        NavigationDestination(
          icon: Icon(Icons.account_tree_outlined),
          selectedIcon: Icon(Icons.account_tree_rounded),
          label: '发展树',
        ),
      ],
    );
  }
}