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

## Requirements

- Python 3.8+
- Windows OS (some features are Windows-specific)
- Required API keys (OpenAI, ElevenLabs, OpenWeather)

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
   - Fill in your API keys in the `.env` file

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
