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
from elevenlabs import generate, play

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

        # Dictionary mapping common app names to their process names or paths
        self.app_commands = {
            "chrome": {
                "command": "chrome",
                "paths": [
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                ]
            },
            "firefox": {
                "command": "firefox",
                "paths": [
                    "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                    "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
                ]
            },
            "edge": {
                "command": "msedge",
                "paths": [
                    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
                ]
            },
            "store": {
                "command": "explorer.exe",
                "args": ["shell:AppsFolder\\Microsoft.WindowsStore_8wekyb3d8bbwe!App"]
            },
            "windows store": {
                "command": "explorer.exe",
                "args": ["shell:AppsFolder\\Microsoft.WindowsStore_8wekyb3d8bbwe!App"]
            },
            "app store": {
                "command": "explorer.exe",
                "args": ["shell:AppsFolder\\Microsoft.WindowsStore_8wekyb3d8bbwe!App"]
            },
            "microsoft store": {
                "command": "explorer.exe",
                "args": ["shell:AppsFolder\\Microsoft.WindowsStore_8wekyb3d8bbwe!App"]
            },
            "notepad": "notepad.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "command prompt": {
                "command": "cmd.exe",
                "args": []
            },
            "command prompt as admin": {
                "command": "cmd.exe",
                "args": ["/c", "start", "cmd.exe", "/k", "cd /d %userprofile%"],
                "admin": True
            }
        }

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
        """Open common applications with enhanced handling and thorough system search"""
        try:
            if self.system_info == "Windows":
                app_key = app_name.lower()
                
                # First check if it's a known application
                if app_key in self.app_commands:
                    app_info = self.app_commands[app_key]
                    
                    if isinstance(app_info, str):
                        try:
                            subprocess.Popen([app_info])
                            return f"I'm opening {app_name} for you now."
                        except FileNotFoundError:
                            return f"I found {app_name} in my known applications list, but I couldn't locate it on your system. Let me try searching for it."
                    else:
                        # Try specific paths first
                        if "paths" in app_info:
                            for path in app_info["paths"]:
                                if os.path.exists(path):
                                    try:
                                        subprocess.Popen([path] + app_info.get("args", []))
                                        return f"I'm opening {app_name} for you now."
                                    except Exception as e:
                                        print(f"Failed to open {path}: {e}")
                                        continue
                        
                        # Try command directly
                        try:
                            subprocess.Popen([app_info["command"]] + app_info.get("args", []))
                            return f"I'm opening {app_name} for you now."
                        except FileNotFoundError:
                            return f"I found {app_name} in my known applications list, but I couldn't locate it. Let me try searching your system."

                # If we get here, either the app wasn't in known list or the known paths failed
                searching_message = f"I'm searching your system for {app_name}. This might take a moment."
                print(searching_message)

                # Additional system paths to search
                system_paths = [
                    os.environ.get('SYSTEMROOT', 'C:\\Windows'),
                    os.path.join(os.environ.get('SYSTEMROOT', 'C:\\Windows'), 'System32'),
                    os.path.join(os.environ.get('SYSTEMROOT', 'C:\\Windows'), 'SysWOW64')
                ]
                
                # User-specific paths
                user_paths = [
                    os.path.expanduser('~'),
                    os.path.join(os.path.expanduser('~'), 'Desktop'),
                    os.path.join(os.path.expanduser('~'), 'Documents'),
                    os.path.join(os.path.expanduser('~'), 'Downloads')
                ]
                
                # Program installation paths
                program_paths = [
                    os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                    os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
                    os.environ.get('LOCALAPPDATA', ''),
                    os.environ.get('APPDATA', ''),
                    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
                    os.path.join(os.environ.get('APPDATA', ''), 'Programs'),
                    'C:\\Program Files\\WindowsApps',  # Windows Store apps
                    'C:\\Users\\Public'
                ]
                
                # Add all drive letters
                import string
                drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
                
                # Possible file extensions to search for
                extensions = [
                    '.exe', '.lnk', '.bat', '.cmd', '.msc',  # Executables and shortcuts
                    '.txt', '.doc', '.docx', '.pdf',         # Documents
                    '.xls', '.xlsx', '.ppt', '.pptx',        # Office files
                    '.jpg', '.jpeg', '.png', '.gif',         # Images
                    '.mp3', '.mp4', '.avi', '.mkv'          # Media files
                ]
                
                # Generate possible filenames
                possible_names = [
                    app_key,
                    f"{app_key}launcher",
                    f"{app_key}-launcher",
                    f"launch{app_key}",
                    f"start{app_key}",
                    f"{app_key}start"
                ]
                
                # Search in Windows Start Menu
                start_menu_paths = [
                    os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'Microsoft\\Windows\\Start Menu\\Programs'),
                    os.path.join(os.environ.get('APPDATA', ''), 'Microsoft\\Windows\\Start Menu\\Programs')
                ]
                
                # Function to search in a directory
                def search_directory(directory, max_depth=5):
                    if not os.path.exists(directory) or max_depth <= 0:
                        return None
                        
                    try:
                        for root, dirs, files in os.walk(directory):
                            # Skip certain system directories
                            if any(skip in root.lower() for skip in ['$recycle.bin', 'system volume information', 'windows.old']):
                                continue
                                
                            # Check current depth
                            depth = root[len(directory):].count(os.sep)
                            if depth > max_depth:
                                continue
                            
                            # Search for exact matches first
                            for name in possible_names:
                                for ext in extensions:
                                    filename = name + ext
                                    if filename.lower() in [f.lower() for f in files]:
                                        actual_file = next(f for f in files if f.lower() == filename.lower())
                                        return os.path.join(root, actual_file)
                            
                            # Then search for partial matches
                            for file in files:
                                if any(name in file.lower() for name in possible_names):
                                    return os.path.join(root, file)
                    except Exception as e:
                        print(f"Error searching {directory}: {e}")
                    return None
                
                # Search in all paths
                all_paths = (
                    start_menu_paths +  # Start Menu first (fastest)
                    system_paths +      # Then system paths
                    program_paths +     # Then program paths
                    user_paths +        # Then user paths
                    drives             # Finally, all drives (slowest)
                )
                
                # Try each path
                for path in all_paths:
                    if not path or not os.path.exists(path):
                        continue
                        
                    result = search_directory(path, max_depth=3 if path in drives else 5)
                    if result:
                        try:
                            if result.lower().endswith('.lnk'):
                                # Resolve shortcut
                                import pythoncom
                                from win32com.shell import shell
                                pythoncom.CoInitialize()
                                shortcut = pythoncom.CoCreateInstance(
                                    shell.CLSID_ShellLink,
                                    None,
                                    pythoncom.CLSCTX_INPROC_SERVER,
                                    shell.IID_IShellLink
                                )
                                shortcut.QueryInterface(pythoncom.IID_IPersistFile).Load(result)
                                result = shortcut.GetPath()[0]
                            
                            subprocess.Popen([result])
                            return f"I found and opened {app_name} from {result}"
                        except Exception as e:
                            return f"I found {app_name} at {result}, but encountered an error while trying to open it: {str(e)}"
                
                return f"I apologize, but I couldn't find {app_name} anywhere on your PC. Please verify that it's installed and try again."
            else:
                return "I apologize, but application opening is only supported on Windows systems for now."
        except Exception as e:
            print(f"Error opening application: {e}")
            return f"I encountered an error while trying to open {app_name}: {str(e)}"

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

    async def process_command(self, command):
        """Process voice commands and generate responses with enhanced command recognition"""
        try:
            # Store the command in lowercase for easier matching
            cmd_lower = command.lower()
            
            # Check for stop command first
            if cmd_lower.strip() == "stop":
                if self.is_speaking:
                    self.interrupt_event.set()
                    return "Stopping current speech..."
                return "I wasn't speaking, but I'm ready for your next command."
            
            # First, check for specific task commands
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

            # For recipe requests that need to be written to Notepad
            if ("recipe" in cmd_lower or "how to make" in cmd_lower) and any(phrase in cmd_lower for phrase in ["notepad", "note"]):
                # Extract the recipe name
                recipe_name = None
                if "recipe" in cmd_lower:
                    recipe_name = cmd_lower.split("recipe")[-1].split("in notepad")[0].split("to notepad")[0].split("on notepad")[0].strip()
                elif "how to make" in cmd_lower:
                    recipe_name = cmd_lower.split("how to make")[-1].split("in notepad")[0].split("to notepad")[0].split("on notepad")[0].strip()
                
                if recipe_name:
                    # Generate recipe using GPT
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are JARVIS, a culinary expert. Provide detailed yet concise recipes with ingredients and step-by-step instructions."},
                            {"role": "user", "content": f"Provide a recipe for {recipe_name}"}
                        ]
                    )
                    
                    # Store the response and write it to notepad
                    self.last_response = response.choices[0].message.content
                    return self.write_to_notepad(self.last_response)
                    
            # For general queries that need to be written to Notepad
            elif any(phrase in cmd_lower for phrase in ["write in notepad", "write to notepad", "write on notepad", "write the"]) and "notepad" in cmd_lower:
                # Extract the content to write
                content = command
                for phrase in ["write in notepad", "write to notepad", "write on notepad", "write the"]:
                    if content.lower().startswith(phrase):
                        content = content[len(phrase):].strip()
                
                content = content.split("in notepad")[0].split("to notepad")[0].split("on notepad")[0].strip()
                
                if not content:
                    return "Please specify what you'd like me to write in Notepad."
                
                # Generate content using GPT
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are JARVIS, a sophisticated AI assistant. Provide detailed and accurate information."},
                        {"role": "user", "content": content}
                    ]
                )
                
                # Store the response and write it to notepad
                self.last_response = response.choices[0].message.content
                return self.write_to_notepad(self.last_response)
            
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
            response = client.chat.completions.create(
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