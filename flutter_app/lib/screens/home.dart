import 'package:flutter/material.dart';
import 'package:icu_app/screens/chat.dart';
import 'package:icu_app/services/api.dart';
import 'package:icu_app/services/storage.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Map<String, dynamic>? _me;
  List<dynamic> _items = [];
  bool _loading = true;
  String? _err;
  final _peerUin = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _err = null;
    });
    try {
      _me = await me();
      _items = await listConversations();
    } catch (e) {
      _err = e.toString();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logout() async {
    await clearTokens();
    if (!mounted) return;
    Navigator.of(context).pushNamedAndRemoveUntil('/email', (_) => false);
  }

  Future<void> _openByUin() async {
    final v = int.tryParse(_peerUin.text.trim());
    if (v == null) return;
    try {
      final c = await openDirect(v);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ChatScreen(
            conversationId: c['id'] as int,
            peerUin: c['peer_uin'] as int,
            title: '${c['peer_uin']}',
          ),
        ),
      );
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final uin = _me?['uin'];
    return Scaffold(
      appBar: AppBar(
        title: Text('ICU${uin != null ? ' · $uin' : ''}'),
        actions: [
          IconButton(
            onPressed: _logout,
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _err != null
              ? Center(child: Text(_err!))
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _peerUin,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Peer UIN',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          FilledButton(
                            onPressed: _openByUin,
                            child: const Text('Open'),
                          ),
                        ],
                      ),
                    ),
                    const Divider(height: 1),
                    Expanded(
                      child: ListView.builder(
                        itemCount: _items.length,
                        itemBuilder: (ctx, i) {
                          final it = _items[i] as Map<String, dynamic>;
                          return ListTile(
                            title: Text('UIN ${it['peer_uin']}'),
                            subtitle: Text(it['peer_display_name']?.toString() ?? ''),
                            onTap: () {
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => ChatScreen(
                                    conversationId: it['id'] as int,
                                    peerUin: it['peer_uin'] as int,
                                    title: '${it['peer_uin']}',
                                  ),
                                ),
                              ).then((_) => _load());
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
    );
  }
}
