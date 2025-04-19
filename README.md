# JARVIS - Voice-Activated AI Assistant

JARVIS is a sophisticated voice-activated AI assistant inspired by Tony Stark's JARVIS. It uses state-of-the-art AI technologies to provide a natural and powerful interface for controlling your computer and accessing information.

## Features

- 🎙️ **Voice Recognition**: Understands natural speech commands using Google's Speech Recognition
- 🗣️ **Natural Speech**: Responds with human-like speech using ElevenLabs' text-to-speech
- 🤖 **AI-Powered Responses**: Uses GPT-4 for intelligent conversation and task handling
- 📝 **Note Taking**: Can create, append to, and manage notes in Notepad
- 🌐 **Web Search**: Performs web searches directly through voice commands
- 💻 **Application Control**: Opens and closes applications with voice commands
- ⚡ **System Commands**: Executes system commands and provides system information
- 🌤️ **Weather Information**: Provides weather updates for any city
- ⏰ **Time Information**: Tells the current time
- 🎯 **Interruption Handling**: Can be interrupted mid-speech with "stop" command

## Technical Architecture

### Core Technologies
- **Python**: Primary programming language
- **OpenAI GPT-4**: Natural language understanding and response generation
- **ElevenLabs**: High-quality text-to-speech with customizable voices
- **Google Speech Recognition**: Primary speech-to-text conversion

### Voice Processing Components
```python
# Speech Recognition Stack
- SpeechRecognition library with PyAudio
- Multiple recognition engines:
  - Google Speech Recognition (primary)
  - Google Cloud Speech (backup)
  - PocketSphinx (offline fallback)
```

### Audio Processing
```python
# Audio Output Stack
- sounddevice: Real-time audio playback
- soundfile: Audio file handling
- numpy: Audio data manipulation
- ElevenLabs API: Primary TTS engine
- OpenAI TTS: Fallback TTS engine
```

### System Integration
```python
# System Control Components
- subprocess: Application launching
- psutil: Process management
- os: File system operations
- platform: OS detection
```

### Program Control Architecture
```python
# Application Management Features
- Dynamic path resolution
- Recursive file search
- Process lifecycle management
- Multi-format support:
  - Executables (.exe)
  - Shortcuts (.lnk)
  - Batch files (.bat, .cmd)
  - System files (.msc)
```

### Advanced Features
1. **Real-time Interruption Detection**
   - Monitors audio input during speech
   - Immediate response to "stop" command

2. **Background Listening**
   - Continuous voice command monitoring
   - Efficient audio processing
   - Low resource utilization

3. **Command Queue Management**
   - Sequential command processing
   - Priority handling
   - State management

4. **Error Handling**
   - Graceful degradation
   - Multiple fallback systems
   - Comprehensive error reporting

## Dependencies

```python
openai>=1.0.0          # AI and TTS capabilities
SpeechRecognition>=3.10.0  # Voice recognition
python-dotenv>=1.0.0   # Environment configuration
psutil>=5.9.0          # System process management
sounddevice>=0.4.6     # Audio output handling
soundfile>=0.12.1      # Audio file processing
numpy>=1.24.0          # Numerical operations
elevenlabs>=0.2.24     # Primary TTS engine
PyAudio>=0.2.13        # Audio input handling
pocketsphinx>=5.0.0    # Offline speech recognition
```

## Voice Command Processing Flow

### 1. Voice Input Processing
```python
# Continuous Monitoring
- Real-time audio capture
- Background noise filtering
- Speech detection algorithms
```

### 2. Command Recognition
```python
# Speech to Command Pipeline
1. Audio capture and preprocessing
2. Speech-to-text conversion
3. Command pattern recognition
4. Argument extraction
```

### 3. Program Control Mechanism
```python
# Application Management
1. Command validation
2. Path resolution
3. Process spawning
4. State monitoring
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jarvis.git
   cd jarvis
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.template` to `.env`
   - Fill in your API keys:
     - OPENAI_API_KEY
     - ELEVENLABS_API_KEY
     - ELEVENLABS_VOICE_ID
     - OPENWEATHER_API_KEY (optional)

## Usage

Run JARVIS:
```bash
python jarvis.py
```

### Example Commands

- "Open Chrome"
- "Close Notepad"
- "Write a shopping list in Notepad"
- "Search for latest tech news"
- "What's the weather in London?"
- "What time is it?"
- "Stop" (interrupts current speech)

## Configuration

JARVIS can be configured through environment variables in the `.env` file:

- `OPENAI_API_KEY`: Your OpenAI API key
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key
- `ELEVENLABS_VOICE_ID`: Your ElevenLabs voice ID
- `OPENWEATHER_API_KEY`: Your OpenWeather API key (optional)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT-4 and TTS capabilities
- ElevenLabs for advanced text-to-speech
- Google for Speech Recognition
- All other open-source libraries used in this project
