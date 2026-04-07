import 'package:flutter/material.dart';
import 'package:icu_app/screens/auth_code.dart';
import 'package:icu_app/screens/auth_email.dart';
import 'package:icu_app/screens/home.dart';
import 'package:icu_app/services/storage.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const IcuApp());
}

class IcuApp extends StatelessWidget {
  const IcuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ICU',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: const _Bootstrap(),
      routes: {
        '/email': (_) => const AuthEmailScreen(),
        '/code': (_) => const AuthCodeScreen(),
        '/home': (_) => const HomeScreen(),
      },
    );
  }
}

class _Bootstrap extends StatefulWidget {
  const _Bootstrap();

  @override
  State<_Bootstrap> createState() => _BootstrapState();
}

class _BootstrapState extends State<_Bootstrap> {
  @override
  void initState() {
    super.initState();
    _go();
  }

  Future<void> _go() async {
    final t = await loadAccessToken();
    if (!mounted) return;
    if (t != null) {
      Navigator.of(context).pushReplacementNamed('/home');
    } else {
      Navigator.of(context).pushReplacementNamed('/email');
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
