from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import asyncio
import threading
from jarvis import Jarvis
import queue
import json
import io
import base64
import numpy as np
import soundfile as sf
import speech_recognition as sr

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create a Jarvis instance
jarvis = Jarvis()
command_queue = queue.Queue()
response_queue = queue.Queue()

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>JARVIS Remote Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f0f2f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .control-panel {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .input-group {
            margin-bottom: 20px;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
            margin-bottom: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        #response {
            margin-top: 20px;
            padding: 15px;
            background: #e9ecef;
            border-radius: 5px;
            min-height: 50px;
        }
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-top: 20px;
        }
        .quick-action-btn {
            background-color: #6c757d;
            font-size: 14px;
            padding: 8px;
        }
        .voice-btn {
            background-color: #28a745;
        }
        .voice-btn.recording {
            background-color: #dc3545;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .status {
            color: #666;
            font-style: italic;
            margin-top: 5px;
            text-align: center;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const socket = io();
            const responseDiv = document.getElementById('response');
            const voiceButton = document.getElementById('voiceButton');
            const statusDiv = document.getElementById('status');
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;

            // Handle incoming text responses
            socket.on('response', function(data) {
                responseDiv.textContent = data.response;
            });

            // Handle incoming audio responses
            socket.on('audio_response', function(data) {
                const audio = new Audio('data:audio/wav;base64,' + data.audio);
                audio.play();
            });

            function sendCommand(command) {
                socket.emit('command', {command: command});
                responseDiv.textContent = 'Processing command...';
            }

            document.getElementById('commandForm').onsubmit = function(e) {
                e.preventDefault();
                const command = document.getElementById('commandInput').value;
                if (command) {
                    sendCommand(command);
                    document.getElementById('commandInput').value = '';
                }
            };

            // Voice recording functionality
            async function startRecording() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];

                    mediaRecorder.ondataavailable = (event) => {
                        audioChunks.push(event.data);
                    };

                    mediaRecorder.onstop = () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        const reader = new FileReader();
                        reader.readAsDataURL(audioBlob);
                        reader.onloadend = () => {
                            const base64Audio = reader.result.split(',')[1];
                            socket.emit('voice_command', { audio: base64Audio });
                            statusDiv.textContent = 'Processing voice command...';
                        };
                    };

                    mediaRecorder.start();
                    isRecording = true;
                    voiceButton.classList.add('recording');
                    voiceButton.textContent = 'Stop Recording';
                    statusDiv.textContent = 'Recording...';
                } catch (err) {
                    console.error('Error accessing microphone:', err);
                    statusDiv.textContent = 'Error accessing microphone';
                }
            }

            function stopRecording() {
                if (mediaRecorder && isRecording) {
                    mediaRecorder.stop();
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    isRecording = false;
                    voiceButton.classList.remove('recording');
                    voiceButton.textContent = 'Start Voice Command';
                }
            }

            voiceButton.onclick = function() {
                if (!isRecording) {
                    startRecording();
                } else {
                    stopRecording();
                }
            };

            // Add click handlers for quick action buttons
            document.querySelectorAll('.quick-action-btn').forEach(button => {
                button.onclick = function() {
                    sendCommand(this.getAttribute('data-command'));
                };
            });
        });
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>JARVIS Remote Control</h1>
        </div>
        <div class="control-panel">
            <button id="voiceButton" class="voice-btn">Start Voice Command</button>
            <div id="status" class="status"></div>
            
            <form id="commandForm">
                <div class="input-group">
                    <input type="text" id="commandInput" placeholder="Or type your command here..." autocomplete="off">
                </div>
                <button type="submit">Send Command</button>
            </form>
            
            <div class="quick-actions">
                <button class="quick-action-btn" data-command="system status">System Status</button>
                <button class="quick-action-btn" data-command="what time is it">Current Time</button>
                <button class="quick-action-btn" data-command="open chrome">Open Chrome</button>
                <button class="quick-action-btn" data-command="close chrome">Close Chrome</button>
            </div>
            
            <div id="response">
                Ready for commands...
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('voice_command')
def handle_voice_command(data):
    try:
        # Convert base64 audio to wav file
        audio_data = base64.b64decode(data['audio'])
        audio = sr.AudioData(audio_data, sample_rate=44100, sample_width=2)
        
        # Use speech recognition
        recognizer = sr.Recognizer()
        try:
            command = recognizer.recognize_google(audio)
            print(f"Recognized voice command: {command}")
            
            # Process the command
            threading.Thread(target=process_command, args=(command,)).start()
        except sr.UnknownValueError:
            socketio.emit('response', {'response': "Sorry, I couldn't understand that. Please try again."})
        except sr.RequestError as e:
            socketio.emit('response', {'response': f"Error with the speech recognition service: {e}"})
    except Exception as e:
        socketio.emit('response', {'response': f"Error processing voice command: {e}"})

@socketio.on('command')
def handle_command(data):
    command = data.get('command')
    if command:
        command_queue.put(command)
        # Start processing in a separate thread to not block Socket.IO
        threading.Thread(target=process_command, args=(command,)).start()

def process_command(command):
    try:
        # Process the command using Jarvis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(jarvis.process_command(command))
        loop.close()
        
        # Emit the text response back to the client
        socketio.emit('response', {'response': response})
        
        # If the response should be spoken, do it in a separate thread
        if response:
            threading.Thread(target=speak_response, args=(response,)).start()
    except Exception as e:
        socketio.emit('response', {'response': f"Error processing command: {str(e)}"})

def speak_response(response):
    try:
        # Create a new event loop for the speech generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Generate speech using ElevenLabs
        audio = jarvis.elevenlabs.generate(
            text=response,
            voice=jarvis.elevenlabs_voice_id,
            model="eleven_monolingual_v1"
        )
        
        # Convert audio to base64
        audio_base64 = base64.b64encode(audio).decode('utf-8')
        
        # Send the audio to the client
        socketio.emit('audio_response', {'audio': audio_base64})
        
        loop.close()
    except Exception as e:
        print(f"Error speaking response: {e}")
        # Fall back to OpenAI TTS if ElevenLabs fails
        try:
            response = jarvis.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=response
            )
            audio_base64 = base64.b64encode(response.content).decode('utf-8')
            socketio.emit('audio_response', {'audio': audio_base64})
        except Exception as e:
            print(f"Error with fallback TTS: {e}")

def run_web_interface():
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)

if __name__ == '__main__':
    run_web_interface() 