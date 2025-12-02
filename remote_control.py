"""
Remote control module for sending and receiving mouse/keyboard events
"""
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import json


class RemoteController:
    """Handles remote mouse and keyboard control"""
    
    def __init__(self):
        """Initialize remote controller"""
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
    def execute_mouse_event(self, event_data):
        """
        Execute a mouse event
        
        Args:
            event_data: Dictionary with event information
                {
                    'type': 'move'|'click'|'scroll',
                    'x': int,
                    'y': int,
                    'button': 'left'|'right'|'middle',
                    'pressed': bool,
                    'dx': int,
                    'dy': int
                }
        """
        event_type = event_data.get('type') or event_data.get('event_type')
        
        if event_type == 'move':
            x = event_data.get('x', 0)
            y = event_data.get('y', 0)
            self.mouse.position = (x, y)
            
        elif event_type == 'click':
            button_name = event_data.get('button', 'left')
            pressed = event_data.get('pressed', True)
            
            button_map = {
                'left': Button.left,
                'right': Button.right,
                'middle': Button.middle
            }
            button = button_map.get(button_name, Button.left)
            
            if pressed:
                self.mouse.press(button)
            else:
                self.mouse.release(button)
                
        elif event_type == 'scroll':
            dx = event_data.get('dx', 0)
            dy = event_data.get('dy', 0)
            self.mouse.scroll(dx, dy)
    
    def execute_keyboard_event(self, event_data):
        """
        Execute a keyboard event
        
        Args:
            event_data: Dictionary with event information
                {
                    'type': 'press'|'release',
                    'key': str,
                    'is_special': bool
                }
        """
        event_type = event_data.get('type') or event_data.get('event_type')
        key_str = event_data.get('key')
        is_special = event_data.get('is_special', False)
        
        # Handle special keys
        if is_special:
            key_map = {
                'enter': Key.enter,
                'tab': Key.tab,
                'space': Key.space,
                'backspace': Key.backspace,
                'delete': Key.delete,
                'esc': Key.esc,
                'ctrl': Key.ctrl,
                'shift': Key.shift,
                'alt': Key.alt,
                'cmd': Key.cmd,
                'up': Key.up,
                'down': Key.down,
                'left': Key.left,
                'right': Key.right,
            }
            key = key_map.get(key_str.lower())
        else:
            key = key_str
        
        if key:
            if event_type == 'press':
                self.keyboard.press(key)
            elif event_type == 'release':
                self.keyboard.release(key)
    
    def execute_event(self, event_json):
        """
        Execute an event from JSON string
        
        Args:
            event_json: JSON string with event data
        """
        try:
            event_data = json.loads(event_json)
            print(f"RemoteController executing: {event_data}")  # Debug
            # Support both 'category' and 'type' for backwards compatibility
            category = event_data.get('category') or event_data.get('type')
            print(f"Event category: {category}")  # Debug
            
            if category == 'mouse':
                # Map event_type to type for execute_mouse_event
                if 'event_type' in event_data:
                    event_data['type'] = event_data['event_type']
                print(f"Executing mouse event: {event_data}")  # Debug
                self.execute_mouse_event(event_data)
            elif category == 'keyboard':
                # Map event_type to type for execute_keyboard_event
                if 'event_type' in event_data:
                    event_data['type'] = event_data['event_type']
                print(f"Executing keyboard event: {event_data}")  # Debug
                self.execute_keyboard_event(event_data)
            else:
                print(f"Unknown category: {category}")  # Debug
        except Exception as e:
            print(f"Error executing event: {e}")
            import traceback
            traceback.print_exc()


class InputCapture:
    """Captures local mouse and keyboard events to send remotely"""
    
    def __init__(self):
        """Initialize input capture"""
        self.mouse_listener = None
        self.keyboard_listener = None
        self.on_event = None
        self.enabled = False
        
    def start(self, callback):
        """
        Start capturing input events
        
        Args:
            callback: Function to call with event data (JSON string)
        """
        self.on_event = callback
        self.enabled = True
        
        # Start mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        
        # Start keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
    def stop(self):
        """Stop capturing input events"""
        self.enabled = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
    
    def _on_mouse_move(self, x, y):
        """Handle mouse move event"""
        if self.enabled and self.on_event:
            event = {
                'category': 'mouse',
                'type': 'move',
                'x': x,
                'y': y
            }
            self.on_event(json.dumps(event))
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click event"""
        if self.enabled and self.on_event:
            button_name = 'left'
            if button == Button.right:
                button_name = 'right'
            elif button == Button.middle:
                button_name = 'middle'
                
            event = {
                'category': 'mouse',
                'type': 'click',
                'x': x,
                'y': y,
                'button': button_name,
                'pressed': pressed
            }
            self.on_event(json.dumps(event))
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll event"""
        if self.enabled and self.on_event:
            event = {
                'category': 'mouse',
                'type': 'scroll',
                'x': x,
                'y': y,
                'dx': dx,
                'dy': dy
            }
            self.on_event(json.dumps(event))
    
    def _on_key_press(self, key):
        """Handle key press event"""
        if self.enabled and self.on_event:
            event = self._format_key_event('press', key)
            if event:
                self.on_event(json.dumps(event))
    
    def _on_key_release(self, key):
        """Handle key release event"""
        if self.enabled and self.on_event:
            event = self._format_key_event('release', key)
            if event:
                self.on_event(json.dumps(event))
    
    def _format_key_event(self, event_type, key):
        """Format keyboard event data"""
        is_special = False
        key_str = ''
        
        try:
            # Check if it's a special key
            if isinstance(key, Key):
                is_special = True
                key_str = key.name
            else:
                key_str = key.char if hasattr(key, 'char') else str(key)
        except AttributeError:
            key_str = str(key)
        
        return {
            'category': 'keyboard',
            'type': event_type,
            'key': key_str,
            'is_special': is_special
        }


if __name__ == "__main__":
    # Test remote control
    import time
    
    def test_controller():
        controller = RemoteController()
        
        # Test mouse movement
        print("Moving mouse...")
        controller.execute_mouse_event({
            'type': 'move',
            'x': 500,
            'y': 500
        })
        time.sleep(1)
        
        # Test mouse click
        print("Clicking...")
        controller.execute_mouse_event({
            'type': 'click',
            'button': 'left',
            'pressed': True
        })
        controller.execute_mouse_event({
            'type': 'click',
            'button': 'left',
            'pressed': False
        })
        
        print("Test complete")
    
    # Uncomment to test
    # test_controller()
