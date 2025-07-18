# Jarvis Voice Assistant 🤖

A sophisticated voice assistant inspired by Tony Stark's J.A.R.V.I.S, built with Python. Now supports both voice control and **web-based remote control from your phone**!

## Features ✨

### Voice Control
- 🎤 Voice commands with wake word detection
- 🔊 Text-to-speech with ElevenLabs integration
- 📧 Gmail integration (read, send, reply to emails)
- 📅 Google Calendar management
- 🌐 Web search functionality
- 📝 Note-taking with Notepad/Word integration
- 💻 System monitoring and app control
- 🌤️ Weather information

### 📱 NEW: Phone/Web Control
- 🌐 **Control Jarvis from your phone browser**
- 📱 Mobile-optimized interface
- 🎙️ Voice input through browser
- ⚡ Real-time WebSocket communication
- 🔘 Quick command buttons
- 📊 Live status monitoring

## Setup 🛠️

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables:**
   Create a `.env` file with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_VOICE_ID=your_voice_id
   OPENWEATHER_API_KEY=your_weather_api_key
   FLASK_SECRET_KEY=your_secret_key (optional)
   ```

3. **Gmail Setup (Optional):**
   - Download `credentials.json` from Google Cloud Console
   - Place it in the project root
   - First run will prompt for Gmail authorization

## Usage 🚀

### Voice-Only Mode (Default)
```bash
python jarvis.py
```

### 📱 Web-Only Mode (Phone Control)
```bash
python jarvis.py --web
```
Then open your phone browser and go to the displayed URL (e.g., `http://192.168.1.100:5000`)

### Hybrid Mode (Voice + Web)
```bash
python jarvis.py --hybrid
```
Enables both voice control on the computer AND web control from your phone simultaneously!

## 📱 Phone Control Features

- **🎤 Voice Input:** Tap the microphone button to use voice commands
- **⌨️ Text Input:** Type commands directly
- **🔘 Quick Commands:** Tap preset buttons for common tasks
- **📊 Real-time Status:** See Jarvis's current state
- **💬 Live Responses:** Get instant feedback from commands
- **📱 Mobile Optimized:** Responsive design that works great on phones

### Quick Commands Available:
- 📧 Check Emails
- 🌤️ Get Weather
- 💻 System Info
- 🌐 Open Chrome
- 📝 Write Note
- 📅 Calendar

## Network Setup 📡

1. **Make sure your phone and computer are on the same WiFi network**
2. **Run Jarvis in web mode:** `python jarvis.py --web`
3. **Note the IP address shown** (e.g., `192.168.1.100:5000`)
4. **Open your phone's browser** and navigate to that address
5. **Start controlling Jarvis remotely!**

## Voice Commands Examples 🗣️

- "Jarvis, check my emails"
- "What's the weather like?"
- "Open Chrome"
- "Write a note about today's meeting"
- "Show my calendar"
- "Search for Python tutorials"
- "Get system info"

## Troubleshooting 🔧

### Web Interface Issues:
- **Can't connect from phone:** Ensure both devices are on the same WiFi
- **Address not working:** Try the IP address shown in the console
- **Voice not working in browser:** Grant microphone permissions when prompted

### Voice Issues:
- **Not hearing Jarvis:** Check your speakers and audio output
- **Voice not recognized:** Ensure microphone permissions are granted
- **ElevenLabs errors:** Verify your API key and internet connection

## Technical Details 🔧

- **Framework:** Python with asyncio for concurrent operations
- **Web Interface:** Flask + Socket.IO for real-time communication
- **Speech Recognition:** Google Speech Recognition API
- **Text-to-Speech:** ElevenLabs API (premium) with fallbacks
- **Email/Calendar:** Google APIs with OAuth2 authentication

## Security Note 🔒

The web interface is designed for local network use only. It binds to `0.0.0.0:5000` to allow access from other devices on your local network but should not be exposed to the internet without proper security measures.

## Contributing 🤝

Feel free to submit issues and enhancement requests!

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.
