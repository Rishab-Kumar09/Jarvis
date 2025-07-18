# 📱 J.A.R.V.I.S Flutter App

A native mobile application for controlling your Jarvis AI Assistant. Built with Flutter for Android and iOS.

## ✨ Features

- **🎤 Voice Commands** - Native speech recognition
- **⌨️ Text Input** - Type commands directly
- **🔘 Quick Commands** - Preset buttons for common tasks
- **💬 Real-time Chat** - Live conversation with Jarvis
- **🌐 Network Connection** - Connect to Jarvis over WiFi
- **🎨 Beautiful UI** - JARVIS-themed design with animations
- **📱 Native Performance** - Smooth mobile experience

## 📋 Prerequisites

1. **Flutter Development Environment**
   - Install Flutter SDK (3.0.0 or higher)
   - Install Android Studio or Xcode
   - Set up device/emulator

2. **Jarvis Backend Running**
   - Your main Jarvis Python app must be running in `--web` or `--hybrid` mode
   - Both devices on same WiFi network

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd jarvis_flutter_app
flutter pub get
```

### 2. Run on Device/Emulator
```bash
# For Android
flutter run

# For iOS
flutter run -d ios

# For specific device
flutter devices  # List available devices
flutter run -d <device_id>
```

### 3. Connect to Jarvis
1. **Start Jarvis backend:** `python jarvis.py --web`
2. **Note the IP address** shown in console (e.g., `192.168.1.100:5000`)
3. **Open the app** and tap the settings icon
4. **Enter the IP and port** from step 2
5. **Tap Connect** and start controlling Jarvis!

## 🛠️ Build for Release

### Android APK
```bash
flutter build apk --release
```
The APK will be in `build/app/outputs/flutter-apk/app-release.apk`

### iOS App (macOS only)
```bash
flutter build ios --release
```

## 📱 App Structure

```
lib/
├── main.dart                 # App entry point
├── providers/
│   └── jarvis_service.dart   # State management & API
├── screens/
│   └── home_screen.dart      # Main interface
└── widgets/
    ├── message_bubble.dart   # Chat message bubbles
    ├── quick_commands.dart   # Quick action buttons
    └── connection_dialog.dart # Server settings
```

## 🎯 Key Components

### JarvisService Provider
- Manages WebSocket connection to Jarvis backend
- Handles command sending and response receiving
- Maintains connection state and message history

### Voice Recognition
- Uses `speech_to_text` plugin for native speech recognition
- Requires microphone permission
- Supports continuous listening

### Real-time Communication
- WebSocket connection for instant responses
- Fallback to HTTP API if WebSocket fails
- Auto-reconnection on network changes

## 🔧 Configuration

### Server Settings
Default connection: `192.168.1.100:5000`

Change in the app:
1. Tap settings icon in app bar
2. Enter new host/port
3. Tap Connect

### Permissions

**Android** (automatically handled):
- `INTERNET` - Connect to Jarvis server
- `RECORD_AUDIO` - Voice input
- `ACCESS_NETWORK_STATE` - Network status
- `ACCESS_WIFI_STATE` - WiFi information

**iOS** (user prompted):
- Microphone access for voice input
- Network access for server connection

## 🎮 Usage

### Voice Commands
1. **Hold the microphone button** to start voice recognition
2. **Speak your command** (e.g., "check my emails")
3. **Release the button** to send the command
4. **See the response** in the chat area

### Quick Commands
- **📧 Check Emails** - Get latest unread emails
- **🌤️ Weather** - Current weather information
- **💻 System Info** - Computer system status
- **🌐 Open Chrome** - Launch Chrome browser
- **📝 Write Note** - Create a new note
- **📅 Calendar** - Check calendar events

### Text Commands
1. **Type in the input field** at the bottom
2. **Press Enter** or tap the send button
3. **View response** in the chat area

## 🔗 Connection Troubleshooting

### ❌ "Failed to connect"
- ✅ Check if Jarvis is running in `--web` mode
- ✅ Verify both devices on same WiFi
- ✅ Confirm IP address is correct
- ✅ Try default port 5000

### ❌ "Voice not working"
- ✅ Grant microphone permission when prompted
- ✅ Check device microphone is working
- ✅ Try using text input as fallback

### ❌ "Connection lost"
- ✅ Check WiFi connectivity
- ✅ Restart Jarvis backend
- ✅ Reconnect in app settings

## 🎨 UI Features

- **Dark Theme** with JARVIS blue accents
- **Gradient Backgrounds** for futuristic look
- **Smooth Animations** using Flutter Animate
- **Chat Bubbles** with different styles for user/Jarvis
- **Connection Status** indicator in app bar
- **Loading States** for better user feedback

## 🔒 Security Notes

- App only connects to local network (same WiFi)
- No data sent to external servers
- Voice processing happens on device
- Secure WebSocket communication with Jarvis

## 🐛 Debugging

### Enable Debug Mode
```bash
flutter run --debug
```

### View Logs
```bash
flutter logs
```

### Check Connection
Test if Jarvis backend is accessible:
```bash
curl http://YOUR_JARVIS_IP:5000/api/status
```

## 📖 Dependencies

- `flutter` - UI framework
- `provider` - State management
- `http` - HTTP requests
- `web_socket_channel` - WebSocket communication
- `speech_to_text` - Voice recognition
- `permission_handler` - Device permissions
- `animated_text_kit` - Text animations
- `flutter_animate` - UI animations

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Test on both Android and iOS
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---

🎉 **Enjoy controlling Jarvis from your mobile device!** 🤖📱 