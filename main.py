"""
Main entry point with GUI for Screener
"""
import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                              QTextEdit, QTabWidget, QMessageBox, QComboBox, 
                              QInputDialog, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QImage, QPixmap, QIcon
import socket
import threading
from server import ScreenShareServer
from client import ScreenShareClient


class InteractiveViewer(QLabel):
    """Interactive viewer that can send mouse and keyboard events"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.remote_width = 1920  # Default, updated from server
        self.remote_height = 1080
        self.control_enabled = False
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(False)  # Only track when control is enabled
        
    def set_remote_size(self, width, height):
        """Set the remote screen dimensions"""
        self.remote_width = width
        self.remote_height = height
    
    def enable_control(self, enabled):
        """Enable or disable remote control"""
        self.control_enabled = enabled
        if enabled:
            self.setStyleSheet("border: 2px solid green; background-color: #000;")
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(True)
        else:
            self.setStyleSheet("background-color: #000; color: #ccc; font-size: 16px;")
            self.setCursor(Qt.ArrowCursor)
            self.setMouseTracking(False)
    
    def map_to_remote(self, local_x, local_y):
        """Map local coordinates to remote screen coordinates"""
        if not self.pixmap():
            return 0, 0
        
        # Get the displayed pixmap size
        pixmap = self.pixmap()
        pixmap_rect = pixmap.rect()
        
        # Calculate the position of the pixmap within the label (centered)
        label_rect = self.rect()
        x_offset = (label_rect.width() - pixmap_rect.width()) / 2
        y_offset = (label_rect.height() - pixmap_rect.height()) / 2
        
        # Adjust for offset
        adjusted_x = local_x - x_offset
        adjusted_y = local_y - y_offset
        
        # Map to remote coordinates
        if pixmap_rect.width() > 0 and pixmap_rect.height() > 0:
            remote_x = int((adjusted_x / pixmap_rect.width()) * self.remote_width)
            remote_y = int((adjusted_y / pixmap_rect.height()) * self.remote_height)
            return remote_x, remote_y
        
        return 0, 0
    
    def send_control_event(self, event_dict):
        """Send control event to server"""
        if not self.control_enabled:
            return
            
        if self.parent_window and self.parent_window.client_thread:
            client = self.parent_window.client_thread.client
            if client and client.connected:
                try:
                    import json
                    event_json = json.dumps(event_dict)
                    print(f"Sending control event: {event_json}")  # Debug
                    client.send_control_event(event_json)
                except Exception as e:
                    print(f"Error sending control event: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"Client not connected: client={client}, connected={client.connected if client else 'N/A'}")
        else:
            print(f"No client thread: parent={self.parent_window}, thread={self.parent_window.client_thread if self.parent_window else 'N/A'}")
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        if not self.control_enabled:
            super().mouseMoveEvent(event)
            return
            
        remote_x, remote_y = self.map_to_remote(event.x(), event.y())
        self.send_control_event({
            'type': 'mouse',
            'event_type': 'move',
            'x': remote_x,
            'y': remote_y
        })
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if not self.control_enabled:
            super().mousePressEvent(event)
            return
            
        remote_x, remote_y = self.map_to_remote(event.x(), event.y())
        button_map = {
            Qt.LeftButton: 'left',
            Qt.RightButton: 'right',
            Qt.MiddleButton: 'middle'
        }
        button = button_map.get(event.button(), 'left')
        self.send_control_event({
            'type': 'mouse',
            'event_type': 'click',
            'x': remote_x,
            'y': remote_y,
            'button': button,
            'pressed': True
        })
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if not self.control_enabled:
            super().mouseReleaseEvent(event)
            return
            
        remote_x, remote_y = self.map_to_remote(event.x(), event.y())
        button_map = {
            Qt.LeftButton: 'left',
            Qt.RightButton: 'right',
            Qt.MiddleButton: 'middle'
        }
        button = button_map.get(event.button(), 'left')
        self.send_control_event({
            'type': 'mouse',
            'event_type': 'click',
            'x': remote_x,
            'y': remote_y,
            'button': button,
            'pressed': False
        })
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel events"""
        if not self.control_enabled:
            super().wheelEvent(event)
            return
            
        delta = event.angleDelta().y() / 120  # Standard wheel step
        self.send_control_event({
            'type': 'mouse',
            'event_type': 'scroll',
            'dx': 0,
            'dy': int(delta)
        })
        super().wheelEvent(event)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if not self.control_enabled:
            super().keyPressEvent(event)
            return
            
        key_text = event.text()
        key = event.key()
        
        # Special keys mapping
        special_keys = {
            Qt.Key_Return: 'enter',
            Qt.Key_Enter: 'enter',
            Qt.Key_Tab: 'tab',
            Qt.Key_Space: 'space',
            Qt.Key_Backspace: 'backspace',
            Qt.Key_Delete: 'delete',
            Qt.Key_Escape: 'esc',
            Qt.Key_Control: 'ctrl',
            Qt.Key_Shift: 'shift',
            Qt.Key_Alt: 'alt',
            Qt.Key_Up: 'up',
            Qt.Key_Down: 'down',
            Qt.Key_Left: 'left',
            Qt.Key_Right: 'right',
        }
        
        if key in special_keys:
            self.send_control_event({
                'type': 'keyboard',
                'event_type': 'press',
                'key': special_keys[key],
                'is_special': True
            })
        elif key_text:
            self.send_control_event({
                'type': 'keyboard',
                'event_type': 'press',
                'key': key_text,
                'is_special': False
            })
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Handle key release events"""
        if not self.control_enabled:
            super().keyReleaseEvent(event)
            return
            
        key_text = event.text()
        key = event.key()
        
        special_keys = {
            Qt.Key_Return: 'enter',
            Qt.Key_Enter: 'enter',
            Qt.Key_Tab: 'tab',
            Qt.Key_Space: 'space',
            Qt.Key_Backspace: 'backspace',
            Qt.Key_Delete: 'delete',
            Qt.Key_Escape: 'esc',
            Qt.Key_Control: 'ctrl',
            Qt.Key_Shift: 'shift',
            Qt.Key_Alt: 'alt',
            Qt.Key_Up: 'up',
            Qt.Key_Down: 'down',
            Qt.Key_Left: 'left',
            Qt.Key_Right: 'right',
        }
        
        if key in special_keys:
            self.send_control_event({
                'type': 'keyboard',
                'event_type': 'release',
                'key': special_keys[key],
                'is_special': True
            })
        elif key_text:
            self.send_control_event({
                'type': 'keyboard',
                'event_type': 'release',
                'key': key_text,
                'is_special': False
            })
        super().keyReleaseEvent(event)


class ServerThread(QThread):
    """Thread for running the server"""
    log_signal = pyqtSignal(str)
    
    def __init__(self, port=5555, fps=30, quality=90, target_kb=200, monitor=1):
        super().__init__()
        self.port = port
        self.fps = fps
        self.quality = quality
        self.target_kb = target_kb
        self.monitor = monitor
        self.server = None
        
    def run(self):
        """Run the server"""
        try:
            self.server = ScreenShareServer(port=self.port, fps=self.fps, quality=self.quality, target_kb=self.target_kb, monitor=self.monitor)
            self.log_signal.emit(f"Server started on port {self.port}")
            self.log_signal.emit(f"Capturing monitor {self.monitor}")
            self.server.start()
            
            # Keep accepting new client connections
            while self.server.running:
                try:
                    self.log_signal.emit(f"Waiting for connection...")
                    client_addr = self.server.wait_for_client()
                    
                    # Check if connection was successful
                    if client_addr is None:
                        # Server was stopped
                        break
                    
                    self.log_signal.emit("Client connected!")
                    
                    # Wait while client is connected (streaming)
                    while self.server.streaming and self.server.running:
                        threading.Event().wait(0.5)
                    
                    # Client disconnected, clean up for next connection
                    if self.server.running:
                        self.log_signal.emit("Client disconnected, ready for new connection")
                        self.server.cleanup_client()
                        
                except Exception as conn_err:
                    if self.server.running:
                        self.log_signal.emit(f"Connection error: {conn_err}")
                        self.server.cleanup_client()
                        threading.Event().wait(1)  # Brief pause before accepting next connection
                
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
    connection_failed = pyqtSignal()
    
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
            self.log_signal.emit(f"Connection failed: {conn_err}")
            self.connection_failed.emit()
            if self.client:
                self.client.disconnect()
        except Exception as e:
            self.log_signal.emit(f"Client error: {e}")
            self.connection_failed.emit()
            if self.client:
                self.client.disconnect()
    
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
        self.devices_file = os.path.join(os.path.dirname(__file__), 'saved_devices.json')
        self.saved_devices = self.load_saved_devices()
        self.init_ui()
        self.init_tray_icon()
        # Auto-start hosting server
        self.auto_start_server()
        
    def auto_start_server(self):
        """Automatically start the hosting server on app launch"""
        try:
            # Small delay to ensure UI is ready
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, self.start_server)
        except Exception as e:
            print(f"Error auto-starting server: {e}")
    
    def init_tray_icon(self):
        """Initialize system tray icon"""
        # Create the tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Try to set an icon (using default application icon if available)
        try:
            # You can replace this with a custom icon file path
            self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        except:
            pass
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide to Tray", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("Screener - Remote Desktop")
        
        # Double-click to show window
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # Show the tray icon
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()
    
    def show_from_tray(self):
        """Show window from system tray"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def quit_application(self):
        """Quit the application completely"""
        # Stop server and client if running
        if self.server_thread:
            self.stop_server()
        if self.client_thread:
            self.stop_client()
        
        # Hide tray icon
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        QApplication.quit()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Screener - Remote Desktop")
        self.setGeometry(100, 100, 1200, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Title
        title = QLabel("Screener")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Main content area - horizontal split
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # Left side - Controls (30%)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(400)
        
        # Host section
        host_group = QLabel("HOST SETTINGS")
        host_group.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(host_group)
        
        # Monitor selection
        monitor_layout = QHBoxLayout()
        monitor_layout.addWidget(QLabel("Monitor:"))
        self.monitor_combo = QComboBox()
        self.populate_monitors()
        self.monitor_combo.setMaximumWidth(150)
        self.monitor_combo.currentIndexChanged.connect(self.on_monitor_changed)
        monitor_layout.addWidget(self.monitor_combo)
        monitor_layout.addStretch()
        left_layout.addLayout(monitor_layout)
        
        # Server settings
        server_settings = QHBoxLayout()
        server_settings.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("5555")
        self.port_input.setMaximumWidth(60)
        server_settings.addWidget(self.port_input)
        server_settings.addWidget(QLabel("FPS:"))
        self.fps_input = QLineEdit("30")
        self.fps_input.setMaximumWidth(50)
        server_settings.addWidget(self.fps_input)
        server_settings.addWidget(QLabel("Quality:"))
        self.quality_input = QLineEdit("90")
        self.quality_input.setMaximumWidth(50)
        server_settings.addWidget(self.quality_input)
        server_settings.addWidget(QLabel("KB:"))
        self.targetkb_input = QLineEdit("200")
        self.targetkb_input.setMaximumWidth(50)
        server_settings.addWidget(self.targetkb_input)
        left_layout.addLayout(server_settings)
        
        # Connection info
        self.connection_info = QLabel("")
        self.connection_info.setStyleSheet("background-color: #e0e0e0; padding: 8px; border-radius: 5px;")
        self.connection_info.setWordWrap(True)
        left_layout.addWidget(self.connection_info)
        
        # Server buttons
        server_btn_layout = QHBoxLayout()
        self.start_server_btn = QPushButton("Start Hosting")
        self.start_server_btn.clicked.connect(self.start_server)
        self.start_server_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        server_btn_layout.addWidget(self.start_server_btn)
        
        self.stop_server_btn = QPushButton("Stop Hosting")
        self.stop_server_btn.clicked.connect(self.stop_server)
        self.stop_server_btn.setEnabled(False)
        self.stop_server_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        server_btn_layout.addWidget(self.stop_server_btn)
        left_layout.addLayout(server_btn_layout)
        
        left_layout.addWidget(QLabel(""))  # Spacer
        
        # Client section
        client_group = QLabel("CLIENT SETTINGS")
        client_group.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(client_group)
        
        # Saved devices
        left_layout.addWidget(QLabel("Saved Devices:"))
        self.saved_devices_combo = QComboBox()
        self.saved_devices_combo.addItem("-- Select a saved device --")
        self.populate_saved_devices()
        self.saved_devices_combo.currentIndexChanged.connect(self.on_device_selected)
        left_layout.addWidget(self.saved_devices_combo)
        
        saved_btn_layout = QHBoxLayout()
        save_device_btn = QPushButton("💾 Save")
        save_device_btn.clicked.connect(self.save_current_device)
        save_device_btn.setStyleSheet("padding: 5px;")
        saved_btn_layout.addWidget(save_device_btn)
        
        delete_device_btn = QPushButton("🗑️ Delete")
        delete_device_btn.clicked.connect(self.delete_saved_device)
        delete_device_btn.setStyleSheet("padding: 5px;")
        saved_btn_layout.addWidget(delete_device_btn)
        left_layout.addLayout(saved_btn_layout)
        
        # Connection settings
        left_layout.addWidget(QLabel("Host IP:"))
        self.host_input = QLineEdit("192.168.1.100")
        left_layout.addWidget(self.host_input)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.client_port_input = QLineEdit("5555")
        self.client_port_input.setMaximumWidth(100)
        port_layout.addWidget(self.client_port_input)
        port_layout.addStretch()
        left_layout.addLayout(port_layout)
        
        # Client buttons
        client_btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.start_client)
        self.connect_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        client_btn_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.stop_client)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        client_btn_layout.addWidget(self.disconnect_btn)
        left_layout.addLayout(client_btn_layout)
        
        self.open_viewer_btn = QPushButton("Open Large Viewer")
        self.open_viewer_btn.clicked.connect(self.open_large_viewer)
        self.open_viewer_btn.setEnabled(False)
        self.open_viewer_btn.setStyleSheet("padding: 8px;")
        left_layout.addWidget(self.open_viewer_btn)
        
        left_layout.addStretch()
        
        content_layout.addWidget(left_panel)
        
        # Right side - Video viewer (70%)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Viewer area - takes all available space
        self.viewer_label = InteractiveViewer(self)
        self.viewer_label.setText("Remote Screen\n\nConnect to view remote desktop")
        self.viewer_label.setAlignment(Qt.AlignCenter)
        self.viewer_label.setStyleSheet("background-color: #000; color: #ccc; font-size: 16px;")
        self.viewer_label.setMinimumSize(600, 400)
        right_layout.addWidget(self.viewer_label)
        
        # Control toggle button
        control_layout = QHBoxLayout()
        self.control_toggle_btn = QPushButton("🎮 Enable Remote Control (Click to activate)")
        self.control_toggle_btn.clicked.connect(self.toggle_remote_control)
        self.control_toggle_btn.setEnabled(False)
        self.control_toggle_btn.setStyleSheet("padding: 8px; font-weight: bold;")
        control_layout.addWidget(self.control_toggle_btn)
        right_layout.addLayout(control_layout)
        
        content_layout.addWidget(right_panel, stretch=1)
        
        # Status/Log area at bottom
        main_layout.addWidget(QLabel("Status:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        main_layout.addWidget(self.log_text)
        
        self.log("Welcome to Screener!")
        self.log(f"Your local IP: {self.get_local_ip()}")
    
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
    
    def populate_monitors(self):
        """Populate the monitor selection dropdown"""
        try:
            import mss
            with mss.mss() as sct:
                monitors = sct.monitors
                self.monitor_combo.clear()
                # Skip index 0 (all monitors combined)
                for i in range(1, len(monitors)):
                    mon = monitors[i]
                    self.monitor_combo.addItem(
                        f"Monitor {i}: {mon['width']}x{mon['height']}",
                        i
                    )
        except Exception as e:
            print(f"Error listing monitors: {e}")
            self.monitor_combo.addItem("Monitor 1 (Primary)", 1)
    
    def on_monitor_changed(self, index):
        """Handle monitor selection change"""
        if self.server_thread and self.server_thread.isRunning():
            monitor = self.monitor_combo.currentData() or 1
            self.log(f"Switching to Monitor {monitor}...")
            # Change monitor on the running server
            if hasattr(self.server_thread, 'server') and self.server_thread.server:
                self.server_thread.server.change_monitor(monitor)
    
    def load_saved_devices(self):
        """Load saved devices from JSON file"""
        if os.path.exists(self.devices_file):
            try:
                with open(self.devices_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading saved devices: {e}")
                return {}
        return {}
    
    def save_devices_to_file(self):
        """Save devices to JSON file"""
        try:
            with open(self.devices_file, 'w') as f:
                json.dump(self.saved_devices, f, indent=2)
        except Exception as e:
            print(f"Error saving devices: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save devices: {e}")
    
    def populate_saved_devices(self):
        """Populate the saved devices dropdown"""
        self.saved_devices_combo.clear()
        self.saved_devices_combo.addItem("-- Select a saved device --")
        for name in sorted(self.saved_devices.keys()):
            device = self.saved_devices[name]
            self.saved_devices_combo.addItem(f"{name} ({device['host']}:{device['port']})", name)
    
    def on_device_selected(self, index):
        """Handle device selection from dropdown"""
        if index > 0:  # Skip the first "Select" item
            device_name = self.saved_devices_combo.currentData()
            if device_name and device_name in self.saved_devices:
                device = self.saved_devices[device_name]
                self.host_input.setText(device['host'])
                self.client_port_input.setText(str(device['port']))
                self.log(f"Selected device: {device_name}")
    
    def save_current_device(self):
        """Save current connection settings as a device"""
        host = self.host_input.text().strip()
        port = self.client_port_input.text().strip()
        
        if not host or not port:
            QMessageBox.warning(self, "Invalid Input", "Please enter both host IP and port.")
            return
        
        # Ask for device name
        name, ok = QInputDialog.getText(self, "Save Device", 
                                         "Enter a name for this device:",
                                         text=host)
        
        if ok and name:
            name = name.strip()
            if name:
                self.saved_devices[name] = {
                    'host': host,
                    'port': int(port) if port.isdigit() else 5555
                }
                self.save_devices_to_file()
                self.populate_saved_devices()
                self.log(f"Saved device: {name}")
                QMessageBox.information(self, "Success", f"Device '{name}' saved successfully!")
    
    def delete_saved_device(self):
        """Delete the selected saved device"""
        index = self.saved_devices_combo.currentIndex()
        if index > 0:
            device_name = self.saved_devices_combo.currentData()
            if device_name and device_name in self.saved_devices:
                reply = QMessageBox.question(self, "Delete Device",
                                            f"Are you sure you want to delete '{device_name}'?",
                                            QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    del self.saved_devices[device_name]
                    self.save_devices_to_file()
                    self.populate_saved_devices()
                    self.log(f"Deleted device: {device_name}")
        else:
            QMessageBox.information(self, "No Selection", "Please select a device to delete.")
    
    def start_server(self):
        """Start the server"""
        try:
            port = int(self.port_input.text())
            fps = int(self.fps_input.text())
            quality = int(self.quality_input.text())
            target_kb = int(self.targetkb_input.text())
            monitor = self.monitor_combo.currentData() or 1
            
            self.server_thread = ServerThread(port, fps, quality, target_kb, monitor)
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
        # Make sure any previous client is fully stopped
        if self.client_thread:
            self.log("Cleaning up previous connection...")
            self.stop_client()
        
        try:
            host = self.host_input.text()
            port = int(self.client_port_input.text())
            
            self.client_thread = ClientThread(host, port)
            self.client_thread.log_signal.connect(self.log)
            self.client_thread.frame_signal.connect(self.update_viewer)
            self.client_thread.connection_failed.connect(self.on_connection_failed)
            self.client_thread.start()
            
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.open_viewer_btn.setEnabled(True)
            
            # Enable control button after a short delay to ensure connection is stable
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.control_toggle_btn.setEnabled(True))
            
        except Exception as e:
            self.log(f"Error connecting: {e}")
            QMessageBox.critical(self, "Error", f"Failed to connect: {e}")
    
    def on_connection_failed(self):
        """Handle connection failure by auto-disconnecting"""
        self.log("Auto-disconnecting due to connection failure...")
        self.stop_client()
    
    def stop_client(self):
        """Stop the client"""
        if self.client_thread:
            # Disconnect all signals before stopping
            try:
                self.client_thread.log_signal.disconnect()
            except:
                pass
            try:
                self.client_thread.frame_signal.disconnect()
            except:
                pass
            
            self.client_thread.stop()
            self.client_thread.wait(3000)  # Wait up to 3 seconds (positional argument)
            self.client_thread = None
        
        # Clean up viewer windows
        if hasattr(self, 'viewer_windows'):
            for vw in self.viewer_windows:
                try:
                    vw.close()
                except:
                    pass
            self.viewer_windows = []
        
        # Reset viewer label
        self.viewer_label.clear()
        self.viewer_label.setText("No video yet")
        self.viewer_label.enable_control(False)
        
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.open_viewer_btn.setEnabled(False)
        self.control_toggle_btn.setEnabled(False)
        self.log("Disconnected from remote")

    def update_viewer(self, qimg: QImage):
        """Render received frame into the viewer label"""
        # Scale to fit while keeping aspect ratio
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(self.viewer_label.width(), self.viewer_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.viewer_label.setPixmap(scaled)
        
        # Update remote screen size if not set
        if self.viewer_label.remote_width == 1920 and qimg.width() > 0:
            self.viewer_label.set_remote_size(qimg.width(), qimg.height())
    
    def toggle_remote_control(self):
        """Toggle remote control on/off"""
        if not self.client_thread or not self.client_thread.client:
            self.log("Error: Not connected to remote")
            QMessageBox.warning(self, "Not Connected", "Please connect to a remote computer first.")
            return
        
        if not self.client_thread.client.connected:
            self.log("Error: Connection not established")
            QMessageBox.warning(self, "Connection Error", "Connection not fully established. Please wait.")
            return
            
        current_state = self.viewer_label.control_enabled
        new_state = not current_state
        self.viewer_label.enable_control(new_state)
        
        if new_state:
            self.control_toggle_btn.setText("🎮 Remote Control: ON (Green border)")
            self.control_toggle_btn.setStyleSheet("padding: 8px; font-weight: bold; background-color: #4CAF50; color: white;")
            self.log("Remote control ENABLED - Click on screen to control")
            self.viewer_label.setFocus()
        else:
            self.control_toggle_btn.setText("🎮 Enable Remote Control (Click to activate)")
            self.control_toggle_btn.setStyleSheet("padding: 8px; font-weight: bold;")
            self.log("Remote control DISABLED")

    # ---- Large Viewer ----
    def open_large_viewer(self):
        if not hasattr(self, 'viewer_windows'):
            self.viewer_windows = []
        vw = ViewerWindow(self, self.client_thread)
        # Reuse existing stream by connecting to the same signal
        if self.client_thread:
            self.client_thread.frame_signal.connect(vw.update_frame)
        vw.show()
        self.viewer_windows.append(vw)
    
    def changeEvent(self, event):
        """Handle window state changes - minimize to tray"""
        if event.type() == event.WindowStateChange:
            if self.isMinimized():
                event.ignore()
                self.hide()
                if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                    self.tray_icon.showMessage(
                        "Screener",
                        "Application minimized to tray",
                        QSystemTrayIcon.Information,
                        2000
                    )
                return
        super().changeEvent(event)
    
    def closeEvent(self, event):
        """Handle close event - minimize to tray instead of closing"""
        event.ignore()
        self.hide()
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Screener",
                "Application is still running in the background",
                QSystemTrayIcon.Information,
                2000
            )


class ViewerWindow(QMainWindow):
    def __init__(self, parent=None, client_thread=None):
        super().__init__(parent)
        self.client_thread = client_thread
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
        # Disconnect from signal if still connected
        if self.client_thread:
            try:
                self.client_thread.frame_signal.disconnect(self.update_frame)
            except:
                pass
        # Remove from parent's viewer_windows list
        if self.parent() and hasattr(self.parent(), 'viewer_windows'):
            try:
                self.parent().viewer_windows.remove(self)
            except:
                pass
        event.accept()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Screener - Remote Desktop Application")
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
