from pynput import keyboard
from typing import Callable

class HotkeyManager:
    def __init__(self, on_hotkey_callback: Callable[[], None]):
        self.on_hotkey_callback = on_hotkey_callback
        self.listener = None

    def start(self):
        self.listener = keyboard.GlobalHotKeys({
            '<ctrl>+<shift>+s': self.on_hotkey_callback
        })
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
