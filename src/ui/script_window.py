from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QSplitter, 
                             QProgressBar, QMessageBox, QTabWidget, QComboBox,
                             QRadioButton, QButtonGroup, QListWidget, QListWidgetItem,
                             QStackedWidget, QFrame, QInputDialog, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
import json
import os
from core.script.script_model import Script
from ai_engine.llm.llm_client import LLMClient
from ai_engine.prompts import SCRIPT_GENERATION_PROMPT
from core.config.config_manager import ConfigManager
from core.project.series_manager import SeriesManager
from ui.script_editor_widget import ScriptEditorWidget

class ScriptGeneratorThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, prompt, api_config, duration, style, context_data=None):
        super().__init__()
        self.prompt = prompt
        self.api_config = api_config or {}
        self.duration = duration
        self.style = style
        self.context_data = context_data or {}

    def run(self):
        try:
            api_key = self.api_config.get("api_key")
            base_url = self.api_config.get("base_url")
            model = self.api_config.get("model")

            client = LLMClient(api_key=api_key, base_url=base_url, model=model)
            
            # Use the advanced prompt if context data is available
            if self.context_data:
                full_prompt = SCRIPT_GENERATION_PROMPT.format(
                    premise=self.context_data.get("premise", ""),
                    genre=self.context_data.get("genre", ""),
                    total_episodes=self.context_data.get("total_episodes", 100),
                    words_per_episode=self.context_data.get("words_per_episode", 300),
                    main_characters=self.context_data.get("main_characters", ""),
                    global_summary=self.context_data.get("global_summary", ""),
                    character_state=self.context_data.get("character_state", ""),
                    recent_episodes_summary=self.context_data.get("recent_episodes_summary", ""),
                    previous_script_excerpt=self.context_data.get("previous_script_excerpt", ""),
                    rag_context=self.context_data.get("rag_context", ""),
                    user_idea=self.prompt,
                    duration=self.duration,
                    style=self.style,
                    episode_number=self.context_data.get("episode_number", "Next"),
                    episode_title="Generated Episode"
                )
            else:
                # Fallback for non-series mode
                full_prompt = f"""
                Create a short drama script.
                Idea: {self.prompt}
                Style: {self.style}
                Duration: {self.duration}
                """

            # Mocking for now if no key provided to avoid crash
            if not api_key or api_key == "sk-placeholder":
                # Return a dummy script for testing
                dummy_json = json.dumps({
                    "title": "Generated Episode",
                    "genre": self.style,
                    "scenes": [
                        {
                            "scene_id": "1",
                            "location": "Unknown Location",
                            "time": "Day",
                            "description": "A scene generated based on context.",
                            "dialogues": [
                                {"role": "Character A", "content": "Did you see what happened last time?", "action": "Whispers", "expression": "Serious"},
                                {"role": "Character B", "content": "Yes, the context was preserved.", "action": "Nods", "expression": "Calm"}
                            ]
                        }
                    ]
                })
                import time
                time.sleep(2)
                self.finished.emit(dummy_json)
            else:
                result = client.generate_script(full_prompt)
                if result:
                    # Clean up markdown if present
                    if result.startswith("```json"):
                        result = result[7:]
                    if result.endswith("```"):
                        result = result[:-3]
                    self.finished.emit(result.strip())
                else:
                    self.error.emit("Failed to generate script.")
        except Exception as e:
            self.error.emit(str(e))

class ScriptWindow(QWidget):
    def __init__(self, project_dir):
        super().__init__()
        self.project_dir = project_dir
        self.current_script = None
        self.current_episode_id = None # Track which episode is being edited
        self.series_manager = None
        self.config_manager = ConfigManager()
        self.init_ui()
        self.check_project_status()

    def check_project_status(self):
        if self.project_dir and os.path.exists(os.path.join(self.project_dir, "project.json")):
            project_name = os.path.basename(self.project_dir)
            self.project_label.setText(f"当前项目: {project_name}")
            self.project_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
            
            # Initialize Series Manager
            self.series_manager = SeriesManager(self.project_dir)
            self.refresh_episode_list()
            
        else:
            self.project_label.setText("未选择项目 (请先在项目管理中加载)")
            self.project_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def set_project_dir(self, path):
        self.project_dir = path
        self.check_project_status()
        self.load_existing_script()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Sidebar ---
        left_sidebar = QFrame()
        left_sidebar.setFixedWidth(280) # Widened for episode list
        left_sidebar.setStyleSheet("background-color: #313131; color: white; border-right: 1px solid #34495e;")
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(15, 20, 15, 20)
        left_layout.setSpacing(15)

        # Project Info
        self.project_label = QLabel("检测中...")
        self.project_label.setWordWrap(True)
        left_layout.addWidget(self.project_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #34495e;")
        left_layout.addWidget(line)

        # Video Ratio
        left_layout.addWidget(QLabel("视频比例"))
        ratio_layout = QHBoxLayout()
        self.ratio_h = QRadioButton("横屏 16:9")
        self.ratio_v = QRadioButton("竖屏 9:16")
        self.ratio_h.setChecked(True)
        self.ratio_h.setStyleSheet("color: white;")
        self.ratio_v.setStyleSheet("color: white;")
        
        ratio_group = QButtonGroup(self)
        ratio_group.addButton(self.ratio_h)
        ratio_group.addButton(self.ratio_v)
        
        ratio_layout.addWidget(self.ratio_h)
        ratio_layout.addWidget(self.ratio_v)
        left_layout.addLayout(ratio_layout)
        
        self.ratio_h.toggled.connect(self.save_project_settings)
        self.ratio_v.toggled.connect(self.save_project_settings)

        # Video Resolution
        left_layout.addWidget(QLabel("视频分辨率"))
        res_layout = QHBoxLayout()
        self.res_1080 = QRadioButton("1080P")
        self.res_720 = QRadioButton("720P")
        self.res_1080.setChecked(True)
        self.res_1080.setStyleSheet("color: white;")
        self.res_720.setStyleSheet("color: white;")
        
        res_group = QButtonGroup(self)
        res_group.addButton(self.res_1080)
        res_group.addButton(self.res_720)
        
        res_layout.addWidget(self.res_1080)
        res_layout.addWidget(self.res_720)
        left_layout.addLayout(res_layout)
        
        self.res_1080.toggled.connect(self.save_project_settings)
        self.res_720.toggled.connect(self.save_project_settings)

        # --- Series Management ---
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #34495e;")
        left_layout.addWidget(line2)
        
        left_layout.addWidget(QLabel("剧集列表 (Series)"))
        
        # Episode List
        self.episode_list = QListWidget()
        self.episode_list.setStyleSheet("""
            QListWidget { background-color: #34495e; border: none; color: white; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2c3e50; }
            QListWidget::item:selected { background-color: #2980b9; }
        """)
        self.episode_list.itemClicked.connect(self.on_episode_selected)
        left_layout.addWidget(self.episode_list)
        
        # Removed "New Series" and "Set Outline" buttons as requested

        # Removed "LLM Model Config" as requested

        # Project Info Box
        info_box = QGroupBox("项目信息")
        info_box.setStyleSheet("""
            QGroupBox {
                border: 1px solid #34495e;
                border-radius: 5px;
                margin-top: 10px;
                color: #bdc3c7;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QLabel {
                color: #ecf0f1;
                font-size: 12px;
            }
        """)
        info_layout = QFormLayout(info_box)
        info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        self.info_type = QLabel("AI短剧")
        self.info_genre = QLabel("未设置")
        self.info_count = QLabel("0 集")
        
        info_layout.addRow("创作类型:", self.info_type)
        info_layout.addRow("故事类型:", self.info_genre)
        info_layout.addRow("总集数:", self.info_count)
        
        left_layout.addWidget(info_box)
        
        left_layout.addStretch() # Push everything up

        main_layout.addWidget(left_sidebar)

        # --- Right Content Area ---
        right_content = QWidget()
        right_content.setStyleSheet("background-color: #1e1e1e;") # Dark background for the whole right area
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Header (Title Bar)
        header = QFrame()
        header.setStyleSheet("background-color: #2c3e50; border-bottom: 1px solid #34495e;")
        header.setFixedHeight(50)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        header_title = QLabel("剧本编辑")
        header_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        right_layout.addWidget(header)

        # Script Editor
        self.script_editor = ScriptEditorWidget()
        right_layout.addWidget(self.script_editor)
        
        # Bottom Bar with Save Button
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("background-color: #2c3e50; border-top: 1px solid #34495e;")
        bottom_bar.setFixedHeight(60)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        
        bottom_layout.addStretch()
        
        save_btn = QPushButton("保存本集")
        save_btn.setFixedSize(120, 40)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #219150;
            }
        """)
        save_btn.clicked.connect(self.save_script)
        bottom_layout.addWidget(save_btn)
        
        right_layout.addWidget(bottom_bar)

        main_layout.addWidget(right_content)

    def refresh_api_list(self):
        self.api_combo.clear()
        configs = self.config_manager.get("api_configs", [])
        llm_configs = [c for c in configs if c.get("type") == "LLM"]
        
        for config in llm_configs:
            self.api_combo.addItem(config.get("name", "Unnamed"), config)
            
        if self.api_combo.count() == 0:
             self.api_combo.addItem("未配置 (使用默认/Mock)", {})

    def refresh_episode_list(self):
        if not self.series_manager:
            return
        
        self.episode_list.clear()
        episodes = self.series_manager.get_episodes()
        
        for ep in episodes:
            item = QListWidgetItem(f"第{ep['id']}集: {ep['title']}")
            item.setData(Qt.ItemDataRole.UserRole, ep)
            self.episode_list.addItem(item)
            
        # Also check for legacy "current_script.json" and maybe import it?
        # For now, we just list what's in series.json

    def create_new_episode_ui(self):
        self.current_script = None
        self.current_episode_id = None
        self.script_editor.load_script(None)
        self.episode_list.clearSelection()

    def edit_premise(self):
        if not self.series_manager: return
        current_premise = self.series_manager.data.get("premise", "")
        text, ok = QInputDialog.getMultiLineText(self, "设定剧集大纲", "输入整个系列的故事背景、世界观和主线:", current_premise)
        if ok:
            self.series_manager.update_premise(text)

    def on_episode_selected(self, item):
        ep_data = item.data(Qt.ItemDataRole.UserRole)
        script_rel_path = ep_data.get("script_path")
        if script_rel_path:
            full_path = os.path.join(self.project_dir, script_rel_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.current_script = Script.from_json(content)
                        
                        # Construct Title
                        project_name = os.path.basename(self.project_dir)
                        ep_id = ep_data.get('id', '?')
                        self.current_episode_id = ep_data.get('id') # Store ID
                        ep_title = ep_data.get('title', 'Untitled')
                        full_title = f"{project_name} - 第 {ep_id} 集: {ep_title}"
                        
                        self.script_editor.load_script(self.current_script, full_title)
                except Exception as e:
                    print(f"Error loading episode script: {e}")

    def load_episode_by_id(self, ep_id):
        """Loads an episode by its ID (string or int)."""
        if not self.series_manager:
            return
            
        ep_id = int(ep_id)
        # Find the item in the list widget
        for i in range(self.episode_list.count()):
            item = self.episode_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data.get("id") == ep_id:
                self.episode_list.setCurrentItem(item)
                self.on_episode_selected(item)
                return
        
        print(f"Episode {ep_id} not found in list.")

    def load_existing_script(self):
        """Loads script from the current project directory if it exists."""
        if not self.project_dir:
            return
            
        # Load Project Settings (Ratio & Style)
        try:
            project_json_path = os.path.join(self.project_dir, "project.json")
            if os.path.exists(project_json_path):
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    ratio = project_data.get("ratio", "16:9")
                    resolution = project_data.get("resolution", "1080p")
                    style = project_data.get("style", "未设置")
                    
                    if ratio == "9:16":
                        self.ratio_v.setChecked(True)
                    else:
                        self.ratio_h.setChecked(True)
                        
                    if resolution == "720p":
                        self.res_720.setChecked(True)
                    else:
                        self.res_1080.setChecked(True)
                        
                    # Update Info Box
                    p_type = project_data.get("type", "original")
                    p_genre = project_data.get("genre", "未设置")
                    p_episodes = project_data.get("total_episodes", 0)
                    
                    type_map = {"original": "原创短剧", "adaptation": "改编短剧"}
                    self.info_type.setText(type_map.get(p_type, "原创短剧"))
                    self.info_genre.setText(p_genre)
                    if p_episodes:
                        self.info_count.setText(f"{p_episodes} 集")
                        
        except Exception as e:
            print(f"Error loading project settings: {e}")

        # Try to load series data
        if self.series_manager:
            self.refresh_episode_list()
            
            # If episodes exist, select the last one
            if self.episode_list.count() > 0:
                self.episode_list.setCurrentRow(self.episode_list.count() - 1)
                self.on_episode_selected(self.episode_list.currentItem())
            else:
                # Fallback to legacy current_script.json if series is empty
                path = os.path.join(self.project_dir, "current_script.json")
                if os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self.current_script = Script.from_json(content)
                            
                            project_name = os.path.basename(self.project_dir)
                            full_title = f"{project_name} - 当前剧本"
                            
                            self.script_editor.load_script(self.current_script, full_title)
                    except Exception as e:
                        print(f"Failed to auto-load script: {e}")

    def start_generation(self):
        prompt = self.topic_input.toPlainText()
        if not prompt:
            QMessageBox.warning(self, "错误", "请输入故事创意。")
            return
            
        self.progress.show()
        self.progress.setRange(0, 0) # Indeterminate
        
        selected_config = self.api_combo.currentData()
        duration = self.duration_combo.currentText()
        style = self.style_list.currentItem().text() if self.style_list.currentItem() else "Default"
        
        # Get Context from SeriesManager (RAG)
        context_data = {}
        if self.series_manager:
            context_data = self.series_manager.get_full_context_data(prompt)
            print(f"DEBUG: Context gathered for generation.")
        
        self.thread = ScriptGeneratorThread(prompt, selected_config, duration, style, context_data)
        self.thread.finished.connect(self.on_generation_finished)
        self.thread.error.connect(self.on_generation_error)
        self.thread.start()

    def on_generation_finished(self, json_str):
        self.progress.hide()
        try:
            self.current_script = Script.from_json(json_str)
            
            # Construct Title
            project_name = os.path.basename(self.project_dir) if self.project_dir else "未保存项目"
            next_id = len(self.series_manager.data.get("episodes", [])) + 1 if self.series_manager else 1
            title = self.current_script.title or "Generated Episode"
            full_title = f"{project_name} - 第 {next_id} 集: {title}"
            
            self.script_editor.load_script(self.current_script, full_title)
            self.content_tabs.setCurrentIndex(1) # Switch to editor tab
        except Exception as e:
            QMessageBox.warning(self, "错误", f"解析生成结果失败: {e}\nRaw: {json_str}")

    def on_generation_error(self, error_msg):
        self.progress.hide()
        QMessageBox.critical(self, "错误", f"生成失败: {error_msg}")

    def save_script(self):
        if not self.current_script:
            return

        # If we are in series mode, save as episode
        if self.series_manager:
            # Determine title
            title = self.current_script.title or "Untitled Episode"
            content = self.current_script.to_json()
            
            if self.current_episode_id:
                # Update existing episode
                success = self.series_manager.update_episode(
                    self.current_episode_id, 
                    title, 
                    content, 
                    summary=self.current_script.summary
                )
                if success:
                    self.refresh_episode_list()
                    # Reselect the current item
                    self.load_episode_by_id(self.current_episode_id)
                    QMessageBox.information(self, "已保存", f"剧集 '{title}' 已更新。")
                else:
                    QMessageBox.warning(self, "错误", "更新剧集失败，ID未找到。")
            else:
                # Add new episode
                self.series_manager.add_episode(title, content, summary=self.current_script.summary)
                self.refresh_episode_list()
                # Select the new (last) item
                if self.episode_list.count() > 0:
                    self.episode_list.setCurrentRow(self.episode_list.count() - 1)
                    item = self.episode_list.currentItem()
                    if item:
                        data = item.data(Qt.ItemDataRole.UserRole)
                        self.current_episode_id = data.get("id")
                
                QMessageBox.information(self, "已保存", f"剧集 '{title}' 已保存到系列。")
            
            # Also save as current_script.json for backward compatibility with other modules
            path = os.path.join(self.project_dir, "current_script.json")
            self.current_script.save(path)
            
        else:
            # Fallback
            path = os.path.join(self.project_dir, "current_script.json")
            self.current_script.save(path)
            QMessageBox.information(self, "已保存", f"剧本已保存至 {path}")
        
        # Also ensure settings are saved
        self.save_project_settings()

    def save_project_settings(self):
        """Saves ratio and resolution to project.json immediately."""
        if not self.project_dir:
            return
            
        try:
            project_json_path = os.path.join(self.project_dir, "project.json")
            if os.path.exists(project_json_path):
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
            else:
                project_data = {}
            
            # Update ratio & resolution
            ratio = "16:9" if self.ratio_h.isChecked() else "9:16"
            resolution = "1080p" if self.res_1080.isChecked() else "720p"
            
            # Only save if changed to avoid unnecessary writes/logs
            if project_data.get("ratio") == ratio and project_data.get("resolution") == resolution:
                return

            project_data["ratio"] = ratio
            project_data["resolution"] = resolution
            
            with open(project_json_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=4, ensure_ascii=False)
                
            # print(f"DEBUG: Project settings saved to {os.path.abspath(project_json_path)}: Ratio={ratio}, Resolution={resolution}")
                
        except Exception as e:
            print(f"DEBUG: Error saving project settings: {e}")
