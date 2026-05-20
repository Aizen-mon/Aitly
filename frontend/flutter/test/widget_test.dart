// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ai_tally_app/main.dart';

void main() {
  testWidgets('renders the dashboard shell', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();

    expect(find.text('Business Dashboard'), findsWidgets);
    expect(find.text('Dashboard'), findsWidgets);
    expect(find.text('Assistant'), findsWidgets);
    expect(find.text('Inventory'), findsWidgets);
  });
}
