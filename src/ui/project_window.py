from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QInputDialog, QMessageBox, 
                             QGroupBox, QFormLayout, QLineEdit, QDialog, QSpinBox, 
                             QTextEdit, QTabWidget, QListWidgetItem, QComboBox, QCheckBox,
                             QProgressDialog, QProgressBar, QApplication, QFileDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QTimer, QSize
import os
import json
import re
from core.project.project_manager import ProjectManager
from core.config.config_manager import ConfigManager
from core.project.series_manager import SeriesManager
from ai_engine.llm.llm_client import LLMClient
from ui.script_window import ScriptGeneratorThread
from ui.utils import show_message

VISUAL_STYLES = [
    "Cinematic (电影质感)",
    "Anime (日系动漫)",
    "3D Animation (3D动画)",
    "Oil Painting (油画风格)",
    "Watercolor (水彩风格)",
    "Cyberpunk (赛博朋克)",
    "Sketch (素描手绘)",
    "Flat Illustration (扁平插画)",
    "Realistic (写实摄影)",
    "Fantasy (奇幻史诗)",
    "Chinese Ink (中国水墨)",
    "Ghibli (吉卜力风格)",
    "Pixel Art (像素风格)",
    "Vintage (复古风格)",
    "Noir (黑色电影)",
    "Impressionism (印象派)",
    "Surrealism (超现实主义)",
    "Ukiyo-e (浮世绘)",
    "Steampunk (蒸汽朋克)",
    "Gothic (哥特风格)"
]

STYLESHEET = """
    QWidget {
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
        color: #ecf0f1;
        background-color: #313131;
    }
    QListWidget {
        background-color: #313131;
        border: 1px solid #34495e;
        border-radius: 6px;
        padding: 5px;
        color: #ecf0f1;
    }
    QListWidget::item {
        padding: 10px;
        border-bottom: 1px solid #34495e;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background-color: #2980b9;
        color: white;
    }
    QListWidget::item:hover:!selected {
        background-color: #34495e;
    }
    QPushButton {
        background-color: #2980b9;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #3498db;
    }
    QPushButton:pressed {
        background-color: #1abc9c;
    }
    QPushButton:disabled {
        background-color: #7f8c8d;
        color: #bdc3c7;
    }
    QLabel {
        color: #ecf0f1;
    }
    QTabWidget::pane {
        border: 1px solid #34495e;
        background: #313131;
        border-radius: 4px;
    }
    QTabBar::tab {
        background: #313131;
        color: #bdc3c7;
        padding: 8px 20px;
        border: 1px solid #34495e;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background: #313131;
        color: #f1c40f;
        border-bottom: 1px solid #313131;
        font-weight: bold;
    }
    QLineEdit, QTextEdit, QComboBox, QSpinBox {
        border: 1px solid #34495e;
        border-radius: 4px;
        padding: 5px;
        background: #313131;
        color: white;
    }
    QGroupBox {
        border: 1px solid #34495e;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 15px;
        font-weight: bold;
        color: #ecf0f1;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        left: 10px;
    }
"""

class EditProjectDialog(QDialog):
    def __init__(self, current_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑项目信息")
        self.setMinimumWidth(500)
        self.current_data = current_data
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.title_edit = QLineEdit(self.current_data.get("title", ""))
        layout.addRow("项目名称:", self.title_edit)
        
        # Project Type Selection
        self.type_combo = QComboBox()
        self.type_combo.addItems(["原创短剧 (Original)", "改编短剧 (Adaptation)"])
        
        # Set current selection
        current_type = self.current_data.get("type", "original")
        if current_type == "adaptation":
            self.type_combo.setCurrentIndex(1)
        else:
            self.type_combo.setCurrentIndex(0)
            
        layout.addRow("创作类型:", self.type_combo)
        
        self.genre_edit = QLineEdit(self.current_data.get("genre", ""))
        layout.addRow("故事类型:", self.genre_edit)

        # Visual Style Selection
        self.style_combo = QComboBox()
        self.style_combo.addItems(VISUAL_STYLES)
        self.style_combo.setEditable(True) # Allow custom styles
        
        current_style = self.current_data.get("visual_style", "")
        if current_style:
            index = self.style_combo.findText(current_style)
            if index >= 0:
                self.style_combo.setCurrentIndex(index)
            else:
                self.style_combo.setEditText(current_style)
        
        layout.addRow("画面风格:", self.style_combo)
        
        self.episodes_spin = QSpinBox()
        self.episodes_spin.setRange(1, 1000)
        self.episodes_spin.setValue(int(self.current_data.get("total_episodes", 100)))
        layout.addRow("总集数:", self.episodes_spin)
        
        self.characters_edit = QTextEdit(self.current_data.get("main_characters", ""))
        self.characters_edit.setMaximumHeight(80)
        layout.addRow("主要角色:", self.characters_edit)
        
        self.premise_edit = QTextEdit(self.current_data.get("premise", ""))
        self.premise_edit.setPlaceholderText("一句话故事梗概 (Logline)")
        self.premise_edit.setMaximumHeight(100)
        layout.addRow("核心梗概:", self.premise_edit)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存修改")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("background-color: #e0e0e0; color: #333;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        project_type = "original" if self.type_combo.currentIndex() == 0 else "adaptation"
        return {
            "title": self.title_edit.text(),
            "type": project_type,
            "genre": self.genre_edit.text(),
            "visual_style": self.style_combo.currentText(),
            "total_episodes": self.episodes_spin.value(),
            "main_characters": self.characters_edit.toPlainText(),
            "premise": self.premise_edit.toPlainText()
        }

class OutlineGeneratorThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_config, prompt, system_prompt=None):
        super().__init__()
        self.api_config = api_config
        self.prompt = prompt
        self.system_prompt = system_prompt

    def run(self):
        try:
            api_key = self.api_config.get("api_key")
            base_url = self.api_config.get("base_url")
            model = self.api_config.get("model")
            client = LLMClient(api_key=api_key, base_url=base_url, model=model)
            
            result = client.generate_script(self.prompt, system_prompt=self.system_prompt)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Empty response from LLM")
        except Exception as e:
            self.error.emit(str(e))

class GenerateOutlineDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("生成大纲配置")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # API Config
        self.api_combo = QComboBox()
        self.refresh_api_list()
        layout.addRow("LLM 模型:", self.api_combo)

        # Style
        self.style_edit = QLineEdit()
        self.style_edit.setPlaceholderText("例如：悬疑、幽默、快节奏")
        layout.addRow("风格基调:", self.style_edit)

        # Extra Instructions
        self.instructions_edit = QTextEdit()
        self.instructions_edit.setPlaceholderText("额外的生成要求...")
        self.instructions_edit.setMaximumHeight(100)
        layout.addRow("额外要求:", self.instructions_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("开始生成")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def refresh_api_list(self):
        self.api_combo.clear()
        configs = self.config_manager.get("api_configs", [])
        llm_configs = [c for c in configs if c.get("type") == "LLM"]
        
        default_index = 0
        for i, config in enumerate(llm_configs):
            self.api_combo.addItem(config.get("name", "Unnamed"), config)
            if config.get("is_default"):
                default_index = i
                
        if self.api_combo.count() == 0:
             self.api_combo.addItem("未配置 (使用默认)", {})
        else:
            self.api_combo.setCurrentIndex(default_index)

    def get_data(self):
        return {
            "api_config": self.api_combo.currentData(),
            "style": self.style_edit.text(),
            "instructions": self.instructions_edit.toPlainText()
        }

class GenerateScriptDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("生成剧本配置")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        # API Config
        self.api_combo = QComboBox()
        self.refresh_api_list()
        layout.addRow("LLM 模型:", self.api_combo)

        # Embedding Config
        self.embedding_combo = QComboBox()
        self.refresh_embedding_list()
        layout.addRow("Embedding 模型:", self.embedding_combo)

        # Idea
        self.idea_edit = QTextEdit()
        self.idea_edit.setPlaceholderText("本集的核心情节、冲突或关键事件...")
        self.idea_edit.setMinimumHeight(80)
        layout.addRow("本集创意:", self.idea_edit)

        # Duration
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["智能时长", "300字", "500字", "800字", "1000字+"])
        layout.addRow("预估篇幅:", self.duration_combo)

        # Style
        self.style_edit = QLineEdit()
        self.style_edit.setPlaceholderText("延续系列风格")
        layout.addRow("风格调整:", self.style_edit)

        # Context Options
        self.context_group = QGroupBox("上下文引用")
        vbox = QVBoxLayout()
        self.use_global = QCheckBox("全局故事梗概 (Global Summary)")
        self.use_global.setChecked(True)
        self.use_state = QCheckBox("角色当前状态 (Character State)")
        self.use_state.setChecked(True)
        self.use_rag = QCheckBox("向量记忆检索 (RAG)")
        self.use_rag.setChecked(True)
        
        vbox.addWidget(self.use_global)
        vbox.addWidget(self.use_state)
        vbox.addWidget(self.use_rag)
        self.context_group.setLayout(vbox)
        layout.addRow(self.context_group)

        # Continuous Generation
        self.continuous_cb = QCheckBox("连续生成直到完结 (Continuous Generation)")
        self.continuous_cb.setToolTip("勾选后，将自动根据大纲生成剩余所有集数，无需每次确认。")
        layout.addRow(self.continuous_cb)

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("开始生成")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def refresh_api_list(self):
        self.api_combo.clear()
        configs = self.config_manager.get("api_configs", [])
        llm_configs = [c for c in configs if c.get("type") == "LLM"]
        
        default_index = 0
        for i, config in enumerate(llm_configs):
            self.api_combo.addItem(config.get("name", "Unnamed"), config)
            if config.get("is_default"):
                default_index = i
                
        if self.api_combo.count() == 0:
             self.api_combo.addItem("未配置 (使用默认)", {})
        else:
            self.api_combo.setCurrentIndex(default_index)

    def refresh_embedding_list(self):
        self.embedding_combo.clear()
        configs = self.config_manager.get("api_configs", [])
        emb_configs = [c for c in configs if c.get("type") == "Embedding"]
        
        self.embedding_combo.addItem("跟随 LLM 配置", {})
        for config in emb_configs:
            self.embedding_combo.addItem(config.get("name", "Unnamed"), config)

    def get_data(self):
        return {
            "api_config": self.api_combo.currentData(),
            "embedding_config": self.embedding_combo.currentData(),
            "idea": self.idea_edit.toPlainText(),
            "duration": self.duration_combo.currentText(),
            "style": self.style_edit.text(),
            "use_global": self.use_global.isChecked(),
            "use_state": self.use_state.isChecked(),
            "use_rag": self.use_rag.isChecked(),
            "continuous": self.continuous_cb.isChecked()
        }

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建项目")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("项目名称:", self.name_edit)

        # Project Type Selection
        self.type_combo = QComboBox()
        self.type_combo.addItems(["原创短剧 (Original)", "改编短剧 (Adaptation)"])
        layout.addRow("创作类型:", self.type_combo)

        self.theme_edit = QLineEdit()
        self.theme_edit.setPlaceholderText("例如：关于爱情的传奇故事")
        layout.addRow("短剧主题:", self.theme_edit)

        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("例如：浪漫爱情故事")
        layout.addRow("故事类型:", self.genre_edit)

        # Visual Style Selection
        self.style_combo = QComboBox()
        self.style_combo.addItems(VISUAL_STYLES)
        self.style_combo.setEditable(True)
        layout.addRow("画面风格:", self.style_combo)

        self.ep_count_spin = QSpinBox()
        self.ep_count_spin.setRange(1, 1000)
        self.ep_count_spin.setValue(100)
        layout.addRow("分集数量:", self.ep_count_spin)

        self.words_spin = QSpinBox()
        self.words_spin.setRange(100, 5000)
        self.words_spin.setValue(300)
        layout.addRow("每集字数:", self.words_spin)

        self.chars_edit = QTextEdit()
        self.chars_edit.setPlaceholderText("例如：李丽丽、王大力等")
        self.chars_edit.setMaximumHeight(60)
        layout.addRow("主要角色:", self.chars_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("创建")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        project_type = "original" if self.type_combo.currentIndex() == 0 else "adaptation"
        return {
            "name": self.name_edit.text(),
            "type": project_type,
            "theme": self.theme_edit.text(),
            "genre": self.genre_edit.text(),
            "visual_style": self.style_combo.currentText(),
            "total_episodes": self.ep_count_spin.value(),
            "words_per_episode": self.words_spin.value(),
            "main_characters": self.chars_edit.toPlainText()
        }

class ScriptAdaptationThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str) # Add progress signal

    def __init__(self, api_config, source_text, style, episode_count=1, words_per_episode=500, current_episode_index=None, previous_context=None, character_list=None):
        super().__init__()
        self.api_config = api_config
        self.source_text = source_text
        self.style = style
        self.episode_count = episode_count
        self.words_per_episode = words_per_episode
        self.current_episode_index = current_episode_index # 1-based index
        self.previous_context = previous_context
        self.character_list = character_list

    def run(self):
        try:
            api_key = self.api_config.get("api_key")
            base_url = self.api_config.get("base_url")
            model = self.api_config.get("model")
            
            client = LLMClient(api_key=api_key, base_url=base_url, model=model)
            
            count_instruction = ""
            if self.current_episode_index is not None:
                # Serial Mode
                count_instruction = f"Write Episode {self.current_episode_index} of {self.episode_count}. Focus ONLY on the part of the story corresponding to this episode."
            elif self.episode_count > 1:
                # Batch Mode
                count_instruction = f"Strictly split the content into exactly {self.episode_count} distinct episodes."
            else:
                count_instruction = "Adapt into a single episode."

            context_instruction = ""
            if self.previous_context:
                context_instruction += f"\n\n[Previous Episode Context (Use this for continuity)]:\n{self.previous_context}"
            
            if self.character_list:
                context_instruction += f"\n\n[Main Characters]:\n{self.character_list}"

            prompt = f"""
            请将以下文本改编为标准的短剧剧本格式（JSON）。
            
            原文内容：
            {self.source_text}
            {context_instruction}
            
            改编要求：
            1. 风格：{self.style}
            2. {count_instruction}
            3. 每集字数大约 {self.words_per_episode} 字。
            4. 保持核心情节，但适应短剧的快节奏。
            5. 适当增加对话和冲突。
            6. 输出格式必须是JSON，包含 "episodes" 列表，每个元素包含 title, genre, scenes。
            7. 确保 JSON 格式合法，不要在中间截断。
            """
            
            system_prompt = """You are a professional screenwriter specializing in adapting novels to short drama scripts.
            Output JSON only. Do not include any explanations or markdown code blocks (like ```json).
            Structure:
            {
                "episodes": [
                    {
                        "title": "Episode Title",
                        "genre": "Genre",
                        "scenes": [
                            {
                                "scene_id": "1",
                                "location": "Location",
                                "time": "Time",
                                "description": "Visual description",
                                "dialogues": [
                                    {"role": "Name", "content": "Line", "action": "Action", "expression": "Expression"}
                                ]
                            }
                        ]
                    }
                ]
            }
            """
            
            result = client.generate_script(prompt, system_prompt=system_prompt)
            
            if result:
                # Clean up markdown
                if result.startswith("```json"):
                    result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
                self.finished.emit(result.strip())
            else:
                self.error.emit("Empty response from LLM")
        except Exception as e:
            self.error.emit(str(e))
            if result:
                # Clean up markdown
                if result.startswith("```json"):
                    result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
                self.finished.emit(result.strip())
            else:
                self.error.emit("Empty response from LLM")
        except Exception as e:
            self.error.emit(str(e))

class AdaptScriptDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("改编短剧")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # API Config
        form_layout = QFormLayout()
        self.api_combo = QComboBox()
        self.refresh_api_list()
        form_layout.addRow("LLM 模型:", self.api_combo)
        layout.addLayout(form_layout)

        # Source Text
        layout.addWidget(QLabel("原文内容 (请输入或导入小说/文本):"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此粘贴小说章节或文本内容...")
        layout.addWidget(self.text_edit)

        # Import Button
        btn_layout = QHBoxLayout()
        import_btn = QPushButton("导入文本文件")
        import_btn.clicked.connect(self.import_file)
        btn_layout.addWidget(import_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Style/Instructions
        form_layout2 = QFormLayout()
        self.style_edit = QLineEdit()
        self.style_edit.setPlaceholderText("例如：保持原著风格、增加冲突、快节奏")
        form_layout2.addRow("改编风格:", self.style_edit)
        
        self.ep_count_spin = QSpinBox()
        self.ep_count_spin.setRange(1, 100) # Increased range to 100
        self.ep_count_spin.setValue(1)
        self.ep_count_spin.setSuffix(" 集")
        form_layout2.addRow("预计生成:", self.ep_count_spin)

        self.words_spin = QSpinBox()
        self.words_spin.setRange(100, 5000)
        self.words_spin.setValue(500)
        self.words_spin.setSuffix(" 字/集")
        form_layout2.addRow("每集字数:", self.words_spin)
        
        # Continuous Generation Checkbox
        self.continuous_cb = QCheckBox("逐集生成 (适用于多集)")
        self.continuous_cb.setToolTip("勾选后，将一集一集地生成，避免超时。适用于生成超过3集的情况。")
        form_layout2.addRow("", self.continuous_cb)
        
        layout.addLayout(form_layout2)

        # Buttons
        action_layout = QHBoxLayout()
        ok_btn = QPushButton("开始改编")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(ok_btn)
        action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)

    def refresh_api_list(self):
        self.api_combo.clear()
        configs = self.config_manager.get("api_configs", [])
        llm_configs = [c for c in configs if c.get("type") == "LLM"]
        for config in llm_configs:
            self.api_combo.addItem(config.get("name", "Unnamed"), config)
        if self.api_combo.count() == 0:
             self.api_combo.addItem("未配置 (使用默认)", {})

    def import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文本文件", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.text_edit.setText(f.read())
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法读取文件: {e}")

    def get_data(self):
        return {
            "api_config": self.api_combo.currentData(),
            "source_text": self.text_edit.toPlainText(),
            "style": self.style_edit.text(),
            "episode_count": self.ep_count_spin.value(),
            "words_per_episode": self.words_spin.value(),
            "continuous": self.continuous_cb.isChecked()
        }

class EpisodeItemWidget(QWidget):
    delete_clicked = pyqtSignal(int) # Emits episode_id

    def __init__(self, text, episode_id, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.label = QLabel(text)
        self.label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setFixedWidth(60)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4d4f;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff7875;
            }
        """)
        self.delete_btn.clicked.connect(self.on_delete)
        layout.addWidget(self.delete_btn)
        
        self.episode_id = episode_id
        
        # Ensure minimum height for visibility
        self.setMinimumHeight(50)
        self.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                border-bottom: 1px solid #34495e;
                color: #ecf0f1;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #ecf0f1;
            }
        """)

    def on_delete(self):
        self.delete_clicked.emit(self.episode_id)

class ProjectWindow(QWidget):
    project_loaded = pyqtSignal(str) # Emits project path
    open_episode = pyqtSignal(str, str) # Emits (project_path, episode_id)

    def __init__(self, projects_dir):
        super().__init__()
        self.manager = ProjectManager(projects_dir)
        self.config_manager = ConfigManager()
        self.current_series_manager = None
        self.current_project_path = None
        self.current_project_type = "original" # Default to original
        self.continuous_mode = False # Initialize continuous_mode
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        self.setStyleSheet(STYLESHEET)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Left: Project List
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("我的项目")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 5px;")
        left_layout.addWidget(title_label)
        
        self.project_list = QListWidget()
        self.project_list.itemClicked.connect(self.on_project_clicked)
        self.project_list.itemDoubleClicked.connect(self.load_selected_project)
        left_layout.addWidget(self.project_list, 1)  # Stretch to fill available space
        
        # Fixed button container at bottom
        btn_container = QWidget()
        btn_container.setFixedHeight(50)
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        new_btn = QPushButton("新建项目")
        new_btn.clicked.connect(self.create_project)
        load_btn = QPushButton("加载项目")
        load_btn.clicked.connect(self.load_selected_project)
        
        btn_layout.addWidget(new_btn)
        btn_layout.addWidget(load_btn)
        left_layout.addWidget(btn_container, 0)  # No stretch, fixed at bottom
        
        # Right: Project Details
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top Actions
        action_layout = QHBoxLayout()
        
        self.gen_outline_btn = QPushButton("生成大纲")
        self.gen_outline_btn.clicked.connect(self.generate_outline)
        self.gen_outline_btn.setEnabled(False)
        
        self.gen_script_btn = QPushButton("生成剧本")
        self.gen_script_btn.clicked.connect(self.generate_next_episode_with_ai)
        self.gen_script_btn.setEnabled(False)
        
        self.adapt_script_btn = QPushButton("改编短剧")
        self.adapt_script_btn.clicked.connect(self.adapt_script)
        self.adapt_script_btn.setEnabled(False)
        
        action_layout.addWidget(self.gen_outline_btn)
        action_layout.addWidget(self.gen_script_btn)
        action_layout.addWidget(self.adapt_script_btn)
        action_layout.addStretch()
        self.right_layout.addLayout(action_layout)

        # Progress Bar Area
        self.progress_container = QWidget()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 5, 0, 5)
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.cancel_btn = QPushButton("停止")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f; 
                color: white; 
                padding: 4px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #c9302c; }
        """)
        self.cancel_btn.clicked.connect(self.cancel_generation)
        self.cancel_btn.hide()
        status_layout.addWidget(self.cancel_btn)
        
        progress_layout.addLayout(status_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate by default
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        
        self.right_layout.addWidget(self.progress_container)

        # Tabs
        self.details_tabs = QTabWidget()
        
        # Tab 1: Info
        self.info_tab = QWidget()
        info_main_layout = QVBoxLayout(self.info_tab)
        
        self.info_form_layout = QFormLayout()
        self.info_form_layout.setSpacing(15)
        self.info_form_layout.setContentsMargins(20, 20, 20, 20)
        info_main_layout.addLayout(self.info_form_layout)
        
        # Add Edit Button to Info Tab (Fixed at bottom)
        self.edit_info_btn = QPushButton("编辑信息")
        self.edit_info_btn.clicked.connect(self.edit_project_info)
        self.edit_info_btn.setEnabled(False)
        self.edit_info_btn.setFixedWidth(120)
        
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.edit_info_btn)
        btn_container.addStretch()
        info_main_layout.addLayout(btn_container)
        info_main_layout.addStretch()
        
        self.details_tabs.addTab(self.info_tab, "基本信息")
        
        # Tab 2: Outline
        self.outline_tab = QWidget()
        outline_layout = QVBoxLayout(self.outline_tab)
        self.outline_edit = QTextEdit()
        self.outline_edit.setPlaceholderText("大纲内容...")
        save_outline_btn = QPushButton("保存大纲")
        save_outline_btn.clicked.connect(self.save_outline)
        outline_layout.addWidget(self.outline_edit)
        outline_layout.addWidget(save_outline_btn)
        self.details_tabs.addTab(self.outline_tab, "大纲")
        
        # Tab 3: Episodes
        self.episodes_tab = QWidget()
        ep_layout = QVBoxLayout(self.episodes_tab)
        self.episode_list = QListWidget()
        self.episode_list.itemDoubleClicked.connect(self.on_episode_clicked)
        ep_layout.addWidget(self.episode_list)
        self.details_tabs.addTab(self.episodes_tab, "分集列表")

        self.right_layout.addWidget(self.details_tabs)

        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 3) # Give more space to details


    def on_project_clicked(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        p_type = item.data(Qt.ItemDataRole.UserRole + 1)
        self.current_project_type = p_type
        self.load_project_details(path)

    def load_project_details(self, path):
        self.current_project_path = path
        self.current_series_manager = SeriesManager(path)
        
        # Update button states based on project type
        self.update_button_states()
        
        # 1. Populate Info
        # Clear existing rows
        while self.info_form_layout.rowCount() > 0:
            self.info_form_layout.removeRow(0)
            
        data = self.current_series_manager.data
        
        def add_info_row(label_text, value_text):
            lbl = QLabel(str(value_text))
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #ecf0f1; font-size: 14px; padding: 5px;")
            self.info_form_layout.addRow(QLabel(label_text), lbl)

        add_info_row("项目名称:", data.get("title", ""))
        
        # Project Type
        p_type = data.get("type", "original")
        type_map = {"original": "原创短剧", "adaptation": "改编短剧"}
        add_info_row("创作类型:", type_map.get(p_type, "原创短剧"))
        
        add_info_row("故事类型:", data.get("genre", ""))
        add_info_row("总集数:", data.get("total_episodes", ""))
        
        # Core Premise with Markdown formatting
        premise = data.get("premise", "")
        
        # Filter out "Brief description of each episode" for the Basic Info view
        display_premise = premise
        split_markers = ["简要描述每集剧情走向", "每集剧情走向", "分集剧情", "**简要描述每集剧情走向"]
        for marker in split_markers:
            if marker in display_premise:
                display_premise = display_premise.split(marker)[0]
                # Clean up trailing asterisks or newlines if split left them
                display_premise = display_premise.strip().rstrip('*').strip()
                break
        
        formatted_premise = self.format_markdown(display_premise)
        
        premise_view = QTextEdit()
        premise_view.setReadOnly(True)
        premise_view.setMarkdown(formatted_premise)
        premise_view.setMinimumHeight(300) # Increased height
        premise_view.setMaximumHeight(600) 
        premise_view.setStyleSheet("""
            QTextEdit { 
                background-color: #2c3e50; 
                border: 1px solid #34495e; 
                border-radius: 4px; 
                padding: 10px; 
                color: #ecf0f1;
                font-size: 14px;
            }
        """)
        self.info_form_layout.addRow(QLabel("核心梗概:"), premise_view)
        
        add_info_row("主要角色:", data.get("main_characters", ""))
        
        # 2. Populate Outline
        # Use the full premise/outline here
        formatted_premise = self.format_markdown(data.get("premise", ""))
        self.outline_edit.setMarkdown(formatted_premise)
        
        # 3. Populate Episodes
        self.refresh_episode_list()

    def edit_project_info(self):
        if not self.current_series_manager:
            return
            
        # We need to pass the current type to the dialog.
        # The type is stored in self.current_project_type (from project.json)
        # But SeriesManager.data (series.json) might not have it or it might be out of sync.
        # Let's inject it into the data passed to dialog.
        dialog_data = self.current_series_manager.data.copy()
        dialog_data["type"] = self.current_project_type
        
        # Also inject visual_style from project.json if possible
        try:
            project_json_path = os.path.join(self.current_project_path, "project.json")
            if os.path.exists(project_json_path):
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    pm = json.load(f)
                    dialog_data["visual_style"] = pm.get("visual_style", "")
        except: pass
        
        dialog = EditProjectDialog(dialog_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            
            # 1. Update SeriesManager (series.json)
            # Note: 'type' is not strictly part of series.json schema usually, but storing it there doesn't hurt.
            # However, the source of truth for the list is project.json.
            self.current_series_manager.data.update(new_data)
            self.current_series_manager.save()
            
            # 2. Update project.json
            # We need to read project.json, update it, and save it.
            try:
                project_json_path = os.path.join(self.current_project_path, "project.json")
                if os.path.exists(project_json_path):
                    with open(project_json_path, 'r', encoding='utf-8') as f:
                        project_meta = json.load(f)
                    
                    project_meta["type"] = new_data["type"]
                    project_meta["visual_style"] = new_data.get("visual_style", "")
                    # Also update name if title changed? Usually project name is folder name, but display name can be title.
                    # Let's keep it simple and just update type for now as requested.
                    
                    with open(project_json_path, 'w', encoding='utf-8') as f:
                        json.dump(project_meta, f, indent=4, ensure_ascii=False)
                        
                # Update local state
                self.current_project_type = new_data["type"]
                
            except Exception as e:
                print(f"Error updating project.json: {e}")
            
            # Refresh view
            self.load_project_details(self.current_project_path)
            self.refresh_list() # Refresh list to show new tags
            self.update_button_states() # Update buttons based on new type
            
            QMessageBox.information(self, "成功", "项目信息已更新")

    def refresh_episode_list(self):
        self.episode_list.clear()
        if self.current_series_manager:
            episodes = self.current_series_manager.get_episodes()
            for ep in episodes:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, ep['id'])
                
                # Create custom widget
                widget = EpisodeItemWidget(f"第 {ep['id']} 集: {ep['title']}", ep['id'])
                widget.delete_clicked.connect(self.delete_episode)
                
                # Set a fixed size hint to prevent overlapping
                item.setSizeHint(QSize(0, 60))
                
                self.episode_list.addItem(item)
                self.episode_list.setItemWidget(item, widget)

    def delete_episode(self, episode_id):
        if not self.current_series_manager:
            return
            
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除第 {episode_id} 集吗？\n此操作将删除对应的剧本文件，且后续集数会重新编号。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.current_series_manager.delete_episode(episode_id)
            if success:
                self.refresh_episode_list()
                QMessageBox.information(self, "成功", "集数已删除并重新编号。")
            else:
                QMessageBox.warning(self, "错误", "删除失败，未找到该集。")

    def generate_outline(self):
        if not self.current_series_manager:
            return
            
        # Check if outline exists
        if self.current_series_manager.data.get("premise"):
            reply = QMessageBox.question(
                self, 
                "确认重新生成", 
                "当前项目已包含大纲内容。重新生成将覆盖现有大纲。\n是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            
        # Show Dialog
        dialog = GenerateOutlineDialog(self.config_manager, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        data = dialog.get_data()
        api_config = data["api_config"]
        style = data["style"]
        instructions = data["instructions"]
        
        project_data = self.current_series_manager.data
        
        prompt = f"""
        请为以下短剧项目生成一个详细的故事大纲：
        项目名称：{project_data.get('title')}
        类型：{project_data.get('genre')}
        主题：{project_data.get('premise')}
        主要角色：{project_data.get('main_characters')}
        集数：{project_data.get('total_episodes')}
        
        风格基调：{style}
        额外要求：{instructions}
        
        要求：
        1. 包含整体故事弧线
        2. 简要描述每集（或关键节点）的剧情走向
        3. 突出冲突和高潮
        4. **重要：请使用Markdown格式，并在每个章节或关键点之间使用双换行符，确保段落分明。**
        5. **格式要求：涉及集数范围时，请使用 '1-5集：标题' 的格式（例如：**1-5集：相遇**），不要使用 '集1-5'。**
        """
        
        system_prompt = "You are a professional screenwriter. Create a detailed story outline. Use Markdown with clear paragraph breaks."
        
        # Start Generation UI
        self.progress_bar.show()
        self.cancel_btn.show()
        self.status_label.setText("正在生成大纲，请稍候...")
        self.gen_outline_btn.setEnabled(False)
        self.gen_script_btn.setEnabled(False)
        self.adapt_script_btn.setEnabled(False)
        self.edit_info_btn.setEnabled(False) # Disable edit button during outline generation
        
        self.outline_thread = OutlineGeneratorThread(api_config, prompt, system_prompt)
        self.outline_thread.finished.connect(self.on_outline_generated)
        self.outline_thread.error.connect(self.handle_outline_error)
        
        self.outline_thread.start()

    def handle_outline_error(self, e):
        self.progress_bar.hide()
        self.cancel_btn.hide()
        self.status_label.setText("生成失败")
        self.update_button_states()
        QMessageBox.critical(self, "Error", e)

    def format_markdown(self, text):
        """Ensure proper spacing for markdown headers and lists."""
        if not text:
            return ""
        
        # 1. Replace non-standard bullets
        text = text.replace('●', '-')
        
        # 2. Fix "*第X集" or "*第X阶段" pattern (often output by LLM without space, causing italics)
        # Turn "*第1集" or "*第一阶段" into "\n- 第1集"
        text = re.sub(r'\*+\s*(第[0-9一二三四五六七八九十]+[集阶段])', r'\n- \1', text)
        
        # 3. Ensure headers (#, ##, ###) start on a new line with a blank line before them
        text = re.sub(r'([^\n])\s*(#+\s)', r'\1\n\n\2', text)
        
        # 4. Ensure lists start on new line (-, *, 1.)
        # Fix "- Text" or "* Text" appearing in middle of line
        text = re.sub(r'([^\n])\s*([*-])\s+([^*-])', r'\1\n\2 \3', text)
        text = re.sub(r'([^\n])\s*(\d+\.)\s+', r'\1\n\2 ', text)
        
        # 5. Fix "Wall of Text" by adding newlines before bold headers
        # Only add newline if ** is preceded by sentence punctuation (. ! ? 。 ！ ？)
        text = re.sub(r'([.!?。！？])\s*\*\*', r'\1\n\n**', text)
        
        # 6. Clean up double bullets like "- -" or "- *" created by replacements
        text = re.sub(r'^\s*[-*]\s*[-*]\s+', '- ', text, flags=re.MULTILINE)
        
        # 7. Fix episode range format: "集1-5" -> "1-5集"
        text = re.sub(r'集(\d+)-(\d+)', r'\1-\2集', text)
        
        return text

    def on_outline_generated(self, outline):
        self.progress_bar.hide()
        self.cancel_btn.hide()
        self.status_label.setText("大纲生成完毕")
        self.update_button_states()

        if outline:
            formatted_outline = self.format_markdown(outline)
            self.outline_edit.setMarkdown(formatted_outline)
            self.save_outline()
            QMessageBox.information(self, "Success", "大纲生成完毕")

    def save_outline(self):
        if self.current_series_manager:
            text = self.outline_edit.toMarkdown()
            self.current_series_manager.update_premise(text)
            QMessageBox.information(self, "保存", "大纲已保存")

    def generate_next_episode_with_ai(self):
        if not self.current_series_manager:
            return

        # Check if episodes exist
        ep_count = len(self.current_series_manager.data.get("episodes", []))
        if ep_count > 0:
             reply = QMessageBox.question(
                self, 
                "确认生成", 
                f"当前项目已有 {ep_count} 集剧本。\n是否继续生成第 {ep_count + 1} 集？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.Yes
            )
             if reply == QMessageBox.StandardButton.No:
                return

        # Show Dialog
        dialog = GenerateScriptDialog(self.config_manager, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        
        # Store config for continuous generation
        self.current_gen_config = data
        self.continuous_mode = data.get("continuous", False)
        
        # Start first generation
        self.start_script_generation(data["idea"])

    def start_script_generation(self, idea):
        data = self.current_gen_config
        api_config = data["api_config"]
        embedding_config = data.get("embedding_config", {})
        duration = data["duration"]
        style = data["style"]
        
        # If embedding config is empty (Follow LLM), use api_config credentials
        if not embedding_config and api_config:
            embedding_config = api_config.copy()
            if "model" in embedding_config:
                del embedding_config["model"]
        
        # Update UI - Preparing
        self.progress_bar.show()
        self.cancel_btn.show()
        self.status_label.setText("正在准备上下文数据...")
        self.gen_outline_btn.setEnabled(False)
        self.gen_script_btn.setEnabled(False)
        self.adapt_script_btn.setEnabled(False)
        self.edit_info_btn.setEnabled(False) # Disable edit button during generation
        QApplication.processEvents() # Force UI update

        # Get context
        context_data = self.current_series_manager.get_full_context_data(idea, embedding_config=embedding_config)
        
        # Filter context
        if not data["use_global"]:
            context_data["global_summary"] = ""
        if not data["use_state"]:
            context_data["character_state"] = {}
        if not data["use_rag"]:
            context_data["rag_context"] = ""

        # Update UI - Generating
        next_ep_id = len(self.current_series_manager.data["episodes"]) + 1
        self.status_label.setText(f"正在生成第 {next_ep_id} 集... (AI思考中)")

        # Start Thread
        self.gen_thread = ScriptGeneratorThread(
            prompt=idea,
            api_config=api_config,
            duration=duration,
            style=style,
            context_data=context_data
        )
        self.gen_thread.finished.connect(self.on_script_generated)
        self.gen_thread.error.connect(lambda e: self.handle_gen_error(e))
        self.gen_thread.start()

    def handle_gen_error(self, e):
        self.progress_bar.hide()
        self.cancel_btn.hide()
        self.status_label.setText("生成出错")
        self.update_button_states()
        
        QMessageBox.critical(self, "Error", e)
        self.continuous_mode = False

    def on_script_generated(self, json_str):
        if not self.current_series_manager:
            return
            
        try:
            # Try to parse as multi-episode package first
            try:
                data = json.loads(json_str)
                if "episodes" in data and isinstance(data["episodes"], list):
                    # Multi-episode handling
                    count = 0
                    for ep_data in data["episodes"]:
                        next_id = len(self.current_series_manager.data["episodes"]) + 1
                        title = ep_data.get("title", f"Episode {next_id}")
                        # Convert back to string for storage
                        self.current_series_manager.add_episode(title, json.dumps(ep_data, ensure_ascii=False))
                        count += 1
                    
                    self.refresh_episode_list()
                    self.progress_bar.hide()
                    self.cancel_btn.hide()
                    self.status_label.setText(f"改编完成，共生成 {count} 集")
                    self.update_button_states()
                    QMessageBox.information(self, "成功", f"成功改编并生成了 {count} 集剧本。")
                    self.continuous_mode = False
                    return # Exit early
            except:
                pass # Fallback to single episode logic

            # Single episode logic (Legacy)
            next_id = len(self.current_series_manager.data["episodes"]) + 1
            title = f"Episode {next_id}"
            
            try:
                script_data = json.loads(json_str)
                if "title" in script_data:
                    title = script_data["title"]
            except:
                pass
            
            self.current_series_manager.add_episode(title, json_str)
            self.refresh_episode_list()
            
            # Check Continuous
            total = int(self.current_series_manager.data.get("total_episodes", 100))
            current_count = len(self.current_series_manager.data["episodes"])
            
            if self.continuous_mode and current_count < total:
                # Continue
                next_idea = "Continue the story based on the outline and previous events."
                self.status_label.setText(f"第 {next_id} 集生成完毕，休息 5 秒后继续...")
                
                # Delay 5 seconds to avoid rate limits
                QTimer.singleShot(5000, lambda: self.start_script_generation(next_idea) if self.continuous_mode else None)
            else:
                # Done
                self.progress_bar.hide()
                self.cancel_btn.hide()
                self.status_label.setText("生成完毕")
                self.update_button_states()
                
                QMessageBox.information(self, "成功", "生成完毕。")
                self.continuous_mode = False
            
        except Exception as e:
            self.progress_bar.hide()
            self.cancel_btn.hide()
            self.status_label.setText("处理结果失败")
            self.update_button_states()
            
            QMessageBox.warning(self, "错误", f"保存生成结果失败: {e}")
            self.continuous_mode = False

    def cancel_generation(self):
        self.continuous_mode = False
        if hasattr(self, 'adaptation_state'):
            self.adaptation_state["active"] = False
            
        self.status_label.setText("正在停止...")
        self.cancel_btn.setEnabled(False)
        
        # Try to stop threads if running
        if hasattr(self, 'gen_thread') and self.gen_thread.isRunning():
            # We can't easily kill the thread safely, but we can disconnect signals
            try:
                self.gen_thread.finished.disconnect(self.on_script_generated)
            except:
                pass
            self.gen_thread.terminate() # Force terminate for now as user requested stop
            if not self.gen_thread.wait(2000): # Wait max 2 seconds
                print("Warning: gen_thread did not terminate instantly.")
            
        if hasattr(self, 'outline_thread') and self.outline_thread.isRunning():
            try:
                self.outline_thread.finished.disconnect(self.on_outline_generated)
            except:
                pass
            self.outline_thread.terminate()
            if not self.outline_thread.wait(2000):
                print("Warning: outline_thread did not terminate instantly.")

        if hasattr(self, 'adapt_thread') and self.adapt_thread.isRunning():
            try:
                self.adapt_thread.finished.disconnect(self.on_adaptation_finished)
            except:
                pass
            self.adapt_thread.terminate()
            if not self.adapt_thread.wait(2000):
                print("Warning: adapt_thread did not terminate instantly.")
            
        self.progress_bar.hide()
        self.cancel_btn.hide()
        self.cancel_btn.setEnabled(True)
        self.status_label.setText("已停止")
        self.update_button_states()

    def adapt_script(self):
        if not self.current_series_manager:
            return
            
        # Check if episodes exist
        ep_count = len(self.current_series_manager.data.get("episodes", []))
        if ep_count > 0:
             reply = QMessageBox.question(
                self, 
                "确认改编", 
                f"当前项目已有 {ep_count} 集剧本。\n是否继续改编生成新的集数？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.Yes
            )
             if reply == QMessageBox.StandardButton.No:
                return
            
        dialog = AdaptScriptDialog(self.config_manager, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        data = dialog.get_data()
        api_config = data["api_config"]
        source_text = data["source_text"]
        style = data["style"]
        episode_count = data["episode_count"]
        words_per_episode = data.get("words_per_episode", 500)
        is_continuous = data.get("continuous", False)
        
        if not source_text.strip():
            QMessageBox.warning(self, "提示", "请输入或导入原文内容")
            return
            
        # Update UI
        self.progress_bar.show()
        self.cancel_btn.show()
        self.gen_outline_btn.setEnabled(False)
        self.gen_script_btn.setEnabled(False)
        self.adapt_script_btn.setEnabled(False)
        self.edit_info_btn.setEnabled(False) # Disable edit button during adaptation
        
        # Initialize Adaptation State
        self.adaptation_state = {
            "active": True,
            "api_config": api_config,
            "source_text": source_text,
            "style": style,
            "total_episodes": episode_count,
            "words_per_episode": words_per_episode,
            "current_episode": 1,
            "is_continuous": is_continuous
        }
        
        self.start_adaptation_step()

    def start_adaptation_step(self):
        state = self.adaptation_state
        if not state["active"]:
            return

        current = state["current_episode"]
        total = state["total_episodes"]
        
        # Prepare Context
        previous_context = ""
        character_list = self.current_series_manager.data.get("main_characters", "")
        
        if current > 1:
            # Try to get the last episode's content
            episodes = self.current_series_manager.data.get("episodes", [])
            if episodes:
                last_ep = episodes[-1]
                # If we have a summary, use it. Otherwise use the last 1000 chars of content.
                if last_ep.get("summary"):
                    previous_context = f"Summary of Episode {len(episodes)}: {last_ep.get('summary')}"
                else:
                    # Fallback to raw content excerpt
                    content = last_ep.get("content", "")
                    excerpt = content[-2000:] if len(content) > 2000 else content
                    previous_context = f"Excerpt from previous episode (JSON):\n{excerpt}"

        if state["is_continuous"]:
            # Serial Mode: Generate one by one
            self.status_label.setText(f"正在改编第 {current}/{total} 集...")
            self.adapt_thread = ScriptAdaptationThread(
                state["api_config"], 
                state["source_text"], 
                state["style"], 
                total, 
                state["words_per_episode"],
                current_episode_index=current,
                previous_context=previous_context,
                character_list=character_list
            )
        else:
            # Batch Mode: Generate all at once (Legacy behavior)
            self.status_label.setText(f"正在批量改编 {total} 集...")
            self.adapt_thread = ScriptAdaptationThread(
                state["api_config"], 
                state["source_text"], 
                state["style"], 
                total, 
                state["words_per_episode"],
                previous_context=previous_context,
                character_list=character_list
            )
            
        # Disconnect any previous connections to be safe
        try:
            self.adapt_thread.finished.disconnect()
        except:
            pass
        self.adapt_thread.finished.connect(self.on_adaptation_finished)
        self.adapt_thread.error.connect(self.handle_gen_error)
        self.adapt_thread.start()

    def on_adaptation_finished(self, json_str):
        if not self.adaptation_state["active"]:
            return

        try:
            # 1. Try parsing as JSON
            data = json.loads(json_str)
            
            episodes_to_save = []
            
            # Case A: {"episodes": [...]}
            if "episodes" in data and isinstance(data["episodes"], list):
                episodes_to_save = data["episodes"]
            # Case B: Single episode object {"title": ..., "scenes": ...}
            elif "scenes" in data:
                episodes_to_save = [data]
            else:
                episodes_to_save = [{"title": "Adapted Script", "content": data}]

            count = 0
            for ep_data in episodes_to_save:
                next_id = len(self.current_series_manager.data["episodes"]) + 1
                title = ep_data.get("title", f"Episode {next_id}")
                content_str = json.dumps(ep_data, ensure_ascii=False)
                # Pass api_config to enable auto-summarization if needed
                # But for adaptation, maybe we skip it to be fast? 
                # Let's skip it for now to avoid timeouts in the loop.
                self.current_series_manager.add_episode(title, content_str)
                count += 1
            
            self.refresh_episode_list()
            
            # Check if we need to continue
            state = self.adaptation_state
            if state["is_continuous"]:
                state["current_episode"] += 1
                if state["current_episode"] <= state["total_episodes"]:
                    # Continue to next episode
                    self.status_label.setText(f"第 {state['current_episode']-1} 集完成，休息 3 秒后继续...")
                    QTimer.singleShot(3000, self.start_adaptation_step)
                    return # Exit, don't reset UI yet

            # If we are here, we are done (either Batch mode finished, or Serial mode finished all eps)
            self.progress_bar.hide()
            self.cancel_btn.hide()
            self.status_label.setText("改编完成")
            self.update_button_states()
            self.adaptation_state["active"] = False
            
            QMessageBox.information(self, "成功", "改编任务全部完成。")
            
        except json.JSONDecodeError:
            # Case D: Not JSON (Raw text)
            next_id = len(self.current_series_manager.data["episodes"]) + 1
            self.current_series_manager.add_episode(f"Episode {next_id}", json_str)
            self.refresh_episode_list()
            
            # If serial mode fails to parse JSON, we probably should stop or continue?
            # Let's stop to be safe.
            self.progress_bar.hide()
            self.cancel_btn.hide()
            self.status_label.setText("改编中断 (格式错误)")
            self.update_button_states()
            self.adaptation_state["active"] = False
            QMessageBox.warning(self, "注意", "返回的内容不是标准的JSON格式，已作为纯文本保存，任务停止。")
            
        except Exception as e:
            self.progress_bar.hide()
            self.cancel_btn.hide()
            self.status_label.setText("改编出错")
            self.update_button_states()
            self.adaptation_state["active"] = False
            QMessageBox.warning(self, "错误", f"保存结果时出错: {e}")

    def generate_next_episode_placeholder(self):
        # Legacy placeholder method - kept if needed or replaced
        pass

    def on_episode_clicked(self, item):
        ep_id = item.data(Qt.ItemDataRole.UserRole)
        # Emit signal to open this episode in Script Window
        self.open_episode.emit(self.current_project_path, str(ep_id))

    def create_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            name = data.pop("name")
            if name:
                try:
                    path = self.manager.create_project(name, extra_data=data)
                    self.refresh_list()
                    QMessageBox.information(self, "成功", f"项目 '{name}' 已创建。")
                except ValueError as e:
                    QMessageBox.warning(self, "错误", str(e))

    def refresh_list(self):
        self.project_list.clear()
        projects = self.manager.list_projects()
        for p in projects:
            p_type = p.get("type", "original")
            type_tag = "[改编]" if p_type == "adaptation" else "[原创]"
            self.project_list.addItem(f"{type_tag} {p['name']}")
            # Store path in item
            item = self.project_list.item(self.project_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, p['path'])
            item.setData(Qt.ItemDataRole.UserRole + 1, p_type)

    def load_selected_project(self):
        item = self.project_list.currentItem()
        if item:
            path = item.data(Qt.ItemDataRole.UserRole)
            p_type = item.data(Qt.ItemDataRole.UserRole + 1)
            
            self.current_project_type = p_type
            self.project_loaded.emit(path)
            
            # Update UI based on project type
            self.update_button_states()
                
            show_message(self, "已加载", f"项目已加载: {item.text()}")

    def update_button_states(self):
        self.edit_info_btn.setEnabled(True)
        
        if self.current_project_type == "adaptation":
            # Adaptation mode: Only Adapt button is active
            self.gen_outline_btn.setEnabled(False)
            self.gen_script_btn.setEnabled(False)
            self.adapt_script_btn.setEnabled(True)
        else:
            # Original mode: Gen Outline/Script active, Adapt inactive
            self.gen_outline_btn.setEnabled(True)
            self.gen_script_btn.setEnabled(True)
            self.adapt_script_btn.setEnabled(False)
