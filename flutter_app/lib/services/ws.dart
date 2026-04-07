import 'dart:async';
import 'dart:convert';

import 'package:icu_app/config.dart';
import 'package:icu_app/services/storage.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

typedef WsEventHandler = void Function(Map<String, dynamic> json);

class WsClient {
  WebSocketChannel? _ch;
  StreamSubscription? _sub;
  Timer? _ping;

  Future<void> connect(WsEventHandler onEvent) async {
    await disconnect();
    final token = await loadAccessToken();
    if (token == null) return;
    final b = Uri.parse(kApiBase);
    final basePath = b.path.endsWith('/') && b.path.length > 1
        ? b.path.substring(0, b.path.length - 1)
        : b.path;
    final wsPath = (basePath.isEmpty || basePath == '/') ? '/v1/ws' : '$basePath/v1/ws';
    final uri = b.replace(
      scheme: b.scheme == 'https' ? 'wss' : 'ws',
      path: wsPath,
      queryParameters: {'token': token},
    );
    _ch = WebSocketChannel.connect(uri);
    _sub = _ch!.stream.listen(
      (raw) {
        try {
          final m = jsonDecode(raw as String) as Map<String, dynamic>;
          onEvent(m);
        } catch (_) {}
      },
      onError: (_) {},
      onDone: () {},
    );
    _ping = Timer.periodic(const Duration(seconds: 25), (_) {
      try {
        _ch?.sink.add(jsonEncode({'type': 'ping'}));
      } catch (_) {}
    });
  }

  Future<void> disconnect() async {
    _ping?.cancel();
    _ping = null;
    await _sub?.cancel();
    _sub = null;
    await _ch?.sink.close();
    _ch = null;
  }
}
