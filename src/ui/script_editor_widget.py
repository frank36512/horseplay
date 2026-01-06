from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QFrame, 
                             QScrollArea, QGroupBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from core.script.script_model import Script, Scene, Dialogue

class ShotWidget(QFrame):
    deleted = pyqtSignal(int)

    def __init__(self, index, dialogue: Dialogue, parent=None):
        super().__init__(parent)
        self.dialogue = dialogue
        self.index = index
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            ShotWidget {
                background-color: #2c3e50;
                border-radius: 5px;
                margin-bottom: 5px;
            }
            QLabel { color: #bdc3c7; font-weight: bold; }
            QLineEdit, QTextEdit { 
                background-color: #34495e; 
                color: white; 
                border: 1px solid #5d6d7e;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Row 1: Index + Subtitle (Role + Content)
        row1 = QHBoxLayout()
        
        idx_lbl = QLabel(f"分镜{self.index}")
        idx_lbl.setFixedWidth(50)
        row1.addWidget(idx_lbl)
        
        row1.addWidget(QLabel("字幕:"))
        
        # Role Input
        self.role_edit = QLineEdit(self.dialogue.role)
        self.role_edit.setPlaceholderText("角色")
        self.role_edit.setFixedWidth(80)
        self.role_edit.textChanged.connect(self.update_role)
        row1.addWidget(self.role_edit)
        
        row1.addWidget(QLabel(":"))
        
        # Content Input
        self.content_edit = QLineEdit(self.dialogue.content)
        self.content_edit.setPlaceholderText("台词内容")
        self.content_edit.textChanged.connect(self.update_content)
        row1.addWidget(self.content_edit)
        
        # Tools (Delete, etc)
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton { color: #5d6d7e; background: transparent; border: none; font-weight: bold; font-size: 16px; }
            QPushButton:hover { color: #e74c3c; background-color: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        """)
        del_btn.clicked.connect(self.on_delete)
        row1.addWidget(del_btn)
        
        layout.addLayout(row1)
        
        # Row 2: Visual Description
        row2 = QHBoxLayout()
        row2.setContentsMargins(50, 0, 0, 0) # Indent to align with subtitle text
        row2.addWidget(QLabel("画面描述:"))
        
        self.action_edit = QLineEdit(self.dialogue.action) # Using QLineEdit for single line visual desc as per screenshot look, or TextEdit if multiline needed
        self.action_edit.setPlaceholderText("画面动作/表情描述")
        self.action_edit.textChanged.connect(self.update_action)
        row2.addWidget(self.action_edit)
        
        layout.addLayout(row2)

    def update_role(self, text):
        self.dialogue.role = text

    def update_content(self, text):
        self.dialogue.content = text

    def update_action(self, text):
        self.dialogue.action = text

    def on_delete(self):
        self.deleted.emit(self.index)

class SceneWidget(QGroupBox):
    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.init_ui()

    def init_ui(self):
        # self.setTitle(f"场景 {self.scene.scene_id} - {self.scene.location} - {self.scene.time}")
        self.setStyleSheet("""
            QGroupBox {
                background-color: #233040;
                border: 1px solid #4a6b8a;
                border-radius: 5px;
                margin-top: 10px;
                color: white;
                font-weight: bold;
                padding-top: 10px;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        
        # Custom Header for Editable Title
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        
        # Scene ID
        id_lbl = QLabel(f"场景 {self.scene.scene_id}")
        id_lbl.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(id_lbl)
        
        header_layout.addWidget(QLabel(" - "))
        
        # Location Input
        self.loc_edit = QLineEdit(self.scene.location)
        self.loc_edit.setPlaceholderText("地点")
        self.loc_edit.setFixedWidth(150)
        self.loc_edit.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 3px; padding: 2px;")
        self.loc_edit.textChanged.connect(self.update_location)
        header_layout.addWidget(self.loc_edit)
        
        header_layout.addWidget(QLabel(" - "))
        
        # Time Input
        self.time_edit = QLineEdit(self.scene.time)
        self.time_edit.setPlaceholderText("时间")
        self.time_edit.setFixedWidth(100)
        self.time_edit.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 3px; padding: 2px;")
        self.time_edit.textChanged.connect(self.update_time)
        header_layout.addWidget(self.time_edit)
        
        header_layout.addStretch()
        
        self.layout.addLayout(header_layout)
        
        # Scene Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("场景描述:"))
        self.desc_edit = QLineEdit(self.scene.description)
        self.desc_edit.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #5d6d7e; padding: 5px;")
        self.desc_edit.textChanged.connect(self.update_desc)
        desc_layout.addWidget(self.desc_edit)
        self.layout.addLayout(desc_layout)
        
        # Shots Container
        self.shots_layout = QVBoxLayout()
        self.layout.addLayout(self.shots_layout)
        
        # Render existing shots
        self.refresh_shots()
        
        # Add Shot Button
        add_btn = QPushButton("+")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1c40f;
                color: #2c3e50;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #f39c12; }
        """)
        add_btn.setFixedSize(30, 30)
        add_btn.clicked.connect(self.add_shot)
        
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(add_btn)
        btn_container.addStretch()
        self.layout.addLayout(btn_container)

    def update_location(self, text):
        self.scene.location = text

    def update_time(self, text):
        self.scene.time = text

    def refresh_shots(self):
        # Clear existing
        while self.shots_layout.count():
            item = self.shots_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        for i, dialogue in enumerate(self.scene.dialogues):
            shot = ShotWidget(i + 1, dialogue)
            shot.deleted.connect(self.remove_shot)
            self.shots_layout.addWidget(shot)

    def remove_shot(self, index):
        # index is 1-based
        if 0 <= index - 1 < len(self.scene.dialogues):
            self.scene.dialogues.pop(index - 1)
            self.refresh_shots()

    def add_shot(self):
        new_dialogue = Dialogue(role="", content="", action="")
        self.scene.dialogues.append(new_dialogue)
        self.refresh_shots()

    def update_desc(self, text):
        self.scene.description = text

class ScriptEditorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_script = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; } QWidget#scroll_content { background-color: #1e1e1e; }")
        
        self.container = QWidget()
        self.container.setObjectName("scroll_content")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(20, 20, 20, 20)
        self.container_layout.setSpacing(20)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def load_script(self, script: Script, title_info=""):
        self.current_script = script
        
        # Clear
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        if not script:
            return

        # Title Section (Project - Episode Info)
        if title_info:
            title_lbl = QLabel(title_info)
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_lbl.setStyleSheet("color: #ecf0f1; font-size: 24px; font-weight: bold; margin-bottom: 15px; font-family: 'Microsoft YaHei';")
            self.container_layout.addWidget(title_lbl)

        # Scenes
        for scene in script.scenes:
            scene_widget = SceneWidget(scene)
            self.container_layout.addWidget(scene_widget)
            
        self.container_layout.addStretch()
