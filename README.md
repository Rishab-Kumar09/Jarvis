# JARVIS - Voice-Activated AI Assistant

JARVIS is a Python-based command-line AI assistant that uses voice input and output to interact with users. It combines OpenAI's GPT-4 for natural language understanding and text-to-speech capabilities for a seamless voice interaction experience.

## Features

- Voice input recognition using Google Speech Recognition
- Text-to-speech output using OpenAI's TTS (with fallback to pyttsx3)
- Natural language processing using GPT-4
- British accent and sophisticated speaking style
- Easy-to-use command-line interface

## Prerequisites

- Python 3.7 or higher
- OpenAI API key
- Microphone for voice input
- Speakers for voice output

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd jarvis
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

1. Run JARVIS:
```bash
python jarvis.py
```

2. Wait for the "Listening..." prompt

3. Speak your command or question

4. Listen to JARVIS's response

5. To exit, say "goodbye", "exit", or "quit"

## Common Commands

- Ask questions
- Request information
- Give instructions
- Have conversations

## Troubleshooting

If you encounter issues with PyAudio installation:

### Windows
```bash
pip install pipwin
pipwin install pyaudio
```

### Linux
```bash
sudo apt-get install python3-pyaudio
```

### macOS
```bash
brew install portaudio
pip install pyaudio
```

## Note

This program requires an active internet connection for:
- Speech recognition
- OpenAI API calls
- Text-to-speech generation
