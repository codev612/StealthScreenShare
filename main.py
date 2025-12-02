"""
Main entry point with GUI for ScreenHacker
"""
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                              QTextEdit, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QImage, QPixmap
import socket
import threading
from server import ScreenShareServer
from client import ScreenShareClient


class ServerThread(QThread):
    """Thread for running the server"""
    log_signal = pyqtSignal(str)
    
    def __init__(self, port=5555, fps=30, quality=90, target_kb=200):
        super().__init__()
        self.port = port
        self.fps = fps
        self.quality = quality
        self.target_kb = target_kb
        self.server = None
        
    def run(self):
        """Run the server"""
        try:
            self.server = ScreenShareServer(port=self.port, fps=self.fps, quality=self.quality, target_kb=self.target_kb)
            self.log_signal.emit(f"Server started on port {self.port}")
            self.log_signal.emit(f"Waiting for connection...")
            
            self.server.start()
            self.server.wait_for_client()
            
            # Keep server running
            while self.server.running:
                threading.Event().wait(1)
                
        except Exception as e:
            self.log_signal.emit(f"Server error: {e}")
    
    def stop(self):
        """Stop the server"""
        if self.server:
            self.server.stop()


class ClientThread(QThread):
    """Thread for running the client"""
    log_signal = pyqtSignal(str)
    frame_signal = pyqtSignal(QImage)
    
    def __init__(self, host, port=5555):
        super().__init__()
        self.host = host
        self.port = port
        self.client = None
        
    def run(self):
        """Run the client"""
        try:
            self.client = ScreenShareClient()
            self.log_signal.emit(f"Connecting to {self.host}:{self.port}...")
            
            # Wire frame callback to emit signal with QImage
            def on_frame(frame_bgr):
                try:
                    h, w, _ = frame_bgr.shape
                    # Convert BGR -> RGB without importing cv2
                    frame_rgb = frame_bgr[:, :, ::-1].copy()
                    qimg = QImage(frame_rgb.data, w, h, 3 * w, QImage.Format_RGB888)
                    self.frame_signal.emit(qimg.copy())  # copy to detach from numpy buffer
                except Exception as e:
                    self.log_signal.emit(f"Frame convert error: {e}")

            self.client.set_on_frame(on_frame)
            self.client.connect(self.host, self.port)
            self.log_signal.emit("Connected! Receiving frames...")

            # Keep thread alive while connected
            while self.client.running:
                threading.Event().wait(0.05)
            
            # Connection ended
            if not self.client.running:
                self.log_signal.emit("Connection closed by server")
            
        except (ConnectionResetError, ConnectionAbortedError, OSError) as conn_err:
            self.log_signal.emit(f"Connection lost: {conn_err}")
        except Exception as e:
            self.log_signal.emit(f"Client error: {e}")
    
    def stop(self):
        """Stop the client"""
        if self.client:
            self.client.disconnect()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.client_thread = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ScreenHacker - Remote Desktop")
        self.setGeometry(100, 100, 600, 500)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Title
        title = QLabel("ScreenHacker")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Remote Desktop Sharing")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Host tab
        host_tab = self.create_host_tab()
        tabs.addTab(host_tab, "Host (Share Screen)")
        
        # Client tab
        client_tab = self.create_client_tab()
        tabs.addTab(client_tab, "Connect (View Remote)")
        
        # Status/Log area
        layout.addWidget(QLabel("Status:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        self.log("Welcome to ScreenHacker!")
        self.log(f"Your local IP: {self.get_local_ip()}")
        
    def create_host_tab(self):
        """Create the host tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Info
        info = QLabel("Share your screen with others. They can view and control your desktop.")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Settings
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("5555")
        self.port_input.setMaximumWidth(100)
        settings_layout.addWidget(self.port_input)
        
        settings_layout.addWidget(QLabel("FPS:"))
        self.fps_input = QLineEdit("30")
        self.fps_input.setMaximumWidth(100)
        settings_layout.addWidget(self.fps_input)
        
        settings_layout.addWidget(QLabel("Quality:"))
        self.quality_input = QLineEdit("90")
        self.quality_input.setMaximumWidth(100)
        settings_layout.addWidget(self.quality_input)

        settings_layout.addWidget(QLabel("Target KB:"))
        self.targetkb_input = QLineEdit("200")
        self.targetkb_input.setMaximumWidth(100)
        settings_layout.addWidget(self.targetkb_input)
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout)
        
        # Connection info
        self.connection_info = QLabel("")
        self.connection_info.setStyleSheet("background-color: #e0e0e0; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.connection_info)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_server_btn = QPushButton("Start Hosting")
        self.start_server_btn.clicked.connect(self.start_server)
        self.start_server_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        button_layout.addWidget(self.start_server_btn)
        
        self.stop_server_btn = QPushButton("Stop Hosting")
        self.stop_server_btn.clicked.connect(self.stop_server)
        self.stop_server_btn.setEnabled(False)
        self.stop_server_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
        button_layout.addWidget(self.stop_server_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return widget
    
    def create_client_tab(self):
        """Create the client tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Info
        info = QLabel("Connect to a remote computer to view and control it.")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Connection settings
        conn_layout = QHBoxLayout()
        
        conn_layout.addWidget(QLabel("Host IP:"))
        self.host_input = QLineEdit("192.168.1.100")
        conn_layout.addWidget(self.host_input)
        
        conn_layout.addWidget(QLabel("Port:"))
        self.client_port_input = QLineEdit("5555")
        self.client_port_input.setMaximumWidth(100)
        conn_layout.addWidget(self.client_port_input)
        
        layout.addLayout(conn_layout)
        
        # Viewer area
        self.viewer_label = QLabel("No video yet")
        self.viewer_label.setAlignment(Qt.AlignCenter)
        self.viewer_label.setStyleSheet("background-color: #000; color: #ccc; padding: 8px;")
        self.viewer_label.setMinimumHeight(360)
        layout.addWidget(self.viewer_label)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "• Press 'C' to toggle remote control ON/OFF\n"
            "• Press 'Q' to quit the remote session\n"
            "• When control is ON, your mouse and keyboard will control the remote computer"
        )
        instructions.setStyleSheet("background-color: #fff3cd; padding: 10px; border-radius: 5px;")
        layout.addWidget(instructions)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.start_client)
        self.connect_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        button_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.stop_client)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
        button_layout.addWidget(self.disconnect_btn)

        # Large viewer button
        self.open_viewer_btn = QPushButton("Open Large Viewer")
        self.open_viewer_btn.clicked.connect(self.open_large_viewer)
        self.open_viewer_btn.setEnabled(False)
        self.open_viewer_btn.setStyleSheet("padding: 10px;")
        button_layout.addWidget(self.open_viewer_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return widget
    
    def get_local_ip(self):
        """Get the local IP address"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except:
            return "Unable to determine"
    
    def log(self, message):
        """Add a message to the log"""
        self.log_text.append(message)
    
    def start_server(self):
        """Start the server"""
        try:
            port = int(self.port_input.text())
            fps = int(self.fps_input.text())
            quality = int(self.quality_input.text())
            target_kb = int(self.targetkb_input.text())
            
            self.server_thread = ServerThread(port, fps, quality, target_kb)
            self.server_thread.log_signal.connect(self.log)
            self.server_thread.start()
            
            self.start_server_btn.setEnabled(False)
            self.stop_server_btn.setEnabled(True)
            
            local_ip = self.get_local_ip()
            self.connection_info.setText(
                f"Server Running!\n"
                f"Share this connection code: {local_ip}:{port}"
            )
            
        except Exception as e:
            self.log(f"Error starting server: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start server: {e}")
    
    def stop_server(self):
        """Stop the server"""
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread.wait()
            self.server_thread = None
        
        self.start_server_btn.setEnabled(True)
        self.stop_server_btn.setEnabled(False)
        self.connection_info.setText("")
        self.log("Server stopped")
    
    def start_client(self):
        """Start the client"""
        try:
            host = self.host_input.text()
            port = int(self.client_port_input.text())
            
            self.client_thread = ClientThread(host, port)
            self.client_thread.log_signal.connect(self.log)
            self.client_thread.frame_signal.connect(self.update_viewer)
            self.client_thread.start()
            
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.open_viewer_btn.setEnabled(True)
            
        except Exception as e:
            self.log(f"Error connecting: {e}")
            QMessageBox.critical(self, "Error", f"Failed to connect: {e}")
    
    def stop_client(self):
        """Stop the client"""
        if self.client_thread:
            self.client_thread.stop()
            self.client_thread.wait()
            self.client_thread = None
        
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.open_viewer_btn.setEnabled(False)
        self.log("Disconnected from remote")

    def update_viewer(self, qimg: QImage):
        """Render received frame into the viewer label"""
        # Scale to fit while keeping aspect ratio
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(self.viewer_label.width(), self.viewer_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.viewer_label.setPixmap(scaled)

    # ---- Large Viewer ----
    def open_large_viewer(self):
        if not hasattr(self, 'viewer_windows'):
            self.viewer_windows = []
        vw = ViewerWindow(self)
        # Reuse existing stream by connecting to the same signal
        if self.client_thread:
            self.client_thread.frame_signal.connect(vw.update_frame)
        vw.show()
        self.viewer_windows.append(vw)


class ViewerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remote Viewer")
        self.resize(1024, 640)
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        self.label = QLabel("Loading…")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background:#000;color:#ccc;")
        v.addWidget(self.label)

        # Toolbar-like buttons
        row = QHBoxLayout()
        btn_full = QPushButton("Toggle Fullscreen")
        btn_full.clicked.connect(self.toggle_fullscreen)
        row.addWidget(btn_full)
        row.addStretch()
        v.addLayout(row)

        self._is_full = False

    def toggle_fullscreen(self):
        if self._is_full:
            self.showNormal()
        else:
            self.showFullScreen()
        self._is_full = not self._is_full

    def update_frame(self, qimg: QImage):
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Just close the viewer window, don't stop the server/client
        event.accept()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ScreenHacker - Remote Desktop Application")
    parser.add_argument('--host', action='store_true', help='Start in host mode')
    parser.add_argument('--connect', type=str, help='Connect to host IP')
    parser.add_argument('--port', type=int, default=5555, help='Port number')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second')
    parser.add_argument('--quality', type=int, default=80, help='Compression quality')
    parser.add_argument('--stealth', action='store_true', help='Run in stealth mode (hidden)')
    
    args = parser.parse_args()
    
    # Command line mode
    if args.host:
        server = ScreenShareServer(port=args.port, fps=args.fps, quality=args.quality)
        server.run()
        return
    
    if args.connect:
        client = ScreenShareClient()
        try:
            client.connect(args.connect, args.port)
            client.display_stream()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            client.disconnect()
        return
    
    # GUI mode (default)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
