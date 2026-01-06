from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QScrollArea, 
                             QGridLayout, QFrame, QFileDialog, QMessageBox, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import os
import shutil
import uuid
import json
from core.scene.scene_model import Scene
from ui.scene_card import SceneCardWidget

class AddSceneDialog(QDialog):
    def __init__(self, parent=None, scene=None):
        super().__init__(parent)
        self.setWindowTitle("添加/编辑场景")
        self.resize(500, 600)
        self.image_path = None
        self.scene = scene
        self.init_ui()
        
        if self.scene:
            self.load_scene_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Image Selection
        self.img_lbl = QLabel("点击选择参考图")
        self.img_lbl.setFixedSize(400, 225) # 16:9 aspect ratio roughly
        self.img_lbl.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                color: #bdc3c7;
                border: 2px dashed #7f8c8d;
                border-radius: 10px;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #f1c40f;
                color: #f1c40f;
            }
        """)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.mousePressEvent = self.select_image
        
        img_container = QHBoxLayout()
        img_container.addStretch()
        img_container.addWidget(self.img_lbl)
        img_container.addStretch()
        layout.addLayout(img_container)
        
        # Form
        form_layout = QVBoxLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("场景名称 (如: 咖啡馆内景)")
        self.name_edit.setStyleSheet("padding: 10px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        row_env = QHBoxLayout()
        self.time_combo = QComboBox()
        self.time_combo.addItems(["白天", "夜晚", "黄昏", "清晨", "室内灯光"])
        self.time_combo.setStyleSheet("padding: 8px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["晴朗", "阴天", "雨天", "雪天", "雾天", "室内无天气"])
        self.weather_combo.setStyleSheet("padding: 8px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        row_env.addWidget(QLabel("时间:"))
        row_env.addWidget(self.time_combo)
        row_env.addWidget(QLabel("天气:"))
        row_env.addWidget(self.weather_combo)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("场景详细描述 (视觉外观、氛围、关键物体等)...")
        self.desc_edit.setStyleSheet("padding: 10px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        self.desc_edit.setFixedHeight(100)
        
        form_layout.addWidget(QLabel("场景名称"))
        form_layout.addWidget(self.name_edit)
        form_layout.addLayout(row_env)
        form_layout.addWidget(QLabel("详细描述"))
        form_layout.addWidget(self.desc_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("padding: 10px; background-color: #7f8c8d; color: white; border-radius: 5px;")
        
        save_btn = QPushButton("保存场景")
        save_btn.clicked.connect(self.save_scene)
        save_btn.setStyleSheet("padding: 10px; background-color: #f1c40f; color: #2c3e50; font-weight: bold; border-radius: 5px;")
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def load_scene_data(self):
        self.name_edit.setText(self.scene.name)
        self.desc_edit.setText(self.scene.description)
        
        idx = self.time_combo.findText(self.scene.time_of_day)
        if idx >= 0: self.time_combo.setCurrentIndex(idx)
        
        idx = self.weather_combo.findText(self.scene.weather)
        if idx >= 0: self.weather_combo.setCurrentIndex(idx)
        
        if self.scene.image_path and os.path.exists(self.scene.image_path):
            self.image_path = self.scene.image_path
            self.update_image_preview()

    def select_image(self, event):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择参考图", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if file_path:
            self.image_path = file_path
            self.update_image_preview()

    def update_image_preview(self):
        if self.image_path:
            pixmap = QPixmap(self.image_path)
            self.img_lbl.setPixmap(pixmap.scaled(
                self.img_lbl.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
            self.img_lbl.setText("")

    def save_scene(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入场景名称")
            return
            
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "time_of_day": self.time_combo.currentText(),
            "weather": self.weather_combo.currentText(),
            "image_path": self.image_path
        }

class SceneSelectorDialog(QDialog):
    scene_selected = pyqtSignal(object) # Scene object

    def __init__(self, storage_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("场景库")
        self.resize(900, 600)
        self.storage_path = storage_path
        self.scenes = []
        self.init_ui()
        self.load_scenes()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("选择场景")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        
        add_btn = QPushButton("+ 新建场景")
        add_btn.clicked.connect(self.create_new_scene)
        add_btn.setStyleSheet("background-color: #f1c40f; color: #2c3e50; padding: 5px 15px; border-radius: 3px; font-weight: bold;")
        header.addWidget(add_btn)
        
        layout.addLayout(header)
        
        # Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(20)
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

    def load_scenes(self):
        # Clear
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        self.scenes = []
        if os.path.exists(self.storage_path):
            for filename in os.listdir(self.storage_path):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.storage_path, filename), 'r', encoding='utf-8') as f:
                            scene = Scene.from_json(f.read())
                            self.scenes.append(scene)
                    except: pass
        
        # Populate Grid
        row, col = 0, 0
        for scene in self.scenes:
            card = SceneCardWidget(scene)
            card.clicked.connect(self.on_card_clicked)
            card.edited.connect(self.edit_scene)
            card.deleted.connect(self.delete_scene)
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col > 3:
                col = 0
                row += 1

    def create_new_scene(self):
        dialog = AddSceneDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            
            # Save Image
            final_img_path = ""
            if data["image_path"]:
                ext = os.path.splitext(data["image_path"])[1]
                new_filename = f"scene_{uuid.uuid4()}{ext}"
                final_img_path = os.path.join(self.storage_path, new_filename)
                shutil.copy2(data["image_path"], final_img_path)
            
            new_scene = Scene(
                id=str(uuid.uuid4()),
                name=data["name"],
                description=data["description"],
                time_of_day=data["time_of_day"],
                weather=data["weather"],
                image_path=final_img_path
            )
            new_scene.save(self.storage_path)
            self.load_scenes()

    def edit_scene(self, scene_id):
        scene = next((s for s in self.scenes if s.id == scene_id), None)
        if not scene: return
        
        dialog = AddSceneDialog(self, scene)
        if dialog.exec():
            data = dialog.get_data()
            
            # Update Image if changed
            if data["image_path"] != scene.image_path:
                if data["image_path"]:
                    ext = os.path.splitext(data["image_path"])[1]
                    new_filename = f"scene_{uuid.uuid4()}{ext}"
                    final_img_path = os.path.join(self.storage_path, new_filename)
                    shutil.copy2(data["image_path"], final_img_path)
                    scene.image_path = final_img_path
            
            scene.name = data["name"]
            scene.description = data["description"]
            scene.time_of_day = data["time_of_day"]
            scene.weather = data["weather"]
            
            scene.save(self.storage_path)
            self.load_scenes()

    def delete_scene(self, scene_id):
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个场景吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            scene = next((s for s in self.scenes if s.id == scene_id), None)
            if scene:
                # Remove json
                json_path = os.path.join(self.storage_path, f"{scene.name}_{scene.id}.json")
                if os.path.exists(json_path):
                    os.remove(json_path)
                # Remove image
                if scene.image_path and os.path.exists(scene.image_path):
                    try:
                        os.remove(scene.image_path)
                    except: pass
                
                self.load_scenes()

    def on_card_clicked(self, scene_id):
        scene = next((s for s in self.scenes if s.id == scene_id), None)
        if scene:
            self.scene_selected.emit(scene)
            self.accept()

class AddSceneImageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新场景图")
        self.resize(400, 500)
        self.image_path = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Image Selection
        self.img_lbl = QLabel("点击选择图片")
        self.img_lbl.setFixedSize(340, 190)
        self.img_lbl.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                color: #bdc3c7;
                border: 2px dashed #7f8c8d;
                border-radius: 10px;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #f1c40f;
                color: #f1c40f;
            }
        """)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.mousePressEvent = self.select_image
        
        img_container = QHBoxLayout()
        img_container.addStretch()
        img_container.addWidget(self.img_lbl)
        img_container.addStretch()
        layout.addLayout(img_container)
        
        # Form
        form_layout = QVBoxLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("场景名称")
        self.name_edit.setStyleSheet("padding: 10px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        row_env = QHBoxLayout()
        self.time_combo = QComboBox()
        self.time_combo.addItems(["白天", "夜晚", "黄昏", "清晨", "室内灯光"])
        self.time_combo.setStyleSheet("padding: 8px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["晴朗", "阴天", "雨天", "雪天", "雾天", "室内无天气"])
        self.weather_combo.setStyleSheet("padding: 8px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        row_env.addWidget(QLabel("时间:"))
        row_env.addWidget(self.time_combo)
        row_env.addWidget(QLabel("天气:"))
        row_env.addWidget(self.weather_combo)
        
        form_layout.addWidget(self.name_edit)
        form_layout.addLayout(row_env)
        
        layout.addLayout(form_layout)
        layout.addStretch(1)  # Add stretch to push buttons to bottom
        
        # Buttons - Fixed at bottom
        btn_container = QWidget()
        btn_container.setFixedHeight(50)
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("padding: 10px; background-color: #7f8c8d; color: white; border-radius: 5px;")
        
        ok_btn = QPushButton("确定添加")
        ok_btn.clicked.connect(self.validate_and_accept)
        ok_btn.setStyleSheet("padding: 10px; background-color: #f1c40f; color: #2c3e50; font-weight: bold; border-radius: 5px;")
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addWidget(btn_container)
        
        self.setStyleSheet("background-color: #1e272e; color: white;")

    def select_image(self, event):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_path = path
            pix = QPixmap(path)
            self.img_lbl.setPixmap(pix.scaled(340, 190, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            
            if not self.name_edit.text():
                base_name = os.path.splitext(os.path.basename(path))[0]
                self.name_edit.setText(base_name)

    def validate_and_accept(self):
        if not self.image_path:
            QMessageBox.warning(self, "提示", "请选择一张图片")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入场景名称")
            return
        self.accept()

    def get_data(self):
        return {
            "image_path": self.image_path,
            "name": self.name_edit.text().strip(),
            "time_of_day": self.time_combo.currentText(),
            "weather": self.weather_combo.currentText()
        }

class ImageCard(QFrame):
    clicked = pyqtSignal(str) # Emits path or "CREATE"
    deleted = pyqtSignal(str) # Emits path

    def __init__(self, img_path, meta=None, is_create=False, parent=None):
        super().__init__(parent)
        self.img_path = img_path
        self.meta = meta or {}
        self.is_create = is_create
        self.init_ui()

    def init_ui(self):
        self.setFixedSize(240, 200) # Wider for scenes
        self.setStyleSheet("""
            ImageCard { background-color: #2c3e50; border-radius: 8px; }
            ImageCard:hover { background-color: #34495e; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        if self.is_create:
            lbl = QLabel("+")
            lbl.setStyleSheet("font-size: 60px; color: #f1c40f; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
            
            txt = QLabel("导入新场景")
            txt.setStyleSheet("color: #f1c40f; font-weight: bold; background: transparent; font-size: 16px; margin-bottom: 20px;")
            txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(txt)
        else:
            # Image
            img_lbl = QLabel()
            img_lbl.setStyleSheet("background-color: #7f8c8d; border-top-left-radius: 8px; border-top-right-radius: 8px;")
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self.img_path and os.path.exists(self.img_path):
                pix = QPixmap(self.img_path)
                img_lbl.setPixmap(pix.scaled(240, 135, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
            else:
                img_lbl.setText("Image Not Found")
            layout.addWidget(img_lbl, 1)
            
            # Info Area
            info_bg = QWidget()
            info_bg.setStyleSheet("background-color: rgba(0,0,0,0.6); border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
            info_layout = QVBoxLayout(info_bg)
            info_layout.setContentsMargins(10, 5, 10, 5)
            info_layout.setSpacing(2)
            
            # Name
            name = self.meta.get("name", "未命名")
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("color: white; font-weight: bold; font-size: 13px; background: transparent;")
            info_layout.addWidget(lbl_name)
            
            # Tags
            tags = f"{self.meta.get('time_of_day','')} {self.meta.get('weather','')}"
            lbl_tags = QLabel(tags)
            lbl_tags.setStyleSheet("color: #bdc3c7; font-size: 11px; background: transparent;")
            info_layout.addWidget(lbl_tags)
            
            # Bottom Row (Source + Delete)
            row_bottom = QHBoxLayout()
            lbl_source = QLabel("本地导入")
            lbl_source.setStyleSheet("color: #95a5a6; font-size: 10px; background: transparent;")
            row_bottom.addWidget(lbl_source)
            row_bottom.addStretch()
            
            del_btn = QPushButton("×")
            del_btn.setFixedSize(20, 20)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton { color: #e74c3c; background: transparent; border: none; font-weight: bold; font-size: 16px; }
                QPushButton:hover { color: #c0392b; background: rgba(255,255,255,0.1); border-radius: 10px; }
            """)
            del_btn.clicked.connect(lambda: self.deleted.emit(self.img_path))
            row_bottom.addWidget(del_btn)
            
            info_layout.addLayout(row_bottom)
            layout.addWidget(info_bg, 0)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.img_path if not self.is_create else "CREATE")
        super().mousePressEvent(event)

class SceneLibraryDialog(QDialog):
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setWindowTitle("场景库")
        self.resize(1100, 750)
        self.scene = scene
        self.selected_image = scene.image_path
        self.library_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resources", "scenes", "library")
        self.meta_file = os.path.join(self.library_dir, "metadata.json")
        self.metadata = self.load_metadata()
        self.init_ui()

    def load_metadata(self):
        if os.path.exists(self.meta_file):
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_metadata(self):
        if not os.path.exists(self.library_dir):
            os.makedirs(self.library_dir)
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=4, ensure_ascii=False)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Left Sidebar (Scene Info) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("background-color: #2c3e50; color: white; border-right: 1px solid #34495e;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(15)

        # Preview
        self.preview_lbl = QLabel()
        self.preview_lbl.setFixedSize(260, 146) # 16:9
        self.preview_lbl.setStyleSheet("""
            QLabel {
                background-color: #34495e; 
                border-radius: 10px; 
                border: 2px dashed #7f8c8d;
            }
        """)
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_preview()
        sidebar_layout.addWidget(self.preview_lbl)
        
        sidebar_layout.addWidget(QLabel("请设置场景信息"))

        # Form Fields
        sidebar_layout.addWidget(QLabel("场景名"))
        self.name_edit = QLineEdit(self.scene.name)
        self.name_edit.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        sidebar_layout.addWidget(self.name_edit)

        sidebar_layout.addWidget(QLabel("场景描述"))
        self.desc_edit = QTextEdit(self.scene.description)
        self.desc_edit.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        self.desc_edit.setFixedHeight(100)
        sidebar_layout.addWidget(self.desc_edit)

        row_env = QHBoxLayout()
        
        time_layout = QVBoxLayout()
        time_layout.addWidget(QLabel("时间"))
        self.time_combo = QComboBox()
        self.time_combo.addItems(["白天", "夜晚", "黄昏", "清晨", "室内灯光"])
        self.time_combo.setCurrentText(self.scene.time_of_day if self.scene.time_of_day else "白天")
        self.time_combo.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        time_layout.addWidget(self.time_combo)
        
        weather_layout = QVBoxLayout()
        weather_layout.addWidget(QLabel("天气"))
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["晴朗", "阴天", "雨天", "雪天", "雾天", "室内无天气"])
        self.weather_combo.setCurrentText(self.scene.weather if self.scene.weather else "晴朗")
        self.weather_combo.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        weather_layout.addWidget(self.weather_combo)

        row_env.addLayout(time_layout)
        row_env.addLayout(weather_layout)
        sidebar_layout.addLayout(row_env)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # --- Right Content (Library) ---
        content = QWidget()
        content.setStyleSheet("background-color: #1e272e;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("场景库")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("background: transparent; color: white; font-size: 20px; border: none;")
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        content_layout.addLayout(header_layout)

        # Filters
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: #2c3e50; border-radius: 5px;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 5, 10, 5)
        
        filter_layout.addWidget(QLabel("筛选:"))
        
        self.filter_time = QComboBox()
        self.filter_time.addItem("全部时间")
        self.filter_time.addItems(["白天", "夜晚", "黄昏", "清晨", "室内灯光"])
        self.filter_time.currentTextChanged.connect(self.apply_filters)
        
        self.filter_weather = QComboBox()
        self.filter_weather.addItem("全部天气")
        self.filter_weather.addItems(["晴朗", "阴天", "雨天", "雪天", "雾天", "室内无天气"])
        self.filter_weather.currentTextChanged.connect(self.apply_filters)
        
        for combo in [self.filter_time, self.filter_weather]:
            combo.setStyleSheet("background-color: #34495e; color: white; border: none; padding: 5px; border-radius: 3px;")
            filter_layout.addWidget(combo)
            
        filter_layout.addStretch()
        content_layout.addWidget(filter_frame)

        # Grid - Add with stretch to allow scrolling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.load_library_images()
                
        scroll.setWidget(self.grid_widget)
        content_layout.addWidget(scroll, 1)  # Add stretch factor to allow resizing

        # Footer - Fixed at bottom with separator
        footer_separator = QFrame()
        footer_separator.setFrameShape(QFrame.Shape.HLine)
        footer_separator.setStyleSheet("background-color: #34495e;")
        footer_separator.setFixedHeight(1)
        content_layout.addWidget(footer_separator)
        
        footer_container = QWidget()
        footer_container.setStyleSheet("background-color: #1e272e;")
        footer_container.setFixedHeight(60)  # Fixed height to ensure visibility
        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(20, 10, 20, 10)
        footer_layout.addStretch()
        confirm_btn = QPushButton("确定")
        confirm_btn.setFixedSize(120, 40)
        confirm_btn.setStyleSheet("background-color: #f1c40f; color: #2c3e50; font-weight: bold; border-radius: 5px; font-size: 16px;")
        confirm_btn.clicked.connect(self.accept_changes)
        footer_layout.addWidget(confirm_btn)
        footer_layout.addStretch()
        
        content_layout.addWidget(footer_container, 0)  # No stretch, fixed at bottom
        main_layout.addWidget(content)

    def load_library_images(self, filters=None):
        # Clear grid
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)

        # Add "Create New" Card
        create_card = ImageCard(None, is_create=True)
        create_card.clicked.connect(self.handle_card_click)
        self.grid_layout.addWidget(create_card, 0, 0)
        
        if not os.path.exists(self.library_dir):
            os.makedirs(self.library_dir)
            
        images = []
        for f in os.listdir(self.library_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                images.append(os.path.join(self.library_dir, f))
        
        # Filter logic
        filtered_images = []
        for img_path in images:
            filename = os.path.basename(img_path)
            meta = self.metadata.get(filename, {})
            
            if filters:
                if filters.get('time') and filters['time'] != "全部时间" and meta.get('time_of_day') != filters['time']:
                    continue
                if filters.get('weather') and filters['weather'] != "全部天气" and meta.get('weather') != filters['weather']:
                    continue
            
            filtered_images.append((img_path, meta))

        row, col = 0, 1
        for img_path, meta in filtered_images:
            card = ImageCard(img_path, meta=meta)
            card.clicked.connect(self.handle_card_click)
            card.deleted.connect(self.delete_image)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def apply_filters(self):
        filters = {
            'time': self.filter_time.currentText(),
            'weather': self.filter_weather.currentText()
        }
        self.load_library_images(filters)

    def handle_card_click(self, path):
        if path == "CREATE":
            self.import_new_image()
        else:
            self.selected_image = path
            self.update_preview()
            
            # Auto-fill sidebar info from metadata if available
            filename = os.path.basename(path)
            meta = self.metadata.get(filename, {})
            if meta:
                if meta.get('name'): self.name_edit.setText(meta['name'])
                if meta.get('time_of_day'): self.time_combo.setCurrentText(meta['time_of_day'])
                if meta.get('weather'): self.weather_combo.setCurrentText(meta['weather'])

    def import_new_image(self):
        dialog = AddSceneImageDialog(self)
        
        # Pre-fill name if available
        if not dialog.name_edit.text() and self.name_edit.text():
            dialog.name_edit.setText(self.name_edit.text())
            
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            src_path = data['image_path']
            
            try:
                if not os.path.exists(self.library_dir):
                    os.makedirs(self.library_dir)
                
                filename = f"{uuid.uuid4()}{os.path.splitext(src_path)[1]}"
                dest_path = os.path.join(self.library_dir, filename)
                shutil.copy2(src_path, dest_path)
                
                # Save metadata
                self.metadata[filename] = {
                    "name": data['name'],
                    "time_of_day": data['time_of_day'],
                    "weather": data['weather']
                }
                self.save_metadata()
                
                self.load_library_images()
                self.apply_filters() 
                
                # Auto-select the new image
                self.selected_image = dest_path
                self.update_preview()
                
                # Auto-fill sidebar if empty
                if not self.name_edit.text(): self.name_edit.setText(data['name'])
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入图片失败: {e}")

    def delete_image(self, path):
        reply = QMessageBox.question(self, "确认删除", "确定要删除这张图片吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                filename = os.path.basename(path)
                if filename in self.metadata:
                    del self.metadata[filename]
                    self.save_metadata()
                    
                self.apply_filters() 
                
                if self.selected_image == path:
                    self.selected_image = None
                    self.update_preview()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")

    def update_preview(self):
        if self.selected_image and os.path.exists(self.selected_image):
            pix = QPixmap(self.selected_image)
            self.preview_lbl.setPixmap(pix.scaled(260, 146, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        else:
            self.preview_lbl.setText("请设置场景图片")

    def accept_changes(self):
        self.scene.name = self.name_edit.text()
        self.scene.description = self.desc_edit.toPlainText()
        self.scene.time_of_day = self.time_combo.currentText()
        self.scene.weather = self.weather_combo.currentText()
        
        if self.selected_image:
            self.scene.image_path = self.selected_image
        self.accept()
