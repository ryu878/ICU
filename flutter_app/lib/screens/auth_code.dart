import 'package:flutter/material.dart';
import 'package:icu_app/services/api.dart';

class AuthCodeScreen extends StatefulWidget {
  const AuthCodeScreen({super.key});

  @override
  State<AuthCodeScreen> createState() => _AuthCodeScreenState();
}

class _AuthCodeScreenState extends State<AuthCodeScreen> {
  final _c = TextEditingController();
  bool _loading = false;
  String? _err;

  Future<void> _submit(String email) async {
    setState(() {
      _loading = true;
      _err = null;
    });
    try {
      await verifyOtp(email, _c.text.trim());
      if (!mounted) return;
      Navigator.of(context).pushNamedAndRemoveUntil('/home', (_) => false);
    } catch (e) {
      setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final email = ModalRoute.of(context)!.settings.arguments as String?;
    if (email == null) {
      return const Scaffold(body: Center(child: Text('Missing email')));
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Email code')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _c,
              keyboardType: TextInputType.number,
              maxLength: 6,
              decoration: const InputDecoration(
                labelText: '6-digit code',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _loading ? null : () => _submit(email),
              child: Text(_loading ? 'Signing in…' : 'Sign in'),
            ),
            if (_err != null) ...[
              const SizedBox(height: 12),
              Text(_err!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ],
          ],
        ),
      ),
    );
  }
}
