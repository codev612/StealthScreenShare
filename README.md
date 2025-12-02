# ScreenHacker - Remote Desktop Application

A lightweight remote desktop application similar to AnyDesk, built with Python.

## Features

- **Screen Sharing**: Real-time screen capture and streaming
- **Remote Control**: Control mouse and keyboard on remote machine
- **Efficient Compression**: H.264 video compression for low bandwidth usage
- **Secure Connection**: Encrypted communication between client and server
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Simple GUI**: Easy-to-use interface for hosting and connecting

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### GUI Mode (Default)
```bash
python main.py
```

### Host Mode (Share your screen)
```bash
python main.py --host
```

### Client Mode (Connect to remote)
```bash
python main.py --connect <host_ip>
```

### Stealth Mode (Hidden, no UI)
```bash
# Windows - completely hidden
pythonw stealth_runner.pyw

# Or use launcher scripts
launch_stealth.bat           # Windows batch
launch_stealth.ps1          # PowerShell

# Direct stealth client
python stealth_client.py <host_ip> [port]
```

See `STEALTH_GUIDE.md` for detailed stealth mode setup.

## Project Structure

- `main.py` - Main entry point and GUI
- `server.py` - Server-side logic (host machine)
- `client.py` - Client-side logic (remote viewer)
- `screen_capture.py` - Screen capture functionality
- `network.py` - Network communication layer
- `remote_control.py` - Mouse and keyboard control
- `compression.py` - Video compression/decompression
- `encryption.py` - Security and encryption

## Security Note

This is a basic implementation for educational purposes. For production use, implement additional security measures like authentication, SSL/TLS, and access control.

## License

MIT License
