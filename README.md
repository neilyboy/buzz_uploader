# BuzzUploader

A slick terminal-based file uploader for BuzzHeavier with a modern TUI (Terminal User Interface) inspired by [Yazi](https://github.com/sxyazi/yazi).

![buzz_uploader_main](https://github.com/user-attachments/assets/84e56458-9114-4e55-86ca-760c4cfbf2b5)

![buzz_uploader_upload](https://github.com/user-attachments/assets/0ba35622-9e84-4015-9043-a57dc51a9203)

## Features

- **Beautiful Terminal UI**: Navigate and select files with a modern, responsive interface
- **Efficient File Management**:
  - Multi-file selection and batch uploads
  - File search functionality
  - Directory navigation
  - File details display (size, type)
- **Seamless Upload Experience**:
  - Real-time upload progress tracking
  - Detailed success/failure reporting
  - One-click URL copying to clipboard
- **Comprehensive BuzzHeavier Integration**:
  - Upload to default location
  - Upload to specific user directories
  - Upload to specific storage locations
  - Add notes to uploads
  - Authentication with BuzzHeavier API key
- **User-Friendly Design**:
  - Intuitive keyboard shortcuts
  - Clear status notifications
  - Persistent settings

## Installation

### Prerequisites

- Python 3.7 or higher
- For clipboard functionality on Linux: `xclip` or `xsel`
  ```bash
  # Ubuntu/Debian
  sudo apt-get install xclip
  
  # Fedora/RHEL
  sudo dnf install xclip
  ```

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/neilyboy/buzz-uploader.git
   cd buzz-uploader
   ```

2. Install the package with clipboard support:
   ```bash
   pip install -e ".[clipboard]"
   ```

   Or install with all development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

   Or install basic dependencies directly:
   ```bash
   pip install -r requirements.txt
   ```

### Using pip

```bash
# Basic installation
pip install buzz-uploader

# With clipboard support
pip install "buzz-uploader[clipboard]"
```

## Usage

### Starting the Application

There are several ways to run BuzzUploader:

#### Using the installed package
```bash
buzz-uploader
```

#### Using the module directly
```bash
python -m buzz_uploader
```

#### Using the launcher script
The repository includes a convenient launcher script (`run.py`) that automatically checks and installs dependencies if needed:

```bash
python run.py
```

This is especially useful for first-time users or when sharing the application with others who may not have all dependencies installed.

### Keyboard Shortcuts

- **Navigation**
  - `↑/↓`: Navigate up/down in file list
  - `←/→`: Navigate between directory tree and file list
  - `Enter`: Enter selected directory
  - `Backspace`: Go to parent directory

- **File Operations**
  - `x`: Select/deselect the highlighted file
  - `a`: Select all files in the current directory
  - `c`: Clear all selections
  - `u`: Upload selected files

- **Interface Controls**
  - `q` or `Esc`: Quit the application or close current screen
  - `s`: Open settings screen
  - `/`: Focus the search box
  - `r`: Refresh the current directory

### Upload Process

1. Navigate to the directory containing files you want to upload
2. Select files using `x` or select all with `a`
3. Press `u` to start the upload process
4. The upload progress screen will show real-time status of each file
5. When complete, you can:
   - Click the "Copy URLs" button to copy all successful upload URLs to clipboard
   - Click "Close" to return to the file browser

### Authentication

To authenticate with BuzzHeavier, you need to provide your API key (Account ID). You can do this in two ways:

1. Set the `BUZZHEAVIER_API_KEY` environment variable:
   ```bash
   export BUZZHEAVIER_API_KEY="your_account_id"
   ```

2. Enter your API key in the Settings screen (press `s` to access)

Your API key will be saved for future sessions once entered in the Settings screen.

### Upload Options

BuzzUploader supports all the upload options provided by the BuzzHeavier API:

| Option | Description | Configuration |
|--------|-------------|---------------|
| Default Upload | Upload to your default location | No configuration needed |
| Parent Directory | Upload to a specific user directory | Enter Parent Directory ID in Settings |
| Location | Upload to a specific storage location | Enter Location ID in Settings |
| Notes | Add notes to uploads | Enter notes in Settings |

All these options can be configured in the Settings screen (press `o` to access).

### Clipboard Functionality

After uploading files, you can easily copy all successful upload URLs to your clipboard:

1. The "Copy URLs" button will be enabled after successful uploads
2. Click the button to copy all URLs in the format: `filename: https://buzzheavier.com/file_id`
3. Paste the URLs anywhere you need them

This makes it easy to share your uploaded files with others.

## API Integration

BuzzUploader uses the BuzzHeavier API as documented at [https://buzzheavier.com/developers](https://buzzheavier.com/developers).

The application supports:
- Authentication via Bearer token
- File uploads to different locations
- Adding notes to uploads
- Retrieving directory information

The application handles both HTTP 200 and 201 status codes as successful uploads, extracting the file ID from the JSON response to generate shareable URLs.

### Recent Improvements

- **Enhanced Upload Process**: Improved asynchronous handling of file uploads with proper UI updates
- **Better Status Reporting**: Real-time progress updates during the upload process
- **Clipboard Integration**: One-click copying of all successful upload URLs
- **Improved Error Handling**: Detailed error reporting for failed uploads
- **UI Responsiveness**: Strategic use of asyncio to ensure the UI remains responsive during uploads

## Development

### Requirements

- Python 3.7+
- Textual 0.27.0+
- Requests 2.28.0+
- Pyperclip 1.8.2+ (for clipboard functionality)
- xclip or xsel (on Linux for clipboard functionality)

### Setup Development Environment

```bash
git clone https://github.com/yourusername/buzz-uploader.git
cd buzz-uploader
pip install -e ".[dev]"
```

### Project Structure

```
buzz-uploader/
├── buzz_uploader/
│   ├── __init__.py        # Package initialization
│   ├── __main__.py        # Entry point for the application
│   ├── app.py             # Main application logic
│   └── app.css            # Textual CSS styling
├── run.py                 # Launcher script with dependency checking
├── setup.py               # Package setup configuration
├── requirements.txt       # Dependencies list
└── README.md              # Documentation
```

### Key Components

- **FileItem**: Class representing a file or directory for upload
- **UploadConfig**: Configuration for BuzzHeavier uploads
- **UploadProgressScreen**: Screen showing upload progress with clipboard functionality
- **FileExplorerApp**: Main application class

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure code quality
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

This project follows the PEP 8 style guide. We use Black for code formatting and isort for import sorting.

```bash
# Format code
black buzz_uploader

# Sort imports
isort buzz_uploader

# Check code quality
pylint buzz_uploader
```

## License

MIT License

## Acknowledgements

- Inspired by [Yazi](https://github.com/sxyazi/yazi) file manager
- Built with [Textual](https://github.com/Textualize/textual) TUI framework
- Uses [Requests](https://requests.readthedocs.io/) for API communication
- Uses [Pyperclip](https://pyperclip.readthedocs.io/) for clipboard functionality
