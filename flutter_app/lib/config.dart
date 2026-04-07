/// API base, e.g. http://127.0.0.1:8000 — override with --dart-define=API_BASE=...
const String kApiBase = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'http://127.0.0.1:8000',
);
