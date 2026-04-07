import 'package:flutter/material.dart';
import 'package:icu_app/services/api.dart';
import 'package:icu_app/services/ws.dart';
import 'package:uuid/uuid.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({
    super.key,
    required this.conversationId,
    required this.peerUin,
    required this.title,
  });

  final int conversationId;
  final int peerUin;
  final String title;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _ctrl = TextEditingController();
  final _ws = WsClient();
  final _uuid = const Uuid();
  List<Map<String, dynamic>> _msgs = [];
  bool _loading = true;
  int? _lastId;

  @override
  void initState() {
    super.initState();
    _load();
    _ws.connect((ev) {
      if (ev['type'] == 'event' && ev['name'] == 'new_message') {
        final m = ev['message'] as Map<String, dynamic>?;
        if (m != null && m['conversation_id'] == widget.conversationId) {
          setState(() {
            _msgs.add(m);
            _lastId = m['id'] as int;
          });
          _markRead(m['id'] as int);
        }
      }
    });
  }

  @override
  void dispose() {
    _ws.disconnect();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await getMessages(widget.conversationId);
      final list = (data['messages'] as List<dynamic>).cast<Map<String, dynamic>>();
      setState(() {
        _msgs = list;
        if (_msgs.isNotEmpty) {
          _lastId = _msgs.last['id'] as int;
        }
      });
      if (_lastId != null) {
        await postReceipts(widget.conversationId, readUpTo: _lastId);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _markRead(int id) async {
    try {
      await postReceipts(widget.conversationId, readUpTo: id);
    } catch (_) {}
  }

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty) return;
    final cid = _uuid.v4();
    _ctrl.clear();
    try {
      final m = await sendMessage(widget.conversationId, text, cid);
      setState(() {
        _msgs.add(Map<String, dynamic>.from(m));
        _lastId = m['id'] as int;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Chat · ${widget.title}')),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : ListView.builder(
                    padding: const EdgeInsets.all(8),
                    itemCount: _msgs.length,
                    itemBuilder: (ctx, i) {
                      final m = _msgs[i];
                      final out = m['outgoing'] == true;
                      final st = m['delivery_status']?.toString();
                      return Align(
                        alignment: out ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 4),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: out
                                ? Theme.of(context).colorScheme.primaryContainer
                                : Theme.of(context).colorScheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(m['body']?.toString() ?? ''),
                              if (out && st != null)
                                Text(
                                  st,
                                  style: const TextStyle(fontSize: 10, color: Colors.grey),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _ctrl,
                      decoration: const InputDecoration(
                        hintText: 'Message…',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      minLines: 1,
                      maxLines: 4,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
