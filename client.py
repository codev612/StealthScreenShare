"""
Client-side logic for viewing and controlling remote screen
"""
import threading
import time
import cv2
import numpy as np
from network import NetworkClient
from compression import VideoCompressor
from remote_control import InputCapture
import pickle


class ScreenShareClient:
    """Client that views remote screen and sends control events"""
    
    def __init__(self):
        """Initialize screen share client"""
        self.network = NetworkClient()
        self.compressor = VideoCompressor()
        self.input_capture = InputCapture()
        
        self.running = False
        self.connected = False
        self.screen_width = 0
        self.screen_height = 0
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.on_frame = None  # Optional callback(frame: np.ndarray BGR)
        
    def connect(self, host, port=5555):
        """
        Connect to the server
        
        Args:
            host: Server IP address
            port: Server port
        """
        print(f"Connecting to {host}:{port}...")
        self.network.connect(host, port)
        self.connected = True
        self.running = True
        
        # Start receiving frames
        self.network.start_receive_thread(self._handle_server_data)
        
        print("Connected! Waiting for screen data...")
        
    def _handle_server_data(self, data):
        """Handle incoming data from server"""
        try:
            packet = pickle.loads(data)
            packet_type = packet.get('type')
            
            if packet_type == 'screen_info':
                self.screen_width = packet.get('width')
                self.screen_height = packet.get('height')
                print(f"Remote screen size: {self.screen_width}x{self.screen_height}")
                
            elif packet_type == 'frame':
                compressed_frame = packet.get('data')
                
                # Decompress frame
                frame = self.compressor.decompress_frame(compressed_frame)
                
                with self.frame_lock:
                    self.current_frame = frame
                # Notify listener (e.g., GUI) if set
                if self.on_frame:
                    try:
                        self.on_frame(frame)
                    except Exception as cb_e:
                        print(f"on_frame callback error: {cb_e}")
                    
        except (ConnectionResetError, ConnectionAbortedError, OSError) as conn_err:
            print(f"Connection lost while receiving data: {conn_err}")
            self.running = False
        except Exception as e:
            print(f"Error handling server data: {e}")
            import traceback
            traceback.print_exc()
    
    def send_control_event(self, event_json):
        """
        Send a control event to the server
        
        Args:
            event_json: JSON string of the control event
        """
        if not self.connected:
            return
        
        try:
            data = pickle.dumps({
                'type': 'control',
                'data': event_json
            })
            self.network.send_data(data)
        except Exception as e:
            print(f"Error sending control event: {e}")
    
    def start_control(self):
        """Start capturing local input to control remote"""
        self.input_capture.start(self.send_control_event)
        print("Remote control enabled")
    
    def stop_control(self):
        """Stop capturing local input"""
        self.input_capture.stop()
        print("Remote control disabled")
    
    def get_current_frame(self):
        """Get the current frame (thread-safe)"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def set_on_frame(self, callback):
        """Register a callback to receive frames (numpy BGR)."""
        self.on_frame = callback
    
    def display_stream(self, window_name="Remote Desktop", stealth=False):
        """
        Display the remote screen stream in a window
        
        Args:
            window_name: Name of the display window
            stealth: If True, runs without visible window (background only)
        """
        # Wait for first frame
        print("Waiting for first frame...")
        wait_count = 0
        while self.current_frame is None and self.running and wait_count < 50:
            time.sleep(0.1)
            wait_count += 1
        
        if self.current_frame is None:
            print("ERROR: No frames received from server!")
            # Ensure clean disconnect so server doesn't keep sending
            self.disconnect()
            return
        
        print("First frame received, starting display...")
        
        if not stealth:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        # Track FPS
        frame_count = 0
        fps_start_time = time.time()
        current_fps = 0
        first_display = True
        
        print("Displaying remote screen. Press 'q' to quit, 'c' to toggle control.")
        control_enabled = False
        
        while self.running:
            frame = self.get_current_frame()
            
            if frame is not None:
                if not stealth:
                    # Add FPS overlay
                    display_frame = frame.copy()
                    cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    if control_enabled:
                        cv2.putText(display_frame, "CONTROL: ON", (10, 70),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    else:
                        cv2.putText(display_frame, "CONTROL: OFF", (10, 70),
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
                    cv2.imshow(window_name, display_frame)
                
                # Calculate FPS
                frame_count += 1
                elapsed = time.time() - fps_start_time
                if elapsed >= 1.0:
                    current_fps = frame_count / elapsed
                    frame_count = 0
                    fps_start_time = time.time()
            
            # Handle key presses
            if stealth:
                # In stealth mode, auto-enable control and run in background
                if not control_enabled:
                    control_enabled = True
                    self.start_control()
                time.sleep(0.033)  # ~30 FPS
            else:
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("Quitting...")
                    break
                elif key == ord('c'):
                    control_enabled = not control_enabled
                    if control_enabled:
                        self.start_control()
                    else:
                        self.stop_control()
        
        if not stealth:
            cv2.destroyAllWindows()
        self.disconnect()
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.stop_control()
        if self.connected:
            self.network.disconnect()
            self.connected = False
        print("Disconnected")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python client.py <server_ip> [port]")
        print("Example: python client.py 192.168.1.100 5555")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5555
    
    # Create and run client
    client = ScreenShareClient()
    
    try:
        client.connect(host, port)
        client.display_stream()
    except KeyboardInterrupt:
        print("\nShutting down client...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()
