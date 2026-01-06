from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QScrollArea, 
                             QGridLayout, QFrame, QTabWidget, QFileDialog, QMenu, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QIcon, QAction
import os
import shutil
import uuid
import json
from ai_engine.audio.tts_client import TTSClient

# Voice Presets Mapping: Display Name -> Prompt
VOICE_PRESETS = {
    "低沉英伦男声": "Deep, resonant male voice with a British accent",
    "神秘温柔女声": "Soft, whispering female voice, mysterious tone",
    "活力少年音": "Energetic young male voice, fast-paced",
    "慈祥老奶奶": "Elderly woman's voice, shaky but kind",
    "威严大叔音": "Gruff, gravelly male voice, authoritative",
    "元气少女音": "Cheerful teenage girl voice, high pitch",
    "机械电子音": "Robotic, monotone voice, synthetic texture",
    "专业旁白音": "Smooth, professional narrator voice, neutral",
    "愤怒咆哮男": "Angry, shouting male voice, aggressive",
    "悲伤哭腔女": "Tearful, emotional female voice, sad",
    "冷嘲热讽男": "Sarcastic, cynical male voice",
    "温暖治愈女": "Warm, motherly voice, comforting",
    "阴险反派男": "Villainous, cold male voice, calculating",
    "正义御姐音": "Heroic, inspiring female voice, strong",
    "天真童声": "Childlike, innocent voice, curious",
    "沙哑烟嗓男": "Raspy, smoky male voice, blues style",
    "清冷公子音": "Cool, detached young male voice, elegant",
    "性感御姐音": "Sultry, husky female voice, alluring",
    "热血动漫男": "Passionate, shouting anime protagonist voice",
    "恐怖幽灵音": "Eerie, echoing ghostly voice, frightening",
    "新闻主播男": "Professional male news anchor, clear and authoritative",
    "新闻主播女": "Professional female news anchor, clear and articulate",
    "讲故事男声": "Warm, engaging male storyteller voice",
    "讲故事女声": "Gentle, captivating female storyteller voice",
    "卡通尖细音": "High-pitched, squeaky cartoon character voice",
    "卡通低沉音": "Deep, goofy cartoon character voice",
    "耳语低语": "Soft, intimate whispering voice",
    "大声喊叫": "Loud, shouting voice, high energy",
    "开心笑意": "Happy, cheerful voice with laughter in tone",
    "悲伤哭泣": "Sad, tearful voice, full of emotion",
    "恐惧颤抖": "Fearful, trembling voice, scared",
    "愤怒咆哮": "Angry, shouting voice, aggressive tone"
}

class AddCharacterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新形象")
        self.resize(400, 500)
        self.image_path = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Image Selection
        self.img_lbl = QLabel("点击选择图片")
        self.img_lbl.setFixedSize(200, 200)
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
        self.name_edit.setPlaceholderText("形象名称 (如: 校园男主)")
        self.name_edit.setStyleSheet("padding: 10px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        row_gender_age = QHBoxLayout()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男性", "女性", "未知"])
        self.gender_combo.setStyleSheet("padding: 8px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        self.age_combo = QComboBox()
        self.age_combo.addItems(["青年", "少年", "中年", "老年", "儿童"])
        self.age_combo.setStyleSheet("padding: 8px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        row_gender_age.addWidget(QLabel("性别:"))
        row_gender_age.addWidget(self.gender_combo)
        row_gender_age.addWidget(QLabel("年龄:"))
        row_gender_age.addWidget(self.age_combo)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["真人", "动漫", "3D", "插画", "动物", "其他"])
        self.type_combo.setStyleSheet("padding: 8px; background-color: #2c3e50; color: white; border: 1px solid #5d6d7e; border-radius: 5px;")
        
        form_layout.addWidget(self.name_edit)
        form_layout.addLayout(row_gender_age)
        form_layout.addWidget(QLabel("类型:"))
        form_layout.addWidget(self.type_combo)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("padding: 10px; background-color: #7f8c8d; color: white; border-radius: 5px;")
        
        ok_btn = QPushButton("确定添加")
        ok_btn.clicked.connect(self.validate_and_accept)
        ok_btn.setStyleSheet("padding: 10px; background-color: #f1c40f; color: #2c3e50; font-weight: bold; border-radius: 5px;")
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("background-color: #1e272e; color: white;")

    def select_image(self, event):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_path = path
            pix = QPixmap(path)
            self.img_lbl.setPixmap(pix.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            
            # Auto-fill name if empty
            if not self.name_edit.text():
                base_name = os.path.splitext(os.path.basename(path))[0]
                self.name_edit.setText(base_name)

    def validate_and_accept(self):
        if not self.image_path:
            QMessageBox.warning(self, "提示", "请选择一张图片")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入形象名称")
            return
        self.accept()

    def get_data(self):
        return {
            "image_path": self.image_path,
            "name": self.name_edit.text().strip(),
            "gender": self.gender_combo.currentText(),
            "age": self.age_combo.currentText(),
            "type": self.type_combo.currentText()
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
        self.setFixedSize(180, 260)
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
            
            txt = QLabel("导入新形象")
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
                img_lbl.setPixmap(pix.scaled(180, 200, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
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
            tags = f"{self.meta.get('gender','')} {self.meta.get('age','')}"
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

class CharacterLibraryDialog(QDialog):
    def __init__(self, character, parent=None):
        super().__init__(parent)
        self.setWindowTitle("形象库")
        self.resize(1100, 750)
        self.character = character
        self.selected_avatar = character.avatar_path
        self.library_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resources", "characters", "library")
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

        # --- Left Sidebar (Character Info) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("background-color: #2c3e50; color: white; border-right: 1px solid #34495e;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(15)

        # Avatar Preview
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(260, 340)
        self.avatar_lbl.setStyleSheet("background-color: #34495e; border-radius: 10px; border: 2px dashed #7f8c8d;")
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_avatar_preview()
        sidebar_layout.addWidget(self.avatar_lbl)
        
        sidebar_layout.addWidget(QLabel("请设置角色形象"))

        # Form Fields
        sidebar_layout.addWidget(QLabel("角色名"))
        self.name_edit = QLineEdit(self.character.name)
        self.name_edit.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        sidebar_layout.addWidget(self.name_edit)

        sidebar_layout.addWidget(QLabel("音色描述 (用于视频生成)"))
        
        # Voice Description with Presets
        self.voice_desc_combo = QComboBox()
        self.voice_desc_combo.setEditable(True)
        
        # Add presets (Display Name)
        self.voice_desc_combo.addItems(list(VOICE_PRESETS.keys()))
        
        # Set current value
        # If current value is in values, set key. If in keys, set key. Else set text.
        current_desc = getattr(self.character, 'voice_description', '')
        
        # Reverse lookup to find display name if prompt is stored
        display_name = next((k for k, v in VOICE_PRESETS.items() if v == current_desc), None)
        
        if display_name:
            self.voice_desc_combo.setCurrentText(display_name)
        elif current_desc:
            self.voice_desc_combo.setCurrentText(current_desc)
        
        self.voice_desc_combo.lineEdit().setPlaceholderText("选择预设或输入英文描述")
        self.voice_desc_combo.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        sidebar_layout.addWidget(self.voice_desc_combo)

        # Language Selection
        sidebar_layout.addWidget(QLabel("发音语言 (Language)"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Chinese", "Japanese", "Korean", "French", "German", "Spanish"])
        current_lang = getattr(self.character, 'language', 'English')
        self.language_combo.setCurrentText(current_lang)
        self.language_combo.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        sidebar_layout.addWidget(self.language_combo)

        row_gender_age = QHBoxLayout()
        
        gender_layout = QVBoxLayout()
        gender_layout.addWidget(QLabel("性别"))
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男性", "女性", "未知"])
        self.gender_combo.setCurrentText(self.character.gender if self.character.gender else "男性")
        self.gender_combo.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        gender_layout.addWidget(self.gender_combo)
        
        age_layout = QVBoxLayout()
        age_layout.addWidget(QLabel("年龄"))
        self.age_combo = QComboBox()
        self.age_combo.addItems(["青年", "少年", "中年", "老年"])
        self.age_combo.setCurrentText(self.character.age if self.character.age else "青年")
        self.age_combo.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px;")
        age_layout.addWidget(self.age_combo)

        row_gender_age.addLayout(gender_layout)
        row_gender_age.addLayout(age_layout)
        sidebar_layout.addLayout(row_gender_age)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # --- Right Content (Library) ---
        content = QWidget()
        content.setStyleSheet("background-color: #1e272e;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("形象库")
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
        
        self.filter_gender = QComboBox()
        self.filter_gender.addItem("全部性别")
        self.filter_gender.addItems(["男性", "女性", "未知"])
        self.filter_gender.currentTextChanged.connect(self.apply_filters)
        
        self.filter_age = QComboBox()
        self.filter_age.addItem("全部年龄")
        self.filter_age.addItems(["青年", "少年", "中年", "老年", "儿童"])
        self.filter_age.currentTextChanged.connect(self.apply_filters)
        
        self.filter_type = QComboBox()
        self.filter_type.addItem("全部类型")
        self.filter_type.addItems(["真人", "动漫", "3D", "插画", "动物", "其他"])
        self.filter_type.currentTextChanged.connect(self.apply_filters)
        
        for combo in [self.filter_gender, self.filter_age, self.filter_type]:
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
                if filters.get('gender') and filters['gender'] != "全部性别" and meta.get('gender') != filters['gender']:
                    continue
                if filters.get('age') and filters['age'] != "全部年龄" and meta.get('age') != filters['age']:
                    continue
                if filters.get('type') and filters['type'] != "全部类型" and meta.get('type') != filters['type']:
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
            'gender': self.filter_gender.currentText(),
            'age': self.filter_age.currentText(),
            'type': self.filter_type.currentText()
        }
        self.load_library_images(filters)

    def handle_card_click(self, path):
        if path == "CREATE":
            self.import_new_image()
        else:
            self.selected_avatar = path
            self.update_avatar_preview()
            
            # Auto-fill sidebar info from metadata if available
            filename = os.path.basename(path)
            meta = self.metadata.get(filename, {})
            if meta:
                if meta.get('name'): self.name_edit.setText(meta['name'])
                if meta.get('gender'): self.gender_combo.setCurrentText(meta['gender'])
                if meta.get('age'): self.age_combo.setCurrentText(meta['age'])

    def import_new_image(self):
        dialog = AddCharacterDialog(self)
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
                    "gender": data['gender'],
                    "age": data['age'],
                    "type": data['type']
                }
                self.save_metadata()
                
                self.load_library_images()
                self.apply_filters() # Re-apply filters to show new image if it matches
                
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
                    
                self.apply_filters() # Reload grid
                
                if self.selected_avatar == path:
                    self.selected_avatar = None
                    self.update_avatar_preview()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")

    def update_avatar_preview(self):
        if self.selected_avatar and os.path.exists(self.selected_avatar):
            pix = QPixmap(self.selected_avatar)
            self.avatar_lbl.setPixmap(pix.scaled(260, 340, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        else:
            self.avatar_lbl.setText("请设置角色形象")

    def accept_changes(self):
        self.character.name = self.name_edit.text()
        
        # Map display name back to prompt if possible
        display_text = self.voice_desc_combo.currentText()
        prompt_text = VOICE_PRESETS.get(display_text, display_text)
        
        self.character.voice_description = prompt_text
        self.character.language = self.language_combo.currentText()
        
        self.character.gender = self.gender_combo.currentText()
        self.character.age = self.age_combo.currentText()
        if self.selected_avatar:
            self.character.avatar_path = self.selected_avatar
        self.accept()
