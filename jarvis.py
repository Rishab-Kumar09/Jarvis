import speech_recognition as sr
import json
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
from elevenlabs import generate, play
import sys
import openai
import win32com.client
import pyttsx3
from pathlib import Path
import asyncio

# Load environment variables
load_dotenv()

# Initialize OpenAI client with API key from environment variable
openai_client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

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
        
        # Add note tracking
        self.note_counter = 1
        self.notes_dir = os.path.join(os.path.expanduser('~'), 'Documents')
        
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

        # Add memory for active notes and last response
        self.active_notepad = None  # Store the active notepad process
        self.active_note_path = None  # Store the path of the active note
        self.last_response = None  # Store the last response from GPT or other commands

        # Initialize app commands with common paths
        self.app_commands = {
            "chrome": {
                "command": "chrome.exe",
                "paths": [
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                ]
            },
            "firefox": {
                "command": "firefox.exe",
                "paths": [
                    "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                    "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
                ]
            },
            "edge": {
                "command": "msedge.exe",
                "paths": [
                    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
                ]
            },
            "word": {
                "command": "winword.exe",
                "paths": [
                    "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office16\\WINWORD.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office16\\WINWORD.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office15\\WINWORD.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office15\\WINWORD.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office14\\WINWORD.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office14\\WINWORD.EXE"
                ]
            },
            "excel": {
                "command": "excel.exe",
                "paths": [
                    "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office16\\EXCEL.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office16\\EXCEL.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office15\\EXCEL.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office15\\EXCEL.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office14\\EXCEL.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office14\\EXCEL.EXE"
                ]
            },
            "powerpoint": {
                "command": "powerpnt.exe",
                "paths": [
                    "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office16\\POWERPNT.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office16\\POWERPNT.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office15\\POWERPNT.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office15\\POWERPNT.EXE",
                    "C:\\Program Files\\Microsoft Office\\Office14\\POWERPNT.EXE",
                    "C:\\Program Files (x86)\\Microsoft Office\\Office14\\POWERPNT.EXE"
                ]
            },
            "notepad": {
                "command": "notepad.exe",
                "paths": [
                    "C:\\Windows\\System32\\notepad.exe",
                    "C:\\Windows\\notepad.exe"
                ]
            },
            "calculator": {
                "command": "calc.exe",
                "paths": [
                    "C:\\Windows\\System32\\calc.exe"
                ]
            },
            "paint": {
                "command": "mspaint.exe",
                "paths": [
                    "C:\\Windows\\System32\\mspaint.exe"
                ]
            },
            "cmd": {
                "command": "cmd.exe",
                "paths": [
                    "C:\\Windows\\System32\\cmd.exe"
                ],
                "admin": True
            },
            "store": {
                "command": "explorer.exe",
                "args": ["shell:AppsFolder\\Microsoft.WindowsStore_8wekyb3d8bbwe!App"],
                "paths": [
                    "C:\\Windows\\explorer.exe"
                ]
            }
        }

        # Add context tracking
        self.last_question = None
        self.last_content = None
        self.waiting_for_response = False

        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        
        # Set properties for the voice
        self.engine.setProperty('rate', 150)    # Speed of speech
        self.engine.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)
        
        # Get available voices and set to a British male voice if available
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if "british" in voice.name.lower() and "male" in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

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

    def generate_note_filename(self, text, filename=None):
        """Generate a human-readable filename for the note"""
        if filename:
            # Use the specified filename
            if not filename.lower().endswith('.txt'):
                filename += '.txt'
            return filename
            
        # Try to generate a filename from the first few words of the text
        words = text.split()
        if len(words) > 0:
            # Take first 4 words and clean them
            title_words = words[:4]
            title = '_'.join(word.lower() for word in title_words if word.isalnum())
            if title:
                return f"jarvis_{title}.txt"
        
        # Fallback to numbered note if text is not suitable for filename
        existing_notes = [f for f in os.listdir(self.notes_dir) 
                         if f.startswith('jarvis_note') and f.endswith('.txt')]
        self.note_counter = len(existing_notes) + 1
        return f"jarvis_note{self.note_counter}.txt"

    def write_to_notepad(self, text, filename=None, append=False):
        """Write text to notepad with improved filename generation and append support"""
        try:
            if self.system_info == "Windows":
                if append and self.active_note_path:
                    file_path = self.active_note_path
                else:
                    # Generate an appropriate filename
                    filename = self.generate_note_filename(text, filename)
                    file_path = os.path.join(self.notes_dir, filename)
                    
                    # Create Documents directory if it doesn't exist
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Write or append the file
                mode = 'a' if append else 'w'
                with open(file_path, mode, encoding='utf-8') as f:
                    if append:
                        f.write('\n\n' + text)  # Add double newline for separation
                    else:
                        f.write(text)
                
                # If there's an active Notepad process, close it before opening the new one
                if self.active_notepad:
                    try:
                        self.active_notepad.terminate()
                    except:
                        pass
                
                # Open the file in Notepad
                self.active_notepad = subprocess.Popen(['notepad.exe', file_path])
                self.active_note_path = file_path
                
                if append:
                    return f"Text has been appended to {file_path}"
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
        """
        Opens an application using predefined paths or system search.
        Returns a message indicating success or failure.
        """
        app_key = app_name.lower()
        
        # Check if it's a known application
        if app_key in self.app_commands:
            app_info = self.app_commands[app_key]
            
            # Try each predefined path
            for path in app_info["paths"]:
                if os.path.exists(path):
                    try:
                        if app_info.get("args"):
                            subprocess.Popen([path] + app_info["args"])
                        elif app_info.get("admin", False):
                            subprocess.Popen(["runas", "/user:Administrator", path])
                        else:
                            subprocess.Popen(path)
                        return f"Opening {app_name} for you now."
                    except Exception as e:
                        return f"Found {app_name} at {path}, but encountered an error while trying to open it: {str(e)}"
            
            # If none of the predefined paths work, try searching
            return f"I found {app_name} in my known applications list, but I couldn't locate it on your system. Let me try searching for it."
        
        # For unknown applications, search the system
        return f"I'll search your system for {app_name}. This might take a moment."

    def close_application(self, app_name):
        """Close specified application with enhanced process handling"""
        try:
            if self.system_info == "Windows":
                # Dictionary mapping common app names to their process names
                app_processes = {
                    "notepad": ["notepad.exe"],
                    "chrome": ["chrome.exe"],
                    "firefox": ["firefox.exe"],
                    "word": ["winword.exe"],
                    "excel": ["excel.exe"],
                    "powerpoint": ["powerpnt.exe"],
                    "calculator": ["calc.exe"],
                    "edge": ["msedge.exe"],
                    "vlc": ["vlc.exe"],
                    "spotify": ["spotify.exe"],
                    "discord": ["discord.exe"],
                    "skype": ["skype.exe"],
                    "teams": ["teams.exe"],
                    "vscode": ["code.exe"],
                    "paint": ["mspaint.exe"],
                    "explorer": ["explorer.exe"],
                    "cmd": ["cmd.exe"],
                    "command prompt": ["cmd.exe"],
                    "terminal": ["cmd.exe", "windowsterminal.exe"],
                }

                app_key = app_name.lower()
                process_names = app_processes.get(app_key)

                if not process_names:
                    # Try to use the app name directly as a process name
                    if app_key.endswith('.exe'):
                        process_names = [app_key]
                    else:
                        process_names = [f"{app_key}.exe"]

                closed_count = 0
                for process_name in process_names:
                    try:
                        # First try to gracefully close processes using psutil
                        for proc in psutil.process_iter(['pid', 'name']):
                            try:
                                if proc.info['name'].lower() == process_name.lower():
                                    # Special handling for Notepad if it's our tracked instance
                                    if process_name.lower() == "notepad.exe" and self.active_notepad and proc.pid == self.active_notepad.pid:
                                        self.active_notepad.terminate()
                                        self.active_notepad = None
                                        self.active_note_path = None
                                    else:
                                        proc.terminate()
                                        proc.wait(timeout=3)  # Wait for the process to terminate
                                    closed_count += 1
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                                continue

                        # If no processes were closed gracefully, try force closing
                        if closed_count == 0:
                            result = os.system(f'taskkill /F /IM "{process_name}"')
                            if result == 0:  # Command executed successfully
                                closed_count += 1

                    except Exception as e:
                        print(f"Error closing {process_name}: {e}")
                        continue

                if closed_count > 0:
                    return f"Closed {closed_count} instance(s) of {app_name}"
                else:
                    return f"No running instances of {app_name} were found"
            else:
                return "Application closing is only supported on Windows for now."
        except Exception as e:
            return f"Error closing {app_name}: {e}"

    def write_to_word(self, text, filename=None):
        """Write text to a new Word document"""
        try:
            if self.system_info == "Windows":
                # Create a Word application instance
                word = win32com.client.Dispatch('Word.Application')
                word.Visible = True
                
                # Create a new document
                doc = word.Documents.Add()
                
                # Add the text
                doc.Content.Text = text
                
                # Save the document if filename is provided
                if filename:
                    if not filename.lower().endswith('.docx'):
                        filename += '.docx'
                    doc_path = os.path.join(os.path.expanduser('~'), 'Documents', filename)
                else:
                    # Generate filename from content
                    words = text.split()[:4]
                    filename = '_'.join(word.lower() for word in words if word.isalnum()) + '.docx'
                    doc_path = os.path.join(os.path.expanduser('~'), 'Documents', filename)
                
                # Create Documents directory if it doesn't exist
                os.makedirs(os.path.dirname(doc_path), exist_ok=True)
                
                # Save the document
                doc.SaveAs(doc_path)
                return f"Content has been written to Word document: {filename}"
            else:
                return "Word document creation is only supported on Windows for now."
        except Exception as e:
            return f"Error writing to Word: {e}"

    async def process_command(self, command):
        """Process voice commands and generate responses with enhanced command recognition"""
        try:
            # Store the command in lowercase for easier matching
            cmd_lower = command.lower()
            
            # Check for responses to previous questions
            if self.waiting_for_response and self.last_question:
                if any(word in cmd_lower for word in ["yes", "yeah", "sure", "okay", "please", "yep", "yup"]):
                    self.waiting_for_response = False
                    if "read" in self.last_question.lower():
                        # Read the last content
                        if self.last_content:
                            await self.speak(self.last_content)
                            return "I hope that was helpful. Is there anything else you'd like me to do?"
                    return "I'm not sure what you'd like me to do. Could you please repeat your request?"
                elif any(word in cmd_lower for word in ["no", "nope", "nah", "don't", "skip"]):
                    self.waiting_for_response = False
                    return "Alright, is there anything else you'd like me to do?"
            
            # Reset context if it's a new command
            self.waiting_for_response = False
            self.last_question = None
            
            # Check for stop command first
            if cmd_lower.strip() == "stop":
                if self.is_speaking:
                    self.interrupt_event.set()
                    return "Stopping current speech..."
                return "I wasn't speaking, but I'm ready for your next command."
            
            # First, check for specific task commands
            if " and " in cmd_lower:
                # Special handling for Word document creation
                if ("create" in cmd_lower and "word" in cmd_lower and "write" in cmd_lower) or \
                   ("open word" in cmd_lower and "write" in cmd_lower):
                    # Extract the content to write
                    content = None
                    if "recipe" in cmd_lower or "how to make" in cmd_lower:
                        # Extract recipe name
                        recipe_name = None
                        if "recipe" in cmd_lower:
                            recipe_name = cmd_lower.split("recipe")[-1].strip()
                            recipe_name = recipe_name.replace("to make", "").replace("for", "").strip()
                        elif "how to make" in cmd_lower:
                            recipe_name = cmd_lower.split("how to make")[-1].strip()
                        
                        if recipe_name:
                            # Generate recipe using GPT
                            response = openai_client.chat.completions.create(
                                model="gpt-4",
                                messages=[
                                    {"role": "system", "content": """You are JARVIS, a culinary expert. When providing recipes:
                                    1. Start with a brief introduction
                                    2. List all ingredients with measurements
                                    3. Provide clear step-by-step instructions
                                    4. Add any helpful tips or variations
                                    5. Keep it concise but detailed enough to follow"""},
                                    {"role": "user", "content": f"Provide a recipe for {recipe_name}"}
                                ]
                            )
                            content = response.choices[0].message.content
                    
                    if content:
                        # Generate filename from recipe name
                        filename = f"Recipe_{recipe_name.replace(' ', '_')}.docx"
                        result = self.write_to_word(content, filename)
                        self.last_content = content
                        self.last_question = "Would you like me to read it to you?"
                        self.waiting_for_response = True
                        return f"{result} Would you like me to read it to you?"
                
                # Handle other compound commands
                commands = cmd_lower.split(" and ")
                responses = []
                for cmd in commands:
                    response = await self.process_command(cmd.strip())
                    responses.append(response)
                return " And ".join(responses)

            # For recipe requests that need to be written to Notepad
            elif any(word in cmd_lower for word in ["recipe", "how to make", "how do i make", "how do you make"]):
                # Extract the recipe name
                recipe_name = None
                if "recipe" in cmd_lower:
                    recipe_name = cmd_lower.split("recipe")[-1].strip()
                    # Remove "to make" or "for" if present
                    recipe_name = recipe_name.replace("to make", "").replace("for", "").strip()
                elif "how to make" in cmd_lower:
                    recipe_name = cmd_lower.split("how to make")[-1].strip()
                elif "how do i make" in cmd_lower:
                    recipe_name = cmd_lower.split("how do i make")[-1].strip()
                elif "how do you make" in cmd_lower:
                    recipe_name = cmd_lower.split("how do you make")[-1].strip()
                
                # Clean up the recipe name by removing notepad references and articles
                for phrase in ["in notepad", "to notepad", "on notepad", "in a note", "to a note", "on a note", "the", "a", "an"]:
                    if recipe_name and (recipe_name.lower().startswith(phrase + " ") or recipe_name.lower().endswith(" " + phrase)):
                        recipe_name = recipe_name.lower().replace(phrase, "").strip()
                
                if recipe_name:
                    # Generate recipe using GPT
                    response = openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": """You are JARVIS, a culinary expert. When providing recipes:
                            1. Start with a brief introduction
                            2. List all ingredients with measurements
                            3. Provide clear step-by-step instructions
                            4. Add any helpful tips or variations
                            5. Keep it concise but detailed enough to follow"""},
                            {"role": "user", "content": f"Provide a recipe for {recipe_name}"}
                        ]
                    )
                    
                    # Store the response
                    recipe_content = response.choices[0].message.content
                    self.last_response = recipe_content
                    self.last_content = recipe_content
                    
                    # Write to notepad and return a confirmation message
                    self.write_to_notepad(recipe_content)
                    self.last_question = "Would you like me to read it to you?"
                    self.waiting_for_response = True
                    return f"I've written the recipe for {recipe_name} to Notepad. Would you like me to read it to you?"
                else:
                    return "Please specify what recipe you'd like me to provide."
                    
            # For general queries that need to be written to Notepad
            elif any(phrase in cmd_lower for phrase in [
                "write in notepad", 
                "write to notepad", 
                "write on notepad", 
                "write the", 
                "write a",
                "write an",
                "open notepad and write",
                "write summary",
                "write the summary",
                "write a summary"
            ]):
                # Extract the content to write
                content = command
                
                # Handle different command patterns
                if content.lower().startswith("open notepad and write"):
                    content = content[len("open notepad and write"):].strip()
                elif content.lower().startswith("write in notepad"):
                    content = content[len("write in notepad"):].strip()
                elif content.lower().startswith("write to notepad"):
                    content = content[len("write to notepad"):].strip()
                elif content.lower().startswith("write on notepad"):
                    content = content[len("write on notepad"):].strip()
                elif content.lower().startswith("write the"):
                    content = content[len("write the"):].strip()
                elif content.lower().startswith("write a"):
                    content = content[len("write a"):].strip()
                elif content.lower().startswith("write an"):
                    content = content[len("write an"):].strip()
                
                # Clean up the content by removing additional notepad references
                for phrase in ["in notepad", "to notepad", "on notepad"]:
                    if content.lower().endswith(phrase):
                        content = content[:-len(phrase)].strip()
                
                if not content:
                    return "Please specify what you'd like me to write in Notepad."
                
                # Generate content using GPT if needed
                if any(word in content.lower() for word in ["summary", "summarize", "summarization"]):
                    # Extract what needs to be summarized
                    summary_topic = content
                    # Remove common phrases
                    phrases_to_remove = [
                        "summary of",
                        "summarize",
                        "write",
                        "the",
                        "a",
                        "an",
                        "summary",
                        "about",
                        "for",
                        "me",
                        "please"
                    ]
                    for phrase in phrases_to_remove:
                        summary_topic = summary_topic.lower().replace(phrase, "").strip()
                    
                    # If the summary topic is empty after cleaning, return error
                    if not summary_topic:
                        return "Please specify what you'd like me to summarize."
                    
                    response = openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": """You are JARVIS, an expert at summarizing content. When summarizing books or topics:
                            1. Start with a brief overview
                            2. List key points and main ideas
                            3. Include important lessons or takeaways
                            4. Provide relevant examples or quotes
                            5. End with a conclusion or final thoughts"""},
                            {"role": "user", "content": f"Provide a detailed summary of {summary_topic}"}
                        ]
                    )
                    
                    # Store the response
                    summary_content = response.choices[0].message.content
                    self.last_response = summary_content
                    self.last_content = summary_content
                    
                    # Write to notepad and return a confirmation message
                    self.write_to_notepad(summary_content)
                    self.last_question = "Would you like me to read it to you?"
                    self.waiting_for_response = True
                    return f"I've written the summary of {summary_topic} to Notepad. Would you like me to read it to you?"
                else:
                    # For direct text, write it to notepad
                    self.write_to_notepad(content)
                    return f"I've written your text to Notepad. Would you like me to read it back to you?"
                
            # Handle requests to write last response to notepad
            elif ("write" in cmd_lower or "save" in cmd_lower) and any(word in cmd_lower for word in ["it", "that", "this", "response", "recipe"]) and any(phrase in cmd_lower for phrase in ["notepad", "note"]):
                if self.last_response:
                    return self.write_to_notepad(self.last_response)
                else:
                    return "I don't have any previous response to write to Notepad."
                    
            # Enhanced write to Notepad command
            elif ("write" in cmd_lower or "append" in cmd_lower) and ("notepad" in cmd_lower or "note" in cmd_lower):
                # Check if we should append
                append = "append" in cmd_lower or "add" in cmd_lower
                
                # Check for filename specification
                filename = None
                if "as" in cmd_lower:
                    parts = command.split(" as ")
                    if len(parts) > 1:
                        filename = parts[1].strip()
                        command = parts[0]
                
                # Extract the text to write
                text_to_write = command
                
                # Remove the write/append command from the beginning
                if text_to_write.lower().startswith("write"):
                    text_to_write = text_to_write[5:].strip()
                elif text_to_write.lower().startswith("append"):
                    text_to_write = text_to_write[6:].strip()
                elif text_to_write.lower().startswith("in the notepad append"):
                    text_to_write = text_to_write[19:].strip()
                elif text_to_write.lower().startswith("in notepad append"):
                    text_to_write = text_to_write[16:].strip()
                
                # Remove notepad/note phrases from the end
                phrases_to_remove = [
                    " in notepad",
                    " to notepad",
                    " on notepad",
                    " in a note",
                    " to a note",
                    " on a note",
                    " in the notepad",
                    " to the notepad",
                    " on the notepad",
                    " append to notepad",
                    " add to notepad"
                ]
                
                for phrase in phrases_to_remove:
                    if text_to_write.lower().endswith(phrase):
                        text_to_write = text_to_write[:-len(phrase)].strip()
                
                if text_to_write:
                    return self.write_to_notepad(text_to_write.strip(), filename, append)
                else:
                    return "Please specify what you'd like me to write in Notepad."
            
            # Save last response to notepad
            elif ("save" in cmd_lower or "write" in cmd_lower) and "last" in cmd_lower and self.last_response:
                filename = None
                if "as" in cmd_lower:
                    filename = command.split("as")[-1].strip()
                return self.write_to_notepad(self.last_response, filename)
            
            # Close application command
            elif "close" in cmd_lower:
                app_name = cmd_lower.replace("close", "").strip()
                if app_name:
                    return self.close_application(app_name)
                return "Please specify which application to close."
            
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
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are JARVIS, a sophisticated AI assistant. Keep responses concise and helpful."},
                    {"role": "user", "content": command}
                ]
            )
            
            # Store the response for potential later use
            self.last_response = response.choices[0].message.content
            return self.last_response
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
                response = openai_client.audio.speech.create(
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
                        
                        # Special handling for "stop" command
                        if text.lower().strip() == "stop":
                            print("Stop command detected!")
                            if self.is_speaking:
                                self.interrupt_event.set()
                                self.command_queue.put(text)
                            continue
                        
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
                
                # Always speak the response, even if it's an error message
                # Only skip speaking if we were interrupted
                if not self.interrupt_event.is_set():
                    # For empty or None responses, provide a default message
                    if not response or response.strip() == "":
                        response = "I apologize, but I couldn't process that command properly. Could you please try again?"
                    await self.speak(response)
                    
            except Exception as e:
                error_message = f"I encountered an error: {str(e)}"
                print(error_message)
                if not self.interrupt_event.is_set():
                    await self.speak(error_message)
                continue
        
        # Clean up
        self.stop_background_listening()

async def main():
    jarvis = Jarvis()
    await jarvis.run()

if __name__ == "__main__":
    asyncio.run(main()) 