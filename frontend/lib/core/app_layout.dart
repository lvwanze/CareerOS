import 'package:flutter/widgets.dart';

/// 三档断点，和 Material 3 的窗口尺寸分级对齐：
/// compact  < 600   手机 / 窄窗口
/// medium   600~1024 平板 / 分屏
/// expanded > 1024  桌面（用户跑 flutter run -d windows 就是这个档）
enum ScreenSize { compact, medium, expanded }

ScreenSize screenSizeOf(BuildContext context) {
  final width = MediaQuery.of(context).size.width;
  if (width < 600) {
    return ScreenSize.compact;
  }
  if (width < 1024) {
    return ScreenSize.medium;
  }
  return ScreenSize.expanded;
}

/// 卡片栅格列数：手机 1 列、平板 2 列、桌面 3 列。
int gridColumnsOf(BuildContext context) {
  switch (screenSizeOf(context)) {
    case ScreenSize.compact:
      return 1;
    case ScreenSize.medium:
      return 2;
    case ScreenSize.expanded:
      return 3;
  }
}

/// 页面内容最大宽度。桌面窗口拉到 2560 也不要把一行文字拉成一米长。
double contentMaxWidthOf(BuildContext context) {
  switch (screenSizeOf(context)) {
    case ScreenSize.compact:
      return double.infinity;
    case ScreenSize.medium:
      return 720;
    case ScreenSize.expanded:
      return 1080;
  }
}

/// 统一的外边距，避免每个页面各写一套数字。
EdgeInsets pagePaddingOf(BuildContext context) {
  switch (screenSizeOf(context)) {
    case ScreenSize.compact:
      return const EdgeInsets.symmetric(horizontal: 12, vertical: 12);
    case ScreenSize.medium:
      return const EdgeInsets.symmetric(horizontal: 20, vertical: 16);
    case ScreenSize.expanded:
      return const EdgeInsets.symmetric(horizontal: 32, vertical: 20);
  }
}

/// 是否用侧边导航（宽屏）还是底部导航（窄屏）。
bool useSideNavigation(BuildContext context) {
  return screenSizeOf(context) != ScreenSize.compact;
}

/// 页面内容居中 + 限宽的统一包裹层。
class ContentWidth extends StatelessWidget {
  const ContentWidth({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final maxWidth = contentMaxWidthOf(context);
    if (maxWidth == double.infinity) {
      return child;
    }
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: child,
      ),
    );
  }
}
