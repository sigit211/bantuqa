"""
Mekanisme untuk memastikan hanya satu instance aplikasi yang berjalan.
Jika instance lain sudah berjalan, signal ke instance yang ada untuk menampilkan window.
"""

import os
import ctypes

class SingleInstanceManager:
    """Manager untuk single instance check dan IPC dengan instance yang ada."""
    
    def __init__(self, app_name="BantuQa"):
        self.app_name = app_name
        self.mutex_name = f"Global\\{app_name}_Mutex"
        self.event_name = f"Global\\{app_name}_Event"
        self.mutex_handle = None
        self.event_handle = None
        
    def check_existing_instance(self):
        """
        Cek apakah instance lain sudah running.
        Return True jika instance lain ada, False jika ini adalah instance pertama.
        """
        try:
            # Coba buka event yang seharusnya dibuat oleh instance yang berjalan
            self.event_handle = ctypes.windll.kernel32.OpenEventW(
                2,  # EVENT_MODIFY_STATE
                False,
                self.event_name
            )
            
            if self.event_handle:
                # Instance lain ada, signal event untuk menampilkan window
                ctypes.windll.kernel32.SetEvent(self.event_handle)
                ctypes.windll.kernel32.CloseHandle(self.event_handle)
                return True
            
            return False
        except Exception:
            return False
    
    def create_instance_lock(self):
        """
        Buat mutex dan event untuk instance ini.
        Return True jika berhasil, False jika ada instance lain.
        """
        try:
            # Buat mutex untuk menandakan instance ini running
            self.mutex_handle = ctypes.windll.kernel32.CreateMutexW(
                None,
                True,
                self.mutex_name
            )
            
            if not self.mutex_handle:
                return False
            
            # Jika error code adalah ERROR_ALREADY_EXISTS (183), berarti instance lain ada
            error_code = ctypes.get_last_error()
            if error_code == 183:  # ERROR_ALREADY_EXISTS
                ctypes.windll.kernel32.CloseHandle(self.mutex_handle)
                self.mutex_handle = None
                return False
            
            # Buat event yang bisa di-signal dari instance lain
            self.event_handle = ctypes.windll.kernel32.CreateEventW(
                None,
                False,  # Auto-reset
                False,
                self.event_name
            )
            
            return True
            
        except Exception as e:
            print(f"Error creating instance lock: {e}")
            return False
    
    def wait_for_signal(self, timeout_ms=100):
        """
        Wait untuk signal dari instance yang lain.
        Return True jika ada signal (berarti ada attempt untuk buka instance baru).
        """
        if not self.event_handle:
            return False
        
        try:
            result = ctypes.windll.kernel32.WaitForSingleObject(
                self.event_handle,
                timeout_ms
            )
            # WAIT_OBJECT_0 = 0 (event di-signal)
            return result == 0
        except Exception:
            return False
    
    def cleanup(self):
        """Cleanup mutex dan event."""
        try:
            if self.mutex_handle:
                ctypes.windll.kernel32.ReleaseMutex(self.mutex_handle)
                ctypes.windll.kernel32.CloseHandle(self.mutex_handle)
                self.mutex_handle = None
            
            if self.event_handle:
                ctypes.windll.kernel32.CloseHandle(self.event_handle)
                self.event_handle = None
        except Exception:
            pass
