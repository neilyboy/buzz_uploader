#!/usr/bin/env python3
"""
Launcher script for BuzzUploader
"""

import sys
import subprocess
import os

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import textual
        import requests
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Installing required dependencies...")
        
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        requirements_path = os.path.join(script_dir, "requirements.txt")
        
        # Install dependencies
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", requirements_path
            ])
            return True
        except subprocess.CalledProcessError:
            print("Failed to install dependencies. Please install them manually:")
            print("pip install -r requirements.txt")
            return False

def main():
    """Main entry point"""
    if not check_dependencies():
        return 1
    
    # Import and run the app
    from buzz_uploader.app import BuzzUploaderApp
    app = BuzzUploaderApp()
    app.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
