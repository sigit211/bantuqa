import customtkinter as ctk
import tkinter as tk
from PIL import Image
import os
import threading
import time
import json
import logging
import tkinter.messagebox as messagebox
import re
import html
import webbrowser
import queue
import ctypes
from src.api import api_client
from src.auth import AuthManager

logger = logging.getLogger(__name__)

# Setup appearance mode
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Utility function to strip HTML tags
def strip_html_tags(text):
    """Remove HTML tags and decode HTML entities from text"""
    if not text:
        return ""
    # Decode HTML entities first (e.g., &nbsp; -> space, &quot; -> ")
    text = html.unescape(text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Custom Scrollable ComboBox Widget
class ScrollableComboBox(ctk.CTkFrame):
    # Class-level variable to track if any dropdown is currently open
    _active_dropdown = None
    
    def __init__(self, parent, variable=None, values=None, command=None, fg_color="#2a2a38", button_color="#2a2a38", searchable=True, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.variable = variable
        self.values = values or []
        self.command = command
        self.fg_color = fg_color
        self.button_color = button_color
        self.searchable = searchable
        self.dropdown_window = None
        self.selected_value = ""
        self.root_bind_id = None  # Store root window binding ID for click-outside detection
        self.dropdown_monitor_id = None
        self.search_text = ""
        
        # Create button frame
        self.button = ctk.CTkButton(
            self,
            text="Select...",
            fg_color=fg_color,
            border_color="#3e4c5f",
            border_width=1,
            command=self.open_dropdown,
            text_color="white",
            anchor="w",
            height=35
        )
        self.button.pack(fill="both", expand=True)
        
    def set(self, value):
        """Set the displayed value"""
        self.selected_value = value
        self.button.configure(text=value)
        if self.variable:
            self.variable.set(value)
    
    def get(self):
        """Get the current value"""
        return self.selected_value
    
    def configure(self, **kwargs):
        """Configure the widget"""
        if 'values' in kwargs:
            self.values = kwargs.pop('values')  # Remove values before calling super()
        if kwargs:  # Only call super() if there are remaining kwargs
            super().configure(**kwargs)

    def _filter_values(self, query):
        """Filter dropdown values case-insensitively by text query."""
        query = (query or "").strip().lower()
        if not query:
            return list(self.values)
        return [item for item in self.values if query in str(item).lower()]

    def _refresh_listbox(self, listbox):
        """Refresh listbox contents using the current search query."""
        filtered = self._filter_values(self.search_text)
        listbox.delete(0, tk.END)
        for item in filtered:
            listbox.insert(tk.END, item)

        if filtered:
            listbox.select_set(0)
            listbox.see(0)
        else:
            listbox.selection_clear(0, tk.END)

    def _clear_search(self, search_entry, listbox):
        """Clear the search text and refresh dropdown contents."""
        self.search_text = ""
        search_entry.delete(0, tk.END)
        self._refresh_listbox(listbox)

    def _scroll_listbox(self, listbox, event):
        """Handle wheel/touchpad scrolling for inner listboxes."""
        try:
            if hasattr(event, "delta") and event.delta != 0:
                steps = int(-1 * (event.delta / 120))
                listbox.yview_scroll(steps, "units")
            elif getattr(event, "num", None) == 5:
                listbox.yview_scroll(1, "units")
            elif getattr(event, "num", None) == 4:
                listbox.yview_scroll(-1, "units")
            return "break"
        except Exception:
            return None

    def open_dropdown(self):
        """Open the dropdown menu with scrollable list - RELIABLE CLICK & CLOSE"""
        # Prevent opening a new dropdown if another one is already open
        if ScrollableComboBox._active_dropdown is not None:
            return
        
        if self.dropdown_window is not None:
            self.destroy_dropdown_window()
        
        if not self.values:
            return
        
        # Mark this dropdown as active
        ScrollableComboBox._active_dropdown = self
        
        # Create toplevel window
        root = self.winfo_toplevel()
        self.dropdown_window = tk.Toplevel(root)
        self.dropdown_window.wm_overrideredirect(True)
        self.dropdown_window.attributes('-topmost', True)
        
        # Position dropdown below the button
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = max(self.winfo_width(), 200)
        
        # Calculate height based on available screen space
        item_height = 32
        search_height = 36 if self.searchable else 0
        screen_height = root.winfo_screenheight()
        screen_width = root.winfo_screenwidth()
        max_dropdown_height = min(600, max(180, screen_height - 40))
        values_for_display = self._filter_values(self.search_text) if self.searchable else list(self.values)
        visible_items = min(len(values_for_display), max(1, max_dropdown_height // item_height))
        dropdown_height = max((visible_items * item_height) + search_height + 8, 180)
        dropdown_height = min(dropdown_height, max_dropdown_height)

        # Keep popup inside the visible screen area so it never overlaps taskbar
        if y + dropdown_height > screen_height - 4:
            y = max(4, screen_height - dropdown_height - 4)
        if x + width > screen_width:
            x = max(0, screen_width - width)
        
        self.dropdown_window.geometry(f"{width}x{dropdown_height}+{x}+{y}")
        
        # Create main frame
        main_frame = tk.Frame(self.dropdown_window, bg="#3a3a48", highlightthickness=2, highlightbackground="#1f6aa5")
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Search entry (kept visible so the last keyword stays available)
        if self.searchable:
            search_frame = tk.Frame(main_frame, bg="#3a3a48")
            search_frame.pack(fill="x", padx=2, pady=(2, 0))
            search_entry = tk.Entry(
                search_frame,
                bg="#2f3144",
                fg="#e0e0e0",
                insertbackground="#e0e0e0",
                relief="flat",
                font=("Segoe UI", 11),
                justify="left"
            )
            clear_button = tk.Button(
                search_frame,
                text="✕",
                bg="#c62828",
                fg="#ffffff",
                activebackground="#e53935",
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                padx=6,
                command=lambda: self._clear_search(search_entry, listbox)
            )
            clear_button.pack(side="left", padx=(2, 4))

            search_entry.pack(side="left", fill="x", expand=True)
            search_entry.insert(0, self.search_text)

        # Create listbox dengan scrollbar
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", bg="#3a3a48", troughcolor="#3a3a48", activebackground="#1f6aa5")
        scrollbar.pack(side="right", fill="y", padx=(0, 2))
        
        listbox = tk.Listbox(
            main_frame,
            bg="#3a3a48",
            fg="#e0e0e0",
            selectmode="single",
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 11),
            highlightthickness=0,
            relief="flat",
            borderwidth=0,
            activestyle="none",
            selectbackground="#1f6aa5",
            selectforeground="white",
            height=visible_items
        )
        listbox.pack(side="left", fill="both", expand=True, padx=(2, 0))
        scrollbar.config(command=listbox.yview)

        # Add items to listbox
        if self.searchable:
            self._refresh_listbox(listbox)
        else:
            listbox.delete(0, tk.END)
            for item in self.values:
                listbox.insert(tk.END, item)
            if self.values:
                listbox.select_set(0)
                listbox.see(0)

        # Keep query text in memory and allow editing it later
        def on_search(event=None):
            self.search_text = search_entry.get()
            self._refresh_listbox(listbox)

        def get_selected_value():
            selection = listbox.curselection()
            if not selection:
                return None
            if self.searchable:
                filtered = self._filter_values(self.search_text)
                if selection[0] < len(filtered):
                    return filtered[selection[0]]
            else:
                if selection[0] < len(self.values):
                    return self.values[selection[0]]
            return None
        
        # RELIABLE click handler - menggunakan event.y coordinate
        def on_item_click(event):
            try:
                index = listbox.nearest(event.y)
                if self.searchable:
                    filtered = self._filter_values(self.search_text)
                    if 0 <= index < len(filtered):
                        value = filtered[index]
                        self.search_text = value
                        self.set(value)
                        self.destroy_dropdown_window()
                        if self.command:
                            self.command(value)
                else:
                    if 0 <= index < len(self.values):
                        value = self.values[index]
                        self.set(value)
                        self.destroy_dropdown_window()
                        if self.command:
                            self.command(value)
            except Exception as e:
                print(f"[DEBUG] Click error: {e}")
        
        # RELIABLE keyboard handler
        def on_key(event):
            try:
                if event.keysym == 'Return':
                    value = get_selected_value()
                    if value is not None:
                        self.search_text = value
                        self.set(value)
                        self.destroy_dropdown_window()
                        if self.command:
                            self.command(value)
                elif event.keysym == 'Escape':
                    self.destroy_dropdown_window()
            except Exception as e:
                print(f"[DEBUG] Key error: {e}")
        
        # EXPLICIT event bindings
        if self.searchable:
            search_entry.bind("<KeyRelease>", on_search)
            search_entry.bind("<Return>", on_key)
            search_entry.bind("<Escape>", lambda event: self.destroy_dropdown_window())
        listbox.bind("<Button-1>", on_item_click)
        listbox.bind("<Key>", on_key)
        listbox.bind("<MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        listbox.bind("<Shift-MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        listbox.bind("<Button-4>", lambda event: self._scroll_listbox(listbox, event))
        listbox.bind("<Button-5>", lambda event: self._scroll_listbox(listbox, event))
        scrollbar.bind("<MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        scrollbar.bind("<Shift-MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        if self.searchable:
            search_entry.bind("<MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
            search_entry.bind("<Shift-MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        main_frame.bind("<MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        main_frame.bind("<Shift-MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        self.dropdown_window.bind("<MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        self.dropdown_window.bind("<Shift-MouseWheel>", lambda event: self._scroll_listbox(listbox, event))
        
        # Bind window close button
        self.dropdown_window.protocol("WM_DELETE_WINDOW", self.destroy_dropdown_window)
        
        # Add click-outside detection to close dropdown
        def on_root_click(event):
            """Close dropdown when clicking outside of it"""
            try:
                # Get dropdown window bounds
                dropdown_x = self.dropdown_window.winfo_x()
                dropdown_y = self.dropdown_window.winfo_y()
                dropdown_width = self.dropdown_window.winfo_width()
                dropdown_height = self.dropdown_window.winfo_height()
                
                # Check if click is outside dropdown bounds
                click_x = event.x_root
                click_y = event.y_root
                
                # Also check if click is on the dropdown button (to allow toggling)
                button_x = self.button.winfo_rootx()
                button_y = self.button.winfo_rooty()
                button_width = self.button.winfo_width()
                button_height = self.button.winfo_height()
                
                # If click is outside both dropdown and button, close it
                if not (dropdown_x <= click_x <= dropdown_x + dropdown_width and
                        dropdown_y <= click_y <= dropdown_y + dropdown_height) and \
                   not (button_x <= click_x <= button_x + button_width and
                        button_y <= click_y <= button_y + button_height):
                    self.destroy_dropdown_window()
            except:
                # If any error occurs, just close the dropdown
                self.destroy_dropdown_window()
        
        # Get root window and bind click event
        self.root_bind_id = root.bind("<Button-1>", on_root_click, add=True)
        
        # Focus the search box when available so typing works immediately after opening
        self.dropdown_window.focus_set()
        if self.searchable:
            search_entry.focus_set()
            search_entry.icursor(tk.END)
            search_entry.select_range(0, tk.END)
        else:
            listbox.focus_set()
        self._schedule_dropdown_monitor()
    
    def _schedule_dropdown_monitor(self):
        """Keep checking if another app became foreground so dropdown can be closed."""
        root = self.winfo_toplevel()
        if root is None or self.dropdown_window is None or not self.dropdown_window.winfo_exists():
            return
        if self.dropdown_monitor_id is not None:
            try:
                root.after_cancel(self.dropdown_monitor_id)
            except:
                pass
            self.dropdown_monitor_id = None
        self.dropdown_monitor_id = root.after(200, self._check_foreground_window)
    
    def _check_foreground_window(self):
        """Close dropdown only when the active foreground window belongs to a different process."""
        self.dropdown_monitor_id = None
        if self.dropdown_window is None or not self.dropdown_window.winfo_exists():
            return
        
        try:
            root = self.winfo_toplevel()
            if root is None or not root.winfo_exists():
                return
            
            active_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if active_hwnd == 0:
                return
            
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(active_hwnd, ctypes.byref(pid))
            current_pid = os.getpid()
            
            # Close only if another application/process is now foreground.
            if pid.value != current_pid:
                self.destroy_dropdown_window()
                return
        except Exception:
            pass
        finally:
            if self.dropdown_window is not None and self.dropdown_window.winfo_exists():
                self._schedule_dropdown_monitor()
    
    def destroy_dropdown_window(self):
        """GUARANTEED way to destroy dropdown window"""
        # Cancel foreground monitor if scheduled
        if self.dropdown_monitor_id is not None:
            try:
                root = self.winfo_toplevel()
                root.after_cancel(self.dropdown_monitor_id)
            except:
                pass
            finally:
                self.dropdown_monitor_id = None
        
        # Unbind the root click handler if it exists
        if self.root_bind_id is not None:
            try:
                root = self.winfo_toplevel()
                root.unbind("<Button-1>", self.root_bind_id)
            except:
                pass
            finally:
                self.root_bind_id = None
        
        if self.dropdown_window is not None:
            try:
                self.dropdown_window.destroy()
            except:
                pass
            finally:
                self.dropdown_window = None
        
        # Clear the active dropdown flag if this is the active one
        if ScrollableComboBox._active_dropdown is self:
            ScrollableComboBox._active_dropdown = None
    
    def close_dropdown(self):
        """Deprecated - use destroy_dropdown_window instead"""
        self.destroy_dropdown_window() 

CACHE_FILE = os.path.join(os.environ.get("TEMP", "."), "BantuQa", "cache.json")

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(data):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

class BantuQaApp(ctk.CTk):
    def __init__(self, capture_queue, on_capture_request, on_window_close=None):
        super().__init__()
        self.capture_queue = capture_queue
        self.on_capture_request = on_capture_request
        self.on_window_close = on_window_close
        self.cache = load_cache()
        self.attachment_ids = {}
        self.attachment_errors = {}
        self.file_comments = {}  # Store comments for each file
        self.test_start_time = None
        self.elapsed_seconds = None
        self.is_paused = False
        self.paused_elapsed = 0
        self.step_status_vars = {}
        self.step_status_dropdowns = {}
        self.step_actuals = {}
        self.step_comment_buttons = {}
        self.step_attachments = {}
        self.step_attachment_lookup = {}
        self._comment_keyboard_guard = False
        self.pending_step_capture = None
        self.current_case_data = None
        self.current_case_name = None
        self.status_id_map = {}
        self.status_options = []
        self._ui_queue = queue.Queue()
        self._ui_queue_scheduled = False
        
        self.title("BantuQa")
        window_width = 950
        window_height = 700
        self.geometry(f"{window_width}x{window_height}")
        self.configure(fg_color="#1a1a24")
        self.protocol("WM_DELETE_WINDOW", self.on_window_delete)
        
        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Login Frame
        self.login_frame = ctk.CTkFrame(self)
        self.setup_login_ui()
        
        # Dashboard Frame
        self.dashboard_frame = ctk.CTkFrame(self)
        self.setup_dashboard_ui()
        
        # Check login
        base_url, email, api_key = AuthManager.load_credentials()
        if base_url and email and api_key:
            api_client.set_credentials(base_url, email, api_key)
            if api_client.validate_login():
                self.show_dashboard()
            else:
                self.show_login()
        else:
            self.show_login()

    def _center_window(self):
        """Position window at top-left corner"""
        window_width = 950
        window_height = 700
        # Set position to top-left corner (0, 0)
        self.geometry(f"{window_width}x{window_height}+0+0")
        self.update()
    
    def hide_window(self):
        self.withdraw()
    
    def on_window_delete(self):
        """Handle window close event"""
        if self.on_window_close:
            self.on_window_close()
        else:
            self.hide_window()

    def show_window(self):
        self.deiconify()
        self.lift()
        # If dashboard is shown (user is logged in), maximize the window
        if self.dashboard_frame.winfo_viewable():
            try:
                self.state('zoomed')
            except:
                pass

    def show_login(self):
        self.dashboard_frame.grid_forget()
        self.login_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(70, 0))
        # Position window at top-left corner for login screen
        self.after(300, self._center_window)
        
    def _enqueue_ui_task(self, callback):
        """Queue a UI update from any thread; it will be executed by the main thread."""
        self._ui_queue.put(callback)
        if not self._ui_queue_scheduled:
            self._ui_queue_scheduled = True
            try:
                self.after(0, self._process_ui_queue)
            except Exception:
                pass

    def _process_ui_queue(self):
        """Run pending UI callbacks on the main thread."""
        self._ui_queue_scheduled = False
        while True:
            try:
                callback = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                pass
            finally:
                self._ui_queue.task_done()

    def show_dashboard(self):
        self.login_frame.grid_forget()
        self.dashboard_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        # Maximize window on Windows - schedule with delay to ensure it takes effect
        def maximize_window():
            try:
                self.state('zoomed')
            except:
                pass
        self.after(100, maximize_window)
        self.after(0, self._process_ui_queue)
        self.load_projects()
        self.load_statuses()
        self.refresh_submit_state()
        self.update_attachment_ids_display()
        self.update_dashboard_thumbnails()

    def _is_ready_to_start(self):
        """Return True only when testing is actively running."""
        return (
            self.test_start_time is not None
            and not self.is_paused
        )

    def _warn_start_testing_first(self):
        """Prompt the user to start or resume the timer before using the capture/comment controls."""
        if self._is_ready_to_start():
            return False

        messagebox.showwarning(
            "Start testing first",
            "Please click the ▶ button in Working Time before adding screenshots or comments here."
        )
        return True

    def _get_elapsed_seconds(self):
        """Return current elapsed working time in seconds."""
        if self.elapsed_seconds is not None:
            return int(self.elapsed_seconds)
        if self.test_start_time is not None:
            return int(time.perf_counter() - self.test_start_time + self.paused_elapsed)
        if self.is_paused:
            return int(self.paused_elapsed)
        return 0

    def _set_comment_input_state(self, enabled):
        """Enable or disable only the main comment field."""
        if hasattr(self, "comment_box") and self.comment_box.winfo_exists():
            self.comment_box.configure(state="normal" if enabled else "disabled")

    def _sync_comment_input_state(self):
        """Re-enable the comment field once working time has actually started."""
        self._set_comment_input_state(self._get_elapsed_seconds() > 0)
        self._sync_bulk_status_controls()

    def _sync_bulk_status_controls(self):
        """Enable or disable bulk step status controls depending on working time."""
        enabled = self._get_elapsed_seconds() > 0 and bool(self.step_status_vars)
        if hasattr(self, 'bulk_step_status_apply_btn') and self.bulk_step_status_apply_btn:
            self.bulk_step_status_apply_btn.configure(state="normal" if enabled else "disabled")
        if hasattr(self, 'bulk_step_status_dropdown') and self.bulk_step_status_dropdown:
            try:
                self.bulk_step_status_dropdown.button.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass

    def _infer_main_status_from_step_statuses(self):
        """Infer a main test result status from the current step statuses when possible."""
        statuses = [
            self.step_status_vars[idx].get()
            for idx in sorted(self.step_status_vars)
            if hasattr(self.step_status_vars[idx], 'get') and self.step_status_vars[idx].get().strip()
        ]
        if not statuses:
            return None
        first = statuses[0]
        if first != "Untested" and all(status == first for status in statuses):
            return first
        return None

    def apply_bulk_step_status(self):
        """Apply the selected bulk status to every visible step status dropdown."""
        if self._get_elapsed_seconds() <= 0:
            messagebox.showwarning(
                "Start testing first",
                "Please click the ▶ button in Working Time before updating all step statuses."
            )
            return

        selected_status = self.bulk_step_status_var.get() if hasattr(self, 'bulk_step_status_var') else None
        if not selected_status:
            return

        for idx, status_var in self.step_status_vars.items():
            if hasattr(status_var, 'set'):
                try:
                    status_var.set(selected_status)
                except Exception:
                    pass
            dropdown = self.step_status_dropdowns.get(idx)
            if dropdown:
                try:
                    dropdown.set(selected_status)
                except Exception:
                    pass

        inferred_status = self._infer_main_status_from_step_statuses()
        if inferred_status and self.status_var.get() == "Untested":
            try:
                self.status_var.set(inferred_status)
                self.status_dropdown.set(inferred_status)
            except Exception:
                pass

        self.append_log(f"[{self.get_timestamp()}] All step statuses updated to {selected_status}\n")

    def _warn_on_click(self, event=None):
        """Warn only when the user clicks into the specific comment field."""
        if self._warn_start_testing_first():
            self._set_comment_input_state(False)

    def _open_status_dropdown(self, dropdown):
        """Warn if the user tries to change result status before starting the test."""
        if self._warn_start_testing_first():
            return
        dropdown.open_dropdown()

    def request_capture(self, step_number=None):
        """Request a screenshot only after the user has started the test."""
        if self._warn_start_testing_first():
            return
        self.on_capture_request(step_number)

    def setup_login_ui(self):
        # Configure login frame to center the card
        self.login_frame.grid_rowconfigure(0, weight=1)
        self.login_frame.grid_columnconfigure(0, weight=1)
        
        # Create centered card frame
        self.card_frame = ctk.CTkFrame(
            self.login_frame,
            width=450,
            height=500,
            fg_color="#283140",
            corner_radius=15
        )
        self.card_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Form Title
        self.login_label = ctk.CTkLabel(
            self.card_frame,
            text="Sign in to Your Account",
            font=("Segoe UI", 24, "bold"),
            text_color="white"
        )
        self.login_label.place(x=40, y=40)
        
        # --- Input URL ---
        self.url_label = ctk.CTkLabel(
            self.card_frame,
            text="TestRail Instance URL",
            font=("Segoe UI", 14),
            text_color="#cbd5e1"
        )
        self.url_label.place(x=40, y=100)
        
        self.url_entry = ctk.CTkEntry(
            self.card_frame,
            width=370,
            height=45,
            placeholder_text="🌐   https://yourcompany.testrail.io",
            fg_color="#283140",
            border_color="#3e4c5f",
            text_color="white",
            placeholder_text_color="#64748b"
        )
        self.url_entry.place(x=40, y=130)
        self.url_entry.bind("<Return>", lambda event: self.do_login())
        
        # --- Input Username ---
        self.user_label = ctk.CTkLabel(
            self.card_frame,
            text="Username",
            font=("Segoe UI", 14),
            text_color="#cbd5e1"
        )
        self.user_label.place(x=40, y=190)
        
        self.email_entry = ctk.CTkEntry(
            self.card_frame,
            width=370,
            height=45,
            placeholder_text="👤   email@example.com",
            fg_color="#283140",
            border_color="#3e4c5f",
            text_color="white",
            placeholder_text_color="#64748b"
        )
        self.email_entry.place(x=40, y=220)
        self.email_entry.bind("<Return>", lambda event: self.do_login())
        
        # --- Input Password ---
        self.pass_label = ctk.CTkLabel(
            self.card_frame,
            text="Password",
            font=("Segoe UI", 14),
            text_color="#cbd5e1"
        )
        self.pass_label.place(x=40, y=280)

        self.password_visible = False
        
        self.api_key_entry = ctk.CTkEntry(
            self.card_frame,
            width=320,
            height=45,
            placeholder_text="🔒   ••••••••",
            show="•",
            fg_color="#283140",
            border_color="#3e4c5f",
            text_color="white",
            placeholder_text_color="#64748b"
        )
        self.api_key_entry.place(x=40, y=310)
        self.api_key_entry.bind("<Return>", lambda event: self.do_login())

        self.password_toggle_btn = ctk.CTkButton(
            self.card_frame,
            text="👁",
            width=35,
            height=45,
            fg_color="transparent",
            border_color="#3e4c5f",
            border_width=1,
            text_color="#cbd5e1",
            hover_color="#334155",
            command=self.toggle_password_visibility
        )
        self.password_toggle_btn.place(x=365, y=310)
        
        # --- Login Button ---
        self.login_btn = ctk.CTkButton(
            self.card_frame,
            text="Sign In",
            width=370,
            height=45,
            font=("Segoe UI", 16, "bold"),
            fg_color="#246bb3",
            hover_color="#1a528a",
            corner_radius=8,
            command=self.do_login
        )
        self.login_btn.place(x=40, y=400)
        
        # Error label
        self.login_error_lbl = ctk.CTkLabel(
            self.card_frame,
            text="",
            text_color="#ff6b6b"
        )
        self.login_error_lbl.place(x=40, y=460)

    def toggle_password_visibility(self):
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.api_key_entry.configure(show="")
            self.password_toggle_btn.configure(text="🙈")
        else:
            self.api_key_entry.configure(show="•")
            self.password_toggle_btn.configure(text="👁")

    def do_login(self):
        url = self.url_entry.get().strip()
        email = self.email_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        
        self.login_btn.configure(state="disabled")
        api_client.set_credentials(url, email, api_key)
        
        def check():
            if api_client.validate_login():
                AuthManager.save_credentials(url, email, api_key)
                self.after(0, self.show_dashboard)
            else:
                self.after(0, lambda: self.login_error_lbl.configure(text="Invalid credentials or URL"))
            self.after(0, lambda: self.login_btn.configure(state="normal"))
            
        threading.Thread(target=check).start()

    def do_logout(self):
        AuthManager.clear_credentials()
        self.url_entry.delete(0, 'end')
        self.email_entry.delete(0, 'end')
        self.api_key_entry.delete(0, 'end')
        self.login_error_lbl.configure(text="")
        self.show_login()

    def _scroll_step_area(self, event, scroll_target):
        """Scroll only the Test Case Steps section when possible.

        If the section is already at its top/bottom limit, the event is left
        untouched so the parent scrollable area can handle it.
        """
        if scroll_target is None or not hasattr(scroll_target, "yview"):
            return None

        try:
            top, bottom = scroll_target.yview()
            if top > 0 or bottom < 1:
                if hasattr(event, "delta"):
                    steps = int(-1 * (event.delta / 120))
                else:
                    steps = -1 if getattr(event, "num", None) == 4 else 1

                if steps != 0:
                    scroll_target.yview_scroll(steps, "units")
                    return "break"
        except Exception:
            pass

        return None

    def _bind_step_scroll(self, widget, scroll_target):
        """Bind wheel handlers and stop bubbling when the section handles the scroll."""
        def make_handler(event):
            if self._scroll_step_area(event, scroll_target) == "break":
                return "break"
            return None

        for sequence in ("<MouseWheel>", "<Shift-MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(sequence, make_handler)

    def _configure_dual_vertical_scrollbars(self, widget, left_scrollbar, right_scrollbar):
        """Sync two vertical scrollbars to one widget for the Test Case Steps section."""
        if left_scrollbar is None or right_scrollbar is None:
            return

        def sync_scrollbars(first, last):
            left_scrollbar.set(first, last)
            right_scrollbar.set(first, last)

        widget.configure(yscrollcommand=sync_scrollbars)
        left_scrollbar.configure(command=widget.yview)
        right_scrollbar.configure(command=widget.yview)

    def setup_dashboard_ui(self):
        # Configure grid untuk dashboard frame
        self.dashboard_frame.grid_rowconfigure(0, weight=0)  # Header
        self.dashboard_frame.grid_rowconfigure(1, weight=1)  # Main content
        self.dashboard_frame.grid_rowconfigure(2, weight=0)  # Bottom buttons
        self.dashboard_frame.grid_columnconfigure(0, weight=1)

        # ================= HEADER =================
        self.create_dashboard_header()

        # ================= MAIN CONTENT =================
        content_frame = ctk.CTkScrollableFrame(
            self.dashboard_frame,
            fg_color="transparent",
            scrollbar_button_color="#3a3a48",
            scrollbar_button_hover_color="#4a4a5a"
        )
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)

        # Only bind wheel events to the specific scrollable canvas, not globally to the whole window.
        if hasattr(content_frame, "_parent_canvas"):
            content_frame._parent_canvas.bind(
                "<MouseWheel>",
                lambda e: content_frame._parent_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            )
            content_frame._parent_canvas.bind(
                "<Shift-MouseWheel>",
                lambda e: content_frame._parent_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units")
            )
            content_frame._parent_canvas.bind(
                "<Button-4>",
                lambda e: content_frame._parent_canvas.yview_scroll(-1, "units")
            )
            content_frame._parent_canvas.bind(
                "<Button-5>",
                lambda e: content_frame._parent_canvas.yview_scroll(1, "units")
            )

        # ================= LEFT PANEL (Configuration) =================
        left_panel = ctk.CTkFrame(content_frame, fg_color="#20202e", corner_radius=15)
        left_panel.pack(fill="x", expand=False, pady=(0, 10))
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_panel, text="Configuration", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 15))

        # Helper function to create dropdown
        def create_dropdown(parent, label_text, icon, var, values_list, command_func):
            ctk.CTkLabel(parent, text=label_text, text_color="#d1d1d1").pack(anchor="w", padx=20, pady=(5, 0))
            dropdown = ScrollableComboBox(parent, variable=var, values=values_list or ["Select..."], 
                                         fg_color="#2a2a38", button_color="#2a2a38", command=command_func)
            dropdown.set(f"{icon} Select...")
            dropdown.pack(fill="x", padx=20, pady=(5, 10))
            return dropdown

        self.proj_var = ctk.StringVar(value="")
        self.proj_combo = create_dropdown(left_panel, "Select Project", "📂", self.proj_var, [], self.on_project_select)
        
        self.plan_var = ctk.StringVar(value="")
        self.plan_combo = create_dropdown(left_panel, "Select Test Plan (Optional)", "📄", self.plan_var, [], self.on_plan_select)
        
        self.run_var = ctk.StringVar(value="")
        self.run_combo = create_dropdown(left_panel, "Select Test Run", "📊", self.run_var, [], self.on_run_select)
        
        self.assign_to_var = ctk.StringVar(value="")
        self.assign_to_combo = ScrollableComboBox(
            left_panel,
            variable=self.assign_to_var,
            values=[],
            command=self.on_assign_to_select,
            fg_color="#2a2a38",
            button_color="#2a2a38",
            searchable=False
        )
        ctk.CTkLabel(left_panel, text="Assign To (Optional)", text_color="#d1d1d1").pack(anchor="w", padx=20, pady=(5, 0))
        self.assign_to_combo.set("👤 Select...")
        self.assign_to_combo.pack(fill="x", padx=20, pady=(5, 10))
        
        self.case_var = ctk.StringVar(value="")
        self.case_combo = create_dropdown(left_panel, "Select Test Case", "🔍", self.case_var, [], self.on_case_select)

        # Test Result Status (moved from right panel)
        ctk.CTkLabel(left_panel, text="Test Result Status", text_color="#d1d1d1").pack(anchor="w", padx=20, pady=(15, 5))
        self.status_var = ctk.StringVar(value="")
        self.status_dropdown = ScrollableComboBox(
            left_panel,
            variable=self.status_var,
            values=[],
            fg_color="#2a2a38",
            button_color="#2a2a38",
            searchable=False
        )
        self.status_dropdown.button.configure(
            command=lambda dropdown=self.status_dropdown: self._open_status_dropdown(dropdown)
        )
        self.status_dropdown.pack(fill="x", padx=20, pady=(5, 15))

        # ================= MIDDLE PANEL (Test Case Steps) =================
        middle_panel = ctk.CTkFrame(content_frame, fg_color="#20202e", corner_radius=15)
        middle_panel.pack(fill="x", expand=False, pady=(0, 10))
        middle_panel.grid_columnconfigure(0, weight=0)
        middle_panel.grid_columnconfigure(1, weight=1)
        middle_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(middle_panel, text="Test Case Steps", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 15))

        self.bulk_actions_frame = ctk.CTkFrame(middle_panel, fg_color="transparent")
        self.bulk_actions_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        self.bulk_actions_frame.grid_columnconfigure(0, weight=0)
        self.bulk_actions_frame.grid_columnconfigure(1, weight=0)
        self.bulk_actions_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(self.bulk_actions_frame, text="Update all step statuses:").grid(row=0, column=0, sticky="w")
        self.bulk_step_status_var = ctk.StringVar(value="Untested")
        self.bulk_step_status_dropdown = ScrollableComboBox(
            self.bulk_actions_frame,
            variable=self.bulk_step_status_var,
            values=[],
            fg_color="#2a2a38",
            button_color="#2a2a38",
            searchable=False
        )
        self.bulk_step_status_dropdown.button.configure(
            command=lambda dropdown=self.bulk_step_status_dropdown: self._open_status_dropdown(dropdown)
        )
        self.bulk_step_status_dropdown.grid(row=0, column=1, sticky="w", padx=(10, 8))

        self.bulk_step_status_apply_btn = ctk.CTkButton(
            self.bulk_actions_frame,
            text="Apply to all",
            width=120,
            height=32,
            fg_color="#1f6aa5",
            hover_color="#185a8a",
            command=self.apply_bulk_step_status,
            state="disabled",
            font=("Segoe UI", 11)
        )
        self.bulk_step_status_apply_btn.grid(row=0, column=2, sticky="w")
        self.bulk_actions_frame.grid_remove()

        # Existing text-based view: keep the textbox's built-in right scrollbar active,
        # and add only a left scrollbar for the section.
        self.steps_textbox = ctk.CTkTextbox(
            middle_panel,
            fg_color="#2a2a38",
            height=560
        )
        self.steps_left_scrollbar = ctk.CTkScrollbar(
            middle_panel,
            orientation="vertical",
            button_color="#3a3a48",
            button_hover_color="#4a4a5a"
        )
        self.steps_left_scrollbar.grid(row=2, column=0, sticky="ns", padx=(20, 0), pady=(0, 20))
        self.steps_textbox.grid(row=2, column=1, sticky="nsew", padx=(0, 20), pady=(0, 20))
        self._configure_dual_vertical_scrollbars(
            self.steps_textbox._textbox,
            self.steps_left_scrollbar,
            self.steps_textbox._y_scrollbar
        )
        self._bind_step_scroll(self.steps_textbox, self.steps_textbox)

        # Alternate structured view for step-based cases
        self.steps_details_frame = ctk.CTkScrollableFrame(
            middle_panel,
            fg_color="transparent",
            height=560
        )
        self.steps_details_left_scrollbar = ctk.CTkScrollbar(
            middle_panel,
            orientation="vertical",
            button_color="#3a3a48",
            button_hover_color="#4a4a5a"
        )
        self.steps_details_left_scrollbar.grid(row=2, column=0, sticky="ns", padx=(20, 0), pady=(0, 20))
        self.steps_details_frame.grid(row=2, column=1, sticky="nsew", padx=(0, 20), pady=(0, 20))
        self.steps_details_frame.grid_remove()
        self.steps_details_content = ctk.CTkFrame(self.steps_details_frame, fg_color="transparent")
        self.steps_details_content.pack(fill="both", expand=True)
        self.steps_details_content.grid_columnconfigure(0, weight=1)
        self.steps_details_content.grid_rowconfigure(0, weight=1)

        # Bind wheel handling so this section scrolls first; parent area only takes over
        # when the step section is already at its top/bottom boundary.
        if hasattr(self.steps_details_frame, "_parent_canvas"):
            detail_canvas = self.steps_details_frame._parent_canvas
            self._configure_dual_vertical_scrollbars(
                detail_canvas,
                self.steps_details_left_scrollbar,
                self.steps_details_frame._scrollbar
            )
            self._bind_step_scroll(detail_canvas, detail_canvas)
            self._bind_step_scroll(self.steps_details_frame, detail_canvas)
            self._bind_step_scroll(self.steps_details_content, detail_canvas)

        # Configure tags for styling text
        # Note: customtkinter TextBox has limited tag support, use foreground color for emphasis
        self.steps_textbox.tag_config("bold", foreground="#e0e0e0")
        self.steps_textbox.tag_config("section_header", foreground="#94a0b8")

        # ================= RIGHT PANEL (Attachment & Actions) =================
        self.sidebar_is_open = False

        self.sidebar_width_var = tk.StringVar(value="520")
        self.sidebar_min_width = 320
        self.sidebar_max_width = 900

        self.right_panel = ctk.CTkFrame(
            self.dashboard_frame,
            width=int(self.sidebar_width_var.get()),
            fg_color="#20202e",
            corner_radius=0,
            border_width=0
        )
        # Keep the sidebar within the main content area so the bottom action buttons
        # do not overlap the lower part of Attachment & Actions.
        self.right_panel.place(relx=1.0, rely=0.0, anchor="ne", x=0, y=0, relheight=0.92)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.place_forget()

        sidebar_top = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        sidebar_top.pack(fill="x", padx=16, pady=(12, 10))

        self.sidebar_back_btn = ctk.CTkButton(
            sidebar_top,
            text="← Back",
            width=90,
            height=32,
            command=self.toggle_sidebar,
            fg_color="#3a3a52",
            hover_color="#4a4a6a",
            font=("Segoe UI", 12)
        )
        self.sidebar_back_btn.pack(side="left")

        sidebar_width_frame = ctk.CTkFrame(sidebar_top, fg_color="transparent")
        sidebar_width_frame.pack(side="right")

        ctk.CTkLabel(sidebar_width_frame, text="Width:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(10, 4))
        self.sidebar_width_entry = ctk.CTkEntry(
            sidebar_width_frame,
            width=70,
            textvariable=self.sidebar_width_var,
            justify="center"
        )
        self.sidebar_width_entry.pack(side="left")

        self.sidebar_width_apply_btn = ctk.CTkButton(
            sidebar_width_frame,
            text="Apply",
            width=60,
            height=28,
            command=self.apply_sidebar_width,
            fg_color="#1f6aa5",
            hover_color="#185a8a",
            font=("Segoe UI", 11)
        )
        self.sidebar_width_apply_btn.pack(side="left", padx=(6, 0))

        ctk.CTkLabel(
            self.right_panel,
            text="Attachment & Actions",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 15))

        # --- Comment field ---
        ctk.CTkLabel(self.right_panel, text="Comment", text_color="#d1d1d1").pack(anchor="w", padx=20, pady=(0, 5))
        self.comment_box = ctk.CTkTextbox(self.right_panel, fg_color="#2a2a38", height=100)
        self.comment_box.pack(fill="both", expand=False, padx=20, pady=(0, 15))
        self.comment_box.bind("<Button-1>", self._warn_on_click)

        # --- Sub-panel Attachments ---
        lampiran_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        lampiran_header.pack(fill="x", padx=20)
        ctk.CTkLabel(lampiran_header, text="List Attachments", text_color="#d1d1d1").pack(side="left")

        attachment_actions_frame = ctk.CTkFrame(lampiran_header, fg_color="transparent")
        attachment_actions_frame.pack(side="right")

        self.btn_add = ctk.CTkButton(
            attachment_actions_frame,
            text="➕",
            width=40,
            height=32,
            fg_color="#2b2b3d",
            command=self.request_capture,
            font=("Arial", 16)
        )
        self.btn_add.pack(side="left", padx=(0, 4))

        self.btn_upload = ctk.CTkButton(
            attachment_actions_frame,
            text="⬆",
            width=40,
            height=32,
            fg_color="#1f6aa5",
            command=self.upload_attachments,
            font=("Arial", 16)
        )
        self.btn_upload.pack(side="left")

        # Create scrollable frame for attachments with buttons
        self.lampiran_frame = ctk.CTkScrollableFrame(self.right_panel, fg_color="#2a2a38", height=120)
        self.lampiran_frame.pack(fill="both", expand=False, padx=20, pady=(5, 15))
        self.lampiran_frame._parent_canvas.configure(highlightthickness=0)
        
        # Store the scrollable frame for dynamic updates
        self.lampiran_box = None  # Deprecated - no longer using textbox

        # --- Sub-panel Log Process ---
        log_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        log_header.pack(fill="x", padx=20, pady=(10, 5))
        ctk.CTkLabel(log_header, text="Process Log:", font=ctk.CTkFont(size=14)).pack(side="left")

        self.log_box = ctk.CTkTextbox(self.right_panel, fg_color="#2a2a38", height=180)
        self.log_box.pack(fill="x", expand=False, padx=20, pady=(0, 20))

        self.dashboard_frame.bind("<Button-1>", self._handle_global_click, add="+")

        # ================= BOTTOM BUTTONS =================
        self.create_bottom_buttons()

        # Status labels (hidden - logs now go to Process Log)
        self.upload_status_lbl = None  # Not displayed, all logs go to Process Log
        self.status_lbl = None  # Not displayed, all logs go to Process Log
        
        self.projects_map = {}
        self.plans_map = {}
        self.runs_map = {}
        self.cases_map = {}
        self.assign_to_map = {}  # Map display_name -> user_id
        self.users_map = {}  # Map user_id -> user_name
        self.run_tests_map = {}  # Cache tests data for current run to filter by assignee

    def create_dashboard_header(self):
        """Create header with centered timer controls and right-side actions."""
        header_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=0)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_columnconfigure(2, weight=0)

        # Left brand label
        left_info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_info_frame.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            left_info_frame,
            text="BantuQa",
            text_color="#ffffff",
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(anchor="w")

        # Centered time display with play/pause controls beside it
        center_info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        center_info_frame.grid(row=0, column=1, sticky="nsew")

        time_controls_frame = ctk.CTkFrame(center_info_frame, fg_color="transparent")
        time_controls_frame.pack(anchor="center")

        self.start_test_btn = ctk.CTkButton(
            time_controls_frame,
            text="▶",
            width=36,
            height=32,
            fg_color="#2ecc71",
            text_color="black",
            hover_color="#27ae60",
            command=self.start_testing,
            font=("Arial", 14)
        )
        self.start_test_btn.pack(side="left", padx=(0, 6))

        self.pause_test_btn = ctk.CTkButton(
            time_controls_frame,
            text="⏸",
            width=36,
            height=32,
            fg_color="#f39c12",
            text_color="black",
            hover_color="#e67e22",
            command=self.hold_testing,
            font=("Arial", 14)
        )
        self.pause_test_btn.pack_forget()

        self.time_lbl = ctk.CTkLabel(
            time_controls_frame,
            text="⏱ Working Time: 0h 0m 0s",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.time_lbl.pack(side="left")

        # Right side buttons
        right_info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_info_frame.grid(row=0, column=2, sticky="e")

        self.logout_btn = ctk.CTkButton(
            right_info_frame,
            text="� Sign Out",
            command=self.do_logout,
            fg_color="#E74C3C",
            hover_color="#CC0000"
        )
        self.logout_btn.pack(side="left", padx=10)

        self.contact_btn = ctk.CTkButton(
            right_info_frame,
            text="C",
            width=40,
            height=32,
            command=self.show_contact_info,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            font=("Segoe UI", 13, "bold")
        )
        self.contact_btn.pack(side="left", padx=(10, 4))

        self.burger_btn = ctk.CTkButton(
            right_info_frame,
            text="☰",
            width=40,
            height=32,
            command=self.toggle_sidebar,
            fg_color="#2b2b3d",
            hover_color="#3a3a52",
            font=("Segoe UI", 13, "bold")
        )
        self.burger_btn.pack(side="left", padx=(4, 0))

    def show_contact_info(self):
        """Show contact and credit information for the application."""
        contact_window = ctk.CTkToplevel(self)
        contact_window.title("Contact & Credits")
        contact_window.geometry("430x240")
        contact_window.resizable(False, False)
        contact_window.transient(self)
        contact_window.grab_set()

        ctk.CTkLabel(
            contact_window,
            text=(
                "BantuQa is designed to help QA teams quickly capture "
                "screenshots and attach them to TestRail as test evidence."
            ),
            font=ctk.CTkFont(size=12),
            wraplength=380,
            justify="center"
        ).pack(pady=(16, 10))

        ctk.CTkLabel(
            contact_window,
            text="Created with AI assistance",
            font=ctk.CTkFont(size=12)
        ).pack()

        ctk.CTkLabel(
            contact_window,
            text="Developer: Sigit Wahyudi",
            font=ctk.CTkFont(size=12)
        ).pack()

        ctk.CTkLabel(
            contact_window,
            text="Email: s.wahyudi21@gmail.com",
            font=ctk.CTkFont(size=12)
        ).pack(pady=(0, 8))

        linkedin_url = "https://www.linkedin.com/in/sigit-wahyudi-21b510148/"
        linkedin_label = ctk.CTkLabel(
            contact_window,
            text="LinkedIn: Sigit Wahyudi",
            font=ctk.CTkFont(size=12, underline=True),
            text_color="#5DADE2"
        )
        linkedin_label.pack()
        linkedin_label.bind("<Button-1>", lambda e: webbrowser.open(linkedin_url))
        linkedin_label.configure(cursor="hand2")

    def apply_sidebar_width(self):
        """Apply the user-defined sidebar width."""
        try:
            width = int(self.sidebar_width_var.get())
        except (TypeError, ValueError):
            messagebox.showerror("Invalid width", "Please enter a valid number.")
            return

        width = max(self.sidebar_min_width, min(width, self.sidebar_max_width))
        self.sidebar_width_var.set(str(width))
        self.right_panel.configure(width=width)
        if self.sidebar_is_open:
            self.right_panel.place_configure(
                relx=1.0,
                rely=0.0,
                anchor="ne",
                x=0,
                y=0,
                relheight=1,
                width=width
            )
            self.right_panel.update_idletasks()

    def _set_sidebar_open(self, is_open):
        """Show or hide the attachment sidebar."""
        self.sidebar_is_open = is_open
        if is_open:
            width = self.right_panel.winfo_reqwidth()
            try:
                width = int(self.sidebar_width_var.get())
            except (TypeError, ValueError):
                width = max(self.sidebar_min_width, min(width, self.sidebar_max_width))
            width = max(self.sidebar_min_width, min(width, self.sidebar_max_width))
            self.right_panel.configure(width=width)
            self.right_panel.place_configure(
                relx=1.0,
                rely=0.0,
                anchor="ne",
                x=0,
                y=0,
                relheight=1,
                width=width
            )
            self.right_panel.update_idletasks()
        else:
            self.right_panel.place_forget()

    def toggle_sidebar(self, event=None):
        """Toggle sidebar visibility."""
        self._set_sidebar_open(not self.sidebar_is_open)

    def _is_widget_in_family(self, widget, family):
        """Check whether widget belongs to any widget family."""
        current = widget
        while current:
            if current in family:
                return True
            current = current.master
        return False

    def _handle_global_click(self, event):
        """Close sidebar when the user clicks outside it."""
        if not self.sidebar_is_open:
            return

        safe_family = (
            self.right_panel,
            self.burger_btn,
            self.contact_btn,
            self.logout_btn,
            self.time_lbl,
            self.start_test_btn,
            self.pause_test_btn,
        )
        if self._is_widget_in_family(event.widget, safe_family):
            return

        self._set_sidebar_open(False)

    def create_bottom_buttons(self):
        """Create bottom button panel"""
        btn_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        # Configure columns - action buttons only
        btn_frame.grid_columnconfigure(0, weight=3)  # Submit (flexible)
        btn_frame.grid_columnconfigure(1, weight=3)  # Clear Progress (flexible)
        btn_frame.grid_columnconfigure(2, weight=0)  # Refresh button

        # Submit to TestRail
        self.submit_btn = ctk.CTkButton(btn_frame, text="Submit to TestRail", fg_color="#3498db", text_color="white", 
                                       hover_color="#2980b9", height=40, command=self.do_submit)
        self.submit_btn.grid(row=0, column=0, sticky="ew", padx=5)
        self.submit_btn.configure(state="disabled")

        # Clear Progress (renamed from "New Test")
        self.new_test_btn = ctk.CTkButton(btn_frame, text="Clear Progress", fg_color="#f39c12", text_color="black", 
                                         hover_color="#d68910", height=40, command=self.new_test_session)
        self.new_test_btn.grid(row=0, column=1, sticky="ew", padx=5)

        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            btn_frame,
            text="↻",
            width=40,
            height=40,
            fg_color="#ffffff",
            text_color="#2b2b3d",
            hover_color="#e6e6e6",
            command=self.load_projects,
            font=("Arial", 16)
        )
        self.refresh_btn.grid(row=0, column=2, sticky="e", padx=(2, 0))

    def copy_attachment_errors(self):
        text = self.log_box.get("1.0", "end").strip()
        if not text:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.append_log(f"[{self.get_timestamp()}] Attachment details copied to clipboard\n")
        except Exception:
            self.append_log(f"[{self.get_timestamp()}] [error] Copy failed\n")

    def get_timestamp(self):
        """Get formatted timestamp for logging"""
        if self.test_start_time is None and not self.is_paused:
            return "00:00:00"
        
        if self.test_start_time is not None:
            elapsed = int(time.perf_counter() - self.test_start_time + self.paused_elapsed)
        else:
            elapsed = self.paused_elapsed
        
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def append_log(self, msg):
        """Append message to log_box"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg)
        self.log_box.see("end")  # Auto-scroll to end
        self.log_box.configure(state="disabled")

    def update_time_label(self):
        """Update header time label"""
        timestamp = self.get_timestamp()
        self.time_lbl.configure(text=f"⏱ Working Time: {timestamp}")
        self._sync_comment_input_state()

    def load_projects(self):
        # Start refresh animation
        self.animate_refresh_start()
        
        def fetch():
            projs = api_client.get_projects()
            self.projects_map = {p['name']: p['id'] for p in projs if p.get('is_completed') == False}
            names = list(self.projects_map.keys())
            if names:
                self._enqueue_ui_task(lambda: self.proj_combo.configure(values=names))
                cached_proj = self.cache.get('project')
                selected = cached_proj if cached_proj in names else names[0]
                self._enqueue_ui_task(lambda: self.proj_combo.set(selected))
                self._enqueue_ui_task(lambda: self.on_project_select(selected))
            # Stop refresh animation when complete
            self._enqueue_ui_task(self.animate_refresh_stop)
        threading.Thread(target=fetch).start()

    def load_statuses(self):
        statuses = api_client.get_statuses()
        self._apply_statuses(statuses)

    def _apply_statuses(self, statuses):
        fallback_status_map = {
            "Passed": 1,
            "Blocked": 2,
            "Untested": 3,
            "Retest": 4,
            "Failed": 5,
        }

        if statuses:
            self.status_id_map = {}
            self.status_options = []
            for item in statuses:
                if not isinstance(item, dict):
                    continue
                sid = item.get('id')
                if sid is None:
                    continue
                label = item.get('label') or item.get('name') or f"Status {sid}"
                if label not in self.status_id_map:
                    self.status_id_map[label] = sid
                    self.status_options.append(label)
        else:
            self.status_id_map = fallback_status_map.copy()
            self.status_options = list(fallback_status_map.keys())

        def choose_default(values):
            for preferred in ("Untested", "Passed", "Failed", "Blocked", "Retest"):
                if preferred in values:
                    return preferred
            return values[0] if values else "Untested"

        default_status = choose_default(self.status_options)

        if hasattr(self, 'status_dropdown') and self.status_dropdown:
            self.status_dropdown.configure(values=self.status_options)
            self.status_var.set(default_status)
            self.status_dropdown.set(default_status)

        if hasattr(self, 'bulk_step_status_dropdown') and self.bulk_step_status_dropdown:
            self.bulk_step_status_dropdown.configure(values=self.status_options)
            self.bulk_step_status_var.set(default_status)
            self.bulk_step_status_dropdown.set(default_status)

        for idx, dropdown in self.step_status_dropdowns.items():
            current = self.step_status_vars.get(idx, ctk.StringVar()).get() if idx in self.step_status_vars else ""
            if current not in self.status_options:
                current = default_status
            if idx in self.step_status_vars:
                self.step_status_vars[idx].set(current)
            dropdown.configure(values=self.status_options)
            dropdown.set(current)

    def animate_refresh_start(self):
        """Start spinning animation for refresh button"""
        self.refresh_animation_frame = 0
        self.animate_refresh_frame()

    def animate_refresh_frame(self):
        """Update refresh button animation frame"""
        if not hasattr(self, 'refresh_animation_frame') or self.refresh_animation_frame is None:
            return
        
        # Spinning animation frames
        frames = ["↻", "↼", "↽", "⤴"]
        frame_idx = self.refresh_animation_frame % len(frames)
        self.refresh_btn.configure(text=frames[frame_idx])
        self.refresh_animation_frame += 1
        
        # Continue animation
        self.after(100, self.animate_refresh_frame)

    def animate_refresh_stop(self):
        """Stop animation and restore refresh button"""
        self.refresh_animation_frame = None
        self.refresh_btn.configure(text="↻")

    def reset_plan_run_and_case(self):
        """Reset test plan, test run, dan test case - dipanggil saat project berubah"""
        self.plan_var.set("")
        self.plan_combo.set("📄 Select...")
        self.plan_combo.configure(values=["Select..."])
        
        self.run_var.set("")
        self.run_combo.set("📊 Select...")
        self.run_combo.configure(values=["Select..."])
        
        self.assign_to_var.set("")
        self.assign_to_combo.set("👤 Select...")
        self.assign_to_combo.configure(values=["Select..."])
        
        self.case_var.set("")
        self.case_combo.set("🔍 Select...")
        self.case_combo.configure(values=["Select..."])
        
        self.plans_map = {}
        self.runs_map = {}
        self.assign_to_map = {}
        self.cases_map = {}
        self.current_case_name = None
    
    def reset_run_and_case(self):
        """Reset test run dan test case - dipanggil saat plan berubah"""
        self.run_var.set("")
        self.run_combo.set("📊 Select...")
        self.run_combo.configure(values=["Select..."])
        
        self.assign_to_var.set("")
        self.assign_to_combo.set("👤 Select...")
        self.assign_to_combo.configure(values=["Select..."])
        
        self.case_var.set("")
        self.case_combo.set("🔍 Select...")
        self.case_combo.configure(values=["Select..."])
        
        self.runs_map = {}
        self.assign_to_map = {}
        self.cases_map = {}
        self.current_case_name = None
    
    def reset_case(self):
        """Reset test case - dipanggil saat run berubah"""
        self.case_var.set("")
        self.case_combo.set("🔍 Select...")
        self.case_combo.configure(values=["Select..."])
        
        self.cases_map = {}
        self.current_case_name = None
    
    def reset_assign_to(self):
        """Reset case dropdown when assign_to changes"""
        self.case_var.set("")
        self.case_combo.set("🔍 Select...")
        self.case_combo.configure(values=["Select..."])
        
        self.cases_map = {}
        self.current_case_name = None

    def _check_and_confirm_clear_progress(self):
        """
        Check if working time > 0, and if so, show confirmation dialog.
        If user confirms, clear progress and return True. Otherwise return False.
        """
        if self._get_elapsed_seconds() > 0:
            confirmed = messagebox.askyesno(
                title="Clear Progress",
                message="Working time has started. Changing this will clear progress, "
                        "attachments, comments, and timer. Continue?"
            )
            if confirmed:
                self.new_test_session(skip_confirmation=True)
                return True
            return False
        return True

    def on_project_select(self, proj_name):
        # Check if working time > 0 and confirm clearing progress
        if not self._check_and_confirm_clear_progress():
            # User didn't confirm, revert the selection
            if self.cache.get('project'):
                self.proj_combo.set(self.cache.get('project'))
            return
        
        # RESET semua dropdown di bawah
        self.reset_plan_run_and_case()
        
        self.cache['project'] = proj_name
        save_cache(self.cache)
        pid = self.projects_map.get(proj_name)
        if not pid: return
        
        def fetch():
            plans = api_client.get_plans(pid)
            self.plans_map = {"[Independent Runs]": None}
            for p in plans:
                if not p.get('is_completed'):
                    self.plans_map[f"Plan {p['id']}: {p['name']}"] = p['id']
            
            names = list(self.plans_map.keys())
            self._enqueue_ui_task(lambda: self.plan_combo.configure(values=names))
            # Gunakan first item, jangan cached (karena sudah di-reset)
            selected = names[0] if names else "[Independent Runs]"
            self._enqueue_ui_task(lambda: self.plan_combo.set(selected))
            self._enqueue_ui_task(lambda: self.on_plan_select(selected))
        threading.Thread(target=fetch).start()

    def on_plan_select(self, plan_name):
        # Check if working time > 0 and confirm clearing progress
        if not self._check_and_confirm_clear_progress():
            # User didn't confirm, revert the selection
            if self.cache.get('plan'):
                self.plan_combo.set(self.cache.get('plan'))
            return
        
        # RESET run dan case dropdown
        self.reset_run_and_case()
        
        self.cache['plan'] = plan_name
        save_cache(self.cache)
        pid = self.projects_map.get(self.proj_var.get())
        if not pid: return
        
        plan_id = self.plans_map.get(plan_name)
        
        def fetch():
            if plan_id is None:
                # Independent runs
                runs = api_client.get_runs(pid)
            else:
                # Plan runs
                runs = api_client.get_plan_runs(plan_id)
                
            self.runs_map = {f"Run {r['id']}: {r['name']}": r['id'] for r in runs if r.get('is_completed') == False}
            names = list(self.runs_map.keys())
            if names:
                self._enqueue_ui_task(lambda: self.run_combo.configure(values=names))
                # Gunakan first item, jangan cached (karena sudah di-reset)
                selected = names[0]
                self._enqueue_ui_task(lambda: self.run_combo.set(selected))
                self._enqueue_ui_task(lambda: self.on_run_select(selected))
            else:
                self._enqueue_ui_task(lambda: self.run_combo.configure(values=["No Active Runs"]))
                self._enqueue_ui_task(lambda: self.run_combo.set("No Active Runs"))
                self._enqueue_ui_task(lambda: self.on_run_select("No Active Runs"))
        threading.Thread(target=fetch).start()

    def on_run_select(self, run_name):
        # Check if working time > 0 and confirm clearing progress
        if not self._check_and_confirm_clear_progress():
            # User didn't confirm, revert the selection
            if self.cache.get('run'):
                self.run_combo.set(self.cache.get('run'))
            return
        
        # RESET case dropdown and assign_to
        self.reset_case()
        self.reset_assign_to()
        
        if run_name != "No Active Runs":
            self.cache['run'] = run_name
            save_cache(self.cache)
        rid = self.runs_map.get(run_name)
        if not rid: 
            self.cases_map = {}
            self.case_combo.configure(values=["No Test Cases"])
            self.case_combo.set("No Test Cases")
            return
        
        def fetch():
            # Fetch all tests for this run
            tests = api_client.get_tests(rid)
            self.run_tests_map = tests  # Cache for filtering
            
            # Extract unique assignee IDs
            assignee_ids = set()
            for test in tests:
                if test.get('assignedto_id'):
                    assignee_ids.add(test.get('assignedto_id'))
            
            # Fetch users from API and build maps
            users = api_client.get_users()
            self.users_map = {user['id']: user['name'] for user in users}
            
            # Build assign_to options: "All" + each assignee
            assign_to_options = ["👤 All"]  # Always show "All" option
            self.assign_to_map = {"👤 All": None}  # None = show all
            
            # Add each assignee as option
            for assignee_id in sorted(assignee_ids):
                assignee_name = self.users_map.get(assignee_id, f"User {assignee_id}")
                display_name = f"👤 {assignee_name} (ID: {assignee_id})"
                assign_to_options.append(display_name)
                self.assign_to_map[display_name] = assignee_id
            
            # Update assign_to dropdown
            self._enqueue_ui_task(lambda: self.assign_to_combo.configure(values=assign_to_options))
            self._enqueue_ui_task(lambda: self.assign_to_combo.set("👤 All"))
            self._enqueue_ui_task(lambda: self.on_assign_to_select("👤 All"))
        threading.Thread(target=fetch).start()

    def on_assign_to_select(self, assign_to_display):
        """Handle assign to selection - filter test cases by assignee"""
        # Check if working time > 0 and confirm clearing progress
        if not self._check_and_confirm_clear_progress():
            # User didn't confirm, revert the selection
            if self.cache.get('assign_to'):
                self.assign_to_combo.set(self.cache.get('assign_to'))
            return
        
        # Reset case dropdown
        self.reset_case()
        
        # Save to cache
        self.cache['assign_to'] = assign_to_display
        save_cache(self.cache)
        
        # Get selected assignee ID (None = show all)
        selected_assignee_id = self.assign_to_map.get(assign_to_display)
        
        # Filter tests based on selected assignee
        if selected_assignee_id is None:
            # Show all tests
            filtered_tests = self.run_tests_map
        else:
            # Show only tests assigned to selected user
            filtered_tests = [t for t in self.run_tests_map if t.get('assignedto_id') == selected_assignee_id]
        
        # Build cases map from filtered tests
        self.cases_map = {f"C{t.get('case_id')}: {t.get('title')}": t.get('case_id') for t in filtered_tests}
        names = list(self.cases_map.keys())
        
        if names:
            self.case_combo.configure(values=names)
            # Gunakan first item, jangan cached (karena sudah di-reset)
            selected = names[0]
            self.case_combo.set(selected)
            self.on_case_select(selected)
        else:
            self.case_combo.configure(values=["No Test Cases"])
            self.case_combo.set("No Test Cases")

    def on_case_select(self, case_name):
        previous_case_name = self.current_case_name

        if case_name != "No Test Cases":
            # Check if user is switching from one case to another with working time > 0
            if (
                previous_case_name and
                case_name != previous_case_name
            ):
                # Use the new helper to check and confirm clearing progress
                if not self._check_and_confirm_clear_progress():
                    # User didn't confirm, revert to previous case
                    self.case_var.set(previous_case_name)
                    self.case_combo.set(previous_case_name)
                    return

            self.cache['case'] = case_name
            save_cache(self.cache)

        self.current_case_name = case_name if case_name != "No Test Cases" else None
        self.current_case_data = None
        self.step_status_vars = {}
        self.step_status_dropdowns = {}
        self.step_actuals = {}

        case_id = self.cases_map.get(case_name)
        if case_id:
            threading.Thread(target=self._load_case_details, args=(case_id,), daemon=True).start()
        else:
            self.display_case_steps_empty()

    def _load_case_details(self, case_id):
        try:
            case_data = api_client.get_case(case_id)
            if case_data:
                self._enqueue_ui_task(lambda: self._set_current_case(case_data))
                self._enqueue_ui_task(lambda: self.display_case_steps(case_data))
            else:
                self._enqueue_ui_task(lambda: self.display_case_steps_error())
        except Exception:
            self._enqueue_ui_task(lambda: self.display_case_steps_error())

    def _set_current_case(self, case_data):
        self.current_case_data = case_data

    def _get_case_format_name(self, case_data):
        """Determine the UI layout based on the case template.

        Rules:
        - template_id == 2 -> Steps layout
        - template_id == 1 or template_id == 4 -> Text layout
        - anything else -> Text layout by default
        """
        if not isinstance(case_data, dict):
            return "text"

        template_id = case_data.get("template_id")
        if template_id == 2 or str(template_id) == "2":
            return "steps"

        return "text"

    def _get_steps_data(self, case_data):
        """Get the correct content payload for the case template.

        Template rules:
        - 2 -> use custom_steps_separated
        - 1 -> use custom_steps
        - 4 -> use custom_testrail_bdd_scenario
        - other -> fall back to the existing step fields when available
        """
        if not isinstance(case_data, dict):
            return None

        template_id = case_data.get('template_id')

        if template_id == 2 or str(template_id) == '2':
            return case_data.get('custom_steps_separated')

        if template_id == 1 or str(template_id) == '1':
            return case_data.get('custom_steps')

        if template_id == 4 or str(template_id) == '4':
            return case_data.get('custom_testrail_bdd_scenario')

        # Fallback for older or unknown payloads
        custom_steps_separated = case_data.get('custom_steps_separated')
        custom_steps = case_data.get('custom_steps')
        steps = case_data.get('steps')

        if isinstance(custom_steps_separated, (list, str, dict)):
            return custom_steps_separated
        if isinstance(custom_steps, (list, str, dict)):
            return custom_steps
        if isinstance(steps, (list, str, dict)):
            return steps

        return None

    def _get_case_preconditions(self, case_data):
        """Get preconditions from the case payload using common field names."""
        if not isinstance(case_data, dict):
            return ""

        for key in (
            'custom_preconds',
            'preconds',
            'preconditions',
            'custom_precondition',
            'custom_preconditions'
        ):
            value = case_data.get(key)
            if isinstance(value, str):
                return strip_html_tags(value)
            if isinstance(value, list):
                cleaned = "\n".join(
                    strip_html_tags(str(item)) for item in value if item is not None
                )
                if cleaned:
                    return cleaned

        return ""

    def _show_text_case_view(self, case_data):
        """Render the existing text-style case details view."""
        self.steps_textbox.grid()
        self.steps_details_frame.grid_remove()
        if hasattr(self, 'bulk_actions_frame') and self.bulk_actions_frame:
            self.bulk_actions_frame.grid_remove()

        self.steps_textbox.configure(state="normal")
        self.steps_textbox.delete("1.0", "end")

        title = case_data.get('title', 'N/A')
        self.steps_textbox.insert("end", f"📋 {title}\n", "bold")
        self.steps_textbox.insert("end", "\n")

        # Preconditions
        self.steps_textbox.insert("end", "📌 PRECONDITIONS\n", "section_header")
        custom_preconds = self._get_case_preconditions(case_data)
        if custom_preconds:
            self.steps_textbox.insert("end", f"\n{custom_preconds}\n\n")
        else:
            self.steps_textbox.insert("end", "\nNo preconditions defined.\n\n")

        # Main content (text case body)
        self.steps_textbox.insert("end", "📝 TEST CONTENT\n", "section_header")
        raw_steps = self._get_steps_data(case_data)
        if raw_steps:
            if isinstance(raw_steps, str):
                self.steps_textbox.insert("end", f"\n{strip_html_tags(raw_steps)}\n\n")
            else:
                for idx, step in enumerate(raw_steps, start=1):
                    if isinstance(step, dict):
                        text = step.get('content') or step.get('text') or ''
                        expected = step.get('expected') or ''
                        clean_text = strip_html_tags(text)
                        clean_expected = strip_html_tags(expected)
                        if clean_text:
                            self.steps_textbox.insert("end", f"{idx}. {clean_text}")
                            if clean_expected:
                                self.steps_textbox.insert("end", f"\n   Expected: {clean_expected}")
                            self.steps_textbox.insert("end", "\n\n")
                    elif isinstance(step, str):
                        self.steps_textbox.insert("end", f"{idx}. {strip_html_tags(step)}\n\n")
                    else:
                        self.steps_textbox.insert("end", f"{idx}. {strip_html_tags(str(step))}\n\n")
        else:
            self.steps_textbox.insert("end", "\nNo content defined for this test case.\n\n")

        # Expected result
        self.steps_textbox.insert("end", "✓ EXPECTED RESULT\n", "section_header")
        custom_expected = case_data.get('custom_expected', '')
        if custom_expected:
            self.steps_textbox.insert("end", f"\n{strip_html_tags(custom_expected)}\n")
        else:
            self.steps_textbox.insert("end", "\nNo expected result defined.\n")

        self.steps_textbox.configure(state="disabled")

    def _show_steps_case_view(self, case_data):
        """Render a structured layout for step-based cases."""
        self.step_status_vars = {}
        self.step_actuals = {}
        self.step_comment_buttons = {}
        self.steps_textbox.grid_remove()
        self.steps_details_frame.grid()
        if hasattr(self, 'bulk_actions_frame') and self.bulk_actions_frame:
            self.bulk_actions_frame.grid()

        # Clear previous content
        for widget in self.steps_details_content.winfo_children():
            widget.destroy()

        self.steps_details_content.grid_columnconfigure(0, weight=1)
        self.steps_details_content.grid_rowconfigure(0, weight=1)

        title = case_data.get('title', 'N/A')
        preconds = self._get_case_preconditions(case_data)
        expected = strip_html_tags(case_data.get('custom_expected', ''))
        steps_data = self._get_steps_data(case_data)

        # Unified content card
        main_card = ctk.CTkFrame(self.steps_details_content, fg_color="#202235", corner_radius=12)
        main_card.grid(row=0, column=0, sticky="nsew")
        main_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            main_card,
            text=f"📋 {title}",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 10))

        # Single content area for preconditions + steps + expected result
        content_area = ctk.CTkFrame(main_card, fg_color="transparent")
        content_area.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        content_area.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content_area,
            text=f"📌 Preconditions\n{preconds if preconds else 'No preconditions defined.'}",
            justify="left",
            wraplength=700,
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", pady=(0, 10))

        if not self.status_options:
            self.load_statuses()

        if isinstance(steps_data, list):
            for idx, step in enumerate(steps_data, start=1):
                step_row = ctk.CTkFrame(content_area, fg_color="#2a2a38", corner_radius=10)
                step_row.grid(row=100 + idx, column=0, sticky="ew", pady=(0, 8))
                step_row.grid_columnconfigure(1, weight=1)

                badge = ctk.CTkFrame(step_row, fg_color="#1f6aa5", corner_radius=8)
                badge.grid(row=0, column=0, sticky="n", padx=(10, 8), pady=10)
                ctk.CTkLabel(
                    badge,
                    text=str(idx),
                    width=28,
                    font=ctk.CTkFont(size=12, weight="bold")
                ).pack(padx=8, pady=6)

                body = ctk.CTkFrame(step_row, fg_color="transparent")
                body.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=10)
                body.grid_columnconfigure(0, weight=1)

                action_frame = ctk.CTkFrame(step_row, fg_color="transparent")
                action_frame.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(0, 10))
                action_frame.grid_columnconfigure(0, weight=0)
                action_frame.grid_columnconfigure(1, weight=0)
                action_frame.grid_columnconfigure(2, weight=0)
                action_frame.grid_columnconfigure(3, weight=1)

                step_status_var = ctk.StringVar(value="Untested")
                self.step_status_vars[idx] = step_status_var
                status_dropdown = ScrollableComboBox(
                    action_frame,
                    variable=step_status_var,
                    values=[],
                    fg_color="#2a2a38",
                    button_color="#2a2a38",
                    searchable=False
                )
                status_dropdown.button.configure(
                    command=lambda dropdown=status_dropdown: self._open_status_dropdown(dropdown)
                )
                self.step_status_dropdowns[idx] = status_dropdown
                if self.status_options:
                    status_dropdown.configure(values=self.status_options)
                    if "Untested" in self.status_options:
                        chosen = "Untested"
                    else:
                        chosen = self.status_var.get() or (self.status_options[0] if self.status_options else "")
                    self.step_status_vars[idx].set(chosen)
                    status_dropdown.set(chosen)
                status_dropdown.grid(row=0, column=0, sticky="w", padx=(0, 6))

                ctk.CTkButton(
                    action_frame,
                    text="+",
                    width=34,
                    height=28,
                    fg_color="#2b2b3d",
                    hover_color="#3a3a52",
                    command=lambda step_number=idx: self.request_capture(step_number),
                    font=("Arial", 14)
                ).grid(row=0, column=1, sticky="w", padx=(0, 6))

                has_comment = bool(self.step_actuals.get(idx, "").strip())
                comment_btn = ctk.CTkButton(
                    action_frame,
                    text="Comment",
                    width=80,
                    height=28,
                    fg_color="#2ecc71" if has_comment else "#2b2b3d",
                    hover_color="#27ae60" if has_comment else "#3a3a52",
                    text_color="black" if has_comment else "white",
                    command=lambda step_number=idx: self.show_step_comment_dialog(step_number),
                    font=("Arial", 12)
                )
                comment_btn.grid(row=0, column=2, sticky="w")
                self.step_comment_buttons[idx] = comment_btn

                if isinstance(step, dict):
                    step_text = step.get('content') or step.get('text') or ''
                    expected_text = step.get('expected') or ''
                    clean_step = strip_html_tags(step_text)
                    clean_expected = strip_html_tags(expected_text)

                    ctk.CTkLabel(
                        body,
                        text=clean_step,
                        justify="left",
                        wraplength=900,
                        anchor="w"
                    ).grid(row=0, column=0, sticky="ew")

                    if clean_expected:
                        ctk.CTkLabel(
                            body,
                            text=f"Expected: {clean_expected}",
                            justify="left",
                            wraplength=880,
                            anchor="w",
                            text_color="#b7f7a8"
                        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))
                elif isinstance(step, str):
                    ctk.CTkLabel(
                        body,
                        text=strip_html_tags(step),
                        justify="left",
                        wraplength=900,
                        anchor="w"
                    ).grid(row=0, column=0, sticky="ew")
                else:
                    ctk.CTkLabel(
                        body,
                        text=strip_html_tags(str(step)),
                        justify="left",
                        wraplength=900,
                        anchor="w"
                    ).grid(row=0, column=0, sticky="ew")
        else:
            ctk.CTkLabel(
                content_area,
                text="No steps defined for this test case.",
                justify="left",
                wraplength=700,
                anchor="w"
            ).grid(row=100, column=0, sticky="ew", pady=(0, 8))


    def display_case_steps(self, case_data):
        """Display test case details using the correct layout based on case format."""
        if self._get_case_format_name(case_data) == "steps":
            self._show_steps_case_view(case_data)
        else:
            self._show_text_case_view(case_data)

    def display_case_steps_empty(self):
        """Display empty state for steps"""
        self.current_case_data = None
        self.step_status_vars = {}
        self.steps_textbox.grid()
        self.steps_details_frame.grid_remove()
        self.steps_textbox.configure(state="normal")
        self.steps_textbox.delete("1.0", "end")
        self.steps_textbox.insert("end", "Select a test case to view steps")
        self.steps_textbox.configure(state="disabled")

    def display_case_steps_error(self):
        """Display error state for steps"""
        self.steps_textbox.grid()
        self.steps_details_frame.grid_remove()
        self.steps_textbox.configure(state="normal")
        self.steps_textbox.delete("1.0", "end")
        self.steps_textbox.insert("end", "Failed to load test case steps")
        self.steps_textbox.configure(state="disabled")

    def delete_file_from_preview(self, path):
        """Delete a file from capture queue and attachments"""
        if path not in self.capture_queue:
            return
        
        # If file has attachment ID, just remove the ID (don't delete file)
        # If file doesn't have attachment ID, delete the file
        if path in self.attachment_ids:
            del self.attachment_ids[path]
            self.append_log(f"[{self.get_timestamp()}] Attachment ID removed for {os.path.basename(path)}\n")
        else:
            self.capture_queue.remove(path)
            self.append_log(f"[{self.get_timestamp()}] File {os.path.basename(path)} removed from queue\n")
        
        # Remove step attachment mapping if present
        if path in self.step_attachment_lookup:
            step_idx = self.step_attachment_lookup.pop(path)
            step_paths = self.step_attachments.get(step_idx, [])
            if path in step_paths:
                step_paths.remove(path)
            if not step_paths:
                self.step_attachments.pop(step_idx, None)
        
        # Remove comment if exists
        if path in self.file_comments:
            del self.file_comments[path]
        
        self.update_dashboard_thumbnails()
        self.refresh_submit_state()

    def show_add_comment_dialog(self, path):
        """Show dialog to add/edit comment for a file"""
        if self._warn_start_testing_first():
            return

        filename = os.path.basename(path)
        current_comment = self.file_comments.get(path, "")
        
        # Get file index from capture queue
        try:
            file_idx = self.capture_queue.index(path) + 1
            # Extract first part of filename (before first underscore or extension)
            name_parts = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
            display_name = f"File {file_idx}: {name_parts}"
        except (ValueError, IndexError):
            display_name = filename
        
        # Create a new top-level window using CustomTkinter
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Add Comment - {display_name}")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1a1a24")
        
        # Center dialog on parent window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 250
        y = self.winfo_y() + (self.winfo_height() // 2) - 175
        dialog.geometry(f"500x350+{x}+{y}")
        
        # Make dialog modal
        dialog.attributes('-topmost', True)
        dialog.grab_set()
        
        # Title label
        title_frame = ctk.CTkFrame(dialog, fg_color="#20202e", corner_radius=10)
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        title_label = ctk.CTkLabel(title_frame, text=f"Comment for: {display_name}", 
                    font=ctk.CTkFont(size=13, weight="bold"), text_color="#d1d1d1")
        title_label.pack(anchor="w", padx=15, pady=10)
        
        # Comment textbox
        textbox_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        textbox_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        comment_textbox = ctk.CTkTextbox(textbox_frame, fg_color="#2a2a38", 
                                         text_color="white", border_color="#3e4c5f",
                                         border_width=1)
        comment_textbox.pack(fill="both", expand=True)
        comment_textbox.insert("1.0", current_comment)
        
        # Button frame - using pack layout for better button visibility
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        def save_comment():
            new_comment = comment_textbox.get("1.0", "end").strip()
            if new_comment:
                self.file_comments[path] = new_comment
                self.append_log(f"[{self.get_timestamp()}] Comment added for {filename}\n")
            else:
                if path in self.file_comments:
                    del self.file_comments[path]
                self.append_log(f"[{self.get_timestamp()}] Comment removed for {filename}\n")
            
            self.update_dashboard_thumbnails()
            dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        save_btn = ctk.CTkButton(button_frame, text="Save", command=save_comment, 
                                fg_color="#2ecc71", text_color="black", hover_color="#27ae60",
                                height=40)
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=cancel,
                                  fg_color="#e74c3c", text_color="white", hover_color="#c0392b",
                                  height=40)
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Focus on textbox
        dialog.after(100, lambda: comment_textbox.focus())

    def _update_step_comment_button(self, step_idx):
        """Update step comment button color based on whether the step has a comment."""
        button = self.step_comment_buttons.get(step_idx)
        if button is None:
            return

        has_comment = bool(self.step_actuals.get(step_idx, "").strip())
        button.configure(
            fg_color="#2ecc71" if has_comment else "#2b2b3d",
            hover_color="#27ae60" if has_comment else "#3a3a52",
            text_color="black" if has_comment else "white"
        )

    def show_step_comment_dialog(self, step_idx):
        """Show dialog to add/edit actual result for a specific step"""
        if self._warn_start_testing_first():
            return

        current_actual = self.step_actuals.get(step_idx, "")

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Actual Result - Step {step_idx}")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1a1a24")

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 250
        y = self.winfo_y() + (self.winfo_height() // 2) - 175
        dialog.geometry(f"500x350+{x}+{y}")

        dialog.attributes('-topmost', True)
        dialog.grab_set()

        title_frame = ctk.CTkFrame(dialog, fg_color="#20202e", corner_radius=10)
        title_frame.pack(fill="x", padx=15, pady=(15, 10))
        title_label = ctk.CTkLabel(
            title_frame,
            text=f"Actual result for Step {step_idx}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#d1d1d1"
        )
        title_label.pack(anchor="w", padx=15, pady=10)

        textbox_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        textbox_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        comment_textbox = ctk.CTkTextbox(
            textbox_frame,
            fg_color="#2a2a38",
            text_color="white",
            border_color="#3e4c5f",
            border_width=1
        )
        comment_textbox.pack(fill="both", expand=True)
        comment_textbox.bind("<Button-1>", self._warn_on_click)
        comment_textbox.insert("1.0", current_actual)

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))

        def save_actual():
            new_actual = comment_textbox.get("1.0", "end").strip()
            if new_actual:
                self.step_actuals[step_idx] = new_actual
                self.append_log(f"[{self.get_timestamp()}] Actual result added for step {step_idx}\n")
            else:
                self.step_actuals.pop(step_idx, None)
                self.append_log(f"[{self.get_timestamp()}] Actual result removed for step {step_idx}\n")
            self._update_step_comment_button(step_idx)
            dialog.destroy()

        def cancel():
            dialog.destroy()

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=save_actual,
            fg_color="#2ecc71",
            text_color="black",
            hover_color="#27ae60",
            height=40
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=cancel,
            fg_color="#e74c3c",
            text_color="white",
            hover_color="#c0392b",
            height=40
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        dialog.after(100, lambda: comment_textbox.focus())

    def clear_step_comments(self):
        """Clear all step comments and step-specific attachments from the current session."""
        self.step_actuals.clear()
        self.step_attachments.clear()
        self.step_attachment_lookup.clear()
        self.pending_step_capture = None

        for step_idx in list(self.step_comment_buttons.keys()):
            self._update_step_comment_button(step_idx)

    def register_step_attachment(self, step_idx, img_path):
        """Associate a captured screenshot with a specific step."""
        if img_path not in self.capture_queue:
            self.capture_queue.append(img_path)

        self.step_attachments.setdefault(step_idx, []).append(img_path)
        self.step_attachment_lookup[img_path] = step_idx
        self.update_dashboard_thumbnails()
        self.refresh_submit_state()

    def update_dashboard_thumbnails(self):
        """Update attachment preview with file list and step markers."""
        # Clear previous content
        for widget in self.lampiran_frame.winfo_children():
            widget.destroy()
        
        if not self.capture_queue:
            no_files_label = ctk.CTkLabel(self.lampiran_frame, text="No attachments yet",
                                         text_color="#808080", font=ctk.CTkFont(size=12))
            no_files_label.pack(pady=20)
            return
        
        # Icons untuk berbagai tipe file
        icons = {
            '.png': '🖼',
            '.jpg': '🖼',
            '.jpeg': '🖼',
            '.pdf': '📄',
            '.log': '📝',
            '.txt': '📝',
            '.mp4': '▶',
            '.avi': '▶',
            '.mov': '▶'
        }
        
        for idx, img_path in enumerate(self.capture_queue, start=1):
            filename = os.path.basename(img_path)
            ext = os.path.splitext(filename)[1].lower()
            icon = icons.get(ext, '📎')
            
            aid = self.attachment_ids.get(img_path)
            is_uploaded = aid is not None
            step_idx = self.step_attachment_lookup.get(img_path)
            is_step_attachment = step_idx is not None
            
            # Create a row frame for each file
            file_row = ctk.CTkFrame(self.lampiran_frame, fg_color="transparent")
            file_row.pack(fill="x", padx=0, pady=5)
            
            # Left section: Delete button (X)
            delete_btn = ctk.CTkButton(file_row, text="X", width=35, height=28,
                                      fg_color="#e74c3c", hover_color="#c0392b",
                                      text_color="white", font=ctk.CTkFont(size=14, weight="bold"),
                                      command=lambda p=img_path: self.delete_file_from_preview(p))
            delete_btn.pack(side="left", padx=(0, 8))
            
            # Left section: step marker or comment button
            if is_step_attachment:
                step_marker = ctk.CTkLabel(
                    file_row,
                    text=f"S{step_idx}",
                    width=35,
                    height=28,
                    fg_color="#3a3a52",
                    corner_radius=6,
                    font=ctk.CTkFont(size=10, weight="bold")
                )
                step_marker.pack(side="left", padx=(0, 0))
            else:
                comment_btn = ctk.CTkButton(file_row, text="💬", width=35, height=28,
                                           fg_color="#3498db", hover_color="#2980b9",
                                           font=ctk.CTkFont(size=12),
                                           command=lambda p=img_path: self.show_add_comment_dialog(p))
                comment_btn.pack(side="left", padx=(0, 0))
            
            # Middle section: File info
            info_frame = ctk.CTkFrame(file_row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)
            
            # File icon and name with status color
            file_status_color = "#2ecc71" if is_uploaded else "#FFD700"  # Green if uploaded, Yellow if pending
            
            if is_uploaded:
                # Create clickable hyperlink for uploaded files
                attachment_url = f"{api_client.base_url}/index.php?/attachments/get/{aid}"
                file_label = tk.Label(info_frame, text=f"{icon} {filename}",
                                     fg=file_status_color, bg="#2a2a38", 
                                     font=("Segoe UI", 8), cursor="hand2", wraplength=400, justify="left")
                file_label.pack(anchor="w", fill="x")
                
                # Bind click event
                file_label.bind("<Button-1>", lambda e, url=attachment_url: webbrowser.open(url))
                file_label.bind("<Enter>", lambda e, lbl=file_label: lbl.config(fg="#00bfff"))
                file_label.bind("<Leave>", lambda e, lbl=file_label: lbl.config(fg=file_status_color))
            else:
                # Non-clickable label for pending files - using tk.Label for consistent sizing
                file_label = tk.Label(info_frame, text=f"{icon} {filename}",
                                     fg=file_status_color, bg="#2a2a38",
                                     font=("Segoe UI", 8), wraplength=400, justify="left")
                file_label.pack(anchor="w", fill="x")
            
            # Comment display (if any)
            if img_path in self.file_comments:
                comment_text = self.file_comments[img_path]
                if len(comment_text) > 40:
                    comment_text = comment_text[:40] + "..."
                comment_label = ctk.CTkLabel(info_frame, text=f"💬 {comment_text}",
                                            text_color="#94a0b8", font=ctk.CTkFont(size=10))
                comment_label.pack(anchor="w")

    def remove_image(self, path):
        if path in self.capture_queue:
            self.capture_queue.remove(path)
        if path in self.attachment_ids:
            del self.attachment_ids[path]

        if path in self.step_attachment_lookup:
            step_idx = self.step_attachment_lookup.pop(path)
            step_paths = self.step_attachments.get(step_idx, [])
            if path in step_paths:
                step_paths.remove(path)
            if not step_paths:
                self.step_attachments.pop(step_idx, None)

        if path in self.file_comments:
            del self.file_comments[path]

        self.update_dashboard_thumbnails()
        self.update_attachment_ids_display()
        self.refresh_submit_state()

    def clear_all_attachments(self):
        if not self.capture_queue:
            return

        confirmed = messagebox.askyesno(
            title="Clear all attachments",
            message="Are you sure you want to remove all attachments? This cannot be undone."
        )

        if not confirmed:
            return

        self.capture_queue.clear()
        self.attachment_ids.clear()
        self.attachment_errors.clear()
        self.file_comments.clear()
        self.step_attachments.clear()
        self.step_attachment_lookup.clear()
        self.update_dashboard_thumbnails()
        self.update_attachment_ids_display()
        self.refresh_submit_state()
        self.append_log(f"[{self.get_timestamp()}] All attachments cleared\n")

    def _has_session_progress(self):
        """Check whether the current testcase session has any unsaved progress."""
        if self.capture_queue or self.attachment_ids or self.attachment_errors or self.file_comments:
            return True
        if self.comment_box.get("1.0", "end").strip():
            return True
        if self.step_actuals or self.step_attachments:
            return True
        if any(var.get().strip() for var in self.step_status_vars.values() if hasattr(var, "get")):
            return True
        if self.test_start_time is not None or self.is_paused or self.paused_elapsed > 0 or self.elapsed_seconds is not None:
            return True
        return False

    def _reset_test_session_state(self):
        """Reset current testcase session state without prompting."""
        self.capture_queue.clear()
        self.attachment_ids.clear()
        self.attachment_errors.clear()
        self.file_comments.clear()
        self.clear_step_comments()
        # Reset per-step status dropdowns to default (Untested) to remove residual progress
        default_status = "Untested" if "Untested" in self.status_options else (self.status_options[0] if self.status_options else "")
        # Also reset the main Test Result Status in the configuration section
        try:
            if hasattr(self, 'status_var') and self.status_var:
                self.status_var.set(default_status)
        except Exception:
            pass
        try:
            if hasattr(self, 'status_dropdown') and self.status_dropdown:
                self.status_dropdown.set(default_status)
        except Exception:
            pass
        try:
            if hasattr(self, 'bulk_step_status_var') and self.bulk_step_status_var:
                self.bulk_step_status_var.set(default_status)
        except Exception:
            pass
        try:
            if hasattr(self, 'bulk_step_status_dropdown') and self.bulk_step_status_dropdown:
                self.bulk_step_status_dropdown.set(default_status)
        except Exception:
            pass
        for idx, var in list(self.step_status_vars.items()):
            try:
                if hasattr(var, "set"):
                    var.set(default_status)
            except Exception:
                pass
            dropdown = self.step_status_dropdowns.get(idx)
            if dropdown:
                try:
                    dropdown.set(default_status)
                except Exception:
                    pass
        self.comment_box.delete("1.0", "end")
        self.elapsed_seconds = None
        self.paused_elapsed = 0
        self.test_start_time = None
        self.is_paused = False
        self.start_test_btn.configure(
            state="normal",
            text="▶",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            command=self.start_testing
        )

        self.update_dashboard_thumbnails()
        self.update_attachment_ids_display()
        self.refresh_submit_state()
        self.update_time_label()
        self.append_log(f"[{self.get_timestamp()}] Ready for new test\n")

    def new_test_session(self, skip_confirmation=False):
        if self._has_session_progress() and not skip_confirmation:
            confirmed = messagebox.askyesno(
                title="Start new test session",
                message="This will reset the current test session, clear attachments, reset timer, and clear comments. Continue?"
            )
            if not confirmed:
                return

        self._reset_test_session_state()

    def are_all_attachments_uploaded(self):
        return all(path in self.attachment_ids for path in self.capture_queue)

    def refresh_submit_state(self):
        if self.submit_btn:
            can_submit = self._get_elapsed_seconds() > 0
            if self.capture_queue and not self.are_all_attachments_uploaded():
                can_submit = False

            self.submit_btn.configure(state="normal" if can_submit else "disabled")

    def update_attachment_ids_display(self):
        """Update log_box with process log"""
        lines = []
        
        # If no logs yet, show default message
        if not lines:
            default_log = "[system] Ready to start testing...\n"
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.insert("1.0", default_log)
            self.log_box.configure(state="disabled")
            return
        
        # Display process log
        text = "\n".join(lines)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("1.0", text)
        
        if self.attachment_errors:
            self.log_box.insert("end", "\n\n[Errors]\n")
            for path, err in self.attachment_errors.items():
                self.log_box.insert("end", f"[error] {os.path.basename(path)}: {err}\n")
        
        self.log_box.configure(state="disabled")

    def upload_attachments(self):
        run_id = self.runs_map.get(self.run_var.get())
        if not run_id:
            self.append_log(f"[{self.get_timestamp()}] [error] Select a valid Run before uploading attachments\n")
            return

        if not self.capture_queue:
            self.append_log(f"[{self.get_timestamp()}] [error] No attachments to upload\n")
            return

        self.append_log(f"[{self.get_timestamp()}] Starting attachment upload...\n")

        # Clear log box and add initial message
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        initial_log = f"[{self.get_timestamp()}] Preparing attachments...\n"
        self.log_box.insert("end", initial_log)
        self.log_box.configure(state="disabled")

        def process_upload():
            try:
                upload_failed = False
                total = len(self.capture_queue)
                for idx, img_path in enumerate(self.capture_queue, start=1):
                    if img_path in self.attachment_ids:
                        log_msg = f"[{self.get_timestamp()}] Skip file {idx} (already uploaded)\n"
                        self.after(0, lambda msg=log_msg: self.append_log(msg))
                        continue

                    log_msg = f"[{self.get_timestamp()}] Processing upload file {idx} ({os.path.basename(img_path)}) started...\n"
                    self.after(0, lambda msg=log_msg: self.append_log(msg))
                    
                    aid = None
                    error_msg = None
                    for attempt in range(3):
                        aid, error_msg = api_client.upload_attachment_to_run(run_id, img_path)
                        if aid:
                            break
                        if not error_msg:
                            error_msg = f"Attempt {attempt + 1} failed"
                        else:
                            error_msg = f"Attempt {attempt + 1} failed: {error_msg}"
                        time.sleep(2)

                    if aid:
                        self.attachment_ids[img_path] = aid
                        if img_path in self.attachment_errors:
                            del self.attachment_errors[img_path]
                        log_msg = f"[{self.get_timestamp()}] Upload file {idx} successful. (ID: {aid})\n"
                        self.after(0, lambda msg=log_msg: self.append_log(msg))
                        self.after(0, self.update_dashboard_thumbnails)
                    else:
                        upload_failed = True
                        self.attachment_errors[img_path] = error_msg or "Unknown upload error"
                        log_msg = f"[{self.get_timestamp()}] [error] Upload file {idx} failed: {error_msg}\n"
                        self.after(0, lambda msg=log_msg: self.append_log(msg))
                        logger.error("Attachment upload failure for %s: %s", img_path, error_msg)
                        break

                self.after(0, self.refresh_submit_state)
                if not upload_failed:
                    self.after(0, lambda: self.append_log(f"[{self.get_timestamp()}] Upload completed successfully\n"))
            except Exception:
                logger.exception("Unexpected error during attachment upload")
                self.after(0, lambda: self.append_log(f"[{self.get_timestamp()}] [error] Upload failed due to internal error\n"))
            finally:
                self.after(0, self.refresh_submit_state)

        threading.Thread(target=process_upload).start()

    def start_testing(self):
        # Handle resume case if paused
        if self.is_paused:
            self.hold_testing()
            return
        
        # Normal start case
        if self.test_start_time is not None:
            return

        self.test_start_time = time.perf_counter()
        self.elapsed_seconds = None
        self.paused_elapsed = 0
        self.is_paused = False
        self.update_elapsed_label()
        self.refresh_submit_state()
        
        # Log to log_box
        log_msg = f"[{self.get_timestamp()}] Started testing\n"
        self.append_log(log_msg)
        
        # Keep the control anchored beside the label and just switch its icon/state.
        self.start_test_btn.configure(
            text="⏸",
            fg_color="#f39c12",
            hover_color="#e67e22",
            command=self.hold_testing
        )

    def hold_testing(self):
        if self.test_start_time is None and not self.is_paused:
            return

        if not self.is_paused:
            # Pause: save elapsed time, hide pause only, show start
            self.paused_elapsed += int(time.perf_counter() - self.test_start_time)
            self.test_start_time = None
            self.is_paused = True
            log_msg = f"[{self.get_timestamp()}] Testing paused\n"
            self.append_log(log_msg)
            # Keep the same button position but switch back to the play state.
            self.start_test_btn.configure(
                text="▶",
                fg_color="#2ecc71",
                hover_color="#27ae60",
                command=self.start_testing
            )
            self.refresh_submit_state()
        else:
            # Resume: continue counting from paused state
            self.test_start_time = time.perf_counter()
            self.is_paused = False
            log_msg = f"[{self.get_timestamp()}] Testing resumed\n"
            self.append_log(log_msg)
            # Keep the same button position while switching to pause mode.
            self.start_test_btn.configure(
                text="⏸",
                fg_color="#f39c12",
                hover_color="#e67e22",
                command=self.hold_testing
            )
            self.update_elapsed_label()
            self.refresh_submit_state()

    def update_elapsed_label(self):
        if self.test_start_time is None:
            return
        elapsed = int(time.perf_counter() - self.test_start_time + self.paused_elapsed)
        self.update_time_label()
        self.refresh_submit_state()
        self.after(500, self.update_elapsed_label)

    def do_submit(self):
        run_name = self.run_var.get()
        run_id = self.runs_map.get(run_name)
        case_name = self.case_var.get()
        case_id = self.cases_map.get(case_name)
        status_name = self.status_var.get()

        if status_name == "Untested":
            inferred_status = self._infer_main_status_from_step_statuses()
            if inferred_status:
                status_name = inferred_status
                try:
                    self.status_var.set(inferred_status)
                    self.status_dropdown.set(inferred_status)
                except Exception:
                    pass
            else:
                self.append_log(f"[{self.get_timestamp()}] [error] Please choose a valid Test Result Status before submit\n")
                self.submit_btn.configure(state="normal")
                return

        fallback_status_map = {"Passed": 1, "Blocked": 2, "Untested": 3, "Retest": 4, "Failed": 5}
        status_id = self.status_id_map.get(status_name)
        if status_id is None:
            status_id = fallback_status_map.get(status_name, 1)
        
        comment = self.comment_box.get("1.0", "end").strip()
        custom_step_results = None

        if self.current_case_data and self._get_case_format_name(self.current_case_data) == "steps":
            steps_data = self._get_steps_data(self.current_case_data)
            if isinstance(steps_data, list):
                custom_step_results = []
                for idx, step in enumerate(steps_data, start=1):
                    if isinstance(step, dict):
                        content = strip_html_tags(step.get('content') or step.get('text') or '')
                        expected = strip_html_tags(step.get('expected') or '')
                    else:
                        content = strip_html_tags(str(step))
                        expected = ''

                    selected_var = self.step_status_vars.get(idx)
                    status_name = selected_var.get() if selected_var else "Untested"
                    step_status_id = self.status_id_map.get(status_name)
                    if step_status_id is None:
                        step_status_id = fallback_status_map.get(status_name, 3)
                    step_payload = {
                        "content": content,
                        "expected": expected,
                        "status_id": step_status_id
                    }
                    actual_parts = []
                    actual = self.step_actuals.get(idx, "")
                    if actual:
                        actual_parts.append(actual)

                    for img_path in self.step_attachments.get(idx, []):
                        aid = self.attachment_ids.get(img_path)
                        if aid:
                            actual_parts.append(f"![](index.php?/attachments/get/{aid})")

                    if actual_parts:
                        step_payload["actual"] = "\n\n".join(part for part in actual_parts if part)
                    custom_step_results.append(step_payload)
        
        if not run_id or not case_id:
            self.append_log(f"[{self.get_timestamp()}] [error] Invalid Run or Case ID\n")
            return

        if self._get_elapsed_seconds() <= 0:
            self.append_log(f"[{self.get_timestamp()}] [error] Please start the working time before submit\n")
            return

        if self.capture_queue and not self.are_all_attachments_uploaded():
            self.append_log(f"[{self.get_timestamp()}] [error] Please upload attachments before submit\n")
            return

        self.submit_btn.configure(state="disabled")
        self.append_log(f"[{self.get_timestamp()}] Submitting result...\n")

        def process():
            try:
                att_ids = []
                for img_path in self.capture_queue:
                    aid = self.attachment_ids.get(img_path)
                    if not aid:
                        att_ids = []
                        break
                    att_ids.append(aid)

                if self.capture_queue and not att_ids:
                    self.after(0, lambda: self.append_log(f"[{self.get_timestamp()}] [error] Please upload attachments before submit\n"))
                    self.after(0, lambda: self.submit_btn.configure(state="normal"))
                    return

                # Build final comment with format: main comment + file comments + attachments
                final_comment_parts = []
                
                # Add main comment
                if comment.strip():
                    final_comment_parts.append(comment.strip())
                
                # Add file-specific comments with attachments for non-step screenshots only
                for img_path in self.capture_queue:
                    if img_path in self.step_attachment_lookup:
                        continue
                    if img_path in self.file_comments:
                        final_comment_parts.append(self.file_comments[img_path])
                    
                    if img_path in self.attachment_ids:
                        aid = self.attachment_ids[img_path]
                        final_comment_parts.append(f"![](index.php?/attachments/get/{aid})")
                
                final_comment = "\n".join(part for part in final_comment_parts if part)

                elapsed_value = None
                if self.elapsed_seconds is not None:
                    elapsed_val = max(1, int(self.elapsed_seconds))
                    elapsed_value = f"{elapsed_val}s"
                elif self.test_start_time is not None:
                    elapsed_val = max(1, int(time.perf_counter() - self.test_start_time + self.paused_elapsed))
                    elapsed_value = f"{elapsed_val}s"
                elif self.is_paused:
                    elapsed_val = max(1, int(self.paused_elapsed))
                    elapsed_value = f"{elapsed_val}s"

                success = api_client.add_result_for_case(
                    run_id,
                    case_id,
                    status_id,
                    final_comment,
                    elapsed=elapsed_value,
                    custom_step_results=custom_step_results
                )

                if success:
                    self.after(0, lambda: self.append_log(f"[{self.get_timestamp()}] Success! Result submitted.\n"))
                    self.capture_queue.clear()
                    self.attachment_ids.clear()
                    self.attachment_errors.clear()
                    self.file_comments.clear()
                    self.after(0, self.clear_step_comments)
                    self.elapsed_seconds = None
                    self.paused_elapsed = 0
                    self.test_start_time = None
                    self.is_paused = False
                    self.after(0, self.update_time_label)
                    self.after(0, self.update_dashboard_thumbnails)
                    self.after(0, self.update_attachment_ids_display)
                    self.after(0, lambda: self.comment_box.delete("1.0", "end"))
                    self.after(0, lambda: self.start_test_btn.configure(
                        state="normal",
                        text="▶",
                        fg_color="#2ecc71",
                        hover_color="#27ae60",
                        command=self.start_testing
                    ))
                    self.after(0, self.refresh_submit_state)
                    # Also reset the test session (same effect as clicking "Clear Progress")
                    self.after(0, self._reset_test_session_state)
                    self.after(0, lambda: messagebox.showinfo("Success", "Result telah berhasil disubmit ke TestRail!"))
                else:
                    self.after(0, lambda: self.append_log(f"[{self.get_timestamp()}] [error] Failed to add result.\n"))
            except Exception:
                logger.exception("Unexpected error during submit")
                self.after(0, lambda: self.append_log(f"[{self.get_timestamp()}] [error] Submit error.\n"))
            finally:
                self.after(0, lambda: self.submit_btn.configure(state="normal"))
            
        threading.Thread(target=process).start()
