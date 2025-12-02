"""
Screen capture module for capturing desktop screens efficiently
"""
import mss
import numpy as np
from PIL import Image
import cv2


class ScreenCapture:
    """Handles screen capture operations"""
    
    def __init__(self, monitor_number=1):
        """
        Initialize screen capture
        
        Args:
            monitor_number: Monitor to capture (1 for primary)
        """
        self.sct = mss.mss()
        self.monitor_number = monitor_number
        self.monitor = self.sct.monitors[monitor_number]
        
    def capture_frame(self):
        """
        Capture a single frame from the screen
        
        Returns:
            numpy.ndarray: Screen frame in BGR format
        """
        # Capture the screen
        screenshot = self.sct.grab(self.monitor)
        
        # Convert to numpy array
        frame = np.array(screenshot)
        
        # Convert BGRA to BGR (remove alpha channel)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        
        return frame
    
    def capture_frame_pil(self):
        """
        Capture frame and return as PIL Image
        
        Returns:
            PIL.Image: Screen frame
        """
        screenshot = self.sct.grab(self.monitor)
        return Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
    
    def get_screen_size(self):
        """
        Get the dimensions of the screen being captured
        
        Returns:
            tuple: (width, height)
        """
        return (self.monitor['width'], self.monitor['height'])
    
    def list_monitors(self):
        """
        List all available monitors
        
        Returns:
            list: List of monitor information
        """
        return self.sct.monitors
    
    def set_monitor(self, monitor_number):
        """
        Change the monitor to capture
        
        Args:
            monitor_number: Monitor index to capture
        """
        self.monitor_number = monitor_number
        self.monitor = self.sct.monitors[monitor_number]
    
    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'sct') and self.sct:
                self.sct.close()
        except (AttributeError, RuntimeError):
            # Ignore cleanup errors (thread-local storage issues)
            pass


if __name__ == "__main__":
    # Test the screen capture
    import time
    
    capturer = ScreenCapture()
    print(f"Screen size: {capturer.get_screen_size()}")
    print(f"Available monitors: {len(capturer.list_monitors()) - 1}")
    
    print("Capturing 5 frames...")
    for i in range(5):
        start = time.time()
        frame = capturer.capture_frame()
        elapsed = time.time() - start
        print(f"Frame {i+1}: {frame.shape}, captured in {elapsed*1000:.2f}ms")
        time.sleep(0.1)
