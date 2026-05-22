import 'dart:convert';
import 'package:http/http.dart' as http;

class Api {
  static const base = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:5000/api',
  );

  static Future<dynamic> get(String path) async {
    const int maxRetries = 3;
    int attempt = 0;
    while (attempt < maxRetries) {
      try {
        final res = await http.get(Uri.parse(base + path));
        if (res.statusCode == 200) return json.decode(res.body);
        // Try to parse error body if available
        try {
          return json.decode(res.body);
        } catch (_) {
          return {'status': 'error', 'message': 'HTTP ${res.statusCode}'};
        }
      } catch (e) {
        attempt += 1;
        print('API GET error (attempt $attempt): $e');
        if (attempt >= maxRetries) {
          return {'status': 'error', 'message': e.toString()};
        }
        await Future.delayed(Duration(milliseconds: 400 * attempt));
      }
    }
    return {'status': 'error', 'message': 'Unknown error'};
  }

  static Future<dynamic> post(String path, Map body) async {
    const int maxRetries = 3;
    int attempt = 0;
    while (attempt < maxRetries) {
      try {
        final res = await http.post(
          Uri.parse(base + path),
          headers: {'Content-Type': 'application/json'},
          body: json.encode(body),
        );

        if (res.statusCode == 200 || res.statusCode == 201) {
          return json.decode(res.body);
        }

        // Parse error body when possible
        try {
          return json.decode(res.body);
        } catch (_) {
          return {'status': 'error', 'message': 'HTTP ${res.statusCode}'};
        }
      } catch (e) {
        attempt += 1;
        print('API POST error (attempt $attempt): $e');
        if (attempt >= maxRetries) {
          return {'status': 'error', 'message': e.toString()};
        }
        await Future.delayed(Duration(milliseconds: 400 * attempt));
      }
    }
    return {'status': 'error', 'message': 'Unknown error'};
  }

  static Future<dynamic> delete(String path) async {
    try {
      final res = await http.delete(Uri.parse(base + path));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
      return null;
    } catch (e) {
      print('API DELETE error: $e');
      return {'status': 'error', 'message': e.toString()};
    }
  }
}
