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
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import base64
from email.mime.text import MIMEText
import pytz
import re
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import base64
from email.mime.text import MIMEText
import pytz
import re
from datetime import datetime, timedelta

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
        
        # Initialize text-to-speech engine with faster rate
        self.engine = pyttsx3.init()
        
        # Set properties for the voice - increased rate for faster speech
        self.engine.setProperty('rate', 450)    # Significantly faster rate (default was 150)
        self.engine.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)
        
        # Get available voices and set to a British male voice if available
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if "british" in voice.name.lower() and "male" in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

        # Initialize GmailManager
        self.gmail_manager = GmailManager()

        # Voice settings optimized for JARVIS clone with faster rate
        self.voice_settings = {
            "stability": 0.53,
            "similarity_boost": 0.85,
            "style": 0.0,
            "use_speaker_boost": True,
            "speed": 2.0  # Increased speed for faster response
        }

        # Add memory for active notes and last response
        self.active_notepad = None  # Store the active notepad process
        self.active_note_path = None  # Store the path of the active note
        self.last_response = None  # Store the last response from GPT or other commands

        # Email state tracking
        self.email_to = None
        self.email_subject = None
        self.email_body = None

        # List of responses to ignore to prevent feedback loops
        self.ignore_phrases = [
            "searching the web for",
            "i apologize",
            "could you please",
            "alright, what else",
            "i encountered an error",
            "i'm not sure how to help",
            "here are your unread emails"
        ]

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
        """Process voice commands with context awareness"""
        try:
            cmd_lower = command.lower()
            response = None

            # Global exit command should be checked first
            if not self.waiting_for_response and cmd_lower in ["quit", "goodbye", "shut down", "terminate"]:
                await self.speak("Goodbye!")
                sys.exit(0)

            # Exit command for any interaction mode
            if self.waiting_for_response and any(phrase in cmd_lower for phrase in [
                "exit", "cancel", "go back", "never mind", "stop this", "leave it", 
                "forget it", "skip it", "leave this", "get out", "done with this"
            ]):
                self.waiting_for_response = False
                self.last_question = None
                self.last_content = None
                return "Alright, what else can I help you with?"

            # Handle notepad writing commands
            if ("write" in cmd_lower or "create" in cmd_lower) and ("notepad" in cmd_lower or "note" in cmd_lower):
                # Check if this is a recipe request
                if "recipe" in cmd_lower:
                    # Extract what recipe to write
                    recipe_item = None
                    if "recipe" in cmd_lower:
                        # Split by "recipe" and look for what comes after
                        parts = cmd_lower.split("recipe", 1)
                        if len(parts) > 1:
                            recipe_text = parts[1].strip()
                            # Remove common phrases
                            recipe_text = recipe_text.replace("for", "").replace("to make", "").replace("of", "").replace("a", "").strip()
                            if recipe_text:
                                recipe_item = recipe_text
                    
                    if recipe_item:
                        # Generate recipe using OpenAI
                        try:
                            response = openai_client.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "system", "content": "You are a helpful cooking assistant. Provide recipes in a clear, step-by-step format."},
                                    {"role": "user", "content": f"Write a simple recipe for {recipe_item}. Include ingredients list and step-by-step instructions."}
                                ]
                            )
                            recipe = response.choices[0].message.content
                            return self.write_to_notepad(recipe)
                        except Exception as e:
                            return f"Error generating recipe: {str(e)}"
                    return "What recipe would you like me to write?"
                
                # Handle regular writing commands
                text_to_write = None
                if "write" in cmd_lower:
                    # Split by "write" and take everything after it
                    parts = cmd_lower.split("write", 1)
                    if len(parts) > 1:
                        text_to_write = parts[1].strip()
                        # Remove "in notepad", "to notepad", etc.
                        text_to_write = text_to_write.replace("in notepad", "").replace("to notepad", "").replace("in the notepad", "").replace("to the notepad", "").strip()
                
                if text_to_write:
                    return self.write_to_notepad(text_to_write)
                return "What would you like me to write in the notepad?"

            # Handle web search commands
            if any(phrase in cmd_lower for phrase in ["search for", "look up", "google", "find", "search"]):
                search_query = cmd_lower
                for phrase in ["search for", "look up", "google", "find", "search"]:
                    search_query = search_query.replace(phrase, "").strip()
                if search_query:
                    return self.search_web(search_query)
                return "What would you like me to search for?"

            # Email commands with more flexible matching
            if any(word in cmd_lower for word in ["check", "show", "get", "read", "open"]) and any(word in cmd_lower for word in ["email", "gmail", "mail", "inbox", "message"]):
                # Check for specific sender
                sender_name = None
                if "from" in cmd_lower:
                    # Extract name after "from"
                    words = cmd_lower.split("from")
                    if len(words) > 1:
                        sender_name = words[1].strip()

                emails = self.gmail_manager.get_unread_emails()
                if isinstance(emails, list):
                    if not emails:
                        return "You have no unread emails."
                    
                    # Filter by sender if specified
                    if sender_name:
                        filtered_emails = [
                            email for email in emails 
                            if sender_name.lower() in email['sender'].lower()
                        ]
                        if not filtered_emails:
                            return f"No unread emails found from {sender_name}."
                        emails = filtered_emails

                    # Store full response for display
                    display_response = "Here are your unread emails:\n\n"
                    for i, email in enumerate(emails, 1):
                        display_response += f"{i}. From: {email['sender']}\nSubject: {email['subject']}\nDate: {email['date']}\n"
                        if i < len(emails):
                            display_response += "\n"

                    # Create speech response without numbers
                    speech_response = "Here are your unread emails. "
                    for email in emails:
                        speech_response += f"From {email['sender']}, Subject: {email['subject']}, Received {email['date']}. "
                    
                    self.last_content = display_response
                    self.last_question = "read_email"
                    self.waiting_for_response = True
                    
                    # First return the display response, then speak and ask about reading
                    response = display_response + "\nWhich email would you like me to read? Just say the number (1-5) or 'leave it' to cancel."
                    asyncio.create_task(self.speak(speech_response + " Which email would you like me to read? Just say the number between 1 and 5, or say leave it to cancel."))
                    return response
                return emails

            # Handle email expansion request with more flexible matching
            if (self.waiting_for_response and self.last_question == "read_email") or \
               any(phrase in cmd_lower for phrase in ["expand email", "show email", "read email", "open email", "last email"]):
                try:
                    # Extract email number from various command formats
                    email_num = None
                    
                    # First check for direct numbers in the command
                    cmd_lower = cmd_lower.strip()
                    if cmd_lower.isdigit():
                        email_num = int(cmd_lower)
                    else:
                        # Check for "last email" command
                        if "last" in cmd_lower or "previous" in cmd_lower:
                            email_num = 1  # First email is the latest
                        else:
                            # Handle ordinal numbers
                            ordinal_map = {
                                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                                "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
                                "last": 1, "latest": 1
                            }
                            
                            # Check for ordinal words
                            for ordinal, num in ordinal_map.items():
                                if ordinal in cmd_lower:
                                    email_num = num
                                    break
                            
                            # If no ordinal found, try other patterns
                            if email_num is None:
                                words = cmd_lower.split()
                                for i, word in enumerate(words):
                                    # Check for direct numbers
                                    if word.isdigit():
                                        email_num = int(word)
                                        break
                                    # Check for number after keywords
                                    elif i < len(words) - 1 and word in ["number", "email", "message", "#", "no", "no.", "num", "num."]:
                                        if words[i + 1].isdigit():
                                            email_num = int(words[i + 1])
                                            break
                    
                    if email_num is None:
                        return "Which email would you like me to read? Please specify the number or say 'leave it' to cancel."
                    
                    emails = self.gmail_manager.get_unread_emails()
                    if isinstance(emails, list) and 1 <= email_num <= len(emails):
                        email = emails[email_num - 1]
                        # Store full response for display
                        display_response = f"Here's email {email_num}:\n\n"
                        display_response += f"From: {email['sender']}\n"
                        display_response += f"Subject: {email['subject']}\n"
                        display_response += f"Date: {email['date']}\n\n"
                        display_response += f"Content:\n{email['body']}\n\n"
                        display_response += "Would you like to reply to this email?"

                        # Create speech response without the email number and content
                        speech_response = f"Here's the email from {email['sender']} about {email['subject']}. Would you like to reply to this email?"
                        
                        self.last_content = display_response
                        self.last_question = "Would you like to reply to this email?"
                        self.waiting_for_response = True
                        
                        # First return the display response, then speak
                        response = display_response
                        asyncio.create_task(self.speak(speech_response))
                        return response
                    return "Invalid email number. Please try again or say 'leave it' to cancel."
                except Exception as e:
                    return f"Error processing email request: {str(e)}"

            # Handle email reply with more flexible matching
            if self.waiting_for_response and self.last_question and "reply" in self.last_question.lower():
                if any(word in cmd_lower for word in ["yes", "yeah", "sure", "okay", "yep", "please", "go ahead"]):
                    self.last_question = "What would you like to say in your reply?"
                    # Don't repeat the email content, just ask for the reply
                    speech_response = "What would you like to say in your reply?"
                    asyncio.create_task(self.speak(speech_response))
                    return "What would you like to say in your reply? Or say 'leave it' to cancel."
                elif any(word in cmd_lower for word in ["no", "nope", "nah", "don't", "skip", "cancel", "leave it"]):
                    self.waiting_for_response = False
                    self.last_question = None
                    return "Okay, is there anything else you'd like me to do?"

            # Handle reply confirmation
            if self.waiting_for_response and self.last_question == "confirm_reply":
                if any(word in cmd_lower for word in ["yes", "yeah", "sure", "okay", "yep", "send", "go ahead"]):
                    # Extract the reply text from last_content
                    reply_text = self.last_content.split("I'll send the following reply:\n\n")[1].split("\n\nShould I send this reply?")[0]
                    emails = self.gmail_manager.get_unread_emails()
                    if isinstance(emails, list) and emails:
                        result = self.gmail_manager.reply_to_email(emails[0]['id'], reply_text)
                        self.waiting_for_response = False
                        self.last_question = None
                        self.last_content = None
                        return result
                    return "Sorry, I couldn't find the email to reply to."
                elif any(word in cmd_lower for word in ["no", "nope", "nah", "modify", "change", "edit"]):
                    self.last_question = "What would you like to say in your reply?"
                    return "What would you like to say in your reply? Or say 'leave it' to cancel."
                elif any(word in cmd_lower for word in ["leave it", "cancel", "exit", "never mind", "stop"]):
                    self.waiting_for_response = False
                    self.last_question = None
                    self.last_content = None
                    return "Okay, I won't send the reply. Is there anything else you'd like me to do?"

            # Send new email command
            if any(phrase in cmd_lower for phrase in ["send email", "compose email", "write email", "new email"]):
                if self.waiting_for_response and self.last_question == "send_email_to":
                    # Got recipient
                    self.email_to = cmd_lower
                    self.last_question = "send_email_subject"
                    return "What should be the subject of the email?"
                elif self.waiting_for_response and self.last_question == "send_email_subject":
                    # Got subject
                    self.email_subject = cmd_lower
                    self.last_question = "send_email_body"
                    return "What would you like to say in the email?"
                elif self.waiting_for_response and self.last_question == "send_email_body":
                    # Got body, confirm before sending
                    self.email_body = cmd_lower
                    self.last_content = f"I'll send the following email:\n\nTo: {self.email_to}\nSubject: {self.email_subject}\nBody: {self.email_body}\n\nShould I send this email?"
                    self.last_question = "confirm_send_email"
                    return self.last_content
                elif self.waiting_for_response and self.last_question == "confirm_send_email":
                    if any(word in cmd_lower for word in ["yes", "yeah", "sure", "okay", "yep", "send", "go ahead"]):
                        result = self.gmail_manager.send_email(self.email_to, self.email_subject, self.email_body)
                        self.waiting_for_response = False
                        self.last_question = None
                        self.last_content = None
                        self.email_to = None
                        self.email_subject = None
                        self.email_body = None
                        return result
                    elif any(word in cmd_lower for word in ["no", "nope", "nah", "modify", "change", "edit"]):
                        self.last_question = "send_email_to"
                        return "Let's start over. Who would you like to send the email to?"
                    else:
                        self.waiting_for_response = False
                        self.last_question = None
                        self.last_content = None
                        self.email_to = None
                        self.email_subject = None
                        self.email_body = None
                        return "Okay, I won't send the email. Is there anything else you'd like me to do?"
                else:
                    # Start new email process
                    self.waiting_for_response = True
                    self.last_question = "send_email_to"
                    return "Who would you like to send the email to?"

            # Calendar commands
            if "calendar" in cmd_lower:
                if "check" in cmd_lower or "show" in cmd_lower or "list" in cmd_lower:
                    events = self.gmail_manager.get_calendar_events()
                    if isinstance(events, list):
                        if not events:
                            return "You have no upcoming events."
                        
                        response = "Here are your upcoming events:\n\n"
                        for i, event in enumerate(events, 1):
                            response += f"{i}. {event['summary']}\n"
                            response += f"   When: {event['start']} to {event['end']}\n"
                            if event['location']:
                                response += f"   Where: {event['location']}\n"
                            if event['attendees']:
                                response += f"   Attendees: {', '.join(event['attendees'])}\n"
                            if i < len(events):
                                response += "\n"
                        return response
                    return events

                elif "respond" in cmd_lower or "accept" in cmd_lower or "decline" in cmd_lower:
                    # Extract event number and response type
                    response_type = "accepted" if "accept" in cmd_lower else "declined" if "decline" in cmd_lower else None
                    if not response_type:
                        return "Would you like to accept or decline the event?"

                    events = self.gmail_manager.get_calendar_events()
                    if isinstance(events, list) and events:
                        result = self.gmail_manager.respond_to_calendar_invite(events[0]['id'], response_type)
                        return result
                    return "Sorry, I couldn't find the calendar invite to respond to."

            # Handle other commands
            if "weather" in cmd_lower:
                # Extract city name after "weather in" or "weather for"
                city = None
                if "weather in" in cmd_lower:
                    city = cmd_lower.split("weather in")[1].strip()
                elif "weather for" in cmd_lower:
                    city = cmd_lower.split("weather for")[1].strip()
                
                if city:
                    return self.get_weather(city)
                return "Which city would you like to check the weather for?"

            if "system info" in cmd_lower or "system status" in cmd_lower:
                return self.get_system_info()

            if "note" in cmd_lower:
                if "new note" in cmd_lower:
                    self.waiting_for_response = True
                    self.last_question = "What would you like to write in the note?"
                    return "What would you like me to write in the note?"
                elif self.waiting_for_response and self.last_question and "note" in self.last_question:
                    return self.write_to_notepad(cmd_lower)

            # Application commands
            if "open" in cmd_lower:
                app_name = cmd_lower.replace("open", "").strip()
                if app_name:
                    return self.open_application(app_name)
                return "Which application would you like me to open?"

            if "close" in cmd_lower:
                app_name = cmd_lower.replace("close", "").strip()
                if app_name:
                    return self.close_application(app_name)
                return "Which application would you like me to close?"

            # If no specific command matched
            return "I'm not sure how to help with that. Could you please rephrase your request?"

        except Exception as e:
            return f"I encountered an error: {str(e)}"

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

            # Set speaking flag at the start
            self.is_speaking = True
            
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
                    await asyncio.sleep(0.01)  # Reduced sleep time
                
                # Wait for thread to fully clean up
                self.speech_thread.join(timeout=0.5)  # Reduced timeout
                
                # Add a small delay after speaking to prevent self-listening
                self.is_speaking = True  # Keep speaking flag on briefly
                await asyncio.sleep(0.2)  # Small delay after speech
                self.is_speaking = False
                
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
        finally:
            # Always ensure speaking flag is cleared
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
            print("\nListening...")  # Print only once at start
            
            while self.background_listening:
                try:
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
                        
                        # Ignore any input while JARVIS is speaking
                        if self.is_speaking:
                            print("Ignoring input while speaking...")
                            continue
                            
                        # Ignore JARVIS's own responses
                        text_lower = text.lower()
                        if any(phrase in text_lower for phrase in self.ignore_phrases):
                            print("Ignoring JARVIS response:", text)
                            continue
                            
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
                        
                        # Process single-word commands like numbers
                        text = text.lower().strip()
                        # Convert word numbers to digits
                        number_map = {
                            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
                            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'
                        }
                        if text in number_map:
                            text = number_map[text]
                        
                        # Handle single-word commands
                        if text.isdigit() or text in ['first', 'second', 'third', 'fourth', 'fifth']:
                            print("Final command:", text)
                            self.command_queue.put(text)
                        # Handle other commands that need at least 2 words
                        elif len(text.split()) >= 2 or self.waiting_for_response:  # Allow single words during response waiting
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
                    print("\nListening...")  # Print after processing command
                    
            except Exception as e:
                error_message = f"I encountered an error: {str(e)}"
                print(error_message)
                if not self.interrupt_event.is_set():
                    await self.speak(error_message)
                print("\nListening...")  # Print after error
                continue
        
        # Clean up
        self.stop_background_listening()

class GmailManager:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.modify',
                      'https://www.googleapis.com/auth/gmail.send',
                      'https://www.googleapis.com/auth/calendar']
        self.creds = None
        self.gmail_service = None
        self.calendar_service = None
        self.initialize_services()

    def initialize_services(self):
        """Initialize Gmail and Calendar services"""
        # Load credentials from token.pickle
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)

        # If credentials are invalid or don't exist, refresh or create them
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        # Build services
        self.gmail_service = build('gmail', 'v1', credentials=self.creds)
        self.calendar_service = build('calendar', 'v3', credentials=self.creds)

    def get_unread_emails(self, max_results=5):
        """Get unread emails from inbox with human-readable time format (default: 5 emails)"""
        try:
            results = self.gmail_service.users().messages().list(
                userId='me',
                labelIds=['INBOX', 'UNREAD'],
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for message in messages:
                msg = self.gmail_service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()

                headers = msg['payload']['headers']
                subject = next(h['value'] for h in headers if h['name'] == 'Subject')
                sender = next(h['value'] for h in headers if h['name'] == 'From')
                date_str = next(h['value'] for h in headers if h['name'] == 'Date')

                # Convert email date to human-readable format
                try:
                    # Parse the email date
                    email_date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                    # Convert to local time
                    local_date = email_date.astimezone()
                    # Format date in a human-friendly way
                    if local_date.date() == datetime.now().date():
                        date = f"Today at {local_date.strftime('%I:%M %p')}"
                    elif local_date.date() == (datetime.now() - timedelta(days=1)).date():
                        date = f"Yesterday at {local_date.strftime('%I:%M %p')}"
                    else:
                        date = local_date.strftime('%B %d at %I:%M %p')
                except:
                    date = date_str  # Fallback to original date if parsing fails

                # Clean up sender name for speech
                if '<' in sender:
                    sender = sender.split('<')[0].strip()
                    if sender.endswith('"'):
                        sender = sender[:-1]
                    if sender.startswith('"'):
                        sender = sender[1:]

                # Get email body
                if 'parts' in msg['payload']:
                    parts = msg['payload']['parts']
                    data = parts[0]['body'].get('data', '')
                else:
                    data = msg['payload']['body'].get('data', '')

                if data:
                    text = base64.urlsafe_b64decode(data).decode('utf-8')
                    # Clean up the body text for speech
                    text = text.replace('\r\n', ' ').replace('\n', ' ')
                    # Remove URLs and email addresses for cleaner speech
                    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 'link', text)
                    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', 'email address', text)
                else:
                    text = "No content"

                emails.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'snippet': msg['snippet'],
                    'body': text
                })

            return emails

        except Exception as e:
            return f"Error fetching emails: {str(e)}"

    def send_email(self, to, subject, body):
        """Send an email"""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            return "Email sent successfully!"
        except Exception as e:
            return f"Error sending email: {str(e)}"

    def reply_to_email(self, email_id, reply_text):
        """Reply to a specific email"""
        try:
            # Get the original message to extract thread ID and references
            original = self.gmail_service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()

            # Create reply message
            headers = original['payload']['headers']
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            if not subject.startswith('Re:'):
                subject = f"Re: {subject}"

            # Get the sender's email address
            from_header = next(h['value'] for h in headers if h['name'] == 'From')
            to_email = from_header.split('<')[-1].strip('>')

            message = MIMEText(reply_text)
            message['to'] = to_email
            message['subject'] = subject
            message['In-Reply-To'] = email_id
            message['References'] = email_id

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            return "Reply sent successfully!"
        except Exception as e:
            return f"Error sending reply: {str(e)}"

    def get_calendar_events(self, days=7):
        """Get upcoming calendar events with human-readable time format"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            end_date = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'

            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end_date,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            formatted_events = []

            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Convert to local timezone and human-readable format
                if 'T' in start:  # This indicates it's a datetime
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    local_tz = pytz.timezone('America/New_York')
                    start_local = start_dt.astimezone(local_tz)
                    end_local = end_dt.astimezone(local_tz)

                    # Format dates in a human-friendly way
                    if start_local.date() == datetime.now().date():
                        start_str = f"Today at {start_local.strftime('%I:%M %p')}"
                        end_str = f"until {end_local.strftime('%I:%M %p')}"
                    elif start_local.date() == (datetime.now() + timedelta(days=1)).date():
                        start_str = f"Tomorrow at {start_local.strftime('%I:%M %p')}"
                        end_str = f"until {end_local.strftime('%I:%M %p')}"
                    else:
                        start_str = start_local.strftime('%B %d at %I:%M %p')
                        end_str = f"until {end_local.strftime('%I:%M %p')}"
                else:
                    # All-day event
                    start_dt = datetime.strptime(start, '%Y-%m-%d')
                    if start_dt.date() == datetime.now().date():
                        start_str = "Today"
                    elif start_dt.date() == (datetime.now() + timedelta(days=1)).date():
                        start_str = "Tomorrow"
                    else:
                        start_str = start_dt.strftime('%B %d')
                    end_str = "(all day)"

                formatted_events.append({
                    'summary': event['summary'],
                    'start': start_str,
                    'end': end_str,
                    'location': event.get('location', ''),
                    'attendees': [
                        attendee.get('email', '').split('@')[0]
                        for attendee in event.get('attendees', [])
                    ] if event.get('attendees') else []
                })

            return formatted_events
        except Exception as e:
            return f"Error fetching calendar events: {str(e)}"

    def create_calendar_event(self, summary, start_time, end_time, description=None, location=None, attendees=None):
        """Create a new calendar event"""
        try:
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'America/New_York',
                }
            }

            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            event = self.calendar_service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'
            ).execute()

            return f"Event created successfully: {event.get('htmlLink')}"
        except Exception as e:
            return f"Error creating calendar event: {str(e)}"

    def respond_to_calendar_invite(self, event_id, response='accepted'):
        """Respond to a calendar invite"""
        try:
            # Get the event
            event = self.calendar_service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()

            # Find the attendee that matches the authenticated user
            for attendee in event.get('attendees', []):
                if attendee.get('self'):
                    attendee['responseStatus'] = response
                    break

            # Update the event
            updated_event = self.calendar_service.events().patch(
                calendarId='primary',
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()

            return f"Successfully {response} the calendar invite."
        except Exception as e:
            return f"Error responding to calendar invite: {str(e)}"

async def main():
    jarvis = Jarvis()
    await jarvis.run()

if __name__ == "__main__":
    asyncio.run(main()) 