import mss
import mss.tools
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
import tkinter.messagebox as messagebox
import os
import uuid
import time
from typing import Callable, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCREENSHOT_DIR = os.path.join(PROJECT_ROOT, "Screenshots")
TEMP_DIR = os.path.join(os.environ.get("TEMP", "."), "BantuQa")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

MAX_UPLOAD_WIDTH = 1200
MAX_UPLOAD_HEIGHT = 1200
MAX_UPLOAD_SIZE_BYTES = 1200 * 1024


def save_image_for_upload(image: Image.Image, output_path: str) -> None:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    width, height = image.size
    if width > MAX_UPLOAD_WIDTH or height > MAX_UPLOAD_HEIGHT:
        scale = min(MAX_UPLOAD_WIDTH / width, MAX_UPLOAD_HEIGHT / height)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = image.resize(new_size, Image.LANCZOS)

    def _save(img: Image.Image) -> None:
        img.save(output_path, optimize=True, compress_level=9)

    _save(image)

    for attempt in range(6):
        file_size = os.path.getsize(output_path)
        if file_size <= MAX_UPLOAD_SIZE_BYTES:
            return

        if attempt == 0:
            image = image.quantize(colors=256, method=Image.FASTOCTREE)
        elif attempt == 1:
            image = image.quantize(colors=128, method=Image.FASTOCTREE)
        elif attempt == 2:
            image = image.quantize(colors=64, method=Image.FASTOCTREE)
        elif attempt == 3:
            image = image.quantize(colors=32, method=Image.FASTOCTREE)
        elif attempt == 4:
            width, height = image.size
            new_size = (max(1, int(width * 0.9)), max(1, int(height * 0.9)))
            image = image.resize(new_size, Image.LANCZOS)
        else:
            width, height = image.size
            new_size = (max(1, int(width * 0.8)), max(1, int(height * 0.8)))
            image = image.resize(new_size, Image.LANCZOS)

        _save(image)

class AnnotationWindow:
    def __init__(self, image_path: str, parent=None):
        self.image_path = image_path
        self.image = Image.open(image_path).convert("RGBA")
        self.saved_path = image_path
        self.root_owner: Optional[tk.Tk] = None
        if parent is not None and parent.winfo_viewable():
            self.window = tk.Toplevel(parent)
            self.window.transient(parent)
        else:
            self.root_owner = tk.Tk()
            self.root_owner.withdraw()
            self.window = tk.Toplevel(self.root_owner)

        self.window.title("Annotate Screenshot")
        self.window.resizable(True, True)
        self.window.attributes("-topmost", True)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        
        # Maximize window on Windows
        try:
            self.window.state('zoomed')
        except:
            # Fallback for other systems
            self.window.geometry(f"{self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()}")

        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas = tk.Canvas(self.window, cursor="cross", bg="gray20")
        self.canvas.pack(side="top", fill="both", expand=True)
        
        # Store image position and ID for centering
        self.image_id = None
        self.image_x = 0  # Image position in canvas
        self.image_y = 0
        
        # Center image in canvas after window updates
        self.window.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.image_x = canvas_width // 2
        self.image_y = canvas_height // 2
        self.image_id = self.canvas.create_image(self.image_x, self.image_y, anchor="center", image=self.tk_image)

        self.draw = ImageDraw.Draw(self.image)
        self.current_tool = "pen"
        self.color = (255, 0, 0, 255)
        self.pen_width = 4
        self.start_x = None
        self.start_y = None
        self.temp_shape = None

        control_frame = tk.Frame(self.window)
        control_frame.pack(side="bottom", fill="x", padx=8, pady=8)

        tk.Button(control_frame, text="Pen", command=lambda: self.set_tool("pen")).pack(side="left", padx=4)
        tk.Button(control_frame, text="Box", command=lambda: self.set_tool("box")).pack(side="left", padx=4)
        tk.Button(control_frame, text="Clear", command=self.clear_annotations).pack(side="left", padx=4)
        tk.Button(control_frame, text="Save", command=self.save_and_close).pack(side="right", padx=4)
        tk.Button(control_frame, text="Cancel", command=self.cancel).pack(side="right", padx=4)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    def set_tool(self, tool: str):
        self.current_tool = tool

    def _canvas_to_image_coords(self, canvas_x, canvas_y):
        """Convert canvas coordinates to image coordinates"""
        img_x = int(canvas_x - (self.image_x - self.image.width / 2))
        img_y = int(canvas_y - (self.image_y - self.image.height / 2))
        return img_x, img_y

    def clear_annotations(self):
        self.canvas.delete("all")
        self.image = Image.open(self.image_path).convert("RGBA")
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.image_x = canvas_width // 2
        self.image_y = canvas_height // 2
        self.image_id = self.canvas.create_image(self.image_x, self.image_y, anchor="center", image=self.tk_image)
        self.draw = ImageDraw.Draw(self.image)

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.current_tool == "box":
            self.temp_shape = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="yellow", width=3, tag="annotation")

    def on_move_press(self, event):
        if self.current_tool == "pen" and self.start_x is not None and self.start_y is not None:
            self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill="red", width=self.pen_width, capstyle="round", smooth=True, tag="annotation")
            # Convert canvas coordinates to image coordinates for drawing
            start_img_x, start_img_y = self._canvas_to_image_coords(self.start_x, self.start_y)
            end_img_x, end_img_y = self._canvas_to_image_coords(event.x, event.y)
            self.draw.line([start_img_x, start_img_y, end_img_x, end_img_y], fill=self.color, width=self.pen_width)
            self.start_x = event.x
            self.start_y = event.y
        elif self.current_tool == "box" and self.temp_shape is not None:
            self.canvas.coords(self.temp_shape, self.start_x, self.start_y, event.x, event.y)

    def on_button_release(self, event):
        if self.current_tool == "box" and self.start_x is not None and self.start_y is not None:
            self.canvas.delete(self.temp_shape)
            self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="yellow", width=3, tag="annotation")
            # Convert canvas coordinates to image coordinates for drawing
            start_img_x, start_img_y = self._canvas_to_image_coords(self.start_x, self.start_y)
            end_img_x, end_img_y = self._canvas_to_image_coords(event.x, event.y)
            self.draw.rectangle([start_img_x, start_img_y, end_img_x, end_img_y], outline=(255, 255, 0, 255), width=3)
            self.temp_shape = None
        self.start_x = None
        self.start_y = None

    def save_and_close(self):
        output_path = os.path.splitext(self.image_path)[0] + "_annotated.png"
        save_image_for_upload(self.image, output_path)
        self.saved_path = output_path
        self.window.destroy()

    def cancel(self):
        self.saved_path = None
        self.window.destroy()

    def run(self) -> str:
        self.window.grab_set()
        self.window.wait_window()
        try:
            if self.root_owner is not None:
                self.root_owner.destroy()
        except Exception:
            pass
        return self.saved_path

class SnippingTool:
    def __init__(self, on_capture_callback: Callable[[str], None], parent=None):
        self.on_capture_callback = on_capture_callback
        self.parent = parent
        self.root_owner: Optional[tk.Tk] = None
        self.root: Optional[tk.Toplevel] = None
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.bg_image_path = os.path.join(TEMP_DIR, "full_screen.png")
        self.tk_bg_image = None
        self.parent_was_minimized = False

    def capture_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # All monitors
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=self.bg_image_path)
            return monitor

    def start_snipping(self, save_dir: Optional[str] = None):
        self.save_dir = save_dir
        
        # Check if parent exists and is viewable
        parent_exists = self.parent is not None and self.parent.winfo_viewable()
        
        # Minimize main window FIRST before taking screenshot
        if parent_exists:
            try:
                self.parent.withdraw()
                self.parent_was_minimized = True
                # Force multiple updates to ensure window is completely hidden
                for _ in range(5):
                    self.parent.update()
                    time.sleep(0.05)  # Small delay between updates
            except Exception:
                pass
        
        # Wait longer to ensure window is fully hidden by window manager
        time.sleep(0.3)
        
        try:
            monitor = self.capture_screen()
        except Exception as exc:
            print(f"Capture failed: {exc}")
            # Restore window if capture fails
            if self.parent_was_minimized and self.parent is not None:
                try:
                    self.parent.deiconify()
                    self.parent.lift()
                    self.parent.focus_force()
                except Exception:
                    pass
                self.parent_was_minimized = False
            try:
                messagebox.showerror("Capture Error", f"Unable to capture screen: {exc}")
            except Exception:
                pass
            return

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        
        # Create overlay window as independent window (NOT transient to parent, since we'll withdraw parent)
        if self.root_owner is None:
            self.root_owner = tk.Tk()
            self.root_owner.withdraw()
        self.root = tk.Toplevel(self.root_owner)

        self.root.attributes('-alpha', 0.35)
        self.root.overrideredirect(True)
        left = monitor['left']
        top = monitor['top']
        width = monitor['width']
        height = monitor['height']
        self.root.geometry(f'{width}x{height}+{left}+{top}')
        self.root.attributes('-topmost', True)
        self.root.configure(cursor="cross")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        # Create canvas and load image BEFORE minimizing parent
        self.canvas = tk.Canvas(self.root, cursor="cross", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        try:
            image = Image.open(self.bg_image_path)
            self.tk_bg_image = ImageTk.PhotoImage(image)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_bg_image)
        except Exception:
            self.canvas.configure(bg="black")

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind("<Escape>", lambda e: self.cancel_snipping())
        
        # Force update to render everything
        self.root.update()
        
        # Main window already minimized at the start, no need to minimize again

        self.root.grab_set()
        self.root.wait_window()
        # Cleanup happens in on_button_release() or cancel_snipping()

    def cleanup_root(self):
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None
        if self.root_owner is not None:
            try:
                self.root_owner.destroy()
            except Exception:
                pass
            self.root_owner = None
        
        # Restore main window if it was minimized
        if self.parent_was_minimized and self.parent is not None:
            try:
                self.parent.deiconify()
                self.parent.lift()
                self.parent.focus_force()
            except Exception:
                pass
            self.parent_was_minimized = False

    def cancel_snipping(self):
        """Called when user presses Escape"""
        # Restore main window if minimized
        if self.parent_was_minimized and self.parent is not None:
            try:
                self.parent.deiconify()
                self.parent.lift()
                self.parent.focus_force()
            except Exception:
                pass
            self.parent_was_minimized = False
        
        self.cleanup_root()

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_move_press(self, event):
        cur_x, cur_y = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        self.canvas.coords(self.current_rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        end_x, end_y = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        
        # Calculate bounding box
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)

        if right - left > 5 and bottom - top > 5:
            # Close overlay window
            self.root.destroy()
            
            # Restore main window BEFORE annotation so it can be transient
            if self.parent_was_minimized and self.parent is not None:
                try:
                    self.parent.deiconify()
                    self.parent.lift()
                    self.parent.focus_force()
                    self.parent.update_idletasks()
                except Exception:
                    pass
                self.parent_was_minimized = False
            
            # Crop image and save to the selected screenshots folder
            img = Image.open(self.bg_image_path)
            cropped = img.crop((left, top, right, bottom))
            save_dir = self.save_dir or SCREENSHOT_DIR
            os.makedirs(save_dir, exist_ok=True)
            output_path = os.path.join(save_dir, f"cap_{uuid.uuid4().hex}.png")
            save_image_for_upload(cropped, output_path)
            
            # Defer annotation window creation to allow event loop to process
            def show_annotation():
                annotated_path = self.annotate_image(output_path)
                # Maximize parent window after annotation is closed
                if self.parent is not None:
                    try:
                        self.parent.state('zoomed')
                    except:
                        pass
                if annotated_path:
                    self.on_capture_callback(annotated_path)
                else:
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                # Clean up after annotation is done
                self.cleanup_root()
            
            # Schedule annotation after a brief delay
            if self.parent is not None and self.parent.winfo_viewable():
                self.parent.after(100, show_annotation)
            else:
                show_annotation()
        else:
            # Close overlay window
            self.root.destroy()
            
            # Restore main window even if selection is too small
            if self.parent_was_minimized and self.parent is not None:
                try:
                    self.parent.deiconify()
                    self.parent.lift()
                    self.parent.focus_force()
                except Exception:
                    pass
                self.parent_was_minimized = False
            
            # Clean up
            self.cleanup_root()

    def annotate_image(self, image_path: str) -> str:
        annotator = AnnotationWindow(image_path, parent=self.parent)
        return annotator.run()

