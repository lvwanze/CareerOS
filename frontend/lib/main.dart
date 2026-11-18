import 'package:flutter/material.dart';

void main() {
  runApp(const CareerOsApp());
}

class CareerOsApp extends StatelessWidget {
  const CareerOsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CareerOS',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: Scaffold(
        appBar: AppBar(title: const Text('CareerOS')),
        body: const Center(child: Text('职业发展路径推荐')),
      ),
    );
  }
}