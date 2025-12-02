"""
Server-side logic for hosting the screen sharing session
"""
import threading
import time
from screen_capture import ScreenCapture
from compression import AdaptiveCompressor
from network import NetworkServer
from remote_control import RemoteController
import pickle


class ScreenShareServer:
    """Server that shares the screen and accepts remote control"""
    
    def __init__(self, host='0.0.0.0', port=5555, fps=30, quality=90, target_kb=200):
        """
        Initialize screen share server
        
        Args:
            host: Host address to bind to
            port: Port to listen on
            fps: Target frames per second
            quality: Compression quality (0-100)
            target_kb: Target compressed frame size in KB for adaptive compressor
        """
        self.host = host
        self.port = port
        self.fps = fps
        self.frame_delay = 1.0 / fps
        
        # Delay ScreenCapture creation to the streaming thread to avoid
        # mss thread-local handle issues on Windows
        self.screen_capture = None
        self.compressor = AdaptiveCompressor(quality)
        try:
            self.compressor.set_target_size(target_kb)
        except Exception:
            pass
        self.network = NetworkServer(host, port)
        self.remote_controller = RemoteController()
        
        self.running = False
        self.streaming = False
        self.stream_thread = None
        
    def start(self):
        """Start the server"""
        print(f"Starting server on {self.host}:{self.port}")
        self.network.start()
        
        # Get local IP for display
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"Your IP address: {local_ip}")
        print(f"Connection code: {local_ip}:{self.port}")
        
        self.running = True
        
    def wait_for_client(self):
        """Wait for a client to connect"""
        client_addr = self.network.accept_connection()
        
        # If accept_connection returns None, server was stopped
        if client_addr is None:
            return None
        
        # Start receiving remote control events
        self.network.start_receive_thread(self._handle_remote_event)
        
        # Start streaming
        self.start_streaming()
        
        return client_addr
    
    def start_streaming(self):
        """Start streaming screen frames"""
        if self.streaming:
            return
        
        self.streaming = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        print("Started streaming")
    
    def _stream_loop(self):
        """Main streaming loop"""
        frame_count = 0
        start_time = time.time()
        
        print("Stream loop started")
        
        # Create ScreenCapture inside this thread to avoid mss thread-local errors
        capturer = None
        try:
            capturer = ScreenCapture()
            # Send screen size to client from this thread
            screen_size = capturer.get_screen_size()
            self.network.send_data(pickle.dumps({
                'type': 'screen_info',
                'width': screen_size[0],
                'height': screen_size[1]
            }))
        except Exception as e:
            print(f"Failed to initialize screen capture: {e}")
            return
        
        while self.streaming and self.running:
            try:
                loop_start = time.time()
                
                # Capture frame
                frame = capturer.capture_frame()
                
                # Compress frame
                compressed = self.compressor.compress_adaptive(frame)
                
                # Send frame
                data = pickle.dumps({
                    'type': 'frame',
                    'data': compressed,
                    'timestamp': time.time()
                })
                
                try:
                    self.network.send_data(data)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as conn_err:
                    print(f"Client disconnected (connection closed)")
                    break
                
                frame_count += 1
                
                # Calculate FPS every second
                elapsed = time.time() - start_time
                if elapsed >= 1.0:
                    fps = frame_count / elapsed
                    print(f"FPS: {fps:.1f}, Quality: {self.compressor.quality}, "
                          f"Frame size: {len(compressed)/1024:.1f}KB")
                    frame_count = 0
                    start_time = time.time()
                
                # Maintain target FPS
                loop_time = time.time() - loop_start
                sleep_time = self.frame_delay - loop_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                print("\nStream interrupted by user")
                break
            except Exception as e:
                print(f"Error in streaming loop: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Mark streaming as stopped when loop exits
        self.streaming = False
        print("Stream loop ended")
        # Cleanup (let GC handle capturer; __del__ will close resources)
    
    def _handle_remote_event(self, data):
        """Handle incoming remote control events"""
        try:
            event = pickle.loads(data)
            if event.get('type') == 'control':
                event_json = event.get('data')
                self.remote_controller.execute_event(event_json)
        except Exception as e:
            print(f"Error handling remote event: {e}")
    
    def stop_streaming(self):
        """Stop streaming frames"""
        self.streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2)
        print("Stopped streaming")
    
    def cleanup_client(self):
        """Clean up after client disconnection to prepare for new connection"""
        self.stop_streaming()
        # Use network's cleanup method
        self.network.cleanup_client()
        print("Cleaned up client connection, ready for new client")
    
    def stop(self):
        """Stop the server"""
        self.stop_streaming()
        self.running = False
        self.network.stop()
        print("Server stopped")
    
    def run(self):
        """Run the server (blocks until stopped)"""
        try:
            self.start()
            self.wait_for_client()
            
            # Keep running until interrupted
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.stop()


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    port = 5555
    fps = 30
    quality = 80
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        fps = int(sys.argv[2])
    if len(sys.argv) > 3:
        quality = int(sys.argv[3])
    
    # Create and run server
    server = ScreenShareServer(port=port, fps=fps, quality=quality)
    server.run()
