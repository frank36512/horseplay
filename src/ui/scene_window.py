from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt
import os
import json
import uuid
from core.scene.scene_model import Scene
from core.script.script_model import Script
from ui.scene_card import SceneCardWidget
from ui.scene_library_dialog import AddSceneDialog, SceneLibraryDialog
from ui.scene_extraction_dialog import SceneExtractionDialog
from ui.flow_layout import FlowLayout

class SceneWindow(QWidget):
    def __init__(self, scene_storage_path):
        super().__init__()
        self.storage_path = scene_storage_path
        self.project_dir = None
        self.scenes = []
        self.init_ui()
        self.load_scenes()

    def set_project_dir(self, path):
        self.project_dir = path

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("场景设定")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f1c40f;")
        subtitle = QLabel("管理项目中的常用场景，保持画面一致性")
        subtitle.setStyleSheet("color: #bdc3c7; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
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
        
        extract_btn = QPushButton("从剧本提取场景")
        extract_btn.clicked.connect(self.extract_from_script)
        extract_btn.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px;")
        
        add_btn = QPushButton("+ 新建场景")
        add_btn.clicked.connect(self.create_new_scene)
        add_btn.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px;")
        
        bottom_layout.addWidget(extract_btn)
        bottom_layout.addWidget(add_btn)
        bottom_layout.addStretch()
        
        main_layout.addLayout(bottom_layout)

    def load_scenes(self):
        # Clear layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            
        self.scenes = []
        if os.path.exists(self.storage_path):
            for filename in os.listdir(self.storage_path):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.storage_path, filename), 'r', encoding='utf-8') as f:
                            scene = Scene.from_json(f.read())
                            self.scenes.append(scene)
                    except:
                        pass
        
        # Group by project
        grouped_scenes = {}
        for scene in self.scenes:
            pid = scene.project_id if hasattr(scene, 'project_id') and scene.project_id else "未分类"
            if pid not in grouped_scenes:
                grouped_scenes[pid] = []
            grouped_scenes[pid].append(scene)
            
        # Create sections
        sorted_pids = sorted(grouped_scenes.keys())
        if "未分类" in sorted_pids:
            sorted_pids.remove("未分类")
            sorted_pids.append("未分类")
            
        for pid in sorted_pids:
            scenes = grouped_scenes[pid]
            
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
            
            for scene in scenes:
                card = SceneCardWidget(scene)
                card.clicked.connect(self.open_scene_library)
                card.edited.connect(self.edit_scene)
                card.deleted.connect(self.delete_scene)
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
        h = abs(hash_val) % 360
        return f"hsla({h}, 40%, 30%, 0.2)"

    def get_project_name(self, project_id):
        if project_id == "未分类":
            return "未分类"
        
        try:
            # self.storage_path is .../resources/scenes (assumed, but actually passed in init)
            # We want .../resources/projects
            # Assuming storage_path is like .../resources/something
            # But wait, in main.py it's likely passed as .../resources/scenes or similar.
            # Let's assume standard structure.
            resources_dir = os.path.dirname(self.storage_path)
            # If storage_path is .../resources/scenes, dirname is .../resources
            
            # Check if projects folder exists there
            projects_dir = os.path.join(resources_dir, "projects")
            if not os.path.exists(projects_dir):
                 # Maybe storage_path is deeper?
                 # Let's try to find 'resources' in path
                 parts = self.storage_path.split(os.sep)
                 if 'resources' in parts:
                     idx = parts.index('resources')
                     resources_dir = os.sep.join(parts[:idx+1])
                     projects_dir = os.path.join(resources_dir, "projects")

            project_json = os.path.join(projects_dir, project_id, "project.json")
            if os.path.exists(project_json):
                with open(project_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("name", project_id)
        except:
            pass
            
        return project_id

    def create_new_scene(self):
        dialog = AddSceneDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            # Save Image
            final_img_path = ""
            if data["image_path"]:
                import shutil
                import uuid
                ext = os.path.splitext(data["image_path"])[1]
                new_filename = f"scene_{uuid.uuid4()}{ext}"
                final_img_path = os.path.join(self.storage_path, new_filename)
                shutil.copy2(data["image_path"], final_img_path)
            
            import uuid
            project_id = os.path.basename(self.project_dir) if self.project_dir else ""
            new_scene = Scene(
                id=str(uuid.uuid4()),
                name=data["name"],
                description=data["description"],
                time_of_day=data["time_of_day"],
                weather=data["weather"],
                image_path=final_img_path,
                project_id=project_id
            )
            new_scene.save(self.storage_path)
            self.load_scenes()

    def extract_from_script(self):
        if not self.project_dir:
            QMessageBox.warning(self, "提示", "请先打开一个项目。")
            return

        project_id = os.path.basename(self.project_dir)
        scenes_found = [] # List of (location, time)
        
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
                
                # Iterate all episodes to find scenes
                for ep in episodes:
                    script_path = os.path.join(self.project_dir, "scripts", f"episode_{ep['id']}.json")
                    if os.path.exists(script_path):
                        try:
                            with open(script_path, 'r', encoding='utf-8') as f:
                                script = Script.from_json(f.read())
                                for scene in script.scenes:
                                    if scene.location:
                                        scenes_found.append((scene.location, scene.time))
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
                        if scene.location:
                            scenes_found.append((scene.location, scene.time))
            except Exception as e:
                QMessageBox.warning(self, "错误", f"读取剧本失败: {e}")
                return

        if not scenes_found:
            QMessageBox.information(self, "提示", "剧本中未找到场景。")
            return

        # Deduplicate based on location name
        unique_scenes = {}
        for loc, time in scenes_found:
            if loc not in unique_scenes:
                unique_scenes[loc] = time
        
        # Convert back to list
        scene_list = [(loc, time) for loc, time in unique_scenes.items()]
        scene_list.sort(key=lambda x: x[0])

        # Get existing scene names
        existing_names = set(s.name for s in self.scenes)

        # Show dialog
        dialog = SceneExtractionDialog(scene_list, existing_names, self)
        if dialog.exec():
            selected_scenes = dialog.get_selected_scenes()
            for loc, time in selected_scenes:
                # Create new scene
                new_scene = Scene(
                    id=str(uuid.uuid4()),
                    name=loc,
                    description=f"Location: {loc}, Time: {time}",
                    time_of_day=time,
                    weather="",
                    image_path="",
                    project_id=project_id
                )
                new_scene.save(self.storage_path)
            
            if selected_scenes:
                self.load_scenes()
                QMessageBox.information(self, "成功", f"已导入 {len(selected_scenes)} 个新场景。")

    def open_scene_library(self, scene_id):
        scene = next((s for s in self.scenes if s.id == scene_id), None)
        if not scene: return
        
        dialog = SceneLibraryDialog(scene, self)
        if dialog.exec():
            scene.save(self.storage_path)
            self.load_scenes()

    def edit_scene(self, scene_id):
        # Redirect to library for editing
        self.open_scene_library(scene_id)

    def delete_scene(self, scene_id):
        scene = next((s for s in self.scenes if s.id == scene_id), None)
        if scene:
            reply = QMessageBox.question(self, "确认删除", f"确定要删除场景 '{scene.name}' 吗？", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Delete file by searching for ID
                    found = False
                    for f in os.listdir(self.storage_path):
                        if f.endswith(".json") and scene.id in f:
                            os.remove(os.path.join(self.storage_path, f))
                            found = True
                            break
                    
                    # Remove image
                    if scene.image_path and os.path.exists(scene.image_path):
                        try:
                            os.remove(scene.image_path)
                        except: pass

                    if found:
                        self.load_scenes()
                    else:
                        # If file not found but object exists, just reload to clear it
                        self.load_scenes()
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"删除失败: {e}")
