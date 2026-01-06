from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QAction
import os

class SceneCardWidget(QWidget):
    clicked = pyqtSignal(str) # scene_id
    deleted = pyqtSignal(str) # scene_id
    edited = pyqtSignal(str)  # scene_id

    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.setFixedSize(200, 280)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Card Container
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: #34495e;
                border-radius: 10px;
            }
            QWidget:hover {
                background-color: #3d566e;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        
        # Image
        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(180, 180)
        self.img_lbl.setStyleSheet("background-color: #2c3e50; border-radius: 5px;")
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if self.scene.image_path and os.path.exists(self.scene.image_path):
            pixmap = QPixmap(self.scene.image_path)
            self.img_lbl.setPixmap(pixmap.scaled(
                self.img_lbl.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.img_lbl.setText("无图片")
            self.img_lbl.setStyleSheet("color: #7f8c8d; background-color: #2c3e50; border-radius: 5px;")
            
        container_layout.addWidget(self.img_lbl)
        
        # Info
        info_layout = QVBoxLayout()
        name_lbl = QLabel(self.scene.name)
        name_lbl.setStyleSheet("font-weight: bold; color: white; font-size: 14px; background: transparent;")
        name_lbl.setWordWrap(True)
        
        desc_lbl = QLabel(self.scene.description[:30] + "..." if len(self.scene.description) > 30 else self.scene.description)
        desc_lbl.setStyleSheet("color: #bdc3c7; font-size: 12px; background: transparent;")
        desc_lbl.setWordWrap(True)
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(desc_lbl)
        container_layout.addLayout(info_layout)
        
        layout.addWidget(self.container)
        
        # Context Menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.scene.id)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
            }
            QMenu::item:selected {
                background-color: #f1c40f;
                color: #2c3e50;
            }
        """)
        
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self.edited.emit(self.scene.id))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.deleted.emit(self.scene.id))
        menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(pos))
