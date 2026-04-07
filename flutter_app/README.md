# ICU Flutter client

Cross-platform UI for the ICU API (auth, chats, WebSocket).

## Prerequisites

- [Flutter](https://docs.flutter.dev/get-started/install) 3.24+ (Dart 3.3+)

## Bootstrap platform folders

This repo ships `lib/` and `pubspec.yaml` only. Generate Android/iOS/desktop runners once:

```bash
cd flutter_app
flutter create . --project-name icu_app
flutter pub get
```

## Run

Default API base URL is `http://127.0.0.1:8000`. Override:

```bash
flutter run --dart-define=API_BASE=http://YOUR_HOST:8000
```

- **Android emulator:** use `http://10.0.2.2:8000` to reach the host machine.
- **Physical device:** use your PC LAN IP, e.g. `http://192.168.1.10:8000`.

## Features

- Email → OTP login, token storage
- Conversation list, open direct chat by peer UIN
- Send/receive messages (REST + WebSocket events)
- Receipts: mark delivered/read up to message id
