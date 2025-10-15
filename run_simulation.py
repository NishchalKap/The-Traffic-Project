#!/usr/bin/env python3
"""
Quick start script for Smart Traffic Light Controller Simulation
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def check_requirements():
    """Check if required packages are installed."""
    try:
        import flask
        import cv2
        import numpy
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def start_web_server():
    """Start the web server."""
    print("🚀 Starting Smart Traffic Light Controller Web Server...")
    print("📱 Web Dashboard: http://localhost:5000")
    print("🎮 Simulation Dashboard: http://localhost:5000/simulation")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 60)
    
    try:
        # Change to the project directory
        project_dir = Path(__file__).parent
        os.chdir(project_dir)
        
        # Start the web server
        subprocess.run([sys.executable, "web/app.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function."""
    print("🚦 Smart Traffic Light Controller - Quick Start")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Start Web Dashboard (Live Mode)")
    print("2. Start Simulation Dashboard (Testing Mode)")
    print("3. Run Command Line Controller")
    print("4. Run Tests")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        print("\n🌐 Starting Web Dashboard...")
        start_web_server()
    elif choice == "2":
        print("\n🎮 Starting Simulation Dashboard...")
        start_web_server()
    elif choice == "3":
        print("\n🖥️  Starting Command Line Controller...")
        subprocess.run([sys.executable, "main.py"])
    elif choice == "4":
        print("\n🧪 Running Tests...")
        subprocess.run([sys.executable, "test_traffic_system.py"])
    else:
        print("❌ Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()
