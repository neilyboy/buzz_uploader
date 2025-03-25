#!/usr/bin/env python3
"""
BuzzUploader - A terminal-based file uploader for BuzzHeavier with a slick TUI
"""

import os
import sys
import base64
import requests
import logging
import traceback
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DirectoryTree, DataTable, Static, Button, Input, Label
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from textual.reactive import reactive
from textual import events
from textual.screen import Screen
from textual.message import Message
from textual.coordinate import Coordinate
from textual.keys import Keys

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to INFO for normal operation
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="buzz_uploader.log",
    filemode="a",  # Append to log file
)
logger = logging.getLogger("buzz_uploader")

class UploadConfig:
    """Configuration for BuzzHeavier uploads"""
    
    def __init__(self):
        self.api_key: Optional[str] = os.environ.get("BUZZHEAVIER_API_KEY")
        self.parent_id: Optional[str] = None
        self.location_id: Optional[str] = None
        self.note: Optional[str] = None
        self.base_url = "https://w.buzzheavier.com"
        self.api_url = "https://buzzheavier.com/api"
    
    def is_authenticated(self) -> bool:
        """Check if API key is set"""
        return bool(self.api_key and self.api_key.strip())

class SelectableDataTable(DataTable):
    """Custom DataTable that properly handles key presses for selection"""
    
    class SelectKeyPressed(Message):
        """Message sent when selection key ('s') is pressed"""
    
    class EnterPressed(Message):
        """Message sent when enter is pressed"""
    
    def on_key(self, event: events.Key) -> bool:
        """Handle key events"""
        # Handle 's' key for selection
        if event.key == "s":
            # Post a message to the app
            self.post_message(self.SelectKeyPressed())
            # Prevent the event from propagating
            event.prevent_default()
            event.stop()
            return True
        
        # Handle enter key specially
        if event.key == "enter" or event.key == Keys.Enter:
            # Post a message to the app
            self.post_message(self.EnterPressed())
            # Prevent the event from propagating
            event.prevent_default()
            event.stop()
            return True
        
        # For all other keys, let the event propagate
        return False

class FileItem:
    """Represents a file or directory for upload"""
    
    def __init__(self, path: Path, is_selected: bool = False):
        # Ensure path is a Path object
        self.path = Path(path) if not isinstance(path, Path) else path
        self._is_selected = is_selected  # Use private attribute with property
        
        # Verify the path exists before checking attributes
        if self.path.exists():
            self.is_dir = self.path.is_dir()
            self.size = self.path.stat().st_size if self.path.is_file() else 0
            self.name = self.path.name
        else:
            # Default values if path doesn't exist
            logger.warning(f"Path does not exist: {self.path}")
            self.is_dir = False
            self.size = 0
            self.name = self.path.name
        
        # Prevent selecting directories
        if self.is_dir:
            self._is_selected = False
        
        # Store upload results
        self.upload_url = None  # Will be set after successful upload
            
        logger.info(f"FileItem created: {self.path}, is_dir: {self.is_dir}, size: {self.size}, selected: {self._is_selected}")
    
    @property
    def is_selected(self) -> bool:
        """Get selection status"""
        return self._is_selected
    
    @is_selected.setter
    def is_selected(self, value: bool) -> None:
        """Set selection status"""
        # Don't allow selecting directories
        if self.is_dir and value:
            logger.warning(f"Cannot select directory: {self.path}")
            return
        self._is_selected = value
        logger.info(f"Selection status changed for {self.path}: {self._is_selected}")
    
    def __str__(self) -> str:
        return f"{'📁' if self.is_dir else '📄'} {self.name}"
    
    def get_size_str(self) -> str:
        """Get human-readable size string"""
        if self.is_dir:
            return "DIR"
        
        size = self.size  # Create a copy to avoid modifying the original
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

class SettingsScreen(Screen):
    """Settings screen for API configuration"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+s", "save", "Save"),
    ]
    
    def __init__(self, config: UploadConfig):
        super().__init__()
        self.config = config
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Container(id="settings-container"):
            yield Label("BuzzHeavier API Settings", id="settings-title")
            
            with Vertical(id="settings-form"):
                yield Label("API Key (Bearer Token)")
                yield Input(
                    value=self.config.api_key or "", 
                    placeholder="Your BuzzHeavier Account ID",
                    id="api-key-input",
                    password=True
                )
                
                yield Label("Parent Directory ID (optional)")
                yield Input(
                    value=self.config.parent_id or "",
                    placeholder="ID of directory where files will be uploaded",
                    id="parent-id-input"
                )
                
                yield Label("Location ID (optional)")
                yield Input(
                    value=self.config.location_id or "",
                    placeholder="Storage location ID",
                    id="location-id-input"
                )
                
                yield Label("Default Note (optional)")
                yield Input(
                    value=self.config.note or "",
                    placeholder="Note to show under download link",
                    id="note-input"
                )
            
            with Horizontal(id="settings-buttons"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")
        
        # Create a custom footer with clear key binding instructions
        footer = Footer()
        # Add custom key binding display
        yield footer
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "cancel-button":
            self.app.pop_screen()
    
    def action_save(self) -> None:
        """Save settings"""
        self.config.api_key = self.query_one("#api-key-input", Input).value
        self.config.parent_id = self.query_one("#parent-id-input", Input).value
        self.config.location_id = self.query_one("#location-id-input", Input).value
        self.config.note = self.query_one("#note-input", Input).value
        
        # Save to environment variable for persistence
        if self.config.api_key:
            os.environ["BUZZHEAVIER_API_KEY"] = self.config.api_key
        
        self.app.notify("Settings saved successfully", title="Success")
        self.app.pop_screen()

class UploadProgressScreen(Screen):
    """Screen showing upload progress"""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]
    
    class UploadComplete(Message):
        """Message sent when upload is complete"""
        def __init__(self, success: bool, message: str):
            self.success = success
            self.message = message
            super().__init__()
    
    def __init__(self, files: List[FileItem], config: UploadConfig):
        super().__init__()
        
        # Filter out only valid, selected files for upload
        self.upload_files = []
        
        # Log what we received
        logger.info(f"UploadProgressScreen received {len(files)} files")
        for i, f in enumerate(files):
            logger.info(f"  Received file {i}: {f.path}, selected: {f.is_selected}, is_dir: {f.is_dir}")
        
        # Process each file to ensure it's valid for upload
        for f in files:
            if not f.is_selected:
                logger.warning(f"Skipping unselected file: {f.path}")
                continue
                
            if f.is_dir:
                logger.warning(f"Skipping directory: {f.path}")
                continue
                
            # Get the path and verify it exists
            path = Path(f.path) if not isinstance(f.path, Path) else f.path
            
            if not path.exists():
                logger.warning(f"Skipping non-existent file: {path}")
                continue
                
            if not path.is_file():
                logger.warning(f"Skipping non-file: {path}")
                continue
                
            # File is valid for upload, add it to our list
            self.upload_files.append(f)
            logger.info(f"Added to upload queue: {path}")
        
        self.config = config
        self.current_index = 0
        self.results: List[Tuple[FileItem, bool, str]] = []
        
        # Log the final upload list
        logger.info(f"UploadProgressScreen prepared {len(self.upload_files)} files for upload")
        for i, f in enumerate(self.upload_files):
            logger.info(f"  File {i} to upload: {f.path}, size: {f.size}")
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        # Get the total number of files for initial display
        total_files = len(self.upload_files)
        
        with Container(id="upload-container"):
            yield Label("Uploading Files to BuzzHeavier", id="upload-title")
            yield Static("Preparing to upload...", id="upload-status")
            yield Static(f"0 / {total_files}", id="upload-progress")
            
            with Container(id="results-container"):
                yield DataTable(id="results-table")
            
            with Horizontal(id="button-container"):
                yield Button("Copy URLs", variant="success", id="copy-button", disabled=True)
                yield Button("Close", variant="primary", id="close-button")
        
        # Create a custom footer with clear key binding instructions
        footer = Footer()
        # Add custom key binding display
        yield footer
    
    async def on_mount(self) -> None:
        """Set up the screen when mounted"""
        # Set up the results table
        table = self.query_one("#results-table", DataTable)
        table.add_columns("File", "Status", "Message")
        
        # Update the status display with the file count
        total_files = len(self.upload_files)
        progress = self.query_one("#upload-progress", Static)
        progress.update(f"0 / {total_files}")
        
        # Log the file count for debugging
        logger.info(f"UploadProgressScreen mounted with {total_files} files ready for upload")
        
        # Start upload process asynchronously
        self.app.call_later(self.start_uploads)
    
    def action_close(self) -> None:
        """Close the screen"""
        logger.info("Closing upload screen via action_close")
        self.app.pop_screen()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        if event.button.id == "close-button":
            logger.info("Close button pressed")
            self.action_close()
        elif event.button.id == "copy-button":
            logger.info("Copy URLs button pressed")
            self.copy_urls_to_clipboard()
            
    def copy_urls_to_clipboard(self) -> None:
        """Copy all successful upload URLs to clipboard"""
        # Get all successful uploads with URLs
        successful_uploads = []
        for file_item, success, _ in self.results:
            if success and hasattr(file_item, 'upload_url') and file_item.upload_url:
                successful_uploads.append(f"{file_item.name}: {file_item.upload_url}")
        
        if not successful_uploads:
            self.app.notify("No successful uploads to copy", title="Copy Failed")
            return
            
        # Join all URLs with newlines
        clipboard_text = "\n".join(successful_uploads)
        
        try:
            # Try using xclip directly first (since we just installed it)
            try:
                import subprocess
                logger.info("Attempting to copy with xclip")
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                process.communicate(input=clipboard_text.encode())
                if process.returncode == 0:
                    self.app.notify(f"Copied {len(successful_uploads)} URLs to clipboard", title="Copy Success")
                    return
                else:
                    logger.warning("xclip process returned non-zero exit code")
            except Exception as e:
                logger.warning(f"xclip attempt failed: {e}")
                
            # Try pyperclip as a fallback
            try:
                import pyperclip
                logger.info("Attempting to copy with pyperclip")
                pyperclip.copy(clipboard_text)
                self.app.notify(f"Copied {len(successful_uploads)} URLs to clipboard", title="Copy Success")
                return
            except Exception as e:
                logger.warning(f"pyperclip attempt failed: {e}")
                raise Exception("All clipboard methods failed")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            # Also show the URLs in a notification so the user can manually copy them
            self.app.notify(f"Failed to copy to clipboard. Here are your URLs:\n{clipboard_text[:100]}{'...' if len(clipboard_text) > 100 else ''}", title="Copy Failed")
    
    async def start_uploads(self) -> None:
        """Start the upload process for all files"""
        status = self.query_one("#upload-status", Static)
        progress = self.query_one("#upload-progress", Static)
        table = self.query_one("#results-table", DataTable)
        close_button = self.query_one("#close-button", Button)
        
        # Disable close button until upload is complete
        close_button.disabled = True
        
        # Get the total number of files to upload
        total_files = len(self.upload_files)
        logger.info(f"Starting upload process for {total_files} files")
        
        # Update the UI to show the correct file count
        if total_files == 0:
            status.update("No files selected for upload")
            progress.update("0 / 0")
            close_button.disabled = False
            return
        
        # Update the progress display with the correct total
        status.update("Starting uploads...")
        progress.update(f"0 / {total_files}")
        
        # Force UI update before starting uploads
        await asyncio.sleep(0.1)
        
        # Process each file in our upload queue
        for i, file_item in enumerate(self.upload_files):
            self.current_index = i + 1
            status.update(f"Uploading: {file_item.name}")
            progress.update(f"{self.current_index} / {total_files}")
            
            # Perform the actual upload
            try:
                # Call the upload_file method directly since it's now async
                logger.info(f"Starting upload for {file_item.name}")
                
                # Force UI update before starting the upload
                await asyncio.sleep(0.1)
                
                success, message = await self.upload_file(file_item)
                logger.info(f"Upload completed for {file_item.name}: success={success}, message={message}")
                
                self.results.append((file_item, success, message))
                table.add_row(
                    str(file_item.name),  # Just show the filename, not the full path
                    "✅ Success" if success else "❌ Failed",
                    message
                )
                
                # Force UI update after each file upload
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.exception(f"Error uploading {file_item.name}: {e}")
                self.results.append((file_item, False, f"Error: {str(e)}"))
                table.add_row(
                    str(file_item.name),
                    "❌ Failed",
                    f"Error: {str(e)}"
                )
                
                # Force UI update after error
                await asyncio.sleep(0.1)
        
        status.update("Upload process complete")
        
        # Enable both buttons
        self.query_one("#close-button", Button).disabled = False
        
        # Enable the Copy URLs button if there were any successful uploads
        success_count = sum(1 for _, success, _ in self.results if success)
        copy_button = self.query_one("#copy-button", Button)
        copy_button.disabled = (success_count == 0)
        
        # Send completion message
        self.post_message(self.UploadComplete(
            success=(success_count == total_files),
            message=f"Successfully uploaded {success_count} of {total_files} files"
        ))
        
        # Make sure the close button is enabled
        close_button = self.query_one("#close-button", Button)
        close_button.disabled = False
        logger.info("Upload complete, close button enabled")
    
    async def upload_file(self, file_item: FileItem) -> Tuple[bool, str]:
        """Upload a single file to BuzzHeavier"""
        try:
            # Verify the file exists and is accessible
            path = Path(file_item.path) if not isinstance(file_item.path, Path) else file_item.path
            
            # Double-check that the file exists and is a file
            if not path.exists():
                logger.error(f"File does not exist: {path}")
                return False, f"File does not exist: {path}"
            
            if not path.is_file() or path.is_dir():
                logger.error(f"Not a valid file: {path}")
                return False, f"Not a valid file: {path}"
            
            # Verify file is readable
            try:
                with open(path, "rb") as test_read:
                    # Just read a small chunk to verify it's readable
                    test_read.read(1024)
            except (IOError, PermissionError) as e:
                logger.error(f"Cannot read file: {path} - {str(e)}")
                return False, f"Cannot read file: {str(e)}"
            
            # Log file details before upload
            file_size = path.stat().st_size
            logger.info(f"Uploading file: {path}, size: {file_size} bytes")
            
            # Prepare the URL based on configuration
            url = f"{self.config.base_url}/{file_item.name}"
            
            # Add parameters if needed
            params = {}
            
            if self.config.parent_id:
                # If parent ID is specified, use the parent ID endpoint
                url = f"{self.config.base_url}/{self.config.parent_id}/{file_item.name}"
                logger.info(f"Using parent ID URL: {url}")
            elif self.config.location_id:
                # If location ID is specified, add it as a parameter
                params["locationId"] = self.config.location_id
                logger.info(f"Using location ID: {self.config.location_id}")
            
            if self.config.note:
                # If note is specified, encode it as base64 and add as parameter
                note_b64 = base64.b64encode(self.config.note.encode()).decode()
                params["note"] = note_b64
                logger.info("Added note to upload")
            
            # Prepare headers
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
                logger.info("Added authorization header")
            else:
                logger.info("Uploading anonymously (no API key)")
            
            # Log the request details
            logger.info(f"Upload request - URL: {url}, Params: {params}, Headers: {headers if not self.config.api_key else 'Contains API key'}")
            
            # For testing purposes, simulate a successful upload after a delay
            # In a real implementation, this would be replaced with actual API calls
            logger.info(f"Starting upload of {file_item.name}")
            
            # Read file content for upload
            try:
                with open(path, "rb") as file:
                    file_content = file.read()
                    logger.info(f"Read {len(file_content)} bytes from {file_item.name}")
            except Exception as e:
                logger.error(f"Failed to read file content: {e}")
                return False, f"Failed to read file: {str(e)}"
            
            # Perform the actual upload using requests (synchronous, but we'll make it work with asyncio)
            try:
                # Create a function to run in a separate thread
                def do_upload():
                    try:
                        logger.info(f"Sending PUT request to {url}")
                        response = requests.put(url, data=file_content, headers=headers, params=params)
                        logger.info(f"Upload response - Status: {response.status_code}, Content: {response.text[:100] if len(response.text) > 0 else 'Empty response'}")
                        
                        # Check if the upload was successful
                        # HTTP 200 (OK) and 201 (Created) are both success codes
                        if response.status_code in [200, 201]:
                            # For 201 responses, try to extract the file ID from the JSON response
                            try:
                                import json
                                response_data = json.loads(response.text)
                                if response.status_code == 201 and 'data' in response_data and 'id' in response_data['data']:
                                    file_id = response_data['data']['id']
                                    full_url = f"https://buzzheavier.com/{file_id}"
                                    # Store the URL in the file_item for later clipboard access
                                    file_item.upload_url = full_url
                                    return True, f"{file_item.name}: {full_url}"
                            except json.JSONDecodeError:
                                pass  # If we can't parse the JSON, fall back to the default message
                            
                            return True, response.text.strip() or f"File {file_item.name} uploaded successfully"
                        else:
                            return False, f"Error: HTTP {response.status_code} - {response.text}"
                    except Exception as e:
                        logger.exception(f"Exception during upload request: {e}")
                        return False, f"Upload request failed: {str(e)}"
                
                # Run the upload in a thread pool to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, do_upload)
                logger.info(f"Upload completed with result: {result}")
                return result
            except Exception as e:
                logger.exception(f"Unexpected error during upload: {e}")
                return False, f"Unexpected error: {str(e)}"
        
        except Exception as e:
            logger.exception(f"Error uploading {file_item.name}: {e}")
            return False, f"Error: {str(e)}"

class BuzzUploaderApp(App):
    """Main application for BuzzHeavier file uploads"""
    
    TITLE = "BuzzUploader"
    CSS_PATH = "app.css"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("o", "toggle_settings", "Settings"),
        Binding("u", "upload", "Upload"),
        # Use 'x' for selection instead of 's'
        Binding("x", "toggle_select", "Select/Deselect"),
        Binding("a", "select_all", "Select All"),
        Binding("c", "clear_selection", "Clear Selection"),
        Binding("/", "focus_search", "Search"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "open_selected", "Open"),
    ]
    
    def is_screen_mounted(self, screen_class):
        """Check if a screen of the given class is currently mounted"""
        return any(isinstance(screen, screen_class) for screen in self.screen_stack)
    
    current_dir = reactive(Path.home())
    selected_files: List[FileItem] = []
    
    def __init__(self):
        super().__init__()
        self.config = UploadConfig()
    
    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header(show_clock=True)
        
        with Container(id="main"):
            with Horizontal(id="explorer"):
                # Left panel - Directory tree
                yield DirectoryTree(Path.home(), id="dir-tree")
                
                # Right panel - File list
                with Vertical(id="file-panel"):
                    with Horizontal(id="search-bar"):
                        yield Input(placeholder="Search files...", id="search-input")
                        yield Button("🔍", variant="primary", id="search-button")
                    
                    # Use our custom SelectableDataTable instead of the standard DataTable
                    yield SelectableDataTable(id="file-table")
                    
                    with Horizontal(id="status-bar"):
                        yield Static("0 items selected", id="selection-status")
                        yield Static("", id="auth-status")
            
            # Bottom panel - Actions
            with Horizontal(id="actions"):
                yield Button("Upload Selected", variant="primary", id="upload-button")
                yield Button("Settings", variant="default", id="settings-button")
                yield Button("Select All", variant="default", id="select-all-button")
                yield Button("Clear Selection", variant="default", id="clear-button")
                yield Button("Refresh", variant="default", id="refresh-button")
        
        # Create a custom footer with clear key binding instructions
        footer = Footer()
        # Add custom key binding display
        yield footer
    
    def on_mount(self) -> None:
        """Set up the app when mounted"""
        # Initialize the file table
        table = self.query_one("#file-table", SelectableDataTable)
        
        # Add columns with proper styling
        table.add_column("Name", width=40)
        table.add_column("Type", width=12)
        table.add_column("Size", width=10)
        table.add_column("Selected", width=10)
        
        # Set cursor type to row
        table.cursor_type = "row"
        
        # Update the directory listing
        self.update_file_list()
        
        # Update authentication status
        self.update_auth_status()
        
        # Connect directory tree to current directory
        dir_tree = self.query_one("#dir-tree", DirectoryTree)
        dir_tree.focus()
        
        # Focus state logging removed to clean up the code
        
        # Log that we're ready
        logger.info("App mounted and ready")
    
    def update_auth_status(self) -> None:
        """Update the authentication status display"""
        status = self.query_one("#auth-status", Static)
        if self.config.is_authenticated():
            status.update("🔑 Authenticated")
            status.add_class("authenticated")
            status.remove_class("unauthenticated")
        else:
            status.update("🔒 Not Authenticated")
            status.add_class("unauthenticated")
            status.remove_class("authenticated")
    
    def update_file_list(self) -> None:
        """Update the file listing based on current directory"""
        table = self.query_one("#file-table", SelectableDataTable)
        table.clear()
        
        try:
            # Get all files and directories in the current directory
            paths = list(self.current_dir.iterdir())
            paths.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
            
            # Add parent directory if not at root
            if self.current_dir != Path.home():
                table.add_row(
                    "📁 ..",
                    "Directory",
                    "",
                    ""
                )
            
            # Add all files and directories
            for path in paths:
                try:
                    file_item = FileItem(path)
                    is_selected = any(f.path == path for f in self.selected_files)
                    
                    # Use a more visible checkmark with color for selected files
                    selection_mark = "[green]✓[/green]" if is_selected else ""
                    
                    table.add_row(
                        str(file_item),
                        "Directory" if file_item.is_dir else "File",
                        file_item.get_size_str(),
                        selection_mark
                    )
                except (PermissionError, OSError):
                    # Skip files that can't be accessed
                    pass
            
            # Update selection status
            self.update_selection_status()
            
            # Set focus to the file table and ensure cursor is visible
            table.focus()
            
            # Log the current directory and file count
            logger.info(f"Updated file list: {self.current_dir}, Files: {table.row_count}")
            
            # Make sure the cursor is at the top
            if table.row_count > 0:
                table.cursor_coordinate = (0, 0)
                
        except Exception as e:
            logger.exception(f"Error updating file list: {e}")
            self.notify(f"Error: {str(e)}", title="Error")
    
    def update_selection_status(self) -> None:
        """Update the selection status display"""
        status = self.query_one("#selection-status", Static)
        count = len(self.selected_files)
        
        if count == 0:
            status.update("0 items selected")
        else:
            total_size = sum(f.size for f in self.selected_files if not f.is_dir)
            
            # Format size
            size_str = "0 B"
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if total_size < 1024.0:
                    size_str = f"{total_size:.1f} {unit}"
                    break
                total_size /= 1024.0
            
            status.update(f"{count} items selected ({size_str})")
    
    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection in the tree"""
        self.current_dir = event.path
        self.update_file_list()
        
        # Focus the file table after selecting a directory
        file_table = self.query_one("#file-table", SelectableDataTable)
        file_table.focus()
        logger.info(f"Focused file table after directory selection: {file_table.has_focus}")
        
        # Force a refresh to ensure focus is applied
        self.refresh()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the file table"""
        try:
            # Double-click handling is done in action_open_selected
            # This handler is just for single clicks
            pass
        except Exception as e:
            logger.exception(f"Error handling row selection: {e}")
            
    def action_open_selected(self) -> None:
        """Open the currently selected directory or file"""
        if not self.is_screen_mounted(UploadProgressScreen) and not self.is_screen_mounted(SettingsScreen):
            try:
                table = self.query_one("#file-table", SelectableDataTable)
                if table.row_count == 0:
                    return
                
                # Get the currently highlighted row
                cursor_row = table.cursor_row
                if cursor_row is None:
                    return
                
                # Get the cell content directly
                row_data = table.get_row_at(cursor_row)
                if not row_data:
                    return
                    
                cell_content = row_data[0]  # First column contains the name
                if not cell_content:
                    return
                
                # Handle parent directory navigation
                if cursor_row == 0 and cell_content.startswith("📁"):
                    self.current_dir = self.current_dir.parent
                    self.update_file_list()
                    return
                
                # Extract filename and create path
                filename = cell_content[2:].strip()
                path = self.current_dir / filename
                
                # Handle directory navigation or file selection
                if path.is_dir():
                    self.current_dir = path
                    self.update_file_list()
                else:
                    # For files, toggle selection
                    self.action_toggle_select()
            except Exception as e:
                logger.exception(f"Error opening selected item: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        button_id = event.button.id
        
        if button_id == "upload-button":
            self.action_upload()
        elif button_id == "settings-button":
            self.action_toggle_settings()
        elif button_id == "select-all-button":
            self.action_select_all()
        elif button_id == "clear-button":
            self.action_clear_selection()
        elif button_id == "refresh-button":
            self.action_refresh()
        elif button_id == "search-button":
            self.action_search()
    
    def on_key(self, event: events.Key) -> None:
        """Handle key events directly"""
        # Only handle keys if we're in the main screen
        if not self.is_screen_mounted(UploadProgressScreen) and not self.is_screen_mounted(SettingsScreen):
            # Handle 's' key for selection globally
            if event.key == "s":
                # Get the file table
                file_table = self.query_one("#file-table", SelectableDataTable)
                
                # Focus the file table first if it doesn't have focus
                if not file_table.has_focus:
                    file_table.focus()
                    
                # Toggle selection
                self._toggle_select_file()
                
                # Prevent the event from propagating
                event.prevent_default()
                event.stop()
    
    def on_selectable_data_table_select_key_pressed(self, message: SelectableDataTable.SelectKeyPressed) -> None:
        """Handle selection key pressed message from SelectableDataTable"""
        # Make sure we're in the main screen
        if not self.is_screen_mounted(UploadProgressScreen) and not self.is_screen_mounted(SettingsScreen):
            self._toggle_select_file()
    
    def on_selectable_data_table_enter_pressed(self, message: SelectableDataTable.EnterPressed) -> None:
        """Handle enter pressed message from SelectableDataTable"""
        logger.info("Received EnterPressed message from SelectableDataTable")
        # Make sure we're in the main screen
        if not self.is_screen_mounted(UploadProgressScreen) and not self.is_screen_mounted(SettingsScreen):
            self.action_open_selected()
    
    def _toggle_select_file(self) -> None:
        """Internal method to toggle selection for the currently focused file"""
        try:
            # Make sure the file table has focus
            table = self.query_one("#file-table", SelectableDataTable)
            
            if not table.has_focus:
                table.focus()
            
            # Get the currently highlighted row
            cursor_row = table.cursor_row
            
            if cursor_row is None:
                logger.warning("No cursor row found")
                return
            
            # Get the cell content directly from the table
            try:
                cell_content = table.get_cell_at((cursor_row, 0))
            except Exception as e:
                logger.error(f"Error getting cell content: {e}")
                return
            
            if not cell_content:
                logger.warning("Empty cell content")
                return
                
            # Skip parent directory
            if cursor_row == 0 and str(cell_content).startswith("📁"):
                logger.info("Skipping parent directory selection")
                return
            
            # Extract filename from the cell content (remove emoji)
            filename = str(cell_content)[2:].strip()
            path = self.current_dir / filename
            
            logger.info(f"Toggling selection for: {path}")
            
            # Only allow selecting files, not directories
            if path.is_dir():
                logger.info(f"Not selecting directory: {path}")
                return
            
            # Verify the file exists
            if not path.exists():
                logger.warning(f"File doesn't exist: {path}")
                return
                
            # Check if already selected by comparing string paths
            path_str = str(path)
            already_selected = False
            for i, f in enumerate(self.selected_files):
                if str(f.path) == path_str:
                    already_selected = True
                    logger.info(f"File already selected at index {i}: {f.path}")
                    break
            
            if already_selected:
                # Remove from selection
                logger.info(f"Removing from selection: {path}")
                self.selected_files = [f for f in self.selected_files if str(f.path) != path_str]
                # Update the table cell
                try:
                    table.update_cell_at((cursor_row, 3), "")
                except Exception as e:
                    logger.error(f"Error updating cell: {e}")
            else:
                # Create a FileItem for the file with is_selected explicitly set to True
                try:
                    file_item = FileItem(path, is_selected=True)
                    logger.info(f"Created FileItem: {file_item.path}, size: {file_item.size}, selected: {file_item.is_selected}")
                    
                    # Double-check that the file is valid before adding to selection
                    if file_item.is_dir:
                        logger.warning(f"Not selecting directory: {path}")
                        return
                        
                    # Add to selection
                    self.selected_files.append(file_item)
                    
                    # Update the table cell with a colored checkmark
                    table.update_cell_at((cursor_row, 3), "[green]✓[/green]")
                except Exception as e:
                    logger.error(f"Error creating FileItem: {e}")
            
            # Log selection status for debugging
            logger.info(f"Selected files count: {len(self.selected_files)}")
            for i, f in enumerate(self.selected_files):
                logger.info(f"  {i}: {f.path}, is_dir: {f.is_dir}, selected: {f.is_selected}")
            
            # Update selection status
            self.update_selection_status()
            
            # Force a refresh of the UI
            self.refresh()
        except Exception as e:
            logger.error(f"Error toggling selection: {e}")
    
    def action_toggle_select(self) -> None:
        """Toggle selection for the currently focused item"""
        # Check if we're in the file table or directory tree
        file_table = self.query_one("#file-table", SelectableDataTable)
        
        if file_table.has_focus:
            # If file table has focus, toggle selection
            self._toggle_select_file()
        else:
            # If file table doesn't have focus, focus it first
            file_table.focus()
            # Give it a moment to focus before toggling
            self.call_after_refresh(self._toggle_select_file)
    
    def action_select_all(self) -> None:
        """Select all files in the current directory"""
        table = self.query_one("#file-table", SelectableDataTable)
        
        # Clear current selection
        self.selected_files = []
        
        # Select all files (not directories) in the current view
        for row in range(table.row_count):
            cell_content = table.get_cell_at((row, 0))
            if not cell_content or cell_content == "📁 ..":
                continue
                
            # Extract filename and check if it's a file
            filename = cell_content[2:].strip()
            path = self.current_dir / filename
            
            if path.is_file():
                self.selected_files.append(FileItem(path, True))
                table.update_cell_at((row, 3), "[green]✓[/green]")
        
        # Log selection for debugging
        logger.info(f"Selected all files. Count: {len(self.selected_files)}")
        
        # Update selection status
        self.update_selection_status()
    
    def action_clear_selection(self) -> None:
        """Clear all selections"""
        table = self.query_one("#file-table", SelectableDataTable)
        
        # Clear selection marks in the table
        for row in range(table.row_count):
            table.update_cell_at((row, 3), "")
        
        # Clear selected files list
        self.selected_files = []
        
        # Update selection status
        self.update_selection_status()
    
    def action_refresh(self) -> None:
        """Refresh the current directory listing"""
        # Only refresh if we're in the main screen
        if not self.is_screen_mounted(UploadProgressScreen) and not self.is_screen_mounted(SettingsScreen):
            self.update_file_list()
    
    def action_focus_search(self) -> None:
        """Focus the search input"""
        # Only focus search if we're in the main screen
        if not self.is_screen_mounted(UploadProgressScreen) and not self.is_screen_mounted(SettingsScreen):
            try:
                self.query_one("#search-input", Input).focus()
            except Exception as e:
                logger.exception(f"Error focusing search: {e}")
    
    def action_search(self) -> None:
        """Search for files in the current directory"""
        # Only search if we're in the main screen
        if not self.is_screen_mounted(UploadProgressScreen) and not self.is_screen_mounted(SettingsScreen):
            try:
                search_input = self.query_one("#search-input", Input)
                query = search_input.value.lower()
                
                if not query:
                    self.update_file_list()
                    return
                
                table = self.query_one("#file-table", SelectableDataTable)
                table.clear()
                
                try:
                    # Get all files and directories in the current directory
                    paths = list(self.current_dir.iterdir())
                    
                    # Filter by search query
                    filtered_paths = [p for p in paths if query in p.name.lower()]
                    filtered_paths.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
                    
                    # Add all matching files and directories
                    for path in filtered_paths:
                        try:
                            file_item = FileItem(path)
                            is_selected = any(f.path == path for f in self.selected_files)
                            
                            table.add_row(
                                str(file_item),
                                "Directory" if file_item.is_dir else "File",
                                file_item.get_size_str(),
                                "✓" if is_selected else ""
                            )
                        except (PermissionError, OSError):
                            # Skip files that can't be accessed
                            pass
                
                except Exception as e:
                    logger.exception(f"Error searching: {e}")
                    self.notify(f"Error: {str(e)}", title="Error")
            except Exception as e:
                logger.exception(f"Error in search action: {e}")
    
    def action_toggle_settings(self) -> None:
        """Show the settings screen"""
        self.push_screen(SettingsScreen(self.config))
    
    def action_upload(self) -> None:
        """Upload selected files"""
        # Log current selection state for debugging
        logger.info(f"Upload requested. Current selection count: {len(self.selected_files)}")
        for f in self.selected_files:
            logger.info(f"  File in selection: {f.path}, is_dir: {f.is_dir}, selected: {f.is_selected}")
            
        if not self.selected_files:
            # Try to select the currently highlighted file if nothing is selected
            self.action_toggle_select()
            
            # Check again after attempting to select
            if not self.selected_files:
                self.notify("No files selected for upload", title="Error")
                return
        
        # Count how many valid files we have
        valid_files = [f for f in self.selected_files if not f.is_dir and f.is_selected]
        
        if not valid_files:
            self.notify("No valid files selected for upload (directories cannot be uploaded)", title="Error")
            return
            
        # Log the files we're about to upload
        logger.info(f"Preparing to upload {len(valid_files)} files:")
        for i, f in enumerate(valid_files):
            logger.info(f"  File {i}: {f.path} (selected: {f.is_selected}, size: {f.size})")
            
        # Show a notification with the count
        self.notify(f"Uploading {len(valid_files)} files", title="Upload Started")
            
        # Create the upload screen with our selected files
        upload_screen = UploadProgressScreen(valid_files, self.config)
        self.push_screen(upload_screen)
    
    def on_upload_progress_screen_upload_complete(self, message: UploadProgressScreen.UploadComplete) -> None:
        """Handle upload completion"""
        if message.success:
            self.notify(message.message, title="Upload Complete")
        else:
            self.notify(message.message, title="Upload Incomplete")
