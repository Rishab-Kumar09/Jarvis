import speech_recognition as sr
import json
from openai import OpenAI
import asyncio
import os
from dotenv import load_dotenv
import webbrowser
import subprocess
import datetime
import psutil
import requests
import platform
import sounddevice as sd
import soundfile as sf
import io
import numpy as np
import time
import threading
import queue
from signalrcore.hub_connection_builder import HubConnectionBuilder
from elevenlabs import generate, play
import jwt

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

class Jarvis:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Adjust recognition parameters
        self.recognizer.energy_threshold = 300  # Minimum audio energy to consider for recording
        self.recognizer.dynamic_energy_threshold = True  # Automatically adjust for ambient noise
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 1.2  # Increased pause threshold to wait longer for complete phrases
        self.recognizer.phrase_threshold = 0.5  # Increased to ensure we catch the start of phrases
        self.recognizer.non_speaking_duration = 1.0  # Increased to better detect end of speaking

        self.voice_profile = {
            "instructions": """Voice Profile:
            Accent & Tone: Sophisticated British male accent, precise and authoritative, with the characteristic JARVIS-like formality.
            Pitch & Pace: Deep masculine pitch, measured and deliberate pace, with technological crispness.
            Delivery Style: Professional and efficient, with undertones of artificial intelligence sophistication.
            Emotion: Calm and composed, with subtle hints of dry wit and unwavering loyalty."""
        }
        self.system_info = platform.system()
        # Set default audio device
        sd.default.samplerate = 24000
        sd.default.channels = 1
        
        # For handling interruptions and continuous listening
        self.is_speaking = False
        self.is_listening = False
        self.speech_thread = None
        self.listen_thread = None
        self.audio_queue = queue.Queue()
        self.command_queue = queue.Queue()
        self.interrupt_event = threading.Event()
        self.interrupt_threshold = 0.1  # Threshold for interruption detection
        self.background_listening = True
        self.last_phrase_time = time.time()
        self.command_timeout = 2.0  # Time to wait for command completion
        
        # Initialize SignalR connection
        self.hub_connection = None
        self.setup_signalr_connection()

        # Load ElevenLabs API key and voice ID
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        self.elevenlabs_voice_id = os.getenv('ELEVENLABS_VOICE_ID')
        
        # Voice settings optimized for JARVIS clone
        self.voice_settings = {
            "stability": 0.53,  # Slightly lower stability for more natural variation
            "similarity_boost": 0.85,  # Higher similarity to match the original voice better
            "style": 0.0,  # Neutral style
            "use_speaker_boost": True  # Enhanced clarity
        }

    def setup_signalr_connection(self):
        """Set up the SignalR connection with Azure SignalR Service"""
        try:
            # Parse the connection string
            connection_string = os.getenv('AZURE_SIGNALR_CONNECTION_STRING', '')
            if not connection_string:
                print("Azure SignalR connection string not found")
                return

            # Parse connection string components
            components = dict(item.split('=', 1) for item in connection_string.split(';') if '=' in item)
            endpoint = components.get('Endpoint', '').rstrip('/')
            access_key = components.get('AccessKey', '')

            print(f"Endpoint: {endpoint}")  # Debug print

            # Remove the protocol from the endpoint if present
            if endpoint.startswith('https://'):
                endpoint = endpoint[8:]
            elif endpoint.startswith('http://'):
                endpoint = endpoint[7:]

            # Generate JWT token for authentication
            now = datetime.datetime.utcnow()
            token = jwt.encode(
                {
                    'aud': endpoint,
                    'exp': int((now + datetime.timedelta(hours=1)).timestamp()),
                    'nbf': int(now.timestamp()),
                    'iat': int(now.timestamp())
                },
                access_key,
                algorithm='HS256'
            )

            # Construct the hub URL with the negotiation endpoint
            hub_url = f"https://{endpoint}/client/negotiate?hub=jarvis"
            print(f"Negotiating with: {hub_url}")  # Debug print
            
            # Get the connection info from the negotiate endpoint
            headers = {
                'Authorization': f'Bearer {token}'
            }
            response = requests.post(hub_url, headers=headers)
            print(f"Negotiate Response Status: {response.status_code}")  # Debug print
            print(f"Negotiate Response: {response.text}")  # Debug print
            
            if response.status_code != 200:
                print(f"Negotiation failed with status {response.status_code}")
                return
                
            negotiate_response = response.json()
            
            # Use the URL from the negotiate response
            connection_url = negotiate_response.get('url', '')
            if not connection_url:
                print("Failed to get connection URL from negotiate endpoint")
                return

            print(f"Connection URL: {connection_url}")  # Debug print

            # Set up the hub connection with the negotiated URL
            self.hub_connection = HubConnectionBuilder()\
                .with_url(connection_url, options={
                    "access_token_factory": lambda: token,
                    "skip_negotiation": False,
                    "transport": "websockets"
                })\
                .with_automatic_reconnect({
                    "type": "interval",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": 5
                })\
                .build()

            # Set up message handler
            self.hub_connection.on("ReceiveMessage", self.handle_signalr_message)
            
            # Start the connection
            self.hub_connection.start()
            print("SignalR connection established with Azure SignalR Service")
            
        except Exception as e:
            print(f"Error setting up SignalR connection: {str(e)}")
            print(f"Error type: {type(e)}")  # Debug print
            self.hub_connection = None

    def handle_signalr_message(self, message):
        """Handle incoming SignalR messages"""
        try:
            print(f"Received SignalR message: {message}")
            # Queue the message for speech output
            if not self.is_speaking:
                asyncio.create_task(self.speak(f"Received message: {message}"))
        except Exception as e:
            print(f"Error handling SignalR message: {e}")

    def send_signalr_message(self, message):
        """Send a message through SignalR hub"""
        try:
            if self.hub_connection and self.hub_connection.transport.connected:
                # Send message with user identifier
                self.hub_connection.send("SendMessage", ["JARVIS", message])
                return f"Message sent via SignalR: {message}"
            else:
                return "SignalR connection not available. Please check your connection."
        except Exception as e:
            print(f"Error sending SignalR message: {e}")
            return f"Failed to send message: {str(e)}"

    def adjust_for_ambient_noise(self, source, duration=1):
        """Adjust recognizer energy threshold based on ambient noise"""
        print("Adjusting for ambient noise. Please wait...")
        self.recognizer.adjust_for_ambient_noise(source, duration=duration)
        print(f"Ambient noise threshold set to {self.recognizer.energy_threshold}")

    def execute_system_command(self, command):
        """Execute system commands safely"""
        try:
            if self.system_info == "Windows":
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return result.stdout
            else:
                return "System command execution is only supported on Windows for now."
        except Exception as e:
            return f"Error executing command: {e}"

    def write_to_notepad(self, text, filename=None):
        """Write text to notepad with optional filename"""
        try:
            if self.system_info == "Windows":
                # Use specified filename or create a default one
                if filename:
                    # Ensure the filename has .txt extension
                    if not filename.lower().endswith('.txt'):
                        filename += '.txt'
                    file_path = os.path.join(os.path.expanduser('~'), 'Documents', filename)
                else:
                    # Create a timestamp-based filename
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_path = os.path.join(os.path.expanduser('~'), 'Documents', f'jarvis_note_{timestamp}.txt')
                
                # Create Documents directory if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Write the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                # Open the file in Notepad
                subprocess.Popen(['notepad.exe', file_path])
                return f"Text has been saved to {file_path}"
            else:
                return "Notepad writing is only supported on Windows for now."
        except Exception as e:
            return f"Error writing to Notepad: {e}"

    def execute_cmd_command(self, cmd_command):
        """Execute a command in Command Prompt"""
        try:
            if self.system_info == "Windows":
                # Open CMD and execute the command
                full_command = f'cmd.exe /c start cmd.exe /k "{cmd_command}"'
                subprocess.Popen(full_command, shell=True)
                return f"Executing command in Command Prompt: {cmd_command}"
            else:
                return "Command Prompt execution is only supported on Windows for now."
        except Exception as e:
            return f"Error executing Command Prompt command: {e}"

    def search_web(self, query):
        """Search the web using default browser"""
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching the web for: {query}"
        except Exception as e:
            return f"Error searching web: {e}"

    def get_system_info(self):
        """Get system information"""
        try:
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return f"CPU Usage: {cpu_usage}%, Memory Usage: {memory.percent}%, Disk Usage: {disk.percent}%"
        except Exception as e:
            return f"Error getting system info: {e}"

    def get_weather(self, city):
        """Get weather information"""
        try:
            # Using OpenWeatherMap API (you'll need to add API key to .env)
            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                return "Weather API key not found in environment variables"
            
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                temp = data['main']['temp']
                desc = data['weather'][0]['description']
                return f"Current weather in {city}: {temp}°C, {desc}"
            else:
                return f"Error getting weather: {data['message']}"
        except Exception as e:
            return f"Error fetching weather: {e}"

    def open_application(self, app_name):
        """Open common applications with enhanced handling"""
        try:
            if self.system_info == "Windows":
                app_commands = {
                    "notepad": "notepad.exe",
                    "calculator": "calc.exe",
                    "chrome": {
                        "command": "chrome.exe",
                        "args": []
                    },
                    "google": {
                        "command": "chrome.exe",
                        "args": ["https://www.google.com"]
                    },
                    "firefox": "firefox.exe",
                    "explorer": "explorer.exe",
                    "word": "winword.exe",
                    "excel": "excel.exe",
                    "powerpoint": "powerpnt.exe",
                    "cmd": {
                        "command": "cmd.exe",
                        "args": ["/k", "cd /d %userprofile%"]
                    },
                    "command prompt": {
                        "command": "cmd.exe",
                        "args": ["/k", "cd /d %userprofile%"]
                    },
                    "command prompt as admin": {
                        "command": "powershell.exe",
                        "args": ["Start-Process", "cmd.exe", "-Verb", "RunAs"]
                    }
                }
                
                app_key = app_name.lower()
                if app_key in app_commands:
                    app_info = app_commands[app_key]
                    
                    if isinstance(app_info, str):
                        # Simple application launch
                        subprocess.Popen([app_info])
                    else:
                        # Complex launch with arguments
                        subprocess.Popen([app_info["command"]] + app_info["args"])
                    
                    return f"Opening {app_name}"
                else:
                    return f"Application {app_name} not found in known applications"
            else:
                return "Application opening is only supported on Windows for now."
        except Exception as e:
            print(f"Error opening application: {e}")  # Log the error but don't return it
            return f"Could not open {app_name}"

    async def process_command(self, command):
        """Process voice commands and generate responses with enhanced command recognition"""
        try:
            # First, check for specific task commands
            cmd_lower = command.lower()
            
            # Handle SignalR commands with simpler "broadcast" keyword
            if cmd_lower.startswith("broadcast "):
                message = command[len("broadcast "):].strip()
                return self.send_signalr_message(message)
            elif "send message" in cmd_lower and "via signalr" in cmd_lower:
                message = command.split("send message")[-1].replace("via signalr", "").strip()
                return self.send_signalr_message(message)
            elif "hello signalr" in cmd_lower:
                return self.send_signalr_message("Hello from JARVIS!")
            
            # Handle compound commands with "and"
            if " and " in cmd_lower:
                # Special handling for Google search compounds
                if "open google" in cmd_lower and ("search for" in cmd_lower or "look up" in cmd_lower):
                    search_terms = None
                    if "search for" in cmd_lower:
                        search_terms = cmd_lower.split("search for")[-1].strip()
                    elif "look up" in cmd_lower:
                        search_terms = cmd_lower.split("look up")[-1].strip()
                    
                    if search_terms:
                        return self.search_web(search_terms)
                    else:
                        return self.open_application("google")
                
                # Handle other compound commands
                commands = cmd_lower.split(" and ")
                responses = []
                for cmd in commands:
                    response = await self.process_command(cmd.strip())
                    responses.append(response)
                return " And ".join(responses)

            # Enhanced write to Notepad command
            if "write" in cmd_lower and ("notepad" in cmd_lower or "note" in cmd_lower):
                # Check for filename specification
                filename = None
                if "as" in cmd_lower:
                    # Extract filename after "as"
                    parts = command.split(" as ")
                    if len(parts) > 1:
                        filename = parts[1].strip()
                        command = parts[0]  # Remove filename part from command
                
                # Extract the text to write
                text_to_write = command.split("write")[-1].replace("in notepad", "").replace("to notepad", "").strip()
                if text_to_write:
                    return self.write_to_notepad(text_to_write, filename)
                else:
                    return "Please specify what you'd like me to write in Notepad."
            
            # Save current notepad command
            elif "save" in cmd_lower and ("notepad" in cmd_lower or "note" in cmd_lower):
                if "as" in cmd_lower:
                    filename = command.split("as")[-1].strip()
                    return f"To save the current note, please use the Ctrl+S shortcut in Notepad and save it as {filename}"
                return "To save the current note, please use the Ctrl+S shortcut in Notepad"
            
            # Enhanced open and search commands
            elif "open" in cmd_lower:
                # Special handling for "command prompt as admin"
                if "command prompt as admin" in cmd_lower:
                    return self.open_application("command prompt as admin")
                # Special handling for Google with search
                elif "google" in cmd_lower:
                    # Check for search terms after "google"
                    search_terms = None
                    if "search for" in cmd_lower:
                        search_terms = command.split("search for")[-1].strip()
                    elif "look up" in cmd_lower:
                        search_terms = command.split("look up")[-1].strip()
                    elif "for" in cmd_lower:
                        search_terms = command.split("for")[-1].strip()
                    
                    if search_terms:
                        # Remove any "and" prefix if it exists
                        search_terms = search_terms.lstrip("and").strip()
                        return self.search_web(search_terms)
                    else:
                        return self.open_application("google")
                else:
                    app_name = cmd_lower.replace("open ", "").strip()
                    return self.open_application(app_name)
            
            # Web search commands
            elif "search for" in cmd_lower or "look up" in cmd_lower:
                if "search for" in cmd_lower:
                    query = command.split("search for")[-1].strip()
                else:
                    query = command.split("look up")[-1].strip()
                # Remove any "and" prefix if it exists
                query = query.lstrip("and").strip()
                return self.search_web(query)
            
            # Execute Command Prompt command
            elif "command prompt" in cmd_lower and "run" in cmd_lower:
                # Extract the command to run
                cmd_to_run = command.split("run")[-1].strip()
                if cmd_to_run:
                    return self.execute_cmd_command(cmd_to_run)
                else:
                    return "Please specify the command you'd like me to run in Command Prompt."
            
            # System information
            elif "system status" in cmd_lower or "system info" in cmd_lower:
                return self.get_system_info()
            
            # Weather information
            elif "weather" in cmd_lower and "in" in cmd_lower:
                city = command.split("in")[-1].strip()
                return self.get_weather(city)
            
            # Time information
            elif "what time" in cmd_lower or "current time" in cmd_lower:
                return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}"
            
            # For general queries, use OpenAI
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are JARVIS, a sophisticated AI assistant. Keep responses concise and helpful."},
                    {"role": "user", "content": command}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I encountered an error: {e}"

    def listen(self):
        """Listen for voice input using microphone with enhanced recognition"""
        with sr.Microphone() as source:
            print("\nListening...")
            
            # Initial adjustment for ambient noise
            self.adjust_for_ambient_noise(source)
            
            try:
                # Record audio with adjusted parameters
                audio = self.recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=15  # Maximum seconds for a phrase
                )
                
                print("Processing your speech...")
                
                # Try multiple recognition attempts with different APIs
                try:
                    # First try Google's recognizer
                    text = self.recognizer.recognize_google(audio, language="en-US")
                    print("Recognized text:", text)
                    return text
                except sr.UnknownValueError:
                    # If Google fails, try other recognizers
                    try:
                        # Try Google Cloud Speech (if credentials are set up)
                        text = self.recognizer.recognize_google_cloud(audio, language="en-US")
                        return text
                    except (sr.UnknownValueError, sr.RequestError):
                        try:
                            # Try Sphinx for offline recognition
                            text = self.recognizer.recognize_sphinx(audio)
                            return text
                        except:
                            return "Could not understand audio"
                            
            except sr.WaitTimeoutError:
                return "No speech detected"
            except sr.RequestError as e:
                return f"Could not request results; {e}"

    def calibrate_microphone(self):
        """Calibrate microphone for optimal recognition"""
        print("Starting microphone calibration...")
        print("Please remain quiet for a moment...")
        
        with sr.Microphone() as source:
            # Extended ambient noise adjustment
            self.adjust_for_ambient_noise(source, duration=2)
            
            print("\nCalibration complete!")
            print(f"Energy threshold set to {self.recognizer.energy_threshold}")
            print("Now try speaking...")

    def check_for_interruption(self):
        """Check for audio input while Jarvis is speaking using direct audio monitoring"""
        try:
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"Audio input status: {status}")
                # Calculate audio energy level
                volume_norm = np.linalg.norm(indata) / np.sqrt(frames)
                if volume_norm > self.interrupt_threshold:
                    print(f"Interruption detected! (Level: {volume_norm:.2f})")
                    self.interrupt_event.set()
                    return

            # Start monitoring audio input
            with sd.InputStream(callback=audio_callback,
                              channels=1,
                              samplerate=24000,
                              blocksize=1024,
                              dtype=np.float32) as stream:
                while self.is_speaking and not self.interrupt_event.is_set():
                    sd.sleep(10)  # Shorter sleep interval for faster response

        except Exception as e:
            print(f"Error in interruption detection: {e}")
            return False

    def play_audio(self, data, samplerate):
        """Play audio in a separate thread"""
        try:
            self.is_speaking = True
            
            # Convert data to float32 (required by sounddevice)
            data = data.astype(np.float32)
            
            # Calculate buffer size for smaller chunks
            chunk_size = int(samplerate * 0.1)  # 100ms chunks
            chunks = np.array_split(data, max(1, len(data) // chunk_size))
            
            # Create output stream
            with sd.OutputStream(samplerate=samplerate, channels=1, dtype=np.float32) as stream:
                stream.start()
                
                for chunk in chunks:
                    if self.interrupt_event.is_set():
                        break
                    
                    stream.write(chunk)
                    # Small sleep to allow interruption checking
                    time.sleep(0.01)
                
                stream.stop()
                if self.interrupt_event.is_set():
                    print("Speech interrupted")
            
            self.is_speaking = False
            self.interrupt_event.clear()
        except Exception as e:
            print(f"Error in audio playback: {e}")
            self.is_speaking = False
            self.interrupt_event.clear()

    async def speak(self, text):
        """Convert text to speech using ElevenLabs with interruption support"""
        try:
            # If already speaking, queue the new text
            if self.is_speaking:
                self.audio_queue.put(text)
                return

            # Clear any previous interrupt event
            self.interrupt_event.clear()

            if not self.elevenlabs_api_key:
                print("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY in your environment variables.")
                return

            if not self.elevenlabs_voice_id:
                print("ElevenLabs Voice ID not found. Please set ELEVENLABS_VOICE_ID in your environment variables.")
                return

            try:
                # Generate audio using ElevenLabs with cloned voice
                audio = generate(
                    text=text,
                    voice=self.elevenlabs_voice_id,
                    model="eleven_monolingual_v1",
                    api_key=self.elevenlabs_api_key
                )
                
                # Convert audio data to numpy array
                with io.BytesIO(audio) as audio_buffer:
                    data, samplerate = sf.read(audio_buffer)
                
                # Start interruption checker in a separate thread
                interrupt_thread = threading.Thread(target=self.check_for_interruption)
                interrupt_thread.daemon = True
                interrupt_thread.start()
                
                # Play audio in a separate thread
                self.speech_thread = threading.Thread(target=self.play_audio, args=(data, samplerate))
                self.speech_thread.daemon = True
                self.speech_thread.start()
                
                # Wait for speech to finish or be interrupted
                while self.speech_thread.is_alive():
                    if self.interrupt_event.is_set():
                        # Clear the audio queue when interrupted
                        with self.audio_queue.mutex:
                            self.audio_queue.queue.clear()
                        break
                    await asyncio.sleep(0.05)
                
                # Wait for thread to fully clean up
                self.speech_thread.join(timeout=1.0)
                
                # Only process queue if not interrupted
                if not self.interrupt_event.is_set():
                    while not self.audio_queue.empty():
                        next_text = self.audio_queue.get()
                        if self.interrupt_event.is_set():
                            break
                        await self.speak(next_text)
                
            except Exception as e:
                print(f"Error generating speech with ElevenLabs: {e}")
                print("Falling back to OpenAI TTS...")
                # Fallback to OpenAI TTS
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text,
                    response_format="mp3",
                    speed=0.95
                )
                
                # Convert response to audio data
                audio_data = io.BytesIO(response.content)
                data, samplerate = sf.read(audio_data)
                
                # Continue with normal playback...
                interrupt_thread = threading.Thread(target=self.check_for_interruption)
                interrupt_thread.daemon = True
                interrupt_thread.start()
                
                self.speech_thread = threading.Thread(target=self.play_audio, args=(data, samplerate))
                self.speech_thread.daemon = True
                self.speech_thread.start()
                
                while self.speech_thread.is_alive():
                    if self.interrupt_event.is_set():
                        with self.audio_queue.mutex:
                            self.audio_queue.queue.clear()
                        break
                    await asyncio.sleep(0.05)
            
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            print(f"Response: {text}")
            self.is_speaking = False
            self.interrupt_event.clear()

    def start_background_listening(self):
        """Start continuous background listening"""
        self.background_listening = True
        self.listen_thread = threading.Thread(target=self._background_listener)
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def stop_background_listening(self):
        """Stop background listening"""
        self.background_listening = False
        if self.listen_thread:
            self.listen_thread.join()

    def _background_listener(self):
        """Continuous background listening function"""
        with sr.Microphone() as source:
            # Initial calibration
            print("Calibrating microphone for background listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while self.background_listening:
                try:
                    print("\nListening...")
                    # Listen for audio with longer timeout and phrase limit
                    audio = self.recognizer.listen(
                        source,
                        timeout=2,
                        phrase_time_limit=15,
                    )
                    
                    try:
                        # Process audio in background
                        text = self.recognizer.recognize_google(audio, language="en-US")
                        current_time = time.time()
                        
                        # If speaking, treat as interruption
                        if self.is_speaking:
                            print("Interruption detected through speech!")
                            self.interrupt_event.set()
                            continue
                            
                        # Check if this is part of an ongoing command
                        if current_time - self.last_phrase_time < self.command_timeout:
                            # Get the previous incomplete command if it exists
                            try:
                                previous_text = self.command_queue.get_nowait()
                                text = f"{previous_text} {text}"
                            except queue.Empty:
                                pass
                        
                        print("Recognized:", text)
                        self.last_phrase_time = current_time
                        
                        # Wait briefly to see if there's more to the command
                        await_more = True
                        wait_start = time.time()
                        while await_more and time.time() - wait_start < self.command_timeout:
                            try:
                                # Try to detect more speech
                                more_audio = self.recognizer.listen(
                                    source,
                                    timeout=1,
                                    phrase_time_limit=5
                                )
                                more_text = self.recognizer.recognize_google(more_audio, language="en-US")
                                text = f"{text} {more_text}"
                                print("Additional input:", more_text)
                                wait_start = time.time()  # Reset wait time for more potential speech
                            except (sr.WaitTimeoutError, sr.UnknownValueError):
                                await_more = False
                            except Exception:
                                await_more = False
                        
                        # Only queue the command if it seems complete
                        if len(text.split()) >= 2:  # Ensure command has at least 2 words
                            print("Final command:", text)
                            self.command_queue.put(text)
                        else:
                            print("Command too short, waiting for more input...")
                            self.command_queue.put(text)  # Store it for potential continuation
                            
                    except sr.UnknownValueError:
                        # Ignore unrecognized audio
                        continue
                    except sr.RequestError as e:
                        print(f"Could not request results; {e}")
                        continue
                        
                except sr.WaitTimeoutError:
                    # Timeout is normal, continue listening
                    continue
                except Exception as e:
                    print(f"Error in background listening: {e}")
                    continue

    async def run(self):
        """Main loop for JARVIS"""
        # Start background listening
        self.start_background_listening()
        
        await self.speak("Hello, I am JARVIS. How may I assist you?")
        
        while True:
            try:
                # Check for commands in the queue
                try:
                    command = self.command_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.1)  # Short sleep if no command
                    continue
                
                if command.lower() in ["exit", "quit", "goodbye"]:
                    await self.speak("Goodbye!")
                    break
                    
                print(f"Command: {command}")
                response = await self.process_command(command)
                print(f"Response: {response}")
                
                # Only speak if not interrupted
                if not self.interrupt_event.is_set():
                    await self.speak(response)
                    
            except Exception as e:
                print(f"Error in main loop: {e}")
                continue
        
        # Clean up
        self.stop_background_listening()

async def main():
    jarvis = Jarvis()
    await jarvis.run()

if __name__ == "__main__":
    asyncio.run(main()) 