#!/usr/bin/env python3
"""
BuzzUploader - A terminal-based file uploader for BuzzHeavier with a slick TUI
"""

import sys
from .app import BuzzUploaderApp

def main():
    """Main entry point for the application"""
    app = BuzzUploaderApp()
    app.run()

if __name__ == "__main__":
    main()
