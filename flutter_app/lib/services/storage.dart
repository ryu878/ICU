import 'package:shared_preferences/shared_preferences.dart';

const _kAccess = 'icu_access_token';
const _kRefresh = 'icu_refresh_token';

Future<void> saveTokens({required String access, required String refresh}) async {
  final p = await SharedPreferences.getInstance();
  await p.setString(_kAccess, access);
  await p.setString(_kRefresh, refresh);
}

Future<void> clearTokens() async {
  final p = await SharedPreferences.getInstance();
  await p.remove(_kAccess);
  await p.remove(_kRefresh);
}

Future<String?> loadAccessToken() async {
  final p = await SharedPreferences.getInstance();
  return p.getString(_kAccess);
}

Future<String?> loadRefreshToken() async {
  final p = await SharedPreferences.getInstance();
  return p.getString(_kRefresh);
}
