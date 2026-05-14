import 'dart:convert';
import 'package:http/http.dart' as http;

class Api {
  // Set to your backend address
  static const base = 'http://127.0.0.1:5000/api'; // use 10.0.2.2 for Android emulator

  static Future<dynamic> get(String path) async {
    try {
      final res = await http.get(Uri.parse(base + path));
      if (res.statusCode == 200) return json.decode(res.body);
      return null;
    } catch (e) {
      print('API GET error: $e');
      return null;
    }
  }

  static Future<dynamic> post(String path, Map body) async {
    try {
      final res = await http.post(
        Uri.parse(base + path),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      );
      
      if (res.statusCode == 200 || res.statusCode == 201) {
        return json.decode(res.body);
      } else if (res.statusCode == 500 || res.statusCode == 400) {
        // Try to parse error response
        try {
          return json.decode(res.body);
        } catch (e) {
          return {'status': 'error', 'message': 'Server error'};
        }
      }
      return null;
    } catch (e) {
      print('API POST error: $e');
      return {'status': 'error', 'message': e.toString()};
    }
  }
}
