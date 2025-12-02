"""
Network communication layer for client-server communication
"""
import socket
import struct
import threading
import pickle


class NetworkServer:
    """Server for hosting the screen sharing session"""
    
    def __init__(self, host='0.0.0.0', port=5555):
        """
        Initialize network server
        
        Args:
            host: Host address to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False
        self.client_running = False
        self.on_data_received = None
        self.receive_thread = None
        
    def start(self):
        """Start the server and listen for connections"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set timeout so accept() doesn't block forever
        self.server_socket.settimeout(1.0)
        # Enable keepalive on the listening socket (propagates to accepted sockets on some OSes)
        try:
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.running = True
        print(f"Server listening on {self.host}:{self.port}")
        
    def accept_connection(self):
        """Wait for and accept a client connection"""
        print("Waiting for client connection...")
        while self.running:
            try:
                self.client_socket, client_address = self.server_socket.accept()
                # Improve TCP behavior on the client socket
                try:
                    self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except OSError:
                    pass
                try:
                    self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except OSError:
                    pass
                self.client_running = True
                print(f"Client connected from {client_address}")
                return client_address
            except socket.timeout:
                # Timeout allows us to check if we should keep running
                continue
            except OSError as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                    raise
                else:
                    return None
        return None
    
    def send_data(self, data):
        """
        Send data to the connected client
        
        Args:
            data: Bytes to send
        """
        if not self.client_socket:
            raise Exception("No client connected")
        
        try:
            # Send data length first (4 bytes)
            data_size = struct.pack("!I", len(data))
            self.client_socket.sendall(data_size)
            
            # Send actual data
            self.client_socket.sendall(data)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            # Don't set running=False here, let the caller handle it
            raise
    
    def receive_data(self):
        """
        Receive data from the client
        
        Returns:
            bytes: Received data
        """
        if not self.client_socket:
            raise Exception("No client connected")
        
        # Receive data size (4 bytes)
        size_data = self._recv_exact(4)
        if not size_data:
            return None
        
        data_size = struct.unpack("!I", size_data)[0]
        
        # Receive actual data
        data = self._recv_exact(data_size)
        return data
    
    def _recv_exact(self, num_bytes):
        """
        Receive exact number of bytes
        
        Args:
            num_bytes: Number of bytes to receive
            
        Returns:
            bytes: Received data
        """
        data = b''
        while len(data) < num_bytes:
            chunk = self.client_socket.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def start_receive_thread(self, callback):
        """
        Start a thread to continuously receive data
        
        Args:
            callback: Function to call with received data
        """
        self.on_data_received = callback
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        return self.receive_thread
    
    def _receive_loop(self):
        """Internal loop for receiving data"""
        while self.running and self.client_running:
            try:
                data = self.receive_data()
                if data and self.on_data_received:
                    self.on_data_received(data)
                elif not data:
                    break
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                if self.client_running:
                    print(f"Client disconnected from receive loop")
                break
            except Exception as e:
                if self.client_running:
                    print(f"Error receiving data: {e}")
                break
    
    def cleanup_client(self):
        """Clean up client connection while keeping server running"""
        self.client_running = False
        
        # Wait for receive thread to finish
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)
        self.receive_thread = None
        
        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except (OSError, AttributeError):
                pass
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        self.on_data_received = None
    
    def stop(self):
        """Stop the server"""
        self.running = False
        try:
            if self.client_socket:
                self.client_socket.shutdown(socket.SHUT_RDWR)
        except (OSError, AttributeError):
            pass
        finally:
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
        
        try:
            if self.server_socket:
                self.server_socket.close()
        except:
            pass
        finally:
            self.server_socket = None
        print("Server stopped")


class NetworkClient:
    """Client for connecting to the screen sharing session"""
    
    def __init__(self):
        """Initialize network client"""
        self.socket = None
        self.running = False
        self.on_data_received = None
        
    def connect(self, host, port=5555):
        """
        Connect to the server
        
        Args:
            host: Server host address
            port: Server port
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Improve TCP behavior on the client socket
        try:
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        self.socket.connect((host, port))
        self.running = True
        print(f"Connected to {host}:{port}")
        
    def send_data(self, data):
        """
        Send data to the server
        
        Args:
            data: Bytes to send
        """
        if not self.socket:
            raise Exception("Not connected")
        
        try:
            # Send data length first (4 bytes)
            data_size = struct.pack("!I", len(data))
            self.socket.sendall(data_size)
            
            # Send actual data
            self.socket.sendall(data)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            self.running = False
            raise
    
    def receive_data(self):
        """
        Receive data from the server
        
        Returns:
            bytes: Received data
        """
        if not self.socket:
            raise Exception("Not connected")
        
        # Receive data size (4 bytes)
        size_data = self._recv_exact(4)
        if not size_data:
            return None
        
        data_size = struct.unpack("!I", size_data)[0]
        
        # Receive actual data
        data = self._recv_exact(data_size)
        return data
    
    def _recv_exact(self, num_bytes):
        """
        Receive exact number of bytes
        
        Args:
            num_bytes: Number of bytes to receive
            
        Returns:
            bytes: Received data
        """
        data = b''
        while len(data) < num_bytes:
            chunk = self.socket.recv(num_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def start_receive_thread(self, callback):
        """
        Start a thread to continuously receive data
        
        Args:
            callback: Function to call with received data
        """
        self.on_data_received = callback
        thread = threading.Thread(target=self._receive_loop, daemon=True)
        thread.start()
        return thread
    
    def _receive_loop(self):
        """Internal loop for receiving data"""
        while self.running:
            try:
                data = self.receive_data()
                if data and self.on_data_received:
                    self.on_data_received(data)
                elif not data:
                    break
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                if self.running:
                    print(f"Server disconnected")
                break
            except Exception as e:
                if self.running:
                    print(f"Error receiving data: {e}")
                break
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        try:
            if self.socket:
                self.socket.shutdown(socket.SHUT_RDWR)
        except (OSError, AttributeError):
            pass
        finally:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
        print("Disconnected from server")


if __name__ == "__main__":
    # Simple test
    import time
    
    def test_server():
        server = NetworkServer(port=5556)
        server.start()
        server.accept_connection()
        
        # Send test data
        for i in range(5):
            server.send_data(f"Message {i}".encode())
            time.sleep(0.5)
        
        server.stop()
    
    def test_client():
        time.sleep(1)  # Wait for server to start
        client = NetworkClient()
        client.connect('localhost', 5556)
        
        # Receive test data
        for i in range(5):
            data = client.receive_data()
            print(f"Received: {data.decode()}")
        
        client.disconnect()
    
    # Run test (uncomment to test)
    # import threading
    # server_thread = threading.Thread(target=test_server)
    # client_thread = threading.Thread(target=test_client)
    # server_thread.start()
    # client_thread.start()
    # server_thread.join()
    # client_thread.join()
