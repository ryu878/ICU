import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:icu_app/config.dart';
import 'package:icu_app/services/storage.dart';

class ApiException implements Exception {
  ApiException(this.status, this.body);
  final int status;
  final String body;
  @override
  String toString() => 'ApiException($status): $body';
}

Future<Map<String, dynamic>> _jsonOrThrow(http.Response r) {
  if (r.statusCode >= 200 && r.statusCode < 300) {
    if (r.body.isEmpty) return Future.value(<String, dynamic>{});
    return Future.value(jsonDecode(r.body) as Map<String, dynamic>);
  }
  throw ApiException(r.statusCode, r.body);
}

Future<void> requestOtp(String email) async {
  final r = await http.post(
    Uri.parse('$kApiBase/v1/auth/request-otp'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'email': email}),
  );
  await _jsonOrThrow(r);
}

Future<Map<String, dynamic>> verifyOtp(String email, String code) async {
  final r = await http.post(
    Uri.parse('$kApiBase/v1/auth/verify-otp'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'email': email, 'code': code}),
  );
  final m = await _jsonOrThrow(r);
  final access = m['access_token'] as String;
  final refresh = m['refresh_token'] as String;
  await saveTokens(access: access, refresh: refresh);
  return m;
}

Future<Map<String, dynamic>> me() async {
  final t = await loadAccessToken();
  final r = await http.get(
    Uri.parse('$kApiBase/v1/users/me'),
    headers: {'Authorization': 'Bearer $t'},
  );
  return _jsonOrThrow(r);
}

Future<List<dynamic>> listConversations() async {
  final t = await loadAccessToken();
  final r = await http.get(
    Uri.parse('$kApiBase/v1/conversations'),
    headers: {'Authorization': 'Bearer $t'},
  );
  if (r.statusCode >= 200 && r.statusCode < 300) {
    return jsonDecode(r.body) as List<dynamic>;
  }
  throw ApiException(r.statusCode, r.body);
}

Future<Map<String, dynamic>> openDirect(int peerUin) async {
  final t = await loadAccessToken();
  final r = await http.post(
    Uri.parse('$kApiBase/v1/conversations/direct'),
    headers: {
      'Authorization': 'Bearer $t',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({'peer_uin': peerUin}),
  );
  return _jsonOrThrow(r);
}

Future<Map<String, dynamic>> getMessages(int conversationId, {int? beforeId}) async {
  final t = await loadAccessToken();
  final q = beforeId != null ? '?before_id=$beforeId' : '';
  final r = await http.get(
    Uri.parse('$kApiBase/v1/conversations/$conversationId/messages$q'),
    headers: {'Authorization': 'Bearer $t'},
  );
  return _jsonOrThrow(r);
}

Future<Map<String, dynamic>> sendMessage(
  int conversationId,
  String body,
  String clientId,
) async {
  final t = await loadAccessToken();
  final r = await http.post(
    Uri.parse('$kApiBase/v1/conversations/$conversationId/messages'),
    headers: {
      'Authorization': 'Bearer $t',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      'body': body,
      'client_message_id': clientId,
    }),
  );
  return _jsonOrThrow(r);
}

Future<void> postReceipts(
  int conversationId, {
  int? deliveredUpTo,
  int? readUpTo,
}) async {
  final t = await loadAccessToken();
  final r = await http.post(
    Uri.parse('$kApiBase/v1/conversations/$conversationId/receipts'),
    headers: {
      'Authorization': 'Bearer $t',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      if (deliveredUpTo != null) 'delivered_up_to_message_id': deliveredUpTo,
      if (readUpTo != null) 'read_up_to_message_id': readUpTo,
    }),
  );
  if (r.statusCode != 204) {
    throw ApiException(r.statusCode, r.body);
  }
}

Future<Map<String, dynamic>> lookupUser(int uin) async {
  final t = await loadAccessToken();
  final r = await http.get(
    Uri.parse('$kApiBase/v1/users/by-uin/$uin'),
    headers: {'Authorization': 'Bearer $t'},
  );
  return _jsonOrThrow(r);
}
