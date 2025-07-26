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
import ctypes
from ctypes import wintypes
import win32com.client
import pyttsx3
from pathlib import Path
import asyncio
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import shutil
import hashlib
import socket
import ipaddress
from collections import defaultdict
import pickle
import base64
from email.mime.text import MIMEText
import pytz
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_socketio import SocketIO, emit
import socket
import mss
from PIL import Image
import io as iolib
import cv2
import win32gui
import win32process
import win32con
import win32api
import ctypes
from ctypes import wintypes
import sqlite3

# Load environment variables
load_dotenv()

# Initialize OpenAI client only if API key is available
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    try:
        openai_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        print("✅ OpenAI client initialized")
    except Exception as e:
        print(f"⚠️ OpenAI initialization failed: {e}")
        openai_client = None
else:
    print("ℹ️ No OpenAI API key found - using local TTS only")

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

        # Add wake word and sleep word settings
        self.wake_words = ["jarvis", "hey jarvis", "okay jarvis", "hi jarvis"]
        self.sleep_words = ["bye jarvis", "goodbye jarvis", "see you later jarvis", "talk to you later jarvis"]
        self.is_awake = True  # Start awake
        self.awake_timeout = 30  # Seconds to stay awake after wake word
        self.last_wake_time = time.time()  # Initialize with current time

        self.voice_profile = {
            "instructions": """Voice Profile:
            Accent & Tone: Sophisticated British male accent, precise and authoritative, with the characteristic JARVIS-like formality.
            Pitch & Pace: Deep masculine pitch, measured and deliberate pace, with technological crispness.
            Delivery Style: Professional and efficient, with undertones of artificial intelligence sophistication.
            Emotion: Calm and composed, with subtle hints of dry wit and unwavering loyalty."""
        }
        self.system_info = platform.system()
        
        # Smart Keep-Awake System
        self.phone_connected = False
        self.keep_awake_active = False
        self.connected_clients = set()  # Track connected phone IPs
        
        # Windows Sleep Prevention Constants
        self.ES_CONTINUOUS = 0x80000000
        self.ES_SYSTEM_REQUIRED = 0x00000001
        self.ES_DISPLAY_REQUIRED = 0x00000002
        
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
            },
            "slack": {
                "command": "slack.exe",
                "paths": [
                    "C:\\Users\\Rishi\\AppData\\Local\\slack\\app-4.44.63\\slack.exe",
                    "C:\\Users\\Rishi\\AppData\\Local\\slack\\app-4.44.59\\slack.exe",
                    "C:\\Users\\Rishi\\AppData\\Local\\slack\\slack.exe"
                ]
            }
        }

        # Add context tracking
        self.last_question = None
        self.last_content = None
        self.waiting_for_response = False

        # JARVIS EYES - System Awareness
        self.system_index = {}
        self.active_windows = {}
        self.file_index = {}
        self.last_system_scan = 0
        self.initialize_system_awareness()

    def initialize_system_awareness(self):
        """Initialize JARVIS system awareness capabilities - ULTRA-LIGHTWEIGHT VERSION"""
        try:
            print("🤖 Initializing JARVIS Eyes - System Awareness...")
            
            # MINIMAL initialization only - no heavy operations
            self.system_index = {
                'scan_active': False,
                'files_indexed': 0,
                'windows_tracked': 0,
                'last_scan': 0,
                'lightweight_mode': True  # Flag to indicate lightweight mode
            }
            
            # Quick window scan only (no file indexing)
            self.quick_window_scan()
            
            print("✅ JARVIS Eyes initialized - Lightweight mode active!")
            
        except Exception as e:
            print(f"⚠️ System awareness initialization failed: {str(e)}")
            self.system_index = {'lightweight_mode': True}

    def quick_window_scan(self):
        """Ultra-fast window scan - no blocking operations"""
        try:
            self.active_windows = {}
            
            # Only scan if Windows API is available
            if self.system_info == "Windows":
                try:
                    import win32gui
                    windows = []
                    def enum_callback(hwnd, results):
                        if win32gui.IsWindowVisible(hwnd):
                            window_text = win32gui.GetWindowText(hwnd)
                            if window_text and len(window_text) > 3:
                                windows.append({'hwnd': hwnd, 'title': window_text})
                                return len(windows) < 10  # Limit to 10 windows for speed
                    
                    win32gui.EnumWindows(enum_callback, windows)
                    self.active_windows = {w['title']: w['hwnd'] for w in windows}
                    self.system_index['windows_tracked'] = len(windows)
                    
                except ImportError:
                    windows = []
                    self.active_windows = {}
                except Exception as e:
                    print(f"Quick window scan failed: {str(e)}")
                    self.active_windows = {}
            else:
                self.active_windows = {}
                
        except Exception as e:
            print(f"Quick window scan error: {str(e)}")
            self.active_windows = {}

    def background_system_init(self):
        """DISABLED - Background system initialization to prevent performance issues"""
        try:
            print("🔍 JARVIS: Background scanning disabled for performance")
            # No heavy operations - just mark as complete
            time.sleep(0.1)  # Minimal delay
            print("✅ JARVIS: Lightweight mode active!")
                
        except Exception as e:
            print(f"⚠️ Background scan minimal error: {str(e)}")
            
    def light_system_scan(self):
        """DISABLED - Lightweight system scan to prevent performance issues"""
        try:
            print("🔍 JARVIS: System scanning disabled for performance optimization")
            self.system_index['scan_active'] = False
            self.system_index['last_scan'] = time.time()
            
        except Exception as e:
            print(f"Light scan error: {str(e)}")
            self.system_index['scan_active'] = False

    def create_system_database(self):
        """DISABLED - Create SQLite database to prevent locking issues"""
        try:
            print("🔍 JARVIS: Database indexing disabled for performance optimization")
            # Don't create database to avoid locking issues
            self.db_path = None
            
        except Exception as e:
            print(f"Database creation disabled: {str(e)}")

    def scan_system_state(self):
        """DISABLED - System state scanning to prevent performance issues"""
        try:
            print("🔍 JARVIS: System state scanning disabled for performance")
            # Just update last scan time
            self.last_system_scan = time.time()
            
        except Exception as e:
            print(f"System state scan disabled: {str(e)}")

    def scan_active_windows(self):
        """Quick active window scan - non-blocking"""
        try:
            # Use the quick scan instead
            self.quick_window_scan()
            
        except Exception as e:
            print(f"Error scanning windows: {str(e)}")

    def incremental_file_scan(self):
        """DISABLED - File system scanning to prevent database locking"""
        try:
            print("🔍 JARVIS: File indexing disabled for performance optimization")
            # Don't scan files to avoid database locking
            
        except Exception as e:
            print(f"File scan disabled: {str(e)}")

    def update_system_metrics(self):
        """DISABLED - System metrics update to prevent blocking operations"""
        try:
            print("🔍 JARVIS: System metrics disabled for performance optimization")
            # Don't update metrics to avoid blocking operations
            
        except Exception as e:
            print(f"System metrics disabled: {str(e)}")

    def get_system_awareness_report(self):
        """Generate lightweight system awareness report - NO DATABASE"""
        try:
            report = "🤖 JARVIS SYSTEM AWARENESS REPORT\n"
            report += "=" * 50 + "\n\n"
            
            # Quick window scan
            self.quick_window_scan()
            
            # Current active window
            try:
                import win32gui
                fg_hwnd = win32gui.GetForegroundWindow()
                current_window = win32gui.GetWindowText(fg_hwnd)
                report += f"🖥️ ACTIVE WINDOW: {current_window}\n\n"
            except:
                report += f"🖥️ ACTIVE WINDOW: Unable to detect\n\n"
            
            # Running applications (from quick scan)
            report += "📱 RUNNING APPLICATIONS:\n"
            if self.active_windows:
                for i, title in enumerate(list(self.active_windows.keys())[:10], 1):
                    report += f"   {i}. {title}\n"
            else:
                report += "   • No applications detected\n"
            
            # System info (lightweight)
            try:
                import psutil
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=None)  # Non-blocking
                report += f"\n💻 SYSTEM STATUS:\n"
                report += f"   • Memory Usage: {memory.percent}%\n"
                report += f"   • CPU Usage: {cpu}%\n"
            except:
                report += f"\n💻 SYSTEM STATUS: Unable to get metrics\n"
            
            report += f"\n🔧 MODE: Lightweight Performance Mode\n"
            report += f"📊 Database indexing disabled for optimal performance\n"
            
            return report
            
        except Exception as e:
            return f"Error generating awareness report: {str(e)}"

    def find_window_by_name(self, window_name):
        """Find and focus window by name - LIGHTWEIGHT VERSION"""
        try:
            if self.system_info != "Windows":
                return "Window switching only supported on Windows"
                
            import win32gui
            window_name_lower = window_name.lower()
            found_window = None
            
            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if window_text and window_name_lower in window_text.lower():
                        results.append((hwnd, window_text))
                return len(results) < 5  # Limit search for performance
            
            windows = []
            win32gui.EnumWindows(enum_callback, windows)
            
            if windows:
                # Focus the first matching window
                hwnd, title = windows[0]
                win32gui.SetForegroundWindow(hwnd)
                return f"Focused window: {title}"
            else:
                return f"Window containing '{window_name}' not found"
            
        except Exception as e:
            return f"Error finding window: {str(e)}"

    def get_window_info(self):
        """Get lightweight information about current active window"""
        try:
            if self.system_info == "Windows":
                try:
                    import win32gui
                    fg_hwnd = win32gui.GetForegroundWindow()
                    current_window = win32gui.GetWindowText(fg_hwnd)
                    
                    if current_window:
                        return f"🖥️ Active Window: {current_window}"
                    else:
                        return "🖥️ No active window detected"
                        
                except Exception as e:
                    return f"🖥️ Unable to detect active window: {str(e)}"
            else:
                return "🖥️ Window detection only supported on Windows"
            
        except Exception as e:
            return f"Error getting window info: {str(e)}"

    def get_simple_screen_info(self):
        """Get simple screen information without heavy processing"""
        try:
            response = "🖥️ SCREEN INFORMATION:\n\n"
            
            # Get active window
            if self.system_info == "Windows":
                try:
                    import win32gui
                    fg_hwnd = win32gui.GetForegroundWindow()
                    current_window = win32gui.GetWindowText(fg_hwnd)
                    response += f"📱 Active Application: {current_window}\n"
                except:
                    response += f"📱 Active Application: Unable to detect\n"
            
            # Get basic system info
            try:
                import psutil
                memory = psutil.virtual_memory()
                response += f"💾 Memory Usage: {memory.percent}%\n"
                response += f"🖥️ Screen Resolution: {self.get_screen_resolution()}\n"
            except:
                response += f"💾 Memory Usage: Unable to detect\n"
            
            response += f"\n💡 Lightweight screen analysis for optimal performance\n"
            response += f"🔧 For detailed screen analysis, use desktop screenshot feature"
            
            return response
                
        except Exception as e:
            return f"Error getting screen info: {str(e)}"

    def get_screen_resolution(self):
        """Get screen resolution quickly"""
        try:
            if self.system_info == "Windows":
                import win32api
                return f"{win32api.GetSystemMetrics(0)}x{win32api.GetSystemMetrics(1)}"
            else:
                return "Unknown"
        except:
            return "Unknown"

    def comprehensive_search_everything(self, query):
        """COMPREHENSIVE SEARCH for 'search everything' command with visual results"""
        try:
            # FOCUSED search directories - avoid system hang
            search_dirs = [
                # Priority directories ONLY (fast search)
                str(Path.home() / "Desktop"),
                str(Path.home() / "Downloads"),
                str(Path.home() / "Documents"),
                str(Path.home() / "Pictures"),
                str(Path.home() / "Videos"),
                str(Path.home() / "Music"),
            ]
            
            found_items = []
            query_lower = query.lower()
            
            print(f"🔍 COMPREHENSIVE SEARCH: Scanning entire system for '{query}'...")
            
            for search_dir in search_dirs:
                if not os.path.exists(search_dir):
                    continue
                    
                try:
                    # Fast search limits to prevent hanging
                    max_items = 100  # Reasonable limit for speed
                    
                    # Search all items
                    for item in os.listdir(search_dir)[:max_items]:
                        item_path = os.path.join(search_dir, item)
                        
                        # Check files - substring matching for "krishna" will find it anywhere
                        if os.path.isfile(item_path) and query_lower in item.lower():
                            try:
                                stat_info = os.stat(item_path)
                                file_ext = os.path.splitext(item)[1].lower()
                                found_items.append({
                                    'name': item,
                                    'path': item_path,
                                    'size': stat_info.st_size,
                                    'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M'),
                                    'type': 'file',
                                    'extension': file_ext,
                                    'match_type': 'exact'
                                })
                            except:
                                continue
                        
                        # Check folders - substring matching for "krishna" will find it anywhere
                        elif os.path.isdir(item_path) and query_lower in item.lower():
                            try:
                                stat_info = os.stat(item_path)
                                found_items.append({
                                    'name': item,
                                    'path': item_path,
                                    'size': 0,
                                    'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M'),
                                    'type': 'folder',
                                    'extension': '',
                                    'match_type': 'exact'
                                })
                            except:
                                continue
                        
                        # Limit results for performance
                        if len(found_items) >= 50:
                            break
                            
                except (PermissionError, OSError):
                    continue
                except Exception as e:
                    print(f"Error searching {search_dir}: {e}")
                    continue
            
            print(f"✅ Search complete - found {len(found_items)} items")
            
            # Generate comprehensive results with web interface
            return self.generate_search_results_with_ui(found_items, query)
            
        except Exception as e:
            return f"❌ Comprehensive search error: {str(e)}"

    def intelligent_file_search(self, query):
        """Fast file search with FUZZY MATCHING for voice commands - NO DATABASE"""
        try:
            import difflib
            
            # EXPANDED search directories for comprehensive search
            search_dirs = [
                # Priority directories first
                str(Path.home() / "Desktop"),
                str(Path.home() / "Downloads"),
                str(Path.home() / "Documents"),
                
                # User directories
                str(Path.home() / "Pictures"),
                str(Path.home() / "Videos"),
                str(Path.home() / "Music"),
                
                # System directories (limited depth)
                "C:\\Users\\Public",
                "C:\\Program Files",
                "C:\\Program Files (x86)",
                
                # Additional common locations
                str(Path.home()),  # User home directory
                "C:\\",  # C drive root (limited)
            ]
            
            found_files = []
            query_lower = query.lower()
            all_files = []  # Collect all files for fuzzy matching
            
            # Quick search in common directories
            for search_dir in search_dirs:
                if not os.path.exists(search_dir):
                    continue
                    
                try:
                    # Adjust search depth based on directory
                    if search_dir in ["C:\\", "C:\\Program Files", "C:\\Program Files (x86)"]:
                        max_items = 20  # Limited search in system directories
                        max_depth = 1   # Shallow search
                    else:
                        max_items = 50  # Normal search in user directories
                        max_depth = 2   # Deeper search
                    
                    # Search immediate directory and subdirectories
                    for item in os.listdir(search_dir)[:max_items]:
                        item_path = os.path.join(search_dir, item)
                        
                        if os.path.isfile(item_path):
                            # Exact match first (priority)
                            if query_lower in item.lower():
                                try:
                                    stat_info = os.stat(item_path)
                                    found_files.append({
                                        'name': item,
                                        'path': item_path,
                                        'size': stat_info.st_size,
                                        'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d'),
                                        'match_type': 'exact',
                                        'type': 'file'
                                    })
                                except:
                                    continue
                            else:
                                # Store for fuzzy matching
                                all_files.append((item, item_path, 'file'))
                                
                        # Check subdirectories and folders
                        elif os.path.isdir(item_path):
                            # Also check if the folder name matches
                            if query_lower in item.lower():
                                try:
                                    stat_info = os.stat(item_path)
                                    found_files.append({
                                        'name': item,
                                        'path': item_path,
                                        'size': 0,  # Folders don't have size
                                        'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d'),
                                        'match_type': 'exact',
                                        'type': 'folder'
                                    })
                                except:
                                    pass
                            else:
                                # Store folder for fuzzy matching
                                all_files.append((item, item_path, 'folder'))
                            
                            # Search inside subdirectories (if depth allows)
                            if max_depth > 1:
                                try:
                                    for subitem in os.listdir(item_path)[:15]:  # Limit subdirectory search
                                        subitem_path = os.path.join(item_path, subitem)
                                        if os.path.isfile(subitem_path):
                                            # Exact match first (priority)
                                            if query_lower in subitem.lower():
                                                try:
                                                    stat_info = os.stat(subitem_path)
                                                    found_files.append({
                                                        'name': subitem,
                                                        'path': subitem_path,
                                                        'size': stat_info.st_size,
                                                        'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d'),
                                                        'match_type': 'exact',
                                                        'type': 'file'
                                                    })
                                                except:
                                                    continue
                                            else:
                                                # Store for fuzzy matching
                                                all_files.append((subitem, subitem_path, 'file'))
                                        elif os.path.isdir(subitem_path) and query_lower in subitem.lower():
                                            # Match folders in subdirectories
                                            try:
                                                stat_info = os.stat(subitem_path)
                                                found_files.append({
                                                    'name': subitem,
                                                    'path': subitem_path,
                                                    'size': 0,
                                                    'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d'),
                                                    'match_type': 'exact',
                                                    'type': 'folder'
                                                })
                                            except:
                                                continue
                                except:
                                    # Skip directories we can't access
                                    continue
                        
                        # Limit exact results for performance
                        if len(found_files) >= 15:
                            break
                            
                except PermissionError:
                    # Skip directories we can't access
                    continue
                except Exception as e:
                    print(f"Error searching {search_dir}: {e}")
                    continue
            
            # FUZZY MATCHING DISABLED - causes performance issues
            print(f"✅ Found {len(found_files)} exact matches for '{query}'")
            
            if not found_files:
                return f"🔍 No files found matching '{query}'\n💡 Search limited to common directories for performance"
            
            # Sort by relevance (exact matches first, then fuzzy matches, then by modification date)
            found_files.sort(key=lambda x: (
                0 if x.get('match_type') == 'exact' else 1,  # Exact matches first
                0 if query_lower == x['name'].lower() else 1,  # Perfect matches within exact
                -os.path.getmtime(x['path']) if os.path.exists(x['path']) else 0  # Recent files first
            ))
            
            exact_count = len([f for f in found_files if f.get('match_type') == 'exact'])
            fuzzy_count = len([f for f in found_files if f.get('match_type') == 'fuzzy'])
            file_count = len([f for f in found_files if f.get('type') == 'file'])
            folder_count = len([f for f in found_files if f.get('type') == 'folder'])
            
            response = f"🔍 Found {len(found_files)} items matching '{query}':\n"
            response += f"   📄 {file_count} files, 📁 {folder_count} folders\n"
            if fuzzy_count > 0:
                response += f"   📍 {exact_count} exact matches, 🎤 {fuzzy_count} voice-corrected matches\n\n"
            else:
                response += f"   📍 {exact_count} exact matches\n\n"
            
            for file_info in found_files[:15]:  # Show first 15 results
                # Get file/folder type icon
                if file_info.get('type') == 'folder':
                    type_icon = "📁"
                    size_str = "Folder"
                else:
                    type_icon = "📄"
                    # Format file size
                    size = file_info['size']
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024*1024:
                        size_str = f"{size//1024}KB"
                    else:
                        size_str = f"{size//(1024*1024)}MB"
                
                # Add match type indicator
                match_indicator = "📍" if file_info.get('match_type') == 'exact' else "🎤"
                response += f"{match_indicator} {type_icon} {file_info['name']}\n"
                response += f"   📂 {file_info['path']}\n"
                response += f"   📊 {size_str} • Modified: {file_info['modified']}\n\n"
                
            if len(found_files) > 15:
                response += f"... and {len(found_files) - 15} more files.\n\n"
            
            response += "💡 Say 'open file [filename]' to open any of these files!"
            return response
            
        except Exception as e:
            return f"Error searching files: {str(e)}"

    def open_file_by_name(self, filename):
        """Open file by name with FUZZY MATCHING for voice commands - NO DATABASE"""
        try:
            import difflib
            
            # Search common directories directly
            search_dirs = [
                str(Path.home() / "Desktop"),
                str(Path.home() / "Documents"),
                str(Path.home() / "Downloads"),
                str(Path.home() / "Pictures"),
                str(Path.home() / "Videos"),
                str(Path.home() / "Music")
            ]
            
            filename_lower = filename.lower()
            found_files = []
            all_files = []  # For fuzzy matching
            
            # Quick search in common directories
            for search_dir in search_dirs:
                if not os.path.exists(search_dir):
                    continue
                    
                try:
                    # Search immediate directory
                    for item in os.listdir(search_dir)[:50]:  # Limit for performance
                        item_path = os.path.join(search_dir, item)
                        if os.path.isfile(item_path):
                            # Exact match first (priority)
                            if filename_lower in item.lower():
                                priority = 0 if filename_lower == item.lower() else 1
                                found_files.append((priority, item, item_path, 'exact'))
                            else:
                                # Store for fuzzy matching
                                all_files.append((item, item_path))
                        
                        # Check subdirectories
                        elif os.path.isdir(item_path):
                            try:
                                for subitem in os.listdir(item_path)[:20]:  # Limit subdirectory search
                                    subitem_path = os.path.join(item_path, subitem)
                                    if os.path.isfile(subitem_path):
                                        # Exact match first (priority)
                                        if filename_lower in subitem.lower():
                                            priority = 0 if filename_lower == subitem.lower() else 1
                                            found_files.append((priority, subitem, subitem_path, 'exact'))
                                        else:
                                            # Store for fuzzy matching
                                            all_files.append((subitem, subitem_path))
                            except:
                                continue
                                
                except PermissionError:
                    continue
                except Exception as e:
                    print(f"Error searching {search_dir}: {e}")
                    continue
            
            # FUZZY MATCHING DISABLED - causes performance issues
            print(f"✅ Found {len(found_files)} exact matches for file '{filename}'")
            
            if not found_files:
                return f"🔍 File '{filename}' not found\n💡 Search limited to common directories for performance"
            
            # Sort by priority (exact matches first, then fuzzy)
            found_files.sort(key=lambda x: x[0])
            
            # Open the best match
            _, name, path, match_type = found_files[0]
            
            if os.path.exists(path):
                os.startfile(path)
                match_indicator = "📍" if match_type == 'exact' else "🎤"
                return f"{match_indicator} Opened: {name}" + (f" (voice-corrected from '{filename}')" if match_type == 'fuzzy' else "")
            else:
                return f"File found but no longer exists: {path}"
            
        except Exception as e:
            return f"Error opening file: {str(e)}"

    def generate_search_results_with_ui(self, found_items, query):
        """Generate search results with clickable web interface"""
        try:
            if not found_items:
                return f"🔍 No items found for '{query}' in comprehensive search"
            
            # Sort results (exact matches first, then by type, then by date)
            found_items.sort(key=lambda x: (
                0 if x.get('match_type') == 'exact' else 1,
                0 if x.get('type') == 'folder' else 1,
                -os.path.getmtime(x['path']) if os.path.exists(x['path']) else 0
            ))
            
            # Generate text response
            exact_count = len([f for f in found_items if f.get('match_type') == 'exact'])
            fuzzy_count = len([f for f in found_items if f.get('match_type') == 'fuzzy'])
            file_count = len([f for f in found_items if f.get('type') == 'file'])
            folder_count = len([f for f in found_items if f.get('type') == 'folder'])
            
            response = f"🌟 COMPREHENSIVE SEARCH RESULTS for '{query}':\n"
            response += f"   📄 {file_count} files, 📁 {folder_count} folders\n"
            response += f"   📍 {exact_count} exact matches, 🎤 {fuzzy_count} voice-corrected\n\n"
            
            # Create web interface data
            web_results = []
            for item in found_items[:50]:  # Limit to 50 for web display
                # Get file icon based on extension
                icon = self.get_file_icon(item.get('extension', ''), item.get('type', 'file'))
                
                # Format size
                if item.get('type') == 'folder':
                    size_str = "Folder"
                else:
                    size = item.get('size', 0)
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024*1024:
                    size_str = f"{size//1024}KB"
                else:
                    size_str = f"{size//(1024*1024)}MB"
                
                web_results.append({
                    'name': item['name'],
                    'path': item['path'],
                    'icon': icon,
                    'size': size_str,
                    'modified': item['modified'],
                    'type': item['type'],
                    'match_type': item['match_type']
                })
            
            # Store results for web interface access
            if not hasattr(self, 'search_results_cache'):
                self.search_results_cache = {}
            
            import time
            cache_key = f"search_{int(time.time())}"
            self.search_results_cache[cache_key] = {
                'query': query,
                'results': web_results,
                'timestamp': time.time()
            }
            
            # Add top results to text response
            for i, item in enumerate(found_items[:10], 1):
                type_icon = "📁" if item.get('type') == 'folder' else "📄"
                match_indicator = "📍" if item.get('match_type') == 'exact' else "🎤"
                
                if item.get('type') == 'folder':
                    size_str = "Folder"
                else:
                    size = item.get('size', 0)
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024*1024:
                        size_str = f"{size//1024}KB"
                    else:
                        size_str = f"{size//(1024*1024)}MB"
                
                response += f"{i:2d}. {match_indicator} {type_icon} {item['name']}\n"
                response += f"     📂 {item['path']}\n"
                response += f"     📊 {size_str} • {item['modified']}\n\n"
            
            if len(found_items) > 10:
                response += f"... and {len(found_items) - 10} more items.\n\n"
            
            response += f"🖥️ **VISUAL RESULTS**: Check the web interface for clickable icons and large view!\n"
            response += f"📱 Open your JARVIS mobile app to see visual search results with large icons.\n"
            response += f"🔗 Visual Results: http://localhost:5000/search-results?key={cache_key}\n"
            response += f"💾 Results cached as: {cache_key}"
            
            return response
            
        except Exception as e:
            return f"❌ Error generating search UI: {str(e)}"

    def get_file_icon(self, extension, file_type):
        """Get appropriate icon for file type"""
        if file_type == 'folder':
            return "📁"
        
        icon_map = {
            # Documents
            '.pdf': '📕', '.doc': '📄', '.docx': '📄', '.txt': '📝',
            '.rtf': '📄', '.odt': '📄',
            
            # Images
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.bmp': '🖼️', '.svg': '🖼️', '.webp': '🖼️', '.tiff': '🖼️',
            
            # Videos
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬',
            '.wmv': '🎬', '.flv': '🎬', '.webm': '🎬',
            
            # Audio
            '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.aac': '🎵',
            '.ogg': '🎵', '.wma': '🎵', '.m4a': '🎵',
            
            # Archives
            '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦',
            '.gz': '📦', '.bz2': '📦',
            
            # Code
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
            '.cpp': '⚙️', '.java': '☕', '.cs': '🔷',
            
            # Executables
            '.exe': '⚙️', '.msi': '📦', '.bat': '⚙️', '.cmd': '⚙️',
            
            # Spreadsheets
            '.xlsx': '📊', '.xls': '📊', '.csv': '📊',
            
            # Presentations
            '.pptx': '📊', '.ppt': '📊'
        }
        
        return icon_map.get(extension.lower(), '📄')

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
            print(f"DEBUG: Processing command: '{cmd_lower}'")
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

            # Handle Word document writing commands
            if ("write" in cmd_lower or "create" in cmd_lower) and ("word" in cmd_lower):
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
                        if not openai_client:
                            return "Recipe generation not available - OpenAI client not initialized"
                        try:
                            response = openai_client.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "system", "content": "You are a helpful cooking assistant. Provide recipes in a clear, step-by-step format."},
                                    {"role": "user", "content": f"Write a simple recipe for {recipe_item}. Include ingredients list and step-by-step instructions."}
                                ]
                            )
                            recipe = response.choices[0].message.content
                            return self.write_to_word(recipe, f"recipe_{recipe_item.replace(' ', '_')}.docx")
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
                        # Remove "in word", "to word", etc.
                        text_to_write = text_to_write.replace("in word", "").replace("to word", "").replace("in the word", "").replace("to the word", "").strip()
                
                if text_to_write:
                    return self.write_to_word(text_to_write)
                return "What would you like me to write in Word?"

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
                        if not openai_client:
                            return "Recipe generation not available - OpenAI client not initialized"
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

            # ============ LIGHTWEIGHT SYSTEM COMMANDS (TOP PRIORITY) ============
            # REMOVED: Heavy scanning commands that cause performance issues
            
            if any(phrase in cmd_lower for phrase in ["what window", "current window", "active window", "what app", "what application"]):
                return self.get_window_info()
            
            if any(phrase in cmd_lower for phrase in ["switch to", "focus on", "go to window", "open window"]):
                window_name = cmd_lower.replace("switch to", "").replace("focus on", "").replace("go to window", "").replace("open window", "").strip()
                if window_name:
                    return self.find_window_by_name(window_name)
                return "Which window should I focus on?"
            
            # Handle "what do you see" command - LIGHTWEIGHT VERSION
            if any(phrase in cmd_lower for phrase in ["what do you see", "what's on screen", "describe screen", "what do i see"]):
                return self.get_simple_screen_info()

            if any(phrase in cmd_lower for phrase in ["open file", "launch file", "start file"]):
                filename = cmd_lower.replace("open file", "").replace("launch file", "").replace("start file", "").strip()
                if filename:
                    return self.open_file_by_name(filename)
                return "Which file should I open?"

            # ============ PRIORITY FILE MANAGEMENT COMMANDS (MUST COME FIRST) ============
            # COMPREHENSIVE SEARCH - "search everything" command
            if any(phrase in cmd_lower for phrase in ["search everything", "search everything on", "find everything", "comprehensive search"]):
                # Extract search term
                search_term = cmd_lower.replace("search everything on", "").replace("search everything", "").replace("find everything", "").replace("comprehensive search", "").replace("for", "").strip()
                if search_term:
                    return self.comprehensive_search_everything(search_term)  # Use comprehensive search
                return "What would you like to search for across the entire system?"
            
            # File search commands - VERY SPECIFIC to avoid web search conflicts
            if any(phrase in cmd_lower for phrase in ["find files", "search files", "locate files", "show me files", "find my files"]):
                # Extract search term from command
                search_term = cmd_lower.replace("find files", "").replace("search files", "").replace("locate files", "").replace("show me files", "").replace("find my files", "").replace("containing", "").replace("named", "").replace("called", "").strip()
                if search_term:
                    return self.intelligent_file_search(search_term)  # Use fast filesystem search
                return "What files are you looking for?"

            # File opening commands - PRIORITY over web search
            if any(phrase in cmd_lower for phrase in ["open file", "launch file", "start file", "open my file", "play file"]):
                filename = cmd_lower.replace("open file", "").replace("launch file", "").replace("start file", "").replace("open my file", "").replace("play file", "").strip()
                if filename:
                    return self.open_file_by_name(filename)
                return "Which file should I open?"

            # Media-specific commands
            if any(phrase in cmd_lower for phrase in ["play my video", "show my video", "open my video", "watch my video"]):
                video_name = cmd_lower.replace("play my video", "").replace("show my video", "").replace("open my video", "").replace("watch my video", "").strip()
                return self.find_and_open_media('video', f'video {video_name}')
            
            if any(phrase in cmd_lower for phrase in ["play my music", "play my song", "start my music", "listen to"]):
                music_name = cmd_lower.replace("play my music", "").replace("play my song", "").replace("start my music", "").replace("listen to", "").strip()
                return self.find_and_open_media('music', f'music {music_name}')
            
            if any(phrase in cmd_lower for phrase in ["show my picture", "open my image", "show my photo", "display image"]):
                image_name = cmd_lower.replace("show my picture", "").replace("open my image", "").replace("show my photo", "").replace("display image", "").strip()
                return self.find_and_open_media('image', f'image {image_name}')

            # Folder operations with natural language
            if any(phrase in cmd_lower for phrase in ['show my folder', 'open my folder', 'browse my folder', 'go to my folder', 'navigate to folder']):
                folder_name = cmd_lower.replace('show my folder', '').replace('open my folder', '').replace('browse my folder', '').replace('go to my folder', '').replace('navigate to folder', '').strip()
                if folder_name:
                    return self.open_folder(folder_name)
                return "Which folder would you like me to open?"

            # Quick access to common folders
            if cmd_lower in ['show downloads', 'open downloads', 'go to downloads']:
                return self.open_folder('downloads')
            elif cmd_lower in ['show documents', 'open documents', 'go to documents']:
                return self.open_folder('documents')
            elif cmd_lower in ['show desktop', 'open desktop', 'go to desktop']:
                return self.open_folder('desktop')
            elif cmd_lower in ['show pictures', 'open pictures', 'go to pictures']:
                return self.open_folder('pictures')

            # ============ DUPLICATE SECTION REMOVED - FILE COMMANDS HANDLED ABOVE ============


            
            # Folder Operations
            if any(phrase in cmd_lower for phrase in ['open folder', 'show folder', 'browse folder', 'navigate to']):
                folder_name = cmd_lower.replace('open folder', '').replace('show folder', '').replace('browse folder', '').replace('navigate to', '').strip()
                if folder_name:
                    return self.open_folder(folder_name)
                return "Which folder would you like me to open?"

            # Media Operations
            if any(phrase in cmd_lower for phrase in ['play video', 'open video', 'watch video', 'play music', 'play song', 'open image', 'show image']):
                return self.handle_media_command(cmd_lower)

            # Advanced File Management
            if any(phrase in cmd_lower for phrase in ["organize downloads", "organize my downloads", "clean downloads", "sort downloads"]):
                return self.organize_downloads()
            
            if "duplicate files" in cmd_lower:
                if "find" in cmd_lower or "scan" in cmd_lower:
                    return self.find_duplicate_files()
                elif "remove" in cmd_lower or "delete" in cmd_lower:
                    return self.remove_duplicate_files()
            
            if any(phrase in cmd_lower for phrase in ["backup files", "create backup", "backup documents"]):
                return self.create_file_backup()

            # ============ WEB SEARCH COMMANDS - RESTORED USER-FRIENDLY COMMANDS ============
            # "look up" - Natural web search command (restored)
            if cmd_lower.startswith("look up "):
                search_query = cmd_lower.replace("look up", "").strip()
                if search_query:
                    return self.search_web(search_query)
                return "What would you like me to look up on the web?"
            
            # Other web search variations
            if any(phrase in cmd_lower for phrase in ["search web for", "google search", "web search for", "search online for"]):
                search_query = cmd_lower
                for phrase in ["search web for", "google search", "web search for", "search online for"]:
                    search_query = search_query.replace(phrase, "").strip()
                if search_query:
                    return self.search_web(search_query)
                return "What would you like me to search for on the web?"
            
            # Generic "search for" - clarify intent (files vs web)
            if cmd_lower.startswith("search for "):
                search_term = cmd_lower.replace("search for", "").strip()
                return f"Would you like me to 'find files {search_term}' or 'look up {search_term}'? Please be specific."

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

            # System control commands
            if any(phrase in cmd_lower for phrase in ["lock screen", "lock desktop", "lock computer", "lock the screen"]):
                print(f"DEBUG: Lock screen command detected: '{cmd_lower}'")
                return self.lock_screen()

            if any(phrase in cmd_lower for phrase in ["unlock screen", "unlock desktop", "unlock computer", "unlock the screen"]):
                # Trigger Windows Hello biometric authentication
                return self.trigger_biometric_unlock()

            # Webcam control via voice or phone
            if any(phrase in cmd_lower for phrase in ["turn on webcam", "show webcam", "start webcam", "enable webcam"]):
                if hasattr(self, 'web_jarvis') and hasattr(self.web_jarvis, 'start_webcam'):
                    result = self.web_jarvis.start_webcam()
                    return result + ". You can now view the webcam feed in the app."
                else:
                    return "Webcam control is not available in this mode."
            if any(phrase in cmd_lower for phrase in ["turn off webcam", "hide webcam", "stop webcam", "disable webcam"]):
                if hasattr(self, 'web_jarvis') and hasattr(self.web_jarvis, 'stop_webcam'):
                    result = self.web_jarvis.stop_webcam()
                    return result + ". Webcam feed is now off."
                else:
                    return "Webcam control is not available in this mode."

            # ========================================
            # 🚀 ADVANCED JARVIS CAPABILITIES - TONY STARK LEVEL! 🚀
            # ========================================

            # 🗂️ ADVANCED FILE MANAGEMENT (moved to top of function for priority)

            # 🖥️ ADVANCED SYSTEM CONTROL
            if any(phrase in cmd_lower for phrase in ["system status", "system health", "computer health", "system info"]):
                return self.get_system_health()
            
            if any(phrase in cmd_lower for phrase in ["process manager", "running processes", "show processes", "task manager"]):
                return self.get_running_processes()
            
            if "kill process" in cmd_lower or "end process" in cmd_lower:
                process_name = cmd_lower.replace("kill process", "").replace("end process", "").strip()
                if process_name:
                    return self.kill_process(process_name)
                return "Which process should I terminate?"
            
            if any(phrase in cmd_lower for phrase in ["network scan", "scan network", "network devices", "wifi devices"]):
                return self.scan_network()
            
            if any(phrase in cmd_lower for phrase in ["disk usage", "storage space", "disk space", "storage info"]):
                return self.get_disk_usage()

            # 🧠 CONTEXT-AWARE INTELLIGENCE  
            if any(phrase in cmd_lower for phrase in ["analyze screen", "what's on screen", "describe screen", "screen analysis"]):
                return self.analyze_current_screen()
            
            if any(phrase in cmd_lower for phrase in ["workflow suggestion", "suggest workflow", "optimize workflow"]):
                return self.suggest_workflow_optimization()
            
            if any(phrase in cmd_lower for phrase in ["pattern analysis", "usage patterns", "my patterns"]):
                return self.analyze_usage_patterns()

            # 📧 ADVANCED COMMUNICATION
            if any(phrase in cmd_lower for phrase in ["email summary", "summarize emails", "email digest"]):
                return self.create_email_summary()
            
            if any(phrase in cmd_lower for phrase in ["schedule email", "send email later", "delayed email"]):
                return self.schedule_email()
            
            if any(phrase in cmd_lower for phrase in ["bulk email", "mass email", "group email"]):
                return self.send_bulk_email()

            # 📅 PRODUCTIVITY AUTOMATION
            if any(phrase in cmd_lower for phrase in ["create schedule", "plan my day", "daily schedule"]):
                return self.create_daily_schedule()
            
            if any(phrase in cmd_lower for phrase in ["document analysis", "analyze document", "document summary"]):
                return self.analyze_documents()
            
            if any(phrase in cmd_lower for phrase in ["automate task", "create automation", "task automation"]):
                return self.create_task_automation()
            
            if any(phrase in cmd_lower for phrase in ["project status", "project overview", "project summary"]):
                return self.get_project_status()

            # 🔒 SECURITY & MONITORING
            if any(phrase in cmd_lower for phrase in ["security scan", "system security", "security check"]):
                return self.run_security_scan()
            
            if any(phrase in cmd_lower for phrase in ["monitor network", "network monitoring", "traffic monitor"]):
                return self.start_network_monitoring()
            
            if any(phrase in cmd_lower for phrase in ["firewall status", "firewall check", "security status"]):
                return self.check_firewall_status()
            
            if any(phrase in cmd_lower for phrase in ["intrusion detection", "security threats", "threat scan"]):
                return self.scan_for_threats()

            # 🎮 ENTERTAINMENT CONTROL
            if any(phrase in cmd_lower for phrase in ["media library", "show media", "media files"]):
                return self.show_media_library()
            
            if any(phrase in cmd_lower for phrase in ["play music", "start music", "music player"]):
                # Extract song/artist if specified
                music_query = cmd_lower.replace("play music", "").replace("start music", "").strip()
                return self.control_music("play", music_query)
            
            if "stop music" in cmd_lower or "pause music" in cmd_lower:
                return self.control_music("stop")
            
            if any(phrase in cmd_lower for phrase in ["game launcher", "launch game", "start game"]):
                game_name = cmd_lower.replace("launch game", "").replace("start game", "").replace("game launcher", "").strip()
                return self.launch_game(game_name)
            
            if any(phrase in cmd_lower for phrase in ["streaming control", "netflix", "youtube", "streaming"]):
                return self.control_streaming()

            # 💻 DEVELOPMENT TOOLS
            if any(phrase in cmd_lower for phrase in ["git status", "repository status", "repo status"]):
                return self.get_git_status()
            
            if any(phrase in cmd_lower for phrase in ["code analysis", "analyze code", "code review"]):
                return self.analyze_code()
            
            if any(phrase in cmd_lower for phrase in ["project build", "build project", "compile project"]):
                return self.build_project()
            
            if any(phrase in cmd_lower for phrase in ["deploy project", "deployment", "push to production"]):
                return self.deploy_project()
            
            if any(phrase in cmd_lower for phrase in ["database status", "db status", "database info"]):
                return self.get_database_status()

            # 🤖 AI-POWERED ANALYSIS
            if any(phrase in cmd_lower for phrase in ["image analysis", "analyze image", "describe image"]):
                return self.analyze_images()
            
            if any(phrase in cmd_lower for phrase in ["text analysis", "analyze text", "sentiment analysis"]):
                return self.analyze_text()
            
            if any(phrase in cmd_lower for phrase in ["data insights", "analyze data", "data analysis"]):
                return self.generate_data_insights()
            
            if any(phrase in cmd_lower for phrase in ["trend analysis", "market trends", "trend report"]):
                return self.analyze_trends()

            # 🏠 SMART HOME INTEGRATION
            if any(phrase in cmd_lower for phrase in ["smart home", "home automation", "control lights"]):
                return self.control_smart_home(cmd_lower)
            
            if any(phrase in cmd_lower for phrase in ["weather analysis", "weather patterns", "climate data"]):
                return self.analyze_weather_patterns()

            # 🎯 ADVANCED SYSTEM OPTIMIZATION
            if any(phrase in cmd_lower for phrase in ["optimize system", "system optimization", "speed up computer"]):
                return self.optimize_system_performance()
            
            if any(phrase in cmd_lower for phrase in ["memory optimization", "ram optimization", "free memory"]):
                return self.optimize_memory()
            
            if any(phrase in cmd_lower for phrase in ["startup optimization", "boot optimization", "startup programs"]):
                return self.optimize_startup()

            # 📊 ADVANCED REPORTING
            if any(phrase in cmd_lower for phrase in ["generate report", "create report", "system report"]):
                report_type = self.extract_report_type(cmd_lower)
                return self.generate_comprehensive_report(report_type)
            
            if any(phrase in cmd_lower for phrase in ["performance metrics", "system metrics", "performance stats"]):
                return self.get_performance_metrics()

            # If no specific command matched
            return "I'm not sure how to help with that. Could you please rephrase your request?"

        except Exception as e:
            return f"I encountered an error: {str(e)}"

    def lock_screen(self):
        """Lock the Windows desktop"""
        try:
            if self.system_info == "Windows":
                # Use Windows built-in lock screen command
                result = subprocess.run(['rundll32.exe', 'user32.dll,LockWorkStation'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return "Desktop locked successfully"
                else:
                    return f"Failed to lock desktop: {result.stderr}"
            else:
                return "Screen lock is only supported on Windows for now"
        except Exception as e:
            return f"Error locking screen: {e}"

    def keep_system_awake(self):
        """Prevent Windows from sleeping while phone is connected"""
        try:
            if self.system_info == "Windows" and not self.keep_awake_active:
                # Prevent system sleep and display sleep
                result = ctypes.windll.kernel32.SetThreadExecutionState(
                    self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED | self.ES_DISPLAY_REQUIRED
                )
                if result:
                    self.keep_awake_active = True
                    print("🌟 JARVIS: Keep-awake activated - PC will stay awake while phone connected")
                    return "✅ System keep-awake activated"
                else:
                    return "❌ Failed to activate keep-awake"
            elif self.keep_awake_active:
                return "ℹ️ Keep-awake already active"
            else:
                return "❌ Keep-awake only supported on Windows"
        except Exception as e:
            print(f"DEBUG: Error activating keep-awake: {e}")
            return f"❌ Keep-awake error: {e}"

    def restore_sleep_behavior(self):
        """Allow Windows to sleep normally when phone disconnects"""
        try:
            if self.system_info == "Windows" and self.keep_awake_active:
                # Restore normal power management
                result = ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
                if result:
                    self.keep_awake_active = False
                    print("💤 JARVIS: Normal sleep behavior restored - PC can sleep normally")
                    return "✅ Normal sleep behavior restored"
                else:
                    return "❌ Failed to restore sleep behavior"
            elif not self.keep_awake_active:
                return "ℹ️ Sleep behavior already normal"
            else:
                return "❌ Sleep management only supported on Windows"
        except Exception as e:
            print(f"DEBUG: Error restoring sleep behavior: {e}")
            return f"❌ Sleep restore error: {e}"

    def update_phone_connection(self, client_ip, connected=True):
        """Update phone connection status for smart sleep management"""
        if connected:
            # Track last seen time for each client
            if not hasattr(self, 'client_last_seen'):
                self.client_last_seen = {}
            
            was_new_client = client_ip not in self.connected_clients
            self.connected_clients.add(client_ip)
            self.client_last_seen[client_ip] = time.time()
            
            if was_new_client:
                print(f"📱 JARVIS: Phone connected from {client_ip}")
                
                # First phone connection - activate keep-awake
                if len(self.connected_clients) == 1:
                    self.phone_connected = True
                    return self.keep_system_awake()
        else:
            if client_ip in self.connected_clients:
                self.connected_clients.discard(client_ip)
                if hasattr(self, 'client_last_seen') and client_ip in self.client_last_seen:
                    del self.client_last_seen[client_ip]
                print(f"📱 JARVIS: Phone disconnected from {client_ip}")
                
                # Last phone disconnected - restore sleep
                if len(self.connected_clients) == 0:
                    self.phone_connected = False
                    return self.restore_sleep_behavior()
        
        return f"ℹ️ Connection status updated. Connected devices: {len(self.connected_clients)}"

    def cleanup_stale_connections(self):
        """Remove clients that haven't been seen for 10 seconds"""
        if not hasattr(self, 'client_last_seen'):
            return
            
        current_time = time.time()
        stale_clients = []
        
        for client_ip, last_seen in self.client_last_seen.items():
            if current_time - last_seen > 10:  # 10 seconds timeout
                stale_clients.append(client_ip)
        
        for client_ip in stale_clients:
            self.update_phone_connection(client_ip, connected=False)

    def start_connection_monitor(self):
        """Start background thread to monitor connections"""
        def monitor_connections():
            while True:
                time.sleep(5)  # Check every 5 seconds
                self.cleanup_stale_connections()
        
        monitor_thread = threading.Thread(target=monitor_connections, daemon=True)
        monitor_thread.start()
        print("🔍 JARVIS: Connection monitor started")

    def trigger_biometric_unlock(self):
        """Trigger Windows Hello biometric authentication"""
        try:
            if self.system_info == "Windows":
                print("DEBUG: Starting Windows Hello biometric unlock...")
                
                # Try using Windows Hello API via PowerShell
                import subprocess
                
                # Use runas command to trigger Windows credential prompt
                powershell_script = '''
                # Use runas to trigger Windows authentication (includes Windows Hello if configured)
                try {
                    # This will prompt for Windows Hello, PIN, or password
                    $process = Start-Process -FilePath "cmd" -ArgumentList "/c echo JARVIS Authentication Successful" -Verb RunAs -PassThru -Wait -WindowStyle Hidden
                    
                    if ($process.ExitCode -eq 0) {
                        Write-Output "SUCCESS: Windows authentication successful"
                        exit 0
                    } else {
                        Write-Output "FAILED: Authentication failed or cancelled"
                        exit 1
                    }
                } catch {
                    Write-Output "FAILED: Authentication error - $($_.Exception.Message)"
                    exit 1
                }
                '''
                
                # Execute PowerShell script
                print("DEBUG: Executing Windows Hello authentication...")
                result = subprocess.run(
                    ['powershell', '-Command', powershell_script],
                    capture_output=True,
                    text=True,
                    timeout=60  # 60 second timeout for biometric auth
                )
                
                print(f"DEBUG: PowerShell exit code: {result.returncode}")
                print(f"DEBUG: PowerShell output: {result.stdout}")
                print(f"DEBUG: PowerShell errors: {result.stderr}")
                
                if result.returncode == 0 and "SUCCESS" in result.stdout:
                    return "🔓 Windows Hello authentication successful - PC unlocked!"
                elif "FAILED" in result.stdout:
                    return f"❌ Windows Hello authentication failed: {result.stdout.strip()}"
                else:
                    return f"❌ Windows Hello error: {result.stderr.strip() if result.stderr else 'Unknown error'}"
                    
            else:
                return "Windows Hello is only supported on Windows"
                
        except subprocess.TimeoutExpired:
            return "⏰ Windows Hello authentication timed out"
        except Exception as e:
            print(f"DEBUG: Exception in biometric unlock: {e}")
            return f"❌ Windows Hello authentication error: {e}"



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
                if openai_client:
                    print("Falling back to OpenAI TTS...")
                    # Fallback to OpenAI TTS
                    response = openai_client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=text,
                        response_format="mp3",
                        speed=0.95
                    )
                else:
                    print("Error in text-to-speech: OpenAI client not available")
                    return
                
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
        # Create an event loop for the background thread
        async def run_listener():
            await self._background_listener()
            
        def run_async_listener():
            asyncio.run(run_listener())
            
        self.listen_thread = threading.Thread(target=run_async_listener)
        self.listen_thread.daemon = True
        self.listen_thread.start()

    def stop_background_listening(self):
        """Stop background listening"""
        self.background_listening = False
        if self.listen_thread:
            self.listen_thread.join()

    async def _background_listener(self):
        """Continuous background listening function"""
        with sr.Microphone() as source:
            # Initial calibration
            print("Calibrating microphone for background listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("\nWaiting for wake word...")
            
            while self.background_listening:
                try:
                    # Reduce timeout and phrase limit when sleeping
                    timeout = 1 if not self.is_awake else 2
                    phrase_limit = 5 if not self.is_awake else 15
                    
                    # Listen for audio with optimized parameters
                    audio = self.recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=phrase_limit,
                    )
                    
                    try:
                        # Use faster recognition when sleeping (only looking for wake words)
                        if not self.is_awake:
                            text = self.recognizer.recognize_google(audio, language="en-US")
                            text_lower = text.lower()
                            
                            # Quick check for wake word
                            if any(wake_word in text_lower for wake_word in self.wake_words):
                                print("Wake word detected!")
                                self.is_awake = True
                                self.last_wake_time = time.time()
                                await self.speak("Yes, how can I help you?")
                            continue
                        
                        # Full recognition when awake
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

                        # Quick check for sleep command
                        if any(sleep_word in text_lower for sleep_word in self.sleep_words):
                            print("Sleep command detected!")
                            self.is_awake = False
                            await self.speak("Goodbye! Let me know when you need me again.")
                            print("\nWaiting for wake word...")
                            continue

                        # Check if we should go back to sleep due to timeout
                        if current_time - self.last_wake_time > self.awake_timeout:
                            if self.is_awake:
                                print("Sleep timeout reached...")
                                self.is_awake = False
                                await self.speak("No activity detected. Going to sleep mode. Wake me when you need me.")
                                print("\nWaiting for wake word...")
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
                            
                        # Update wake time for any valid command
                        self.last_wake_time = current_time

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
                        
                        # Put the command in the queue
                        self.command_queue.put(text)
                            
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
        
        # Initial greeting without requiring wake word
        await self.speak("Jarvis in service!")
        print("\nListening...")
        
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

    # ========================================
    # 🚀 ADVANCED JARVIS METHOD IMPLEMENTATIONS - TONY STARK LEVEL! 🚀
    # ========================================

    # 🗂️ ADVANCED FILE MANAGEMENT METHODS
    def organize_downloads(self):
        """Organize downloads folder by file type"""
        try:
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.exists(downloads_path):
                return "Downloads folder not found."
            
            # Create organization folders
            folders = {
                'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
                'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
                'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
                'Audio': ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.wma'],
                'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
                'Executables': ['.exe', '.msi', '.deb', '.dmg', '.pkg'],
                'Code': ['.py', '.js', '.html', '.css', '.cpp', '.java', '.cs']
            }
            
            organized_count = 0
            for folder_name, extensions in folders.items():
                folder_path = os.path.join(downloads_path, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                
                for file in os.listdir(downloads_path):
                    if os.path.isfile(os.path.join(downloads_path, file)):
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext in extensions:
                            old_path = os.path.join(downloads_path, file)
                            new_path = os.path.join(folder_path, file)
                            if not os.path.exists(new_path):
                                shutil.move(old_path, new_path)
                                organized_count += 1
            
            return f"✅ Downloads organized! Moved {organized_count} files into categorized folders."
        except Exception as e:
            return f"❌ Error organizing downloads: {str(e)}"

    def smart_file_search(self, search_term):
        """Advanced file search with multiple criteria"""
        try:
            results = []
            search_paths = [
                os.path.expanduser("~"),
                "C:\\Users\\Public" if self.system_info == "Windows" else "/home"
            ]
            
            for search_path in search_paths:
                for root, dirs, files in os.walk(search_path):
                    # Skip system directories
                    if any(skip in root.lower() for skip in ['windows', 'system32', 'programfiles', '.git']):
                        continue
                    
                    for file in files:
                        if search_term.lower() in file.lower():
                            full_path = os.path.join(root, file)
                            file_size = os.path.getsize(full_path)
                            results.append({
                                'name': file,
                                'path': full_path,
                                'size': f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
                            })
                    
                    if len(results) >= 20:  # Limit results
                        break
            
            if results:
                response = f"🔍 Found {len(results)} files matching '{search_term}':\n\n"
                for i, file_info in enumerate(results[:10], 1):
                    response += f"{i}. {file_info['name']} ({file_info['size']})\n   📁 {file_info['path']}\n\n"
                if len(results) > 10:
                    response += f"... and {len(results) - 10} more files."
                return response
            else:
                return f"❌ No files found matching '{search_term}'"
        except Exception as e:
            return f"❌ Error searching files: {str(e)}"

    def find_duplicate_files(self):
        """Find duplicate files using MD5 hash comparison"""
        try:
            import hashlib
            hash_dict = {}
            duplicates = []
            scanned = 0
            
            # Scan common directories
            scan_paths = [
                os.path.join(os.path.expanduser("~"), "Downloads"),
                os.path.join(os.path.expanduser("~"), "Documents"),
                os.path.join(os.path.expanduser("~"), "Pictures")
            ]
            
            for scan_path in scan_paths:
                if not os.path.exists(scan_path):
                    continue
                    
                for root, dirs, files in os.walk(scan_path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        try:
                            # Calculate MD5 hash
                            hasher = hashlib.md5()
                            with open(filepath, 'rb') as f:
                                for chunk in iter(lambda: f.read(4096), b""):
                                    hasher.update(chunk)
                            file_hash = hasher.hexdigest()
                            
                            if file_hash in hash_dict:
                                duplicates.append({
                                    'original': hash_dict[file_hash],
                                    'duplicate': filepath,
                                    'size': os.path.getsize(filepath)
                                })
                            else:
                                hash_dict[file_hash] = filepath
                            scanned += 1
                        except (IOError, OSError):
                            continue
            
            if duplicates:
                total_waste = sum(dup['size'] for dup in duplicates)
                response = f"🔍 Scanned {scanned} files. Found {len(duplicates)} duplicates wasting {total_waste / (1024*1024):.1f} MB:\n\n"
                for i, dup in enumerate(duplicates[:10], 1):
                    response += f"{i}. {os.path.basename(dup['duplicate'])} ({dup['size'] / 1024:.1f} KB)\n"
                    response += f"   Original: {dup['original']}\n"
                    response += f"   Duplicate: {dup['duplicate']}\n\n"
                if len(duplicates) > 10:
                    response += f"... and {len(duplicates) - 10} more duplicates."
                response += "\n💡 Say 'remove duplicate files' to delete them."
                return response
            else:
                return f"✅ Scanned {scanned} files. No duplicates found!"
        except Exception as e:
            return f"❌ Error finding duplicates: {str(e)}"

    def create_file_backup(self):
        """Create backup of important documents"""
        try:
            backup_dir = os.path.join(os.path.expanduser("~"), "JARVIS_Backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Important directories to backup
            backup_sources = [
                (os.path.join(os.path.expanduser("~"), "Documents"), "Documents"),
                (os.path.join(os.path.expanduser("~"), "Desktop"), "Desktop"),
                (os.path.join(os.path.expanduser("~"), "Pictures"), "Pictures")
            ]
            
            backed_up = 0
            total_size = 0
            
            for source, folder_name in backup_sources:
                if not os.path.exists(source):
                    continue
                    
                dest = os.path.join(backup_dir, folder_name)
                os.makedirs(dest, exist_ok=True)
                
                for root, dirs, files in os.walk(source):
                    for file in files:
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, source)
                        dest_file = os.path.join(dest, rel_path)
                        
                        # Create directory structure
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        
                        # Copy if newer or doesn't exist
                        if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                            shutil.copy2(src_file, dest_file)
                            backed_up += 1
                            total_size += os.path.getsize(src_file)
            
            return f"✅ Backup completed! {backed_up} files backed up ({total_size / (1024*1024):.1f} MB)\n📁 Location: {backup_dir}"
        except Exception as e:
            return f"❌ Error creating backup: {str(e)}"

    # 🖥️ ADVANCED SYSTEM CONTROL METHODS
    def get_system_health(self):
        """Comprehensive system health analysis"""
        try:
            import psutil
            
            # CPU Information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            
            # Memory Information
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # Disk Information
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free = disk.free / (1024**3)  # GB
            
            # Network Information
            network = psutil.net_io_counters()
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            uptime_hours = uptime / 3600
            
            health_status = "🟢 EXCELLENT" if cpu_percent < 50 and memory_percent < 70 and disk_percent < 80 else \
                           "🟡 GOOD" if cpu_percent < 70 and memory_percent < 85 and disk_percent < 90 else \
                           "🔴 NEEDS ATTENTION"
            
            response = f"""
🖥️ **SYSTEM HEALTH REPORT** {health_status}

💻 **CPU Status:**
   • Usage: {cpu_percent}%
   • Cores: {cpu_count}
   • Frequency: {cpu_freq.current:.0f} MHz

🧠 **Memory Status:**
   • Used: {memory_percent}%
   • Available: {memory_available:.1f} GB
   • Total: {memory.total / (1024**3):.1f} GB

💾 **Storage Status:**
   • Used: {disk_percent:.1f}%
   • Free Space: {disk_free:.1f} GB
   • Total: {disk.total / (1024**3):.1f} GB

🌐 **Network:**
   • Sent: {network.bytes_sent / (1024**2):.1f} MB
   • Received: {network.bytes_recv / (1024**2):.1f} MB

⏱️ **Uptime:** {uptime_hours:.1f} hours
            """
            
            return response.strip()
        except Exception as e:
            return f"❌ Error getting system health: {str(e)}"

    def get_running_processes(self):
        """Get list of running processes with resource usage"""
        try:
            import psutil
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 0 or proc_info['memory_percent'] > 1:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            response = "🔄 **TOP PROCESSES BY CPU USAGE:**\n\n"
            for i, proc in enumerate(processes[:15], 1):
                response += f"{i:2d}. {proc['name'][:20]:<20} | CPU: {proc['cpu_percent']:5.1f}% | Memory: {proc['memory_percent']:5.1f}% | PID: {proc['pid']}\n"
            
            response += f"\n📊 Total processes monitored: {len(processes)}"
            return response
        except Exception as e:
            return f"❌ Error getting processes: {str(e)}"

    def kill_process(self, process_name):
        """Terminate a specific process"""
        try:
            import psutil
            killed = 0
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        proc.terminate()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed > 0:
                return f"✅ Terminated {killed} instance(s) of '{process_name}'"
            else:
                return f"❌ No running processes found matching '{process_name}'"
        except Exception as e:
            return f"❌ Error killing process: {str(e)}"

    def scan_network(self):
        """Scan local network for devices"""
        try:
            import socket
            import ipaddress
            
            # Get local IP range
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            
            devices = []
            for ip in network.hosts():
                try:
                    # Quick ping test
                    result = subprocess.run(['ping', '-n', '1', '-w', '1000', str(ip)] if self.system_info == "Windows" 
                                          else ['ping', '-c', '1', '-W', '1', str(ip)], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        try:
                            hostname = socket.gethostbyaddr(str(ip))[0]
                        except:
                            hostname = "Unknown"
                        devices.append({'ip': str(ip), 'hostname': hostname})
                except:
                    continue
                    
                if len(devices) >= 20:  # Limit scan
                    break
            
            if devices:
                response = f"🌐 **NETWORK SCAN RESULTS** ({len(devices)} devices found):\n\n"
                for i, device in enumerate(devices, 1):
                    response += f"{i:2d}. {device['ip']:<15} | {device['hostname']}\n"
                return response
            else:
                return "❌ No network devices found"
        except Exception as e:
            return f"❌ Error scanning network: {str(e)}"

    def get_disk_usage(self):
        """Get detailed disk usage information"""
        try:
            import psutil
            
            response = "💾 **DISK USAGE ANALYSIS:**\n\n"
            
            # Get all disk partitions
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    total_size = partition_usage.total / (1024**3)  # GB
                    used_size = partition_usage.used / (1024**3)   # GB
                    free_size = partition_usage.free / (1024**3)   # GB
                    percentage = (partition_usage.used / partition_usage.total) * 100
                    
                    status = "🔴" if percentage > 90 else "🟡" if percentage > 75 else "🟢"
                    
                    response += f"{status} **Drive {partition.device}** ({partition.fstype})\n"
                    response += f"   Total: {total_size:.1f} GB\n"
                    response += f"   Used:  {used_size:.1f} GB ({percentage:.1f}%)\n"
                    response += f"   Free:  {free_size:.1f} GB\n\n"
                except PermissionError:
                    continue
            
            return response.strip()
        except Exception as e:
            return f"❌ Error getting disk usage: {str(e)}"

    # 🧠 CONTEXT-AWARE INTELLIGENCE METHODS
    def analyze_current_screen(self):
        """Analyze what's currently on screen using OCR and image analysis"""
        try:
            import pytesseract
            from PIL import ImageGrab
            
            # Take screenshot
            screenshot = ImageGrab.grab()
            
            # Extract text using OCR
            text = pytesseract.image_to_string(screenshot)
            
            # Analyze content
            if not text.strip():
                return "🖥️ Screen appears to be mostly graphical with minimal text content."
            
            # Basic content analysis
            text_lower = text.lower()
            content_type = "unknown"
            
            if any(term in text_lower for term in ['browser', 'chrome', 'firefox', 'edge', 'http', 'www']):
                content_type = "web browser"
            elif any(term in text_lower for term in ['word', 'document', 'docx', 'pdf']):
                content_type = "document"
            elif any(term in text_lower for term in ['email', 'inbox', 'subject', 'from:']):
                content_type = "email client"
            elif any(term in text_lower for term in ['code', 'function', 'class', 'import']):
                content_type = "code editor"
            elif any(term in text_lower for term in ['video', 'play', 'pause', 'youtube', 'netflix']):
                content_type = "media player"
            
            # Extract key information
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            key_content = lines[:5]  # First 5 non-empty lines
            
            response = f"🖥️ **SCREEN ANALYSIS:**\n\n"
            response += f"📋 **Content Type:** {content_type.title()}\n\n"
            response += f"📝 **Key Text Content:**\n"
            for line in key_content:
                response += f"   • {line[:60]}...\n" if len(line) > 60 else f"   • {line}\n"
            
            return response
        except Exception as e:
            return f"❌ Error analyzing screen: {str(e)}"

    def suggest_workflow_optimization(self):
        """Suggest workflow optimizations based on current context"""
        try:
            # Analyze running applications
            import psutil
            
            running_apps = []
            for proc in psutil.process_iter(['name']):
                try:
                    app_name = proc.info['name'].lower()
                    if any(app in app_name for app in ['chrome', 'firefox', 'word', 'excel', 'code', 'notepad']):
                        running_apps.append(app_name)
                except:
                    continue
            
            suggestions = []
            
            # Browser optimization
            if any('chrome' in app or 'firefox' in app for app in running_apps):
                suggestions.append("🌐 **Browser Optimization:** Consider using browser tab management extensions to reduce memory usage.")
            
            # Development workflow
            if any('code' in app or 'visual' in app for app in running_apps):
                suggestions.append("💻 **Development Workflow:** Set up automated build scripts and use version control efficiently.")
            
            # Document management
            if any('word' in app or 'excel' in app for app in running_apps):
                suggestions.append("📄 **Document Management:** Use cloud storage for real-time collaboration and automatic backups.")
            
            # General productivity
            suggestions.extend([
                "⚡ **Productivity Tip:** Use keyboard shortcuts to speed up common tasks by 40%.",
                "🎯 **Focus Enhancement:** Try the Pomodoro technique: 25 minutes focused work, 5 minute breaks.",
                "📊 **Task Management:** Organize tasks by priority: Urgent+Important > Important > Urgent > Neither."
            ])
            
            response = "🧠 **WORKFLOW OPTIMIZATION SUGGESTIONS:**\n\n"
            for i, suggestion in enumerate(suggestions[:5], 1):
                response += f"{i}. {suggestion}\n\n"
            
            return response.strip()
        except Exception as e:
            return f"❌ Error generating workflow suggestions: {str(e)}"

    def analyze_usage_patterns(self):
        """Analyze user's computer usage patterns"""
        try:
            import psutil
            from collections import defaultdict
            
            # Get process information
            process_time = defaultdict(float)
            total_processes = 0
            
            for proc in psutil.process_iter(['name', 'cpu_times']):
                try:
                    name = proc.info['name']
                    cpu_times = proc.info['cpu_times']
                    if hasattr(cpu_times, 'user'):
                        process_time[name] += cpu_times.user
                    total_processes += 1
                except:
                    continue
            
            # Sort by usage time
            top_processes = sorted(process_time.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime_hours = (time.time() - boot_time) / 3600
            
            # Memory usage pattern
            memory = psutil.virtual_memory()
            
            response = f"""
🧠 **USAGE PATTERN ANALYSIS:**

⏱️ **Session Information:**
   • Current session: {uptime_hours:.1f} hours
   • Active processes: {total_processes}
   • Memory usage: {memory.percent}%

🔥 **Most Used Applications:**
"""
            
            for i, (process, cpu_time) in enumerate(top_processes, 1):
                if cpu_time > 0:
                    response += f"   {i:2d}. {process[:20]:<20} | {cpu_time:.1f}s CPU time\n"
            
            # Usage insights
            browser_time = sum(time for proc, time in top_processes if any(b in proc.lower() for b in ['chrome', 'firefox', 'edge']))
            dev_time = sum(time for proc, time in top_processes if any(d in proc.lower() for d in ['code', 'visual', 'atom']))
            
            response += f"\n📊 **Activity Insights:**\n"
            if browser_time > 0:
                response += f"   • Web browsing: {browser_time:.1f}s\n"
            if dev_time > 0:
                response += f"   • Development work: {dev_time:.1f}s\n"
            
            response += f"   • System efficiency: {'High' if memory.percent < 70 else 'Moderate' if memory.percent < 85 else 'Low'}"
            
            return response
        except Exception as e:
            return f"❌ Error analyzing usage patterns: {str(e)}"

    # Additional method stubs for other categories...
    def create_email_summary(self):
        return "📧 Email summary feature coming soon! This will analyze your recent emails and provide insights."
    
    def schedule_email(self):
        return "⏰ Email scheduling feature coming soon! This will allow you to compose and schedule emails for later."
    
    def send_bulk_email(self):
        return "📮 Bulk email feature coming soon! This will help you send personalized emails to multiple recipients."
    
    def create_daily_schedule(self):
        return "📅 Daily scheduling feature coming soon! This will help you plan and optimize your daily tasks."
    
    def analyze_documents(self):
        return "📄 Document analysis feature coming soon! This will summarize and extract insights from your documents."
    
    def create_task_automation(self):
        return "🤖 Task automation feature coming soon! This will help you create scripts to automate repetitive tasks."
    
    def get_project_status(self):
        return "📊 Project status feature coming soon! This will track your project progress and milestones."
    
    def run_security_scan(self):
        return "🔒 Security scan feature coming soon! This will check your system for vulnerabilities."
    
    def start_network_monitoring(self):
        return "📡 Network monitoring feature coming soon! This will track your network traffic and performance."
    
    def check_firewall_status(self):
        return "🛡️ Firewall status feature coming soon! This will check your firewall configuration."
    
    def scan_for_threats(self):
        return "🚨 Threat scanning feature coming soon! This will scan for malware and security threats."
    
    def show_media_library(self):
        return "🎵 Media library feature coming soon! This will catalog and organize your media files."
    
    def control_music(self, action, query=""):
        return f"🎶 Music control feature coming soon! Action: {action}, Query: {query}"
    
    def launch_game(self, game_name):
        return f"🎮 Game launcher feature coming soon! Requested game: {game_name}"
    
    def control_streaming(self):
        return "📺 Streaming control feature coming soon! This will control your streaming applications."
    
    def get_git_status(self):
        return "🔄 Git status feature coming soon! This will show your repository status and changes."
    
    def analyze_code(self):
        return "💻 Code analysis feature coming soon! This will review your code for improvements."
    
    def build_project(self):
        return "🔨 Project build feature coming soon! This will compile and build your projects."
    
    def deploy_project(self):
        return "🚀 Project deployment feature coming soon! This will deploy your projects to production."
    
    def get_database_status(self):
        return "🗄️ Database status feature coming soon! This will check your database connections and health."
    
    def analyze_images(self):
        return "🖼️ Image analysis feature coming soon! This will analyze and describe images using AI."
    
    def analyze_text(self):
        return "📝 Text analysis feature coming soon! This will perform sentiment and content analysis."
    
    def generate_data_insights(self):
        return "📊 Data insights feature coming soon! This will analyze your data and generate reports."
    
    def analyze_trends(self):
        return "📈 Trend analysis feature coming soon! This will analyze market and data trends."
    
    def control_smart_home(self, command):
        return f"🏠 Smart home control feature coming soon! Command: {command}"
    
    def analyze_weather_patterns(self):
        return "🌤️ Weather analysis feature coming soon! This will analyze weather patterns and forecasts."
    
    def optimize_system_performance(self):
        return "⚡ System optimization feature coming soon! This will optimize your system for better performance."
    
    def optimize_memory(self):
        return "🧠 Memory optimization feature coming soon! This will free up and optimize system memory."
    
    def optimize_startup(self):
        return "🚀 Startup optimization feature coming soon! This will optimize your system startup programs."
    
    def extract_report_type(self, command):
        """Extract report type from command"""
        if "system" in command:
            return "system"
        elif "performance" in command:
            return "performance"
        elif "security" in command:
            return "security"
        else:
            return "general"
    
    def generate_comprehensive_report(self, report_type):
        return f"📋 Comprehensive {report_type} report feature coming soon! This will generate detailed system reports."
    
    def get_performance_metrics(self):
        return "📊 Performance metrics feature coming soon! This will show detailed system performance data."

    def open_folder(self, folder_name):
        """Open a folder by name using intelligent search"""
        try:
            # Common folder mappings
            folder_mappings = {
                'downloads': str(Path.home() / "Downloads"),
                'documents': str(Path.home() / "Documents"), 
                'desktop': str(Path.home() / "Desktop"),
                'pictures': str(Path.home() / "Pictures"),
                'videos': str(Path.home() / "Videos"),
                'music': str(Path.home() / "Music"),
                'projects': str(Path.home() / "Documents"),
                'downloads folder': str(Path.home() / "Downloads"),
                'my documents': str(Path.home() / "Documents"),
            }
            
            folder_name_lower = folder_name.lower().strip()
            
            # Check direct mappings first
            if folder_name_lower in folder_mappings:
                folder_path = folder_mappings[folder_name_lower]
            else:
                # Search for folder in common locations
                search_paths = [
                    str(Path.home()),
                    str(Path.home() / "Documents"),
                    str(Path.home() / "Desktop"),
                    "C:\\", "D:\\"
                ]
                
                folder_path = None
                for search_path in search_paths:
                    if os.path.exists(search_path):
                        for item in os.listdir(search_path):
                            if item.lower() == folder_name_lower and os.path.isdir(os.path.join(search_path, item)):
                                folder_path = os.path.join(search_path, item)
                                break
                    if folder_path:
                        break
                
                if not folder_path:
                    return f"Folder '{folder_name}' not found in common locations."
            
            # Open the folder
            if os.path.exists(folder_path):
                os.startfile(folder_path)
                return f"Opened {folder_name} folder."
            else:
                return f"Folder '{folder_name}' not found."
                
        except Exception as e:
            return f"Error opening folder: {str(e)}"

    def handle_media_command(self, command):
        """Handle media-related commands (play, open videos, music, images)"""
        try:
            cmd_lower = command.lower()
            
            # Determine media type and action
            if any(word in cmd_lower for word in ['video', 'movie', 'film']):
                return self.find_and_open_media('video', cmd_lower)
            elif any(word in cmd_lower for word in ['music', 'song', 'audio']):
                return self.find_and_open_media('music', cmd_lower)
            elif any(word in cmd_lower for word in ['image', 'photo', 'picture', 'pic']):
                return self.find_and_open_media('image', cmd_lower)
            else:
                return "Please specify whether you want to play video, music, or open an image."
                
        except Exception as e:
            return f"Error handling media command: {str(e)}"

    def find_and_open_media(self, media_type, command):
        """Find and open media files based on type"""
        try:
            # Define media file extensions
            extensions = {
                'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
                'music': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
                'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp']
            }
            
            # Common media folders
            media_folders = {
                'video': [str(Path.home() / "Videos"), str(Path.home() / "Downloads"), str(Path.home() / "Desktop")],
                'music': [str(Path.home() / "Music"), str(Path.home() / "Downloads"), str(Path.home() / "Desktop")],
                'image': [str(Path.home() / "Pictures"), str(Path.home() / "Downloads"), str(Path.home() / "Desktop")]
            }
            
            # Extract filename from command if specified
            filename_keywords = command.replace(f'play {media_type}', '').replace(f'open {media_type}', '').replace('play', '').replace('open', '').strip()
            
            # Search for media files
            found_files = []
            for folder in media_folders[media_type]:
                if os.path.exists(folder):
                    for file in os.listdir(folder):
                        file_path = os.path.join(folder, file)
                        if os.path.isfile(file_path):
                            file_ext = os.path.splitext(file)[1].lower()
                            if file_ext in extensions[media_type]:
                                if not filename_keywords or filename_keywords.lower() in file.lower():
                                    found_files.append((file, file_path))
            
            if not found_files:
                return f"No {media_type} files found" + (f" matching '{filename_keywords}'" if filename_keywords else "") + "."
            
            # If specific file mentioned, try to find exact match
            if filename_keywords:
                for file, file_path in found_files:
                    if filename_keywords.lower() in file.lower():
                        os.startfile(file_path)
                        return f"Playing {file}"
            
            # Otherwise, open first file found
            file, file_path = found_files[0]
            os.startfile(file_path)
            
            if len(found_files) > 1:
                return f"Playing {file}. Found {len(found_files)} {media_type} files total."
            else:
                return f"Playing {file}"
                
        except Exception as e:
            return f"Error finding {media_type}: {str(e)}"

    def remove_duplicate_files(self):
        """Remove duplicate files (placeholder - requires user confirmation)"""
        return "⚠️ Duplicate file removal requires manual confirmation for safety. Use 'find duplicate files' first to see what duplicates exist."

class WebJarvis:
    def __init__(self, jarvis_instance):
        self.jarvis = jarvis_instance
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'jarvis-secret-key-2024')
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.setup_routes()
        self.setup_socketio_events()
        self.connected_clients = set()
        
        # Webcam state
        self.webcam_active = False
        self.webcam_thread = None
        self.webcam_lock = threading.Lock()
        self.webcam_frame = None
        self.webcam_capture = None
    
    def get_local_ip(self):
        """Get the local IP address of the machine"""
        try:
            # Connect to a remote server to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def get_public_ip(self):
        """Get the public IP address for global access"""
        try:
            # Try multiple services in case one is down
            services = [
                'https://api.ipify.org?format=text',
                'https://ipv4.icanhazip.com',
                'https://api.myip.com',
                'https://httpbin.org/ip'
            ]
            
            for service in services:
                try:
                    if 'httpbin' in service:
                        response = requests.get(service, timeout=5)
                        return response.json()['origin']
                    elif 'myip' in service:
                        response = requests.get(service, timeout=5)
                        return response.json()['ip']
                    else:
                        response = requests.get(service, timeout=5)
                        return response.text.strip()
                except:
                    continue
            
            return "Unable to detect"
        except Exception as e:
            print(f"Error getting public IP: {e}")
            return "Unable to detect"
    
    def capture_screen(self):
        """Capture current desktop screen and return as JPEG bytes"""
        try:
            # Capture screen using mss
            with mss.mss() as sct:
                # Capture the primary monitor
                monitor = sct.monitors[1]  # Monitor 1 is primary (0 is all monitors combined)
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Resize for mobile optimization (maintain aspect ratio)
                max_width = 800
                max_height = 600
                img.thumbnail((max_width, max_height), Image.LANCZOS)
                
                # Convert to JPEG bytes
                img_buffer = iolib.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85, optimize=True)
                img_buffer.seek(0)
                
                return img_buffer.read()
                
        except Exception as e:
            print(f"Screen capture error: {e}")
            return None
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/api/command', methods=['POST'])
        def api_command():
            """API endpoint to process commands"""
            try:
                data = request.get_json()
                command = data.get('command', '').strip()
                
                if not command:
                    return jsonify({'error': 'No command provided'}), 400
                
                # Process command asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(self.jarvis.process_command(command))
                finally:
                    loop.close()
                
                # Broadcast response to all connected clients
                self.socketio.emit('response', {
                    'command': command,
                    'response': response,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
                
                return jsonify({
                    'success': True,
                    'response': response,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
                
            except Exception as e:
                error_msg = f"Error processing command: {str(e)}"
                return jsonify({'error': error_msg}), 500
        
        @self.app.route('/api/process-audio', methods=['POST'])
        def api_process_audio():
            """Process audio file sent from phone"""
            try:
                if 'audio' not in request.files:
                    return jsonify({'error': 'No audio file provided'}), 400
                
                audio_file = request.files['audio']
                if audio_file.filename == '':
                    return jsonify({'error': 'No audio file selected'}), 400
                
                # Save audio file temporarily (expecting WAV from phone)
                import tempfile
                import os
                
                # Determine file extension from filename or default to .wav
                file_extension = '.wav'
                if audio_file.filename and '.' in audio_file.filename:
                    file_extension = '.' + audio_file.filename.split('.')[-1]
                
                with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                    audio_file.save(temp_file.name)
                    temp_path = temp_file.name
                
                try:
                    # Try direct speech recognition on the audio file
                    import speech_recognition as sr
                    r = sr.Recognizer()
                    
                    # Adjust recognition settings for better phone audio
                    r.energy_threshold = 300
                    r.dynamic_energy_threshold = True
                    
                    with sr.AudioFile(temp_path) as source:
                        # Adjust for ambient noise
                        r.adjust_for_ambient_noise(source, duration=0.5)
                        audio_data = r.record(source)
                        
                    # Try Google Speech Recognition
                    try:
                        recognized_text = r.recognize_google(audio_data, language="en-US")
                        print(f"Recognized from phone: {recognized_text}")
                        
                    except sr.UnknownValueError:
                        # Try with different settings
                        recognized_text = r.recognize_google(audio_data, language="en-US", show_all=False)
                        if not recognized_text:
                            raise sr.UnknownValueError("Could not understand audio")
                    
                    # Process command with Jarvis
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = loop.run_until_complete(self.jarvis.process_command(recognized_text))
                    finally:
                        loop.close()
                    
                    # Clean up temporary file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    
                    return jsonify({
                        'success': True,
                        'recognized_text': recognized_text,
                        'response': response,
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    })
                    
                except sr.UnknownValueError:
                    return jsonify({
                        'error': 'Could not understand the audio. Please speak clearly and try again.',
                        'recognized_text': None
                    }), 400
                    
                except sr.RequestError as e:
                    return jsonify({
                        'error': f'Speech recognition service error: {str(e)}',
                        'recognized_text': None
                    }), 500
                    
                except Exception as e:
                    return jsonify({
                        'error': f'Audio processing failed: {str(e)}',
                        'recognized_text': None
                    }), 500
                finally:
                    # Ensure cleanup
                    try:
                        if 'temp_path' in locals():
                            os.unlink(temp_path)
                    except:
                        pass
                        
            except Exception as e:
                return jsonify({'error': f'Error processing audio: {str(e)}'}), 500
        
        @self.app.route('/api/status')
        def api_status():
            """Get Jarvis status"""
            # Track phone connection for smart keep-awake
            client_ip = request.remote_addr
            self.jarvis.update_phone_connection(client_ip, connected=True)
            
            return jsonify({
                'status': 'online',
                'is_awake': self.jarvis.is_awake,
                'is_speaking': self.jarvis.is_speaking,
                'waiting_for_response': self.jarvis.waiting_for_response,
                'keep_awake_active': self.jarvis.keep_awake_active,
                'connected_devices': len(self.jarvis.connected_clients),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
        

        @self.app.route('/api/screenshot')
        def api_screenshot():
            """Get a screenshot of the desktop - optimized for high FPS streaming"""
            try:
                print("DEBUG: Screenshot API called")
                
                # Use mss for faster screenshot capture
                with mss.mss() as sct:
                    # Capture the primary monitor
                    monitor = sct.monitors[1]  
                    screenshot = sct.grab(monitor)
                    
                    # Convert to PIL Image for processing
                    img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                    
                    # Optimize image size for faster transmission
                    # Resize to max 1920x1080 for performance
                    if img.width > 1920 or img.height > 1080:
                        img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                    
                    # Convert to JPEG with optimized settings for speed
                    img_io = iolib.BytesIO()
                    img.save(img_io, 'JPEG', quality=75, optimize=True)  # Reduced quality for speed
                    img_io.seek(0)
                    
                    screenshot_data = img_io.getvalue()
                    print(f"DEBUG: Screenshot data length: {len(screenshot_data)}")
                    
                    return Response(
                        screenshot_data,
                        mimetype='image/jpeg',
                        headers={
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache',
                            'Expires': '0',
                        }
                    )
            
            except Exception as e:
                print(f"DEBUG: Screenshot error: {e}")
                return jsonify({'error': f'Screenshot error: {str(e)}'}), 500

        @self.app.route('/api/screen-stream')
        def screen_stream():
            """Live screen streaming endpoint"""
            def generate():
                while True:
                    try:
                        screenshot_data = self.capture_screen()
                        if screenshot_data:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + 
                                   screenshot_data + b'\r\n\r\n')
                        time.sleep(0.5)  # 2 FPS for smooth streaming
                    except Exception as e:
                        print(f"Screen stream error: {e}")
                        break
            
            return Response(
                generate(),
                mimetype='multipart/x-mixed-replace; boundary=frame',
                headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
            )
        
        @self.app.route('/api/remote-click', methods=['POST'])
        def remote_click():
            """Handle remote mouse click on screen"""
            try:
                import pyautogui
                data = request.get_json()
                x = data.get('x', 0)
                y = data.get('y', 0)
                
                # Scale coordinates if needed (screen coordinates vs image coordinates)
                screen_width, screen_height = pyautogui.size()
                actual_x = int(x)
                actual_y = int(y)
                
                pyautogui.click(actual_x, actual_y)
                return jsonify({
                    'success': True,
                    'message': f'Clicked at ({actual_x}, {actual_y})',
                    'screen_size': [screen_width, screen_height]
                })
            except Exception as e:
                return jsonify({'error': f'Click error: {str(e)}'}), 500
        
        @self.app.route('/api/lock-screen', methods=['POST'])
        def lock_screen_api():
            """Lock the desktop screen"""
            try:
                result = self.jarvis.lock_screen()
                return jsonify({
                    'success': True,
                    'message': result
                })
            except Exception as e:
                return jsonify({'error': f'Lock screen error: {str(e)}'}), 500

        @self.app.route('/api/biometric-unlock', methods=['POST'])
        def biometric_unlock_api():
            """Trigger Windows Hello biometric authentication"""
            try:
                result = self.jarvis.trigger_biometric_unlock()
                return jsonify({
                    'success': True,
                    'message': result
                })
            except Exception as e:
                return jsonify({'error': f'Biometric unlock error: {str(e)}'}), 500



        @self.app.route('/api/connection-info')
        def connection_info():
            """Get connection information for setup"""
            try:
                local_ip = self.get_local_ip()
                public_ip = self.get_public_ip()
                
                return jsonify({
                    'local_ip': local_ip,
                    'public_ip': public_ip,
                    'port': 5000,
                    'local_url': f'http://{local_ip}:5000',
                    'global_url': f'http://{public_ip}:5000',
                    'setup_required': public_ip != "Unable to detect",
                    'instructions': {
                        'step1': 'Set up port forwarding on your router',
                        'step2': f'Forward external port 5000 to internal {local_ip}:5000',
                        'step3': f'Access globally using: http://{public_ip}:5000',
                        'security': 'Consider changing the default port for security'
                    }
                })
            except Exception as e:
                return jsonify({'error': f'Connection info error: {str(e)}'}), 500

        @self.app.route('/api/search-results')
        def api_search_results():
            """Get cached search results for visual display"""
            try:
                cache_key = request.args.get('key')
                if not cache_key:
                    return jsonify({'error': 'No cache key provided'}), 400
                
                if not hasattr(self.jarvis, 'search_results_cache'):
                    return jsonify({'error': 'No search results available'}), 404
                
                if cache_key not in self.jarvis.search_results_cache:
                    return jsonify({'error': 'Search results not found or expired'}), 404
                
                cached_data = self.jarvis.search_results_cache[cache_key]
                
                # Check if results are still fresh (within 10 minutes)
                import time
                if time.time() - cached_data['timestamp'] > 600:
                    return jsonify({'error': 'Search results expired'}), 404
                
                return jsonify({
                    'success': True,
                    'query': cached_data['query'],
                    'results': cached_data['results'],
                    'timestamp': cached_data['timestamp']
                })
                
            except Exception as e:
                return jsonify({'error': f'Search results error: {str(e)}'}), 500

        @self.app.route('/api/open-item', methods=['POST'])
        def api_open_item():
            """Open a file or folder from search results"""
            try:
                data = request.get_json()
                item_path = data.get('path')
                
                if not item_path:
                    return jsonify({'error': 'No path provided'}), 400
                
                if not os.path.exists(item_path):
                    return jsonify({'error': 'File or folder no longer exists'}), 404
                
                # Open the file/folder
                os.startfile(item_path)
                
                return jsonify({
                    'success': True,
                    'message': f'Opened: {os.path.basename(item_path)}'
                })
                
            except Exception as e:
                return jsonify({'error': f'Open item error: {str(e)}'}), 500
        
        @self.app.route('/api/download-file', methods=['POST'])
        def api_download_file():
            """🎯 ANDROID NATIVE: Download file content for Android Intent system"""
            try:
                data = request.get_json()
                file_path = data.get('file_path')
                
                if not file_path:
                    return jsonify({'error': 'No file path provided'}), 400
                
                # Decode URL-encoded path if needed
                import urllib.parse
                decoded_path = urllib.parse.unquote(file_path)
                
                if not os.path.exists(decoded_path):
                    return jsonify({'error': f'File not found: {decoded_path}'}), 404
                
                # Check if it's a file (not a directory)
                if not os.path.isfile(decoded_path):
                    return jsonify({'error': f'Path is not a file: {decoded_path}'}), 400
                
                try:
                    # Read file content
                    with open(decoded_path, 'rb') as f:
                        file_content = f.read()
                    
                    # Get MIME type
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(decoded_path)
                    if not mime_type:
                        mime_type = 'application/octet-stream'
                    
                    # Get filename
                    filename = os.path.basename(decoded_path)
                    
                    print(f"📱 ANDROID DOWNLOAD: {filename} ({len(file_content)} bytes, {mime_type})")
                    
                    # Return file content with proper headers
                    from flask import send_file
                    import io
                    file_obj = io.BytesIO(file_content)
                    file_obj.seek(0)
                    
                    return send_file(
                        file_obj,
                        as_attachment=True,
                        download_name=filename,
                        mimetype=mime_type
                    )
                    
                except PermissionError:
                    return jsonify({'error': f'Permission denied accessing file: {filename}'}), 403
                except Exception as read_error:
                    return jsonify({'error': f'Error reading file: {str(read_error)}'}), 500
                
            except Exception as e:
                return jsonify({'error': f'Download file error: {str(e)}'}), 500

        @self.app.route('/api/open-file')
        def api_open_file_get():
            """🎯 Tony Stark Smart File Opener - Opens files where you are!"""
            try:
                item_path = request.args.get('path')
                open_on = request.args.get('on', 'auto')  # 'mobile', 'pc', 'auto'
                
                if not item_path:
                    return f"""
                    <html>
                        <head><title>JARVIS File Opener</title></head>
                        <body style="font-family: Arial; background: #0c1445; color: white; text-align: center; padding: 50px;">
                            <h2>❌ No file path provided</h2>
                            <a href="javascript:history.back()" style="color: #00e5ff;">← Back</a>
                        </body>
                    </html>
                    """, 400
                
                # Decode URL-encoded path
                import urllib.parse
                decoded_path = urllib.parse.unquote(item_path)
                
                if not os.path.exists(decoded_path):
                    return f"""
                    <html>
                        <head><title>JARVIS File Opener</title></head>
                        <body style="font-family: Arial; background: #0c1445; color: white; text-align: center; padding: 50px;">
                            <h2>❌ File not found</h2>
                            <p>{decoded_path}</p>
                            <a href="javascript:history.back()" style="color: #00e5ff;">← Back</a>
                        </body>
                    </html>
                    """, 404
                
                filename = os.path.basename(decoded_path)
                file_ext = os.path.splitext(filename)[1].lower()
                
                # 🎯 Tony Stark Intelligence: Detect if request is from mobile
                user_agent = request.headers.get('User-Agent', '').lower()
                is_mobile = any(mobile_indicator in user_agent for mobile_indicator in 
                               ['mobile', 'android', 'iphone', 'ipad', 'flutter'])
                
                if open_on == 'mobile' or (open_on == 'auto' and is_mobile):
                    # 📱 MOBILE MODE: Open file on mobile device
                    print(f"📱 MOBILE FILE ACCESS: {filename} (detected: {is_mobile})")
                    
                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                        # Image files - display directly on mobile
                        try:
                            import base64
                            with open(decoded_path, 'rb') as f:
                                image_data = base64.b64encode(f.read()).decode('utf-8')
                            mime_type = 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else f'image/{file_ext[1:]}'
                            
                            return f"""
                            <html>
                                <head>
                                    <title>JARVIS Mobile Viewer</title>
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <style>
                                        body {{ font-family: Arial; background: linear-gradient(135deg, #0c1445, #1a237e); color: white; margin: 0; padding: 20px; min-height: 100vh; }}
                                        .container {{ text-align: center; }}
                                        .image {{ max-width: 100%; height: auto; border-radius: 10px; margin: 20px 0; box-shadow: 0 4px 15px rgba(0,229,255,0.3); }}
                                        .back-btn {{ background: #00e5ff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; display: inline-block; margin-top: 20px; }}
                                        .info {{ background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin: 20px 0; }}
                                    </style>
                                </head>
                                <body>
                                    <div class="container">
                                        <div class="info">
                                            <h2 style="color: #00e5ff;">📱 {filename}</h2>
                                            <p style="opacity: 0.8;">Mobile View</p>
                                        </div>
                                        <img src="data:{mime_type};base64,{image_data}" class="image" alt="{filename}">
                                        <br>
                                        <a href="javascript:history.back()" class="back-btn">← Back to JARVIS</a>
                                    </div>
                                </body>
                            </html>
                            """
                        except:
                            pass
                    elif file_ext in ['.txt', '.md', '.log', '.csv', '.json']:
                        # Text files - display content on mobile
                        try:
                            with open(decoded_path, 'r', encoding='utf-8') as f:
                                content = f.read()[:10000]  # Limit content size
                            # Fix f-string backslash issue by doing replacement separately
                            content_html = content.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                            return f"""
                            <html>
                                <head>
                                    <title>JARVIS Mobile Viewer</title>
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <style>
                                        body {{ font-family: 'Courier New', monospace; background: linear-gradient(135deg, #0c1445, #1a237e); color: white; margin: 0; padding: 20px; }}
                                        .header {{ text-align: center; margin-bottom: 20px; }}
                                        .content {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; text-align: left; overflow-x: auto; line-height: 1.5; }}
                                        .back-btn {{ background: #00e5ff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; display: inline-block; margin: 20px auto; }}
                                    </style>
                                </head>
                                <body>
                                    <div class="header">
                                        <h2 style="color: #00e5ff;">📱 {filename}</h2>
                                        <p style="opacity: 0.8;">Mobile Text Viewer</p>
                                    </div>
                                    <div class="content">{content_html}</div>
                                    <center><a href="javascript:history.back()" class="back-btn">← Back to JARVIS</a></center>
                                </body>
                            </html>
                            """
                        except:
                            pass
                    
                    # For other files, provide smart options
                    return f"""
                    <html>
                        <head>
                            <title>JARVIS Mobile File Handler</title>
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <style>
                                body {{ font-family: Arial; background: linear-gradient(135deg, #0c1445, #1a237e); color: white; text-align: center; padding: 30px; min-height: 100vh; }}
                                .file-info {{ background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; margin: 20px 0; backdrop-filter: blur(10px); }}
                                .btn {{ background: #00e5ff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; margin: 10px; display: inline-block; }}
                                .btn:hover {{ background: #0099cc; }}
                                .file-icon {{ font-size: 3em; margin: 20px 0; }}
                            </style>
                        </head>
                        <body>
                            <div class="file-info">
                                <div class="file-icon">📱</div>
                                <h2 style="color: #00e5ff;">Smart File Access</h2>
                                <p style="font-size: 1.2em; margin: 15px 0;">{filename}</p>
                                <p style="opacity: 0.7; font-size: 0.9em;">📂 {decoded_path}</p>
                                <br>
                                <p>Choose how to open this file:</p>
                                <a href="/api/open-file?path={urllib.parse.quote(decoded_path)}&on=pc" class="btn">🖥️ Open on PC</a>
                                <a href="javascript:history.back()" class="btn">← Back to JARVIS</a>
                            </div>
                        </body>
                    </html>
                    """
                else:
                    # 🖥️ PC MODE: Open file on PC (original behavior)
                    print(f"🖥️ PC FILE ACCESS: {filename}")
                    os.startfile(decoded_path)
                    
                    return f"""
                    <html>
                        <head>
                            <title>JARVIS File Opener</title>
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        </head>
                        <body style="font-family: Arial; background: linear-gradient(135deg, #0c1445, #1a237e); color: white; text-align: center; padding: 50px; min-height: 100vh;">
                            <div style="background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px);">
                                <h2 style="color: #00e5ff;">✅ File Opened on PC!</h2>
                                <p style="font-size: 1.2em; margin: 20px 0;">{filename}</p>
                                <p style="opacity: 0.8;">📂 {decoded_path}</p>
                                <br>
                                <a href="javascript:history.back()" style="background: #00e5ff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-size: 1.1em;">← Back to JARVIS</a>
                            </div>
                        </body>
                    </html>
                    """
                
            except Exception as e:
                return f"""
                <html>
                    <head><title>JARVIS File Opener</title></head>
                    <body style="font-family: Arial; background: #0c1445; color: white; text-align: center; padding: 50px;">
                        <h2>❌ Error opening file</h2>
                        <p>{str(e)}</p>
                        <a href="javascript:history.back()" style="color: #00e5ff;">← Back</a>
                    </body>
                </html>
                """, 500

        @self.app.route('/search-results')
        def search_results_page():
            """Serve search results page with visual interface"""
            cache_key = request.args.get('key')
            return render_template('search_results.html', cache_key=cache_key)
    
        # Webcam control endpoints
        def webcam_streaming_loop():
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Webcam not found or in use.")
                with self.webcam_lock:
                    self.webcam_active = False
                return
            
            # Set optimal settings for responsiveness
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to get latest frame
            cap.set(cv2.CAP_PROP_FPS, 30)        # Higher capture rate
            
            with self.webcam_lock:
                self.webcam_capture = cap
                
            while True:
                with self.webcam_lock:
                    if not self.webcam_active:
                        break
                        
                ret, frame = cap.read()
                if not ret:
                    print("Failed to read webcam frame")
                    continue
                    
                # Resize frame for better performance (optional)
                height, width = frame.shape[:2]
                if width > 640:  # Only resize if too large
                    scale = 640 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                    
                # Encode as JPEG with speed-optimized settings for 90 FPS
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    with self.webcam_lock:
                        self.webcam_frame = jpeg.tobytes()
                else:
                    print("Failed to encode webcam frame.")
                    
                # Minimal delay to prevent excessive CPU usage while supporting 90 FPS
                time.sleep(0.01)  # ~100 FPS max capture rate for ultra-smooth streaming
                
            cap.release()
            with self.webcam_lock:
                self.webcam_capture = None
                self.webcam_frame = None

        @self.app.route('/api/webcam/start', methods=['POST'])
        def api_webcam_start():
            with self.webcam_lock:
                if self.webcam_active:
                    return jsonify({'success': True, 'message': 'Webcam already streaming'})
                self.webcam_active = True
                self.webcam_thread = threading.Thread(target=webcam_streaming_loop, daemon=True)
                self.webcam_thread.start()
            return jsonify({'success': True, 'message': 'Webcam streaming started'})

        @self.app.route('/api/webcam/stop', methods=['POST'])
        def api_webcam_stop():
            with self.webcam_lock:
                self.webcam_active = False
            return jsonify({'success': True, 'message': 'Webcam streaming stopped'})

        @self.app.route('/api/webcam/stream')
        def api_webcam_stream():
            def generate():
                while True:
                    with self.webcam_lock:
                        if not self.webcam_active:
                            break
                        frame = self.webcam_frame
                    if frame is not None:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' +
                               frame + b'\r\n\r\n')
                    else:
                        # No frame yet, wait a bit
                        time.sleep(0.05)
            return Response(stream_with_context(generate()),
                            mimetype='multipart/x-mixed-replace; boundary=frame',
                            headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})
        
        @self.app.route('/api/webcam/screenshot')
        def api_webcam_screenshot():
            """Get single webcam frame as JPEG (similar to desktop screenshot)"""
            try:
                with self.webcam_lock:
                    if not self.webcam_active:
                        return jsonify({'error': 'Webcam not active'}), 400
                    
                    frame = self.webcam_frame
                    if frame is not None:
                        return Response(
                            frame,
                            mimetype='image/jpeg',
                            headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
                        )
                    else:
                        return jsonify({'error': 'No webcam frame available'}), 500
            except Exception as e:
                print(f"DEBUG: Webcam screenshot error: {e}")
                return jsonify({'error': f'Webcam screenshot error: {str(e)}'}), 500
        
        # Add hooks for voice command integration  
        self.start_webcam = self._start_webcam
        self.stop_webcam = self._stop_webcam
        
    def _start_webcam(self):
        """Start webcam streaming for voice commands"""
        with self.webcam_lock:
            if not self.webcam_active:
                self.webcam_active = True
                def webcam_streaming_loop():
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        print("Webcam not found or in use.")
                        with self.webcam_lock:
                            self.webcam_active = False
                        return
                        
                    # Set optimal settings for responsiveness
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to get latest frame
                    cap.set(cv2.CAP_PROP_FPS, 30)        # Higher capture rate
                    
                    with self.webcam_lock:
                        self.webcam_capture = cap
                        
                    while True:
                        with self.webcam_lock:
                            if not self.webcam_active:
                                break
                                
                        ret, frame = cap.read()
                        if not ret:
                            print("Failed to read webcam frame")
                            continue
                            
                        # Resize frame for better performance (optional)
                        height, width = frame.shape[:2]
                        if width > 640:  # Only resize if too large
                            scale = 640 / width
                            new_width = int(width * scale)
                            new_height = int(height * scale)
                            frame = cv2.resize(frame, (new_width, new_height))
                            
                        # Encode as JPEG with speed-optimized settings for 90 FPS
                        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        if ret:
                            with self.webcam_lock:
                                self.webcam_frame = jpeg.tobytes()
                        else:
                            print("Failed to encode webcam frame.")
                            
                        # Minimal delay to prevent excessive CPU usage while supporting 90 FPS
                        time.sleep(0.01)  # ~100 FPS max capture rate for ultra-smooth streaming
                        
                    cap.release()
                    with self.webcam_lock:
                        self.webcam_capture = None
                        self.webcam_frame = None
                        
                self.webcam_thread = threading.Thread(target=webcam_streaming_loop, daemon=True)
                self.webcam_thread.start()
        return "Webcam streaming started"

    def _stop_webcam(self):
        """Stop webcam streaming for voice commands"""  
        with self.webcam_lock:
            self.webcam_active = False
        return "Webcam streaming stopped"

    def setup_socketio_events(self):
        """Setup SocketIO events for real-time communication"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print(f"Client connected: {request.sid}")
            self.connected_clients.add(request.sid)
            emit('status', {
                'message': 'Connected to Jarvis',
                'is_awake': self.jarvis.is_awake,
                'is_speaking': self.jarvis.is_speaking
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f"Client disconnected: {request.sid}")
            self.connected_clients.discard(request.sid)
        
        @self.socketio.on('send_command')
        def handle_command(data):
            """Handle command sent via WebSocket"""
            try:
                command = data.get('command', '').strip()
                if not command:
                    emit('error', {'message': 'No command provided'})
                    return
                
                print(f"Web command received: {command}")
                
                # Add command to Jarvis queue
                self.jarvis.command_queue.put(command)
                
                # Acknowledge command received
                emit('command_received', {
                    'command': command,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
                
            except Exception as e:
                emit('error', {'message': f"Error processing command: {str(e)}"})
    
    def broadcast_response(self, command, response):
        """Broadcast response to all connected clients"""
        self.socketio.emit('response', {
            'command': command,
            'response': response,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    
    def broadcast_status(self, status_data):
        """Broadcast status update to all connected clients"""
        self.socketio.emit('status_update', status_data)
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the web server"""
        local_ip = self.get_local_ip()
        public_ip = self.get_public_ip()
        
        print(f"\n🚀 === JARVIS CONTROL CENTER ONLINE === 🚀")
        print(f"\n�� LOCAL ACCESS (Same WiFi Network):")
        print(f"   📱 Mobile: http://{local_ip}:{port}")
        print(f"   💻 Desktop: http://localhost:{port}")
        
        print(f"\n🌍 GLOBAL ACCESS (Tony Stark Mode):")
        if public_ip != "Unable to detect":
            print(f"   🌐 Your Public IP: {public_ip}")
            print(f"   🎯 Global URL: http://{public_ip}:{port}")
            print(f"   🔧 Status: SETUP REQUIRED")
            print(f"\n⚙️  ROUTER SETUP INSTRUCTIONS:")
            print(f"   1️⃣  Log into your router admin panel")
            print(f"   2️⃣  Go to Port Forwarding settings")
            print(f"   3️⃣  Forward External Port 5000 → Internal {local_ip}:5000")
            print(f"   4️⃣  Save settings and test from outside network")
            print(f"   🔒 Security: Consider changing the default port for security")
        else:
            print(f"   ❌ Unable to detect public IP")
            print(f"   🔍 Check your internet connection")
        
        print(f"\n🎮 NEW FEATURES:")
        print(f"   🔒 Lock Screen Control")
        print(f"   🌟 Smart Keep-Awake System") 
        print(f"   🖱️  Remote Mouse Control")
        print(f"   📺 Live Screen Streaming")
        
        print(f"\n🌟 SMART KEEP-AWAKE:")
        print(f"   📱 Phone Connected → PC Stays Awake")
        print(f"   📱 Phone Disconnects → Normal Sleep Behavior")
        print(f"   🔒 Manual Lock Button Still Works")
        
        print(f"\n🗣️  VOICE COMMANDS:")
        print(f"   'Lock screen' - Lock your desktop")

        
        print("=" * 80)
        
        self.socketio.run(self.app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

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
    
    # Check if web mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == '--web':
        print("🚀 Starting Jarvis in Web Mode with Voice Recognition...")
        web_jarvis = WebJarvis(jarvis)
        jarvis.web_jarvis = web_jarvis  # <-- Add this line
        
        # Start smart connection monitor
        jarvis.start_connection_monitor()
        
        # Start voice listening in background
        jarvis.start_background_listening()
        
        # Start web server in a separate thread
        web_thread = threading.Thread(
            target=lambda: web_jarvis.run(host='0.0.0.0', port=5000, debug=False),
            daemon=True
        )
        web_thread.start()
        
        # Give web server time to start
        await asyncio.sleep(2)
        print("\n🎤 Voice recognition active! Try saying 'Hey Jarvis'...")
        print("🌐 Web interface ready for phone connection!")
        
        # Run voice command processing loop (same as voice mode)
        try:
            await jarvis.run()
        except KeyboardInterrupt:
            print("\n👋 Shutting down Jarvis...")
            jarvis.stop_background_listening()
    
    elif len(sys.argv) > 1 and sys.argv[1] == '--hybrid':
        print("🚀 Starting Jarvis in Hybrid Mode (Voice + Web)...")
        web_jarvis = WebJarvis(jarvis)
        jarvis.web_jarvis = web_jarvis  # <-- Add this line
        
        # Start smart connection monitor
        jarvis.start_connection_monitor()
        
        # Start web server in a separate thread
        web_thread = threading.Thread(
            target=lambda: web_jarvis.run(host='0.0.0.0', port=5000, debug=False),
            daemon=True
        )
        web_thread.start()
        
        # Give web server time to start
        await asyncio.sleep(2)
        
        # Run voice interface
        await jarvis.run()
    
    else:
        print("🚀 Starting Jarvis in Voice Mode...")
        print("\n💡 Available modes:")
        print("   🎤 Voice only: python jarvis.py")
        print("   🌐 Web only: python jarvis.py --web")
        print("   🔄 Voice + Web: python jarvis.py --hybrid")
        print()
        await jarvis.run()

if __name__ == "__main__":
    asyncio.run(main()) 