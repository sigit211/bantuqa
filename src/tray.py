import pystray
from PIL import Image, ImageDraw
import threading
from .auth import AuthManager

class TrayManager:
    def __init__(self, on_show_dashboard, on_exit):
        self.on_show_dashboard = on_show_dashboard
        self.on_exit = on_exit
        self.icon = None

    def create_image(self):
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)
        d.ellipse((6, 6, 58, 58), fill=(40, 120, 220, 255), outline=(255, 255, 255, 255), width=3)
        d.rectangle((18, 24, 46, 42), fill=(255, 255, 255, 255))
        d.polygon([(18, 20), (46, 20), (32, 10)], fill=(255, 255, 255, 255))
        return image

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", lambda: self.on_show_dashboard()),
            pystray.MenuItem("Exit", lambda: self.stop())
        )
        self.icon = pystray.Icon("BantuQa", self.create_image(), "BantuQa", menu)
        self.icon.run()

    def stop(self):
        # Force logout by clearing credentials
        AuthManager.clear_credentials()
        if self.icon:
            self.icon.stop()
        self.on_exit()
