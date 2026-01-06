from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame)
from PyQt6.QtCore import Qt
import os
from ui.character_window import CharacterWindow
from ui.scene_window import SceneWindow
from ui.script_window import ScriptWindow
from ui.storyboard_window import StoryboardWindow
from ui.synthesis_window import SynthesisWindow
from ui.project_window import ProjectWindow
from ui.settings_window import SettingsWindow
from ui.help_window import HelpWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("马上短剧生成系统 (Horseplay)")
        self.resize(1600, 1000)
        self.setMinimumSize(1024, 768)
        
        # Main layout container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Navigation Bar
        self.navbar = QFrame()
        self.navbar.setObjectName("navbar")
        self.navbar.setFixedHeight(60)
        self.navbar.setStyleSheet("""
            #navbar {
                background-color: #313131;
                color: white;
                border-bottom: 1px solid #34495e;
            }
            QPushButton {
                text-align: center;
                padding: 0 20px;
                border: none;
                color: white;
                font-size: 14px;
                font-weight: bold;
                height: 60px;
            }
            QPushButton:hover {
                background-color: #34495e;
                border-bottom: 3px solid #3498db;
            }
            QPushButton:checked {
                background-color: #2980b9;
                border-bottom: 3px solid #f1c40f;
            }
        """)
        
        navbar_layout = QHBoxLayout(self.navbar)
        navbar_layout.setContentsMargins(0, 0, 0, 0)
        navbar_layout.setSpacing(0)

        # Navigation Buttons
        self.nav_buttons = []
        self.create_nav_button("项目管理", 0, navbar_layout)
        self.create_nav_button("剧本创作", 1, navbar_layout)
        self.create_nav_button("角色设定", 2, navbar_layout)
        self.create_nav_button("场景设定", 3, navbar_layout)
        self.create_nav_button("分镜生成", 4, navbar_layout)
        self.create_nav_button("视频合成", 5, navbar_layout)
        self.create_nav_button("全局设置", 6, navbar_layout)
        self.create_nav_button("帮助", 7, navbar_layout)
        
        navbar_layout.addStretch()
        
        # Content Area
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("background-color: #313131;")
        
        # Paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        resources_dir = os.path.join(base_dir, "resources")
        characters_dir = os.path.join(resources_dir, "characters")
        scenes_dir = os.path.join(resources_dir, "scenes")
        projects_dir = os.path.join(resources_dir, "projects")
        
        # Initialize Windows
        # Pass None initially for project-dependent windows to indicate no project loaded
        self.project_window = ProjectWindow(projects_dir)
        self.script_window = ScriptWindow(None) 
        self.char_window = CharacterWindow(characters_dir)
        self.scene_window = SceneWindow(scenes_dir)
        self.storyboard_window = StoryboardWindow(None)
        self.synthesis_window = SynthesisWindow(None)
        self.settings_window = SettingsWindow()
        self.help_window = HelpWindow()

        # Connect Project Load Signal
        self.project_window.project_loaded.connect(self.on_project_loaded)
        self.project_window.open_episode.connect(self.open_episode_in_script_editor)

        # Add widgets for each section
        self.content_area.addWidget(self.project_window)
        self.content_area.addWidget(self.script_window)
        self.content_area.addWidget(self.char_window)
        self.content_area.addWidget(self.scene_window)
        self.content_area.addWidget(self.storyboard_window)
        self.content_area.addWidget(self.synthesis_window)
        self.content_area.addWidget(self.settings_window)
        self.content_area.addWidget(self.help_window)

        # Add to main layout
        main_layout.addWidget(self.navbar)
        main_layout.addWidget(self.content_area)

    def on_project_loaded(self, project_path):
        # Update all windows with the new project path
        if hasattr(self.script_window, 'set_project_dir'):
            self.script_window.set_project_dir(project_path)
        else:
            self.script_window.project_dir = project_path
            
        self.storyboard_window.project_dir = project_path
        self.synthesis_window.project_dir = project_path
        self.char_window.set_project_dir(project_path)
        self.scene_window.set_project_dir(project_path)
        
        # Trigger auto-load
        if hasattr(self.storyboard_window, 'load_existing_data'):
            self.storyboard_window.load_existing_data()
            
        if hasattr(self.synthesis_window, 'load_existing_data'):
            self.synthesis_window.load_existing_data()
        
        # Do NOT switch tab automatically, stay in Project Window to see details
        # self.switch_tab(1, self.nav_buttons[1])

    def open_episode_in_script_editor(self, project_path, episode_id):
        # Ensure project is loaded
        self.on_project_loaded(project_path)
        
        # Switch to Script Tab
        self.switch_tab(1, self.nav_buttons[1])
        
        # Load the specific episode
        if hasattr(self.script_window, 'load_episode_by_id'):
            self.script_window.load_episode_by_id(episode_id)
            
        # Also update Storyboard Window context
        if hasattr(self.storyboard_window, 'set_current_episode'):
            self.storyboard_window.set_current_episode(episode_id)

        # Update Synthesis Window context
        if hasattr(self.synthesis_window, 'set_current_episode'):
            self.synthesis_window.set_current_episode(episode_id)

    def create_nav_button(self, text, index, layout):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.switch_tab(index, btn))
        layout.addWidget(btn)
        self.nav_buttons.append(btn)
        if index == 0:
            btn.setChecked(True)

    def switch_tab(self, index, sender_btn):
        self.content_area.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setChecked(False)
        sender_btn.setChecked(True)
        
        # Refresh data for the active window
        current_widget = self.content_area.currentWidget()
        if hasattr(current_widget, 'load_existing_data'):
            current_widget.load_existing_data()
        elif hasattr(current_widget, 'load_existing_script'): # ScriptWindow
            current_widget.load_existing_script()

    def create_placeholder(self, text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(f"{text} Module\n(Under Construction)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; color: #7f8c8d;")
        layout.addWidget(label)
        return widget
