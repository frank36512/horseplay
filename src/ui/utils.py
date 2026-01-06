from PyQt6.QtWidgets import QMessageBox
import ctypes

def apply_windows_dark_title_bar(window):
    try:
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 2004+ and Windows 11)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        hwnd = int(window.winId())
        value = ctypes.c_int(1) # TRUE
        set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass

def show_message(parent, title, text, icon=QMessageBox.Icon.Information):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(icon)
    
    # Apply dark theme stylesheet explicitly if needed, though it should inherit from app
    # But title bar needs the DWM hack
    apply_windows_dark_title_bar(msg)
    
    msg.exec()

def show_warning(parent, title, text):
    show_message(parent, title, text, QMessageBox.Icon.Warning)

def show_error(parent, title, text):
    show_message(parent, title, text, QMessageBox.Icon.Critical)

