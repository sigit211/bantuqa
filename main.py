import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import threading
import sys
import os
import re
import time
import logging

LOG_DIR = os.path.join(os.environ.get("TEMP", "."), "BantuQa")
LOG_FILE = os.path.join(LOG_DIR, "BantuQa.log")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

script_dir = os.path.abspath(os.path.dirname(__file__))
if getattr(sys, '_MEIPASS', None):
    script_dir = sys._MEIPASS
project_root = os.path.abspath(os.path.join(script_dir, '..'))
SCREENSHOT_BASE = os.path.join(project_root, 'Screenshots')
os.makedirs(SCREENSHOT_BASE, exist_ok=True)
if os.path.isdir(os.path.join(script_dir, 'src')):
    sys.path.insert(0, script_dir)
elif os.path.isdir(os.path.join(project_root, 'src')):
    sys.path.insert(0, project_root)
else:
    sys.path.insert(0, script_dir)

from src.ui import BantuQaApp
from src.capture import SnippingTool
from src.hotkey import HotkeyManager
from src.tray import TrayManager
from src.single_instance import SingleInstanceManager
from src.auth import AuthManager

def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_\- ]+", "", name or "")
    return safe.strip().replace(" ", "_") or "default"


def get_system_uptime_ms():
    """Get system uptime in milliseconds using Windows API."""
    try:
        return ctypes.windll.kernel32.GetTickCount64()
    except Exception as e:
        logging.error(f"Failed to get system uptime: {e}")
        return None


def check_system_restart():
    """Check if system has restarted since last app run.
    If restarted or first run, clear credentials to force login."""
    uptime_file = os.path.join(LOG_DIR, ".last_uptime")
    current_uptime = get_system_uptime_ms()
    
    if current_uptime is None:
        logging.warning("Could not determine system uptime. Proceeding without restart check.")
        return
    
    try:
        if os.path.exists(uptime_file):
            # Read last saved uptime
            with open(uptime_file, 'r') as f:
                last_uptime = int(f.read().strip())
            
            if current_uptime < last_uptime:
                # System was restarted (uptime decreased)
                logging.info(f"System restart detected. Last uptime: {last_uptime}ms, Current: {current_uptime}ms. Clearing credentials.")
                AuthManager.clear_credentials()
            else:
                # Normal app re-launch without restart
                logging.debug(f"Normal app re-launch. Uptime preserved: {current_uptime}ms")
        else:
            # First run ever
            logging.info("First run detected. Clearing any previous credentials and forcing login.")
            AuthManager.clear_credentials()
    except Exception as e:
        logging.error(f"Error checking system restart: {e}")
    finally:
        # Always save current uptime for next run
        try:
            with open(uptime_file, 'w') as f:
                f.write(str(current_uptime))
            logging.debug(f"Saved current uptime: {current_uptime}ms")
        except Exception as e:
            logging.error(f"Failed to save uptime: {e}")


def main():
    # Check if system has restarted since last app run
    check_system_restart()
    
    # Check if another instance is already running
    instance_manager = SingleInstanceManager()
    if instance_manager.check_existing_instance():
        logging.info("Another instance is already running. Exiting.")
        print("Another instance is already running!")
        return
    
    # Create lock for this instance
    if not instance_manager.create_instance_lock():
        logging.error("Failed to create instance lock")
        return
    
    capture_queue = []
    
    tray_manager = None
    app = None
    
    def setup_tray():
        nonlocal tray_manager
        if tray_manager is None:
            tray_manager = TrayManager(
                on_show_dashboard=lambda: app.after(0, app.show_window),
                on_exit=on_exit
            )
            threading.Thread(target=tray_manager.run, daemon=True).start()
    
    def on_window_closed():
        app.hide_window()
        setup_tray()
    
    app = BantuQaApp(
        capture_queue,
        on_capture_request=lambda step_number=None: start_snipping(step_number),
        on_window_close=on_window_closed
    )
    
    def on_capture_callback(img_path):
        capture_queue.append(img_path)
        if getattr(app, 'pending_step_capture', None) is not None:
            step_number = app.pending_step_capture
            app.after(0, lambda: app.register_step_attachment(step_number, img_path))
            app.after(0, lambda: app.append_log(f"[{app.get_timestamp()}] Screenshot attached to step {step_number}: {img_path}\n"))
        else:
            app.after(0, app.update_dashboard_thumbnails)
            app.after(0, lambda: app.append_log(f"[{app.get_timestamp()}] Screenshot tersimpan: {img_path}\n"))
    
    snipping_tool = SnippingTool(on_capture_callback, parent=app)
    
    def get_screenshot_dir():
        case_name = getattr(app, 'case_var', None) and app.case_var.get()
        cases_map = getattr(app, 'cases_map', {})
        case_id = cases_map.get(case_name)
        base_dir = SCREENSHOT_BASE
        if case_id:
            folder_name = f"case_{case_id}"
        elif case_name:
            folder_name = sanitize_filename(case_name)
        else:
            folder_name = "default"
        return os.path.join(base_dir, folder_name)

    def start_snipping(step_number=None):
        save_dir = get_screenshot_dir()
        if step_number is not None:
            app.pending_step_capture = step_number
        else:
            app.pending_step_capture = None
        app.after(0, lambda: snipping_tool.start_snipping(save_dir=save_dir))

    hotkey_manager = HotkeyManager(on_hotkey_callback=start_snipping)
    hotkey_manager.start()
    
    def on_exit():
        instance_manager.cleanup()
        hotkey_manager.stop()
        app.quit()
        os._exit(0)
    
    # Thread untuk listen signal dari instance lain
    def listen_for_signal():
        while True:
            try:
                if instance_manager.wait_for_signal(timeout_ms=500):
                    logging.info("Received signal from another instance. Showing window.")
                    app.after(0, app.show_window)
            except Exception as e:
                logging.error(f"Error listening for signal: {e}")
                break
    
    signal_thread = threading.Thread(target=listen_for_signal, daemon=True)
    signal_thread.start()
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            on_exit()
            return
        logging.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        on_exit()

    sys.excepthook = handle_exception

    try:
        app.mainloop()
    except KeyboardInterrupt:
        on_exit()
    except Exception:
        logging.exception("Exception in main loop")
        on_exit()

if __name__ == '__main__':
    main()
