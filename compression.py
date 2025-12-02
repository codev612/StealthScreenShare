"""
Video compression and decompression module for efficient streaming
"""
import cv2
import numpy as np
from io import BytesIO


class VideoCompressor:
    """Handles video frame compression and decompression"""
    
    def __init__(self, quality=80):
        """
        Initialize compressor
        
        Args:
            quality: JPEG quality (0-100), higher = better quality but larger size
        """
        self.quality = quality
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    
    def compress_frame(self, frame):
        """
        Compress a frame using JPEG encoding
        
        Args:
            frame: numpy array of the frame (BGR format)
            
        Returns:
            bytes: Compressed frame data
        """
        # Encode frame as JPEG
        result, encoded_frame = cv2.imencode('.jpg', frame, self.encode_param)
        
        if not result:
            raise Exception("Failed to compress frame")
        
        # Convert to bytes
        return encoded_frame.tobytes()
    
    def decompress_frame(self, compressed_data):
        """
        Decompress a frame from JPEG data
        
        Args:
            compressed_data: Compressed frame bytes
            
        Returns:
            numpy.ndarray: Decompressed frame (BGR format)
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(compressed_data, np.uint8)
        
        # Decode JPEG
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise Exception("Failed to decompress frame")
        
        return frame
    
    def set_quality(self, quality):
        """
        Adjust compression quality
        
        Args:
            quality: JPEG quality (0-100)
        """
        self.quality = quality
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    
    def compress_with_resize(self, frame, scale=0.75):
        """
        Compress frame with resizing for lower bandwidth
        
        Args:
            frame: numpy array of the frame
            scale: Scale factor (e.g., 0.5 for half size)
            
        Returns:
            tuple: (compressed_data, original_size)
        """
        original_size = (frame.shape[1], frame.shape[0])
        
        # Resize frame
        new_size = (int(frame.shape[1] * scale), int(frame.shape[0] * scale))
        resized = cv2.resize(frame, new_size, interpolation=cv2.INTER_LINEAR)
        
        # Compress
        compressed = self.compress_frame(resized)
        
        return compressed, original_size
    
    def decompress_with_resize(self, compressed_data, target_size):
        """
        Decompress and resize frame to target size
        
        Args:
            compressed_data: Compressed frame bytes
            target_size: Tuple of (width, height)
            
        Returns:
            numpy.ndarray: Decompressed and resized frame
        """
        # Decompress
        frame = self.decompress_frame(compressed_data)
        
        # Resize to target
        resized = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)
        
        return resized


class AdaptiveCompressor(VideoCompressor):
    """
    Adaptive compression that adjusts quality based on network conditions
    """
    
    def __init__(self, initial_quality=80):
        super().__init__(initial_quality)
        self.min_quality = 30
        self.max_quality = 95
        self.target_size_kb = 50  # Target size per frame in KB
    
    def compress_adaptive(self, frame):
        """
        Compress with adaptive quality based on target size
        
        Args:
            frame: Frame to compress
            
        Returns:
            bytes: Compressed data
        """
        compressed = self.compress_frame(frame)
        size_kb = len(compressed) / 1024
        
        # Adjust quality for next frame
        if size_kb > self.target_size_kb * 1.2:
            # Too large, reduce quality
            self.quality = max(self.min_quality, self.quality - 5)
            self.set_quality(self.quality)
        elif size_kb < self.target_size_kb * 0.8:
            # Too small, can increase quality
            self.quality = min(self.max_quality, self.quality + 2)
            self.set_quality(self.quality)
        
        return compressed
    
    def set_target_size(self, target_kb):
        """Set target frame size in KB"""
        self.target_size_kb = target_kb


if __name__ == "__main__":
    # Test compression
    import time
    from screen_capture import ScreenCapture
    
    capturer = ScreenCapture()
    compressor = VideoCompressor(quality=80)
    
    print("Testing compression...")
    frame = capturer.capture_frame()
    
    start = time.time()
    compressed = compressor.compress_frame(frame)
    compress_time = time.time() - start
    
    start = time.time()
    decompressed = compressor.decompress_frame(compressed)
    decompress_time = time.time() - start
    
    original_size = frame.nbytes / 1024
    compressed_size = len(compressed) / 1024
    compression_ratio = original_size / compressed_size
    
    print(f"Original size: {original_size:.2f} KB")
    print(f"Compressed size: {compressed_size:.2f} KB")
    print(f"Compression ratio: {compression_ratio:.2f}x")
    print(f"Compression time: {compress_time*1000:.2f}ms")
    print(f"Decompression time: {decompress_time*1000:.2f}ms")
    print(f"Frame shape: {frame.shape} -> {decompressed.shape}")
