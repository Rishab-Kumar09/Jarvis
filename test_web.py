#!/usr/bin/env python3
"""
Simple test script to verify Jarvis web interface functionality
"""

import sys
import os
import time
import threading
import webbrowser
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from jarvis import Jarvis, WebJarvis
    print("✅ Successfully imported Jarvis classes")
except ImportError as e:
    print(f"❌ Failed to import Jarvis: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

def test_basic_functionality():
    """Test basic Jarvis functionality"""
    print("\n🧪 Testing basic Jarvis functionality...")
    
    try:
        # Create Jarvis instance (without starting voice listening)
        jarvis = Jarvis()
        print("✅ Jarvis instance created successfully")
        
        # Test WebJarvis creation
        web_jarvis = WebJarvis(jarvis)
        print("✅ WebJarvis instance created successfully")
        
        # Get local IP
        local_ip = web_jarvis.get_local_ip()
        print(f"✅ Local IP detected: {local_ip}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in basic functionality test: {e}")
        return False

def test_web_server():
    """Test web server startup"""
    print("\n🌐 Testing web server startup...")
    
    try:
        # Create Jarvis and WebJarvis instances
        jarvis = Jarvis()
        web_jarvis = WebJarvis(jarvis)
        
        print("🚀 Starting web server on port 5000...")
        print("📱 You can test the interface by opening: http://localhost:5000")
        print("⚠️  Press Ctrl+C to stop the server\n")
        
        # Start the web server
        web_jarvis.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n👋 Web server stopped by user")
    except Exception as e:
        print(f"❌ Error starting web server: {e}")

if __name__ == "__main__":
    print("🤖 Jarvis Web Interface Test")
    print("=" * 40)
    
    # Test basic functionality first
    if test_basic_functionality():
        print("\n✅ All basic tests passed!")
        
        # Ask user if they want to test web server
        response = input("\n🌐 Would you like to test the web server? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            test_web_server()
        else:
            print("👍 Test completed. Run with 'python jarvis.py --web' to start the web interface!")
    else:
        print("\n❌ Basic tests failed. Please check your setup.")
        sys.exit(1) 