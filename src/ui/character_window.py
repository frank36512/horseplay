from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QMessageBox, QFrame)
from PyQt6.QtCore import Qt
import os
import json
import uuid
from core.character.character_model import Character
from core.script.script_model import Script
from ui.character_extraction_dialog import CharacterExtractionDialog
from ui.character_card import CharacterCardWidget
from ui.character_library_dialog import CharacterLibraryDialog
from ui.flow_layout import FlowLayout

class CharacterWindow(QWidget):
    def __init__(self, character_storage_path):
        super().__init__()
        self.storage_path = character_storage_path
        self.project_dir = None
        self.characters = []
        self.init_ui()
        self.load_characters()

    def set_project_dir(self, path):
        self.project_dir = path

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("为角色设置形象")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f1c40f;")
        subtitle = QLabel("已根据故事识别角色，请点击角色卡片设置形象")
        subtitle.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # one_click_btn removed as per request
        
        main_layout.addLayout(header_layout)

        # Grid Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")
        
        self.grid_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.grid_widget)
        self.cards_layout.setSpacing(30)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll)
        
        # Bottom Actions
        bottom_layout = QHBoxLayout()
        extract_btn = QPushButton("从剧本提取角色")
        extract_btn.clicked.connect(self.extract_from_script)
        extract_btn.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px;")
        
        add_btn = QPushButton("+ 手动添加角色")
        add_btn.clicked.connect(self.create_new_character)
        add_btn.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px;")
        
        bottom_layout.addWidget(extract_btn)
        bottom_layout.addWidget(add_btn)
        bottom_layout.addStretch()
        
        main_layout.addLayout(bottom_layout)

    def load_characters(self):
        # Clear layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            
        self.characters = []
        if os.path.exists(self.storage_path):
            for filename in os.listdir(self.storage_path):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.storage_path, filename), 'r', encoding='utf-8') as f:
                            char = Character.from_json(f.read())
                            self.characters.append(char)
                    except:
                        pass
        
        # Group by project
        grouped_chars = {}
        for char in self.characters:
            pid = char.project_id if hasattr(char, 'project_id') and char.project_id else "未分类"
            if pid not in grouped_chars:
                grouped_chars[pid] = []
            grouped_chars[pid].append(char)
            
        # Create sections
        sorted_pids = sorted(grouped_chars.keys())
        if "未分类" in sorted_pids:
            sorted_pids.remove("未分类")
            sorted_pids.append("未分类")
            
        for pid in sorted_pids:
            chars = grouped_chars[pid]
            
            # Section Container
            section = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 20)
            
            # Header
            project_name = self.get_project_name(pid)
            header = QLabel(f"📂 {project_name}")
            header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ecf0f1; margin-bottom: 10px;")
            section_layout.addWidget(header)
            
            # Grid for this project
            grid_widget = QWidget()
            # Set background for the grid area
            bg_color = self.get_project_color(pid)
            grid_widget.setStyleSheet(f"background-color: {bg_color}; border-radius: 10px;")
            
            # Use FlowLayout for responsive grid
            grid = FlowLayout(grid_widget, margin=20, spacing=20)
            
            for char in chars:
                card = CharacterCardWidget(char)
                card.clicked.connect(self.open_character_library)
                card.deleted.connect(self.delete_character)
                grid.addWidget(card)
            
            section_layout.addWidget(grid_widget)
            self.cards_layout.addWidget(section)
            
        self.cards_layout.addStretch()

    def get_project_color(self, project_id):
        if project_id == "未分类":
            return "rgba(255, 255, 255, 0.05)"
        
        # Generate a consistent color from string
        hash_val = 0
        for char in project_id:
            hash_val = ord(char) + ((hash_val << 5) - hash_val)
            
        # Convert to pastel color (HSL)
        # Reduced opacity to 0.2 and saturation to 40% for a lighter/fainter look
        h = abs(hash_val) % 360
        return f"hsla({h}, 40%, 30%, 0.2)"

    def get_project_name(self, project_id):
        if project_id == "未分类":
            return "未分类"
        
        try:
            # self.storage_path is .../resources/characters
            # We want .../resources/projects
            resources_dir = os.path.dirname(self.storage_path)
            project_json = os.path.join(resources_dir, "projects", project_id, "project.json")
            if os.path.exists(project_json):
                with open(project_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("name", project_id)
        except:
            pass
            
        return project_id

    def delete_character(self, char_id):
        char = next((c for c in self.characters if c.id == char_id), None)
        if char:
            reply = QMessageBox.question(self, "确认删除", f"确定要删除角色 '{char.name}' 吗？", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Delete file
                    filename = f"{char.name}_{char.id}.json"
                    # Try to find the file since name might have changed or encoding issues
                    # Actually we should probably store filename in character or search by ID
                    # But here we iterate to find the file
                    found = False
                    for f in os.listdir(self.storage_path):
                        if f.endswith(".json") and char.id in f:
                            os.remove(os.path.join(self.storage_path, f))
                            found = True
                            break
                    
                    if found:
                        self.load_characters()
                    else:
                        QMessageBox.warning(self, "错误", "找不到角色文件。")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"删除失败: {e}")

    def open_character_library(self, char_id):
        char = next((c for c in self.characters if c.id == char_id), None)
        if char:
            dialog = CharacterLibraryDialog(char, self)
            if dialog.exec():
                char.save(self.storage_path)
                self.load_characters()

    def create_new_character(self):
        project_id = os.path.basename(self.project_dir) if self.project_dir else ""
        new_char = Character(
            id=str(uuid.uuid4()),
            name="新角色",
            age="",
            gender="",
            appearance_features="",
            style_description="",
            project_id=project_id
        )
        new_char.save(self.storage_path)
        self.load_characters()
        # Open dialog immediately
        self.open_character_library(new_char.id)

    def extract_from_script(self):
        if not self.project_dir:
            QMessageBox.warning(self, "提示", "请先打开一个项目。")
            return

        project_id = os.path.basename(self.project_dir)
        roles = set()
        
        # Check for Series (series.json)
        series_path = os.path.join(self.project_dir, "series.json")
        if os.path.exists(series_path):
            try:
                with open(series_path, 'r', encoding='utf-8') as f:
                    series_data = json.load(f)
                
                episodes = series_data.get("episodes", [])
                if not episodes:
                    QMessageBox.warning(self, "提示", "当前项目没有分集。")
                    return
                
                # Iterate all episodes to find roles
                for ep in episodes:
                    # Try to find script file
                    # 1. Try standard path: scripts/episode_{id}.json
                    script_path = os.path.join(self.project_dir, "scripts", f"episode_{ep['id']}.json")
                    
                    if os.path.exists(script_path):
                        try:
                            with open(script_path, 'r', encoding='utf-8') as f:
                                script = Script.from_json(f.read())
                                for scene in script.scenes:
                                    for dialogue in scene.dialogues:
                                        if dialogue.role:
                                            roles.add(dialogue.role)
                        except:
                            continue
            except Exception as e:
                QMessageBox.warning(self, "错误", f"读取剧集失败: {e}")
                return
        else:
            # Legacy / Single Script
            script_path = os.path.join(self.project_dir, "current_script.json")
            if not os.path.exists(script_path):
                QMessageBox.warning(self, "提示", "当前项目没有剧本文件。")
                return

            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    script = Script.from_json(f.read())
                    for scene in script.scenes:
                        for dialogue in scene.dialogues:
                            if dialogue.role:
                                roles.add(dialogue.role)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"读取剧本失败: {e}")
                return

        if not roles:
            QMessageBox.information(self, "提示", "剧本中未找到角色。")
            return

        # Get existing character names
        existing_names = set(c.name for c in self.characters)

        # Show dialog
        dialog = CharacterExtractionDialog(sorted(list(roles)), existing_names, self)
        if dialog.exec():
            selected_roles = dialog.get_selected_roles()
            for role in selected_roles:
                # Create new character
                new_char = Character(
                    id=str(uuid.uuid4()),
                    name=role,
                    age="",
                    gender="",
                    appearance_features="",
                    style_description="",
                    project_id=project_id
                )
                new_char.save(self.storage_path)
            
            if selected_roles:
                self.load_characters()
                QMessageBox.information(self, "成功", f"已导入 {len(selected_roles)} 个新角色。")

    def auto_select_images(self):
        QMessageBox.information(self, "提示", "一键选形象功能正在开发中...")

