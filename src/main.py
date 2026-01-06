import sys
import os
import ctypes
import shutil
import imageio_ffmpeg

# Add the src directory to the python path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPalette, QColor, QIcon
from ui.main_window import MainWindow

def apply_dark_theme(app):
    # Fusion style is a good base for dark themes
    app.setStyle("Fusion")
    
    # Define Dark Palette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(49, 49, 49))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(44, 62, 80))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(49, 49, 49))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(52, 73, 94))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(236, 240, 241))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    
    app.setPalette(dark_palette)
    
    # Global Stylesheet for specific widgets
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        QMessageBox {
            background-color: #313131;
        }
        QMessageBox QLabel {
            color: #ecf0f1;
        }
        QDialog {
            background-color: #313131;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2c3e50;
            color: #ecf0f1;
            border: 1px solid #34495e;
            border-radius: 3px;
            selection-background-color: #3498db;
        }
        QListWidget, QTreeWidget, QTableWidget {
            background-color: #2c3e50;
            color: #ecf0f1;
            border: 1px solid #34495e;
        }
        QHeaderView::section {
            background-color: #34495e;
            color: white;
            border: 1px solid #2c3e50;
            padding: 4px;
        }
        QScrollBar:vertical {
            border: none;
            background: #2c3e50;
            width: 10px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #95a5a6;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)

def apply_windows_dark_title_bar(window):
    try:
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 2004+ and Windows 11)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        hwnd = int(window.winId())
        value = ctypes.c_int(1) # TRUE
        set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except Exception as e:
        print(f"Failed to apply dark title bar: {e}")

def check_ffmpeg():
    # First check system path
    if shutil.which("ffmpeg"):
        return True
        
    # Then check imageio_ffmpeg
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_exe):
            # Add to PATH so other modules can find it
            ffmpeg_dir = os.path.dirname(ffmpeg_exe)
            if ffmpeg_dir not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + ffmpeg_dir
            return True
    except:
        pass
        
    print("Warning: FFmpeg not found in PATH. Video synthesis will fail.")
    return False

def main():
    app = QApplication(sys.argv)
    
    # Set Application Icon
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "horseplay.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    if not check_ffmpeg():
        QMessageBox.warning(None, "Missing Dependency", 
                            "FFmpeg was not found in your system PATH.\n"
                            "Video synthesis features will not work until FFmpeg is installed.")

    # Apply Dark Theme
    apply_dark_theme(app)
    
    window = MainWindow()
    
    # Apply Windows Dark Title Bar
    apply_windows_dark_title_bar(window)
    
    window.showMaximized()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
