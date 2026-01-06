from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QScrollArea, QGridLayout, 
                             QFileDialog, QMessageBox, QProgressBar, QComboBox,
                             QFrame, QTextEdit, QSplitter, QListWidgetItem,
                             QDialog, QCheckBox, QButtonGroup, QInputDialog, QMenu,
                             QSpinBox, QDoubleSpinBox, QStackedWidget, QStyle, QRadioButton,
                             QSlider, QLineEdit)
from PyQt6.QtGui import QPixmap, QIcon, QColor, QAction, QMouseEvent
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import os
import json
import shutil
from core.script.script_model import Script, Dialogue
from core.storyboard.storyboard_model import Storyboard, Panel
from core.storyboard.prompt_factory import generate_panel_prompt, construct_prompt_from_params
from ai_engine.image_gen.image_client import ImageGenClient
from ai_engine.video_gen.video_client import VideoGenClient
from core.config.config_manager import ConfigManager
from core.character.character_model import Character
from ai_engine.utils.prompt_utils import construct_veo_prompt
from ui.scene_library_dialog import SceneSelectorDialog

class VideoPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Content Area (Stack for Video vs Placeholder)
        self.content_stack = QStackedWidget()
        
        # 0: Video Surface
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black; border-radius: 5px;")
        self.content_stack.addWidget(self.video_widget)
        
        # 1: Placeholder
        self.placeholder = QLabel("暂无视频")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("background-color: #000; color: #7f8c8d; font-size: 20px; border-radius: 5px;")
        self.content_stack.addWidget(self.placeholder)
        
        layout.addWidget(self.content_stack)
        
        # Controls
        controls_frame = QFrame()
        controls_frame.setFixedHeight(40)
        controls_frame.setStyleSheet("background-color: #2c3e50; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;")
        ctrl_layout = QHBoxLayout(controls_frame)
        ctrl_layout.setContentsMargins(10, 0, 10, 0)
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.setStyleSheet("color: white; border: none; font-size: 16px;")
        self.play_btn.clicked.connect(self.toggle_playback)
        ctrl_layout.addWidget(self.play_btn)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #5d6d7e;
                height: 4px;
                background: #34495e;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #f1c40f;
                border: 1px solid #f1c40f;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        self.slider.sliderMoved.connect(self.set_position)
        ctrl_layout.addWidget(self.slider)
        
        layout.addWidget(controls_frame)
        
        # Player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.playbackStateChanged.connect(self.media_state_changed)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)
        
        # Default to placeholder
        self.show_placeholder()

    def set_source(self, path):
        print(f"DEBUG: VideoPlayer setting source: {path}")
        self.content_stack.setCurrentIndex(0)
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.play_btn.setText("▶")
        self.slider.setValue(0)
        self.play_btn.setEnabled(True)
        self.slider.setEnabled(True)

    def show_placeholder(self):
        self.media_player.stop()
        self.content_stack.setCurrentIndex(1)
        self.play_btn.setEnabled(False)
        self.slider.setEnabled(False)

    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def media_state_changed(self, state):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.media_player.stop()
            self.play_btn.setText("▶")
            # Reset to start to show "cover" (first frame)
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            print(f"Error: Invalid Media. Error string: {self.media_player.errorString()}")
            # Try to show placeholder or error
            self.content_stack.setCurrentIndex(1)
            self.placeholder.setText(f"无法播放视频: {self.media_player.errorString()}")
            self.media_player.setPosition(0)

    def position_changed(self, position):
        self.slider.setValue(position)

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def set_position(self, position):
        self.media_player.setPosition(position)
        
    def stop(self):
        self.media_player.stop()

class HistoryItemWidget(QWidget):
    selected = pyqtSignal(str)
    deleted = pyqtSignal(str)

    def __init__(self, file_path, is_selected=False, is_video=False, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_video = is_video
        self.setFixedSize(80, 100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Container for overlay
        self.container = QFrame()
        self.container.setFixedSize(80, 100)
        
        # Style based on selection
        border_color = "#f1c40f" if is_selected else "#5d6d7e"
        border_width = "2px" if is_selected else "1px"
        
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: #34495e;
                border: {border_width} solid {border_color};
                border-radius: 4px;
            }}
        """)
        
        # Image/Video Label
        self.img_lbl = QLabel(self.container)
        self.img_lbl.setGeometry(2, 2, 76, 96)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists(file_path):
            if is_video:
                # For video, show a video icon placeholder
                # In a more advanced implementation, we could extract a frame
                self.img_lbl.setText("🎬")
                self.img_lbl.setStyleSheet("font-size: 36px;")
            else:
                pix = QPixmap(file_path)
                self.img_lbl.setPixmap(pix.scaled(76, 96, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            self.img_lbl.setText("Missing")
            
        # Delete Button (Top Right)
        self.del_btn = QPushButton("×", self.container)
        self.del_btn.setGeometry(60, 0, 20, 20)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 150);
                color: white;
                border: none;
                border-bottom-left-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """)
        self.del_btn.clicked.connect(self.on_delete)
        
        layout.addWidget(self.container)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.file_path)
            
    def on_delete(self):
        self.deleted.emit(self.file_path)

class VideoGenThread(QThread):
    finished = pyqtSignal(str, str, str) # panel_id, video_path, task_id

    def __init__(self, panel_id, image_path, prompt, output_path, api_config, text=None, voice_id=None, ratio="16:9", language="English", end_image_path=None, input_video_path=None):
        super().__init__()
        self.panel_id = panel_id
        self.image_path = image_path
        self.prompt = prompt
        self.output_path = output_path
        self.api_config = api_config or {}
        self.text = text
        self.voice_id = voice_id
        self.ratio = ratio
        self.language = language
        self.end_image_path = end_image_path
        self.input_video_path = input_video_path

    def run(self):
        try:
            api_key = self.api_config.get("api_key")
            base_url = self.api_config.get("base_url")
            model = self.api_config.get("model")
            provider = self.api_config.get("provider")

            print(f"DEBUG: Starting video generation for panel {self.panel_id} with provider {provider}, ratio {self.ratio}, language {self.language}")
            # Import here to ensure no circular dependency issues or early import failures
            from ai_engine.video_gen.video_client import VideoGenClient
            
            client = VideoGenClient(api_key=api_key, base_url=base_url, model=model, provider=provider, api_config=self.api_config)
            
            # Pass text, voice_id and ratio to generate_video
            result = client.generate_video(
                self.image_path, 
                self.prompt, 
                self.output_path, 
                self.text, 
                self.voice_id, 
                aspect_ratio=self.ratio, 
                language=self.language,
                end_image_path=self.end_image_path,
                input_video_path=self.input_video_path
            )
            
            # Handle both tuple (path, task_id) and legacy string path
            video_path = None
            task_id = ""
            if isinstance(result, tuple) and len(result) == 2:
                video_path, task_id = result
            else:
                video_path = result
            
            print(f"DEBUG: Video generation finished. Path: {video_path}, TaskID: {task_id}")
            self.finished.emit(self.panel_id, video_path or "", task_id or "")
        except Exception as e:
            print(f"DEBUG: Exception in VideoGenThread: {e}")
            import traceback
            traceback.print_exc()
            # Try to extract task_id even on exception (might be download error after successful generation)
            task_id = ""
            try:
                if 'result' in locals() and isinstance(result, tuple) and len(result) >= 2:
                    task_id = result[1] or ""
            except:
                pass
            self.finished.emit(self.panel_id, "", task_id)

class BatchVideoDialog(QDialog):
    def __init__(self, storyboard, project_dir, current_panel_idx=-1, parent=None):
        super().__init__(parent)
        print("DEBUG: BatchVideoDialog.__init__ started")
        try:
            self.setWindowTitle("批量转动态")
            self.resize(900, 600)
            self.storyboard = storyboard
            self.project_dir = project_dir
            self.current_panel_idx = current_panel_idx
            self.config_manager = ConfigManager()
            self.selected_panels = set()
            self.init_ui()
            print("DEBUG: BatchVideoDialog.__init__ finished")
        except Exception as e:
            print(f"ERROR in BatchVideoDialog.__init__: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def load_video_models(self):
        configs = self.config_manager.get("api_configs", [])
        # Filter for both generic 'Video' and specific 'ImageToVideo' types
        video_configs = [c for c in configs if c.get("type") in ["Video", "ImageToVideo"]]
        
        self.model_combo.clear()
        
        default_index = 0
        # Add configured models first
        for i, config in enumerate(video_configs):
            name = config.get("name", f"{config.get('provider')} - {config.get('model')}")
            self.model_combo.addItem(name, config)
            if config.get("is_default"):
                default_index = i
            
        # Add local/mock option as fallback (at the end, so it's not default if others exist)
        self.model_combo.addItem("默认 (本地 Ken Burns)", {"provider": "mock", "model": "ken_burns"})
        
        # If we have valid configs, select the default one
        if video_configs:
            self.model_combo.setCurrentIndex(default_index)
        else:
            self.model_combo.setCurrentIndex(self.model_combo.count() - 1)

    def get_selected_config(self):
        config = self.model_combo.currentData() or {}
        # Create a copy to avoid modifying the original config dict stored in combo
        config = config.copy()
        if hasattr(self, 'prompt_input') and self.prompt_input.text().strip():
            config['prompt_suffix'] = self.prompt_input.text().strip()
        if hasattr(self, 'chk_use_end_frame'):
            config['use_end_frame'] = self.chk_use_end_frame.isChecked()
        if hasattr(self, 'chk_extend_video'):
            config['extend_video'] = self.chk_extend_video.isChecked()
        return config

    def init_ui(self):
        self.setStyleSheet("background-color: #1e272e; color: white;")
        layout = QVBoxLayout(self)
        
        # Header Tabs
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        self.btn_batch = QPushButton("图片转视频")
        self.btn_batch.setCheckable(True)
        self.btn_batch.setChecked(True)
        self.btn_batch.setStyleSheet("background-color: transparent; color: #f1c40f; font-size: 16px; font-weight: bold; border-bottom: 2px solid #f1c40f;")
        
        
        header_layout.addWidget(self.btn_batch)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Model Selection & Config
        config_frame = QFrame()
        config_frame.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")
        config_layout = QVBoxLayout(config_frame)
        
        # Row 1: Model
        row1 = QHBoxLayout()
        lbl_model = QLabel("视频模型:")
        lbl_model.setStyleSheet("font-size: 14px; color: #bdc3c7;")
        row1.addWidget(lbl_model)
        
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #34495e;
                color: white;
                border: 1px solid #7f8c8d;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.load_video_models()
        row1.addWidget(self.model_combo)
        
        # Use End Frame Checkbox
        self.chk_use_end_frame = QCheckBox("使用下一分镜作为尾帧 (首尾帧生成)")
        self.chk_use_end_frame.setStyleSheet("color: #bdc3c7; margin-left: 10px;")
        self.chk_use_end_frame.setToolTip("如果勾选，将使用当前分镜的图片作为首帧，下一分镜的图片作为尾帧，生成过渡视频。\n适用于同一场景的连续动作。")
        row1.addWidget(self.chk_use_end_frame)

        # Extend Video Checkbox
        self.chk_extend_video = QCheckBox("视频延展 (Video Extension)")
        self.chk_extend_video.setStyleSheet("color: #bdc3c7; margin-left: 10px;")
        self.chk_extend_video.setToolTip("如果勾选，将尝试使用上一分镜的视频作为输入，生成当前分镜的视频，实现连续镜头。\n注意：上一分镜必须已有视频。")
        row1.addWidget(self.chk_extend_video)
        
        row1.addStretch()
        config_layout.addLayout(row1)
        
        # Row 2: Prompt / Params
        row2 = QHBoxLayout()
        lbl_prompt = QLabel("附加提示词:")
        lbl_prompt.setStyleSheet("font-size: 14px; color: #bdc3c7;")
        row2.addWidget(lbl_prompt)
        
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("输入附加提示词 (可选)...")
        self.prompt_input.setStyleSheet("background-color: #34495e; color: white; border: 1px solid #7f8c8d; border-radius: 5px; padding: 5px;")
        row2.addWidget(self.prompt_input)
        config_layout.addLayout(row2)
        
        layout.addWidget(config_frame)

        # Select All
        self.chk_all = QCheckBox("全选")
        self.chk_all.setStyleSheet("margin-left: 10px; font-size: 14px;")
        self.chk_all.stateChanged.connect(self.toggle_all)
        layout.addWidget(self.chk_all)
        
        # List Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #2c3e50; border-radius: 10px;")
        
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setSpacing(10)
        
        self.checkboxes = []
        
        for i, panel in enumerate(self.storyboard.panels):
            if not panel.image_path:
                continue
                
            item_frame = QFrame()
            item_frame.setFixedHeight(80)
            item_frame.setStyleSheet("background-color: #34495e; border-radius: 5px;")
            item_layout = QHBoxLayout(item_frame)
            
            # Checkbox
            chk = QCheckBox()
            chk.setProperty("panel_id", panel.panel_id)
            chk.stateChanged.connect(self.update_selection)
            
            # Default select if matches current_panel_idx
            if i == self.current_panel_idx:
                chk.setChecked(True)
                
            self.checkboxes.append(chk)
            item_layout.addWidget(chk)
            
            # Index
            idx_lbl = QLabel(f"{i+1:02d}")
            idx_lbl.setStyleSheet("color: #f1c40f; font-weight: bold; font-size: 16px;")
            item_layout.addWidget(idx_lbl)
            
            # Thumb
            thumb = QLabel()
            thumb.setFixedSize(100, 60)
            thumb.setStyleSheet("background-color: black;")
            if os.path.exists(panel.image_path):
                pix = QPixmap(panel.image_path)
                thumb.setPixmap(pix.scaled(100, 60, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
            item_layout.addWidget(thumb)
            
            # Info Label (Project, Scene, Shot)
            info_text = f"项目: {self.storyboard.script_title} | 场景: {panel.scene_id} | 分镜: {panel.panel_id}"
            lbl_info = QLabel(info_text)
            lbl_info.setStyleSheet("color: #bdc3c7; font-size: 12px;")
            item_layout.addWidget(lbl_info)
            
            item_layout.addStretch()
            
            self.list_layout.addWidget(item_frame)
            
        self.list_layout.addStretch()
        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll)
        
        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedSize(100, 40)
        btn_cancel.setStyleSheet("background-color: #7f8c8d; border-radius: 5px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_next = QPushButton("下一步")
        btn_next.setFixedSize(100, 40)
        btn_next.setStyleSheet("background-color: #f1c40f; color: #2c3e50; font-weight: bold; border-radius: 5px;")
        btn_next.clicked.connect(self.accept)
        
        footer_layout.addWidget(btn_cancel)
        footer_layout.addWidget(btn_next)
        
        layout.addLayout(footer_layout)

    def toggle_all(self, state):
        for chk in self.checkboxes:
            chk.setChecked(state == Qt.CheckState.Checked.value)

    def update_selection(self, state=None):
        # Optional: Keep track of selection for UI feedback if needed
        pass

    def accept(self):
        # We'll calculate selection in get_selected_panels
        super().accept()
                
    def get_selected_panels(self):
        selected = []
        for chk in self.checkboxes:
            if chk.isChecked():
                pid = chk.property("panel_id")
                if pid:
                    selected.append(pid)
        print(f"DEBUG: get_selected_panels found {len(selected)} items: {selected}")
        return selected

class ImageGenSettingsDialog(QDialog):
    def __init__(self, current_settings, parent=None, project_style=None):
        super().__init__(parent)
        self.setWindowTitle("生图参数设置")
        self.resize(400, 350)
        self.settings = current_settings or {}
        self.project_style = project_style
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #2c3e50; color: white;")
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Style
        layout.addWidget(QLabel("风格预设 (Style Preset):"))
        self.style_combo = QComboBox()
        # Common styles + project style if exists
        styles = [
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
            "Gothic (哥特风格)",
            "None"
        ]
        
        # If project style is set, ensure it's in the list and selected
        if self.project_style:
            if self.project_style not in styles:
                styles.insert(0, self.project_style)
            self.style_combo.addItems(styles)
            self.style_combo.setCurrentText(self.project_style)
            self.style_combo.setEnabled(False) # Disable editing if project style is enforced
            
            # Add a label to explain
            lbl = QLabel(f"已锁定项目风格: {self.project_style}")
            lbl.setStyleSheet("color: #f1c40f; font-style: italic;")
            layout.addWidget(lbl)
        else:
            self.style_combo.addItems(styles)
            # Try to match existing setting to new list (fuzzy match or exact)
            current = self.settings.get("style", "Cinematic (电影质感)")
            # If current is old style name (e.g. "Cinematic"), try to find it in new list
            found = False
            for s in styles:
                if current in s: # Simple substring match for compatibility
                    self.style_combo.setCurrentText(s)
                    found = True
                    break
            if not found:
                self.style_combo.setCurrentText(current)
            
        self.style_combo.setStyleSheet("padding: 5px; background-color: #34495e; color: white; border: 1px solid #5d6d7e;")
        self.style_combo.setDisabled(bool(self.project_style)) # Double check disable
        layout.addWidget(self.style_combo)
        
        # Negative Prompt
        layout.addWidget(QLabel("反向提示词 (Negative Prompt):"))
        self.neg_prompt = QTextEdit()
        self.neg_prompt.setPlaceholderText("不想出现在画面中的内容...")
        self.neg_prompt.setText(self.settings.get("negative_prompt", ""))
        self.neg_prompt.setMaximumHeight(80)
        self.neg_prompt.setStyleSheet("padding: 5px; background-color: #34495e; color: white; border: 1px solid #5d6d7e;")
        layout.addWidget(self.neg_prompt)
        
        # Steps
        layout.addWidget(QLabel("生成步数 (Steps):"))
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 100)
        self.steps_spin.setValue(self.settings.get("steps", 30))
        self.steps_spin.setStyleSheet("padding: 5px; background-color: #34495e; color: white; border: 1px solid #5d6d7e;")
        layout.addWidget(self.steps_spin)
        
        # CFG Scale
        layout.addWidget(QLabel("提示词相关性 (CFG Scale):"))
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(1.0, 20.0)
        self.cfg_spin.setValue(self.settings.get("cfg_scale", 7.0))
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setStyleSheet("padding: 5px; background-color: #34495e; color: white; border: 1px solid #5d6d7e;")
        layout.addWidget(self.cfg_spin)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet("background-color: #f1c40f; color: #2c3e50; font-weight: bold; padding: 8px; border-radius: 4px;")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background-color: #7f8c8d; color: white; padding: 8px; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def get_settings(self):
        return {
            "style": self.style_combo.currentText(),
            "negative_prompt": self.neg_prompt.toPlainText(),
            "steps": self.steps_spin.value(),
            "cfg_scale": self.cfg_spin.value()
        }

class ParamsEditorWidget(QWidget):
    def __init__(self, params, visible_fields=None, parent=None):
        super().__init__(parent)
        self.params = params or {}
        self.visible_fields = visible_fields
        self.widgets = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        content_widget = QWidget()
        form_layout = QVBoxLayout(content_widget)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(8) # Reasonable spacing between fields

        # Helper to add fields
        def add_field(label, key, widget_type=QLineEdit, options=None):
            if self.visible_fields is not None and key not in self.visible_fields:
                return None

            # Container for the field to keep label and input close
            field_container = QWidget()
            field_layout = QVBoxLayout(field_container)
            field_layout.setContentsMargins(0, 0, 0, 0) # No margin
            field_layout.setSpacing(2) # Tight spacing between label and input

            lbl = QLabel(label)
            lbl.setStyleSheet("color: #f1c40f; font-weight: bold; font-size: 12px; margin: 0px; padding: 0px;") 
            field_layout.addWidget(lbl)
            
            # If options provided, use ComboBox
            if options:
                widget = QComboBox()
                # Check if options are strings or tuples
                for opt in options:
                    if isinstance(opt, tuple):
                        widget.addItem(opt[0], opt[1])
                    else:
                        widget.addItem(opt)
                
                widget.setEditable(True)
                
                # Set current value
                current_val = self.params.get(key, "")
                # Try to find if current_val matches any data
                index = widget.findData(current_val)
                if index >= 0:
                    widget.setCurrentIndex(index)
                else:
                    widget.setCurrentText(current_val)
                    
                widget.setStyleSheet("""
                    QComboBox {
                        padding: 4px; 
                        background-color: #34495e; 
                        border: 1px solid #5d6d7e;
                        min-height: 24px;
                        margin: 0px;
                        border-radius: 3px;
                    }
                    QComboBox::drop-down {
                        border: none;
                        background: #2c3e50;
                        width: 20px;
                    }
                """)
            elif widget_type == QTextEdit:
                widget = QTextEdit()
                widget.setPlainText(self.params.get(key, ""))
                widget.setMaximumHeight(60) # Reduced height
                widget.setStyleSheet("padding: 4px; background-color: #34495e; border: 1px solid #5d6d7e; margin: 0px; border-radius: 3px;")
            else:
                widget = QLineEdit()
                widget.setText(self.params.get(key, ""))
                widget.setStyleSheet("padding: 4px; background-color: #34495e; border: 1px solid #5d6d7e; margin: 0px; border-radius: 3px;")
            
            field_layout.addWidget(widget)
            form_layout.addWidget(field_container)
            
            self.widgets[key] = widget
            return widget

        # Define Options
        
        # 1. Cinematography
        shot_type_opts = [
            ("无 (None)", ""),
            ("电影级中景 (Cinematic medium shot)", "Cinematic medium shot"),
            ("电影级特写 (Cinematic close-up shot)", "Cinematic close-up shot"),
            ("电影级广角 (Cinematic wide shot)", "Cinematic wide shot"),
            ("极度特写 (Extreme close-up shot)", "Extreme close-up shot"),
            ("牛仔镜头 (Cinematic cowboy shot)", "Cinematic cowboy shot"),
            ("过肩镜头 (Over-the-shoulder shot)", "Over-the-shoulder shot"),
            ("第一人称视角 (POV shot)", "POV shot"),
            ("车内镜头 (Interior car shot)", "Interior car shot"),
            ("双人镜头 (Cinematic two-shot)", "Cinematic two-shot"),
            ("群像镜头 (Cinematic group shot)", "Cinematic group shot"),
            ("航拍镜头 (Aerial shot)", "Aerial shot"),
            ("鱼眼镜头 (Fisheye shot)", "Fisheye shot"),
            ("微距镜头 (Macro shot)", "Macro shot")
        ]
        add_field("镜头类型 (Shot Type)", "shot_type", options=shot_type_opts)
        
        camera_movement_opts = [
            ("无 (None)", ""),
            ("固定镜头 (Static camera)", "Static camera"),
            ("跟随移动 (Tracking shot)", "Tracking shot following the movement"),
            ("希区柯克变焦 (Dolly zoom)", "Fast dolly zoom (vertigo effect)"),
            ("缓慢推进 (Slow push-in)", "Slow, steady push-in"),
            ("缓慢拉远 (Slow pull-out)", "Slow pull-out"),
            ("手持摇晃 (Handheld camera shake)", "Handheld camera shake"),
            ("左摇 (Pan left)", "Pan left"),
            ("右摇 (Pan right)", "Pan right"),
            ("上摇 (Tilt up)", "Tilt up"),
            ("下摇 (Tilt down)", "Tilt down"),
            ("环绕 (Orbit)", "Orbit")
        ]
        add_field("运镜方式 (Camera Movement)", "camera_movement", options=camera_movement_opts)
        
        viewpoint_opts = [
            ("无 (None)", ""),
            ("正视 (Eye-level)", "Eye-level"),
            ("俯视 (High angle)", "High angle"),
            ("仰视 (Low angle)", "Low angle"),
            ("侧视 (Side profile)", "Side profile"),
            ("顶视 (Top-down)", "Top-down"),
            ("虫视 (Worm's eye view)", "Worm's eye view"),
            ("荷兰角 (Dutch angle)", "Dutch angle"),
            ("自拍视角 (Selfie view)", "Selfie view")
        ]
        add_field("视角 (Viewpoint)", "viewpoint", options=viewpoint_opts)
        
        composition_opts = [
            ("无 (None)", ""),
            ("居中构图 (Centered composition)", "Centered composition"),
            ("三分法 (Rule of thirds)", "Rule of thirds"),
            ("对称构图 (Symmetrical composition)", "Symmetrical composition"),
            ("黄金比例 (Golden ratio)", "Golden ratio"),
            ("引导线 (Leading lines)", "Leading lines"),
            ("极简构图 (Minimalist)", "Minimalist"),
            ("景深虚化 (Depth of field)", "Depth of field"),
            ("框架构图 (Framing)", "Framing")
        ]
        add_field("构图与站位 (Composition)", "composition", options=composition_opts)
        
        lighting_opts = [
            ("无 (None)", ""),
            ("自然光 (Natural lighting)", "Natural lighting"),
            ("电影布光 (Cinematic lighting)", "Cinematic lighting"),
            ("柔光 (Soft lighting)", "Soft lighting"),
            ("侧光 (Side lighting)", "Side lighting"),
            ("逆光 (Backlighting)", "Backlighting"),
            ("伦勃朗光 (Rembrandt lighting)", "Rembrandt lighting"),
            ("赛博朋克霓虹 (Cyberpunk neon)", "Cyberpunk neon"),
            ("黄金时刻 (Golden hour)", "Golden hour"),
            ("蓝色时刻 (Blue hour)", "Blue hour"),
            ("阴郁光线 (Moody lighting)", "Moody lighting"),
            ("摄影棚光 (Studio lighting)", "Studio lighting"),
            ("体积光 (Volumetric lighting)", "Volumetric lighting")
        ]
        add_field("光线与色彩 (Lighting)", "lighting", options=lighting_opts)
        
        # 2. Subject & Action
        # For Subject and Action, we provide some generic enhancers but keep it editable
        subject_opts = [
            ("无 (None)", ""),
            ("高细节主体 (Highly detailed subject)", "Highly detailed subject"),
            ("写实风格 (Realistic style)", "Realistic style"),
            ("动漫风格 (Anime style)", "Anime style")
        ]
        add_field("主体描述 (Subject)", "subject", options=subject_opts)
        
        action_opts = [
            ("无 (None)", ""),
            ("静态 (Static)", "Static"),
            ("缓慢移动 (Slow motion)", "Slow motion"),
            ("快速移动 (Fast motion)", "Fast motion"),
            ("正在说话 (Talking)", "Talking"),
            ("正在行走 (Walking)", "Walking"),
            ("正在奔跑 (Running)", "Running"),
            ("正在大笑 (Laughing)", "Laughing"),
            ("正在哭泣 (Crying)", "Crying"),
            ("正在战斗 (Fighting)", "Fighting"),
            ("正在进食 (Eating)", "Eating")
        ]
        add_field("动作与神态 (Action)", "action", options=action_opts)
        
        # 3. Environment
        context_opts = [
            ("无 (None)", ""),
            ("模糊背景 (Blurred background)", "Blurred background"),
            ("详细背景 (Detailed background)", "Detailed background"),
            ("纯色背景 (Solid color background)", "Solid color background"),
            ("室内 (Indoor)", "Indoor"),
            ("室外 (Outdoor)", "Outdoor")
        ]
        add_field("环境背景 (Context)", "context", options=context_opts)
        
        style_opts = [
            ("无 (None)", ""),
            ("电影感 (Cinematic)", "Cinematic"),
            ("照片级真实 (Photorealistic)", "Photorealistic"),
            ("油画风格 (Oil painting)", "Oil painting"),
            ("水彩风格 (Watercolor)", "Watercolor"),
            ("赛博朋克 (Cyberpunk)", "Cyberpunk"),
            ("黑白电影 (Film noir)", "Film noir"),
            ("复古风格 (Vintage)", "Vintage")
        ]
        add_field("画面风格 (Style)", "style", options=style_opts)
        
        texture_opts = [
            ("无 (None)", ""),
            ("高分辨率 (8k resolution)", "8k resolution"),
            ("胶片颗粒 (Film grain)", "Film grain"),
            ("柔焦 (Soft focus)", "Soft focus"),
            ("锐利 (Sharp)", "Sharp")
        ]
        add_field("细节质感 (Texture)", "texture", options=texture_opts)
        
        audio_opts = [
            ("无 (None)", ""),
            ("无声 (Silent)", "Silent"),
            ("环境音 (Ambient noise)", "Ambient noise"),
            ("人声对话 (Dialogue)", "Dialogue"),
            ("背景音乐 (Background music)", "Background music"),
            ("嘈杂声 (Crowd noise)", "Crowd noise"),
            ("自然声 (Nature sounds)", "Nature sounds")
        ]
        add_field("音频/音效 (Audio - for Video)", "audio", options=audio_opts)
        
        # 4. Video Specific (Veo 3.1)
        env_dynamics_opts = [
            ("无 (None)", ""),
            ("风吹草动 (Wind blowing)", "Wind blowing"),
            ("下雨 (Raining)", "Raining"),
            ("下雪 (Snowing)", "Snowing"),
            ("烟雾缭绕 (Foggy)", "Foggy"),
            ("人群流动 (Crowd moving)", "Crowd moving"),
            ("车流穿梭 (Traffic moving)", "Traffic moving"),
            ("云层流动 (Clouds moving)", "Clouds moving"),
            ("水面波纹 (Water rippling)", "Water rippling")
        ]
        add_field("环境动态 (Environment Dynamics)", "environment_dynamics", options=env_dynamics_opts)
        
        lighting_dynamics_opts = [
            ("无 (None)", ""),
            ("光线闪烁 (Flickering light)", "Flickering light"),
            ("阳光移动 (Sunlight moving)", "Sunlight moving"),
            ("阴影变化 (Shadows shifting)", "Shadows shifting"),
            ("霓虹闪烁 (Neon blinking)", "Neon blinking"),
            ("闪电 (Lightning)", "Lightning")
        ]
        add_field("光影动态 (Lighting Dynamics)", "lighting_dynamics", options=lighting_dynamics_opts)
        
        video_config_opts = [
            ("默认 (Default)", ""),
            ("高质量 (High Quality)", "High Quality"),
            ("高帧率 (High FPS)", "High FPS")
        ]
        add_field("视频参数 (Video Config)", "video_config", options=video_config_opts)

        form_layout.addStretch() 
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def get_params(self):
        result = self.params.copy()
        for key, widget in self.widgets.items():
            if isinstance(widget, QComboBox):
                # Prefer itemData if available, else currentText
                val = widget.currentData()
                if val is None:
                    val = widget.currentText()
                result[key] = val
            elif isinstance(widget, QTextEdit):
                result[key] = widget.toPlainText()
            elif isinstance(widget, QLineEdit):
                result[key] = widget.text()
        return result

class PromptParamsDialog(QDialog):
    def __init__(self, image_params, video_params, parent=None):
        super().__init__(parent)
        self.setWindowTitle("提示词参数调整")
        self.resize(500, 600) # Reduced size
        
        self.setStyleSheet("background-color: #2c3e50; color: white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Tabs
        from PyQt6.QtWidgets import QTabWidget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #5d6d7e; background-color: #34495e; }
            QTabBar::tab { background-color: #2c3e50; color: #bdc3c7; padding: 8px 15px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #34495e; color: white; font-weight: bold; }
        """)
        
        # Define visible fields based on user preference
        # Image: Shot Type, Viewpoint, Composition, Lighting (Subject, Action, Style, Context, Texture hidden)
        self.image_fields = ['shot_type', 'viewpoint', 'composition', 'lighting']
        
        # Video: Action, Audio, Camera Movement, Environment Dynamics, Lighting Dynamics, Video Config
        self.video_fields = ['action', 'audio', 'camera_movement', 'environment_dynamics', 'lighting_dynamics', 'video_config']
        
        self.image_editor = ParamsEditorWidget(image_params, visible_fields=self.image_fields)
        self.video_editor = ParamsEditorWidget(video_params, visible_fields=self.video_fields)
        
        self.tab_widget.addTab(self.image_editor, "图片参数 (Image)")
        self.tab_widget.addTab(self.video_editor, "视频参数 (Video)")
        
        layout.addWidget(self.tab_widget)

        # Buttons
        btn_layout = QHBoxLayout()
        
        # Sync Button Removed as requested
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("保存参数")
        save_btn.setStyleSheet("background-color: #f1c40f; color: #2c3e50; font-weight: bold; padding: 10px; border-radius: 5px;")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background-color: #7f8c8d; color: white; padding: 10px; border-radius: 5px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_image_params(self):
        return self.image_editor.get_params()

    def get_video_params(self):
        return self.video_editor.get_params()

class ImageGenThread(QThread):
    finished = pyqtSignal(str, str, str) # panel_id, image_path, image_url
    error = pyqtSignal(str, str, str)    # panel_id, error_message, image_url
    status = pyqtSignal(str)        # status message

    def __init__(self, panel_id, prompt, output_path, api_config, ref_images=None, gen_settings=None, ratio="16:9", resolution="1080P"):
        super().__init__()
        self.panel_id = panel_id
        self.prompt = prompt
        self.output_path = output_path
        self.api_config = api_config or {}
        self.ref_images = ref_images or []
        self.gen_settings = gen_settings or {}
        self.ratio = ratio
        self.resolution = resolution

    def run(self):
        try:
            api_key = self.api_config.get("api_key")
            base_url = self.api_config.get("base_url")
            model = self.api_config.get("model")
            provider = self.api_config.get("provider")
            
            final_prompt = self.prompt
            
            # Clean up existing style in prompt if we are enforcing a project style
            if self.gen_settings.get("style") and self.gen_settings.get("style") != "None":
                import re
                # Remove "Style: xxx." or "Style: xxx," case insensitive
                final_prompt = re.sub(r'Style:\s*[^.,]+[.,]?', '', final_prompt, flags=re.IGNORECASE)
                final_prompt = final_prompt.strip()
                # Clean up double spaces
                final_prompt = re.sub(r'\s+', ' ', final_prompt)
            
            if self.ref_images:
                final_prompt += f" --with-ref-images"

            # Add ratio and resolution to settings
            settings = self.gen_settings.copy()
            settings['aspect_ratio'] = self.ratio
            settings['resolution'] = self.resolution

            client = ImageGenClient(api_key=api_key, base_url=base_url, model=model, provider=provider)
            
            # Pass status callback
            def update_status(msg):
                self.status.emit(msg)
                
            result = client.generate_image(final_prompt, self.output_path, self.ref_images, settings, status_callback=update_status)
            
            # Handle both tuple (path, url) and legacy string path
            image_path = None
            image_url = ""
            if isinstance(result, tuple) and len(result) == 2:
                image_path, image_url = result
            else:
                image_path = result
            
            if image_path:
                self.finished.emit(self.panel_id, image_path, image_url or "")
            else:
                # Even on failure, pass the URL if available for retry
                self.error.emit(self.panel_id, "生成失败: 未返回图片路径", image_url or "")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Try to get URL even on exception (might be download error after successful generation)
            image_url = ""
            error_msg = str(e)
            
            # First try: check if we have result tuple
            try:
                if 'result' in locals() and isinstance(result, tuple) and len(result) >= 2:
                    image_url = result[1] or ""
            except:
                pass
            
            # Second try: extract URL from error message (format: "下载失败: xxx. URL: http...")
            if not image_url and "URL: " in error_msg:
                try:
                    url_part = error_msg.split("URL: ", 1)[1]
                    # URL might end with quote, newline, or be at end of string
                    image_url = url_part.strip().rstrip("'\"")
                    print(f"[DEBUG] Extracted URL from error message: {image_url[:50]}...")
                except:
                    pass
            
            self.error.emit(self.panel_id, error_msg, image_url)

class ShotListItem(QWidget):
    deleted = pyqtSignal(str)
    regenerate = pyqtSignal(str) # Signal to regenerate this panel

    def __init__(self, index, panel, shot_number_in_scene=None, parent=None):
        super().__init__(parent)
        self.panel = panel
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Index (Try to parse from panel_id if possible, else use index)
        display_idx = f"{index:02d}"
        if self.panel and self.panel.panel_id:
            # Try to extract number from p_1, p_2 etc.
            import re
            match = re.search(r'(\d+)', self.panel.panel_id)
            if match:
                try:
                    num = int(match.group(1))
                    display_idx = f"{num:02d}"
                except: pass
        
        self.idx_lbl = QLabel(display_idx)
        self.idx_lbl.setStyleSheet("color: #bdc3c7; font-weight: bold; font-size: 14px;")
        self.idx_lbl.setFixedWidth(25)
        self.idx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.idx_lbl)
        
        # Center Content (Image + Info)
        center_layout = QVBoxLayout()
        center_layout.setSpacing(2)
        
        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setFixedSize(120, 68) # 16:9 ratio
        self.thumb.setStyleSheet("background-color: #34495e; border: 1px solid #5d6d7e; border-radius: 4px;")
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_thumb()
        
        center_layout.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Info
        if shot_number_in_scene is not None:
            info_text = f"场景{panel.scene_id} - 分镜{shot_number_in_scene}"
        else:
            # Clean up panel ID for display
            pid_display = str(panel.panel_id)
            if pid_display.startswith("p_"):
                pid_display = pid_display[2:]
            info_text = f"场景{panel.scene_id} - 分镜{pid_display}"

        self.info_lbl = QLabel(info_text)
        self.info_lbl.setStyleSheet("color: #95a5a6; font-size: 10px;")
        self.info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.info_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addLayout(center_layout)
        
        # Right Side Buttons (Delete + Regenerate)
        right_btn_layout = QVBoxLayout()
        right_btn_layout.setContentsMargins(0, 0, 0, 0)
        right_btn_layout.setSpacing(5)
        
        # Delete Button
        self.del_btn = QPushButton("×")
        self.del_btn.setFixedSize(20, 20)
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setStyleSheet("""
            QPushButton { color: #5d6d7e; background: transparent; border: none; font-weight: bold; font-size: 16px; }
            QPushButton:hover { color: #e74c3c; background-color: rgba(255, 255, 255, 0.1); border-radius: 10px; }
        """)
        self.del_btn.clicked.connect(self.on_delete)
        right_btn_layout.addWidget(self.del_btn, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        # Regenerate Button (Moved here, light gray)
        self.regen_btn = QPushButton("↻") # Use refresh icon instead of lightning
        self.regen_btn.setFixedSize(20, 20)
        self.regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.regen_btn.setToolTip("刷新分镜信息 (从剧本同步)")
        self.regen_btn.setStyleSheet("""
            QPushButton { 
                color: #7f8c8d; 
                background: transparent; 
                border: none; 
                font-weight: bold; 
                font-size: 14px; 
            }
            QPushButton:hover { 
                color: #bdc3c7; 
                background-color: rgba(255, 255, 255, 0.1); 
                border-radius: 10px; 
            }
        """)
        self.regen_btn.clicked.connect(self.on_regenerate)
        right_btn_layout.addWidget(self.regen_btn, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        
        right_btn_layout.addStretch()
        layout.addLayout(right_btn_layout)

    def on_delete(self):
        self.deleted.emit(self.panel.panel_id)
        
    def on_regenerate(self):
        # No confirmation needed for data refresh
        self.regenerate.emit(self.panel.panel_id)

    def update_thumb(self):
        if not self.panel:
            return
            
        if self.panel.image_path and os.path.exists(self.panel.image_path):
            pix = QPixmap(self.panel.image_path)
            if not pix.isNull():
                self.thumb.setPixmap(pix.scaled(120, 68, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
            else:
                self.thumb.setText("Error")
            
            # Overlay video icon if animated
            if getattr(self.panel, 'is_animated', False) and getattr(self.panel, 'video_path', None):
                self.thumb.setStyleSheet("background-color: #34495e; border: 2px solid #f1c40f; border-radius: 4px;")
            else:
                self.thumb.setStyleSheet("background-color: #34495e; border: 1px solid #5d6d7e; border-radius: 4px;")
                
        else:
            self.thumb.setText("No Img")
            self.thumb.setStyleSheet("background-color: #34495e; border: 1px solid #5d6d7e; border-radius: 4px;")

class StoryboardWindow(QWidget):
    def __init__(self, project_dir):
        super().__init__()
        self.project_dir = project_dir
        self.current_script = None
        self.current_storyboard = None
        self.config_manager = ConfigManager()
        self.current_panel_index = -1
        self.current_episode_id = None # Track current episode for Series
        self.image_gen_settings = {}
        self.project_style = self.load_project_style()
        self.init_ui()

    def load_project_style(self):
        try:
            if not self.project_dir:
                return ""
            project_json = os.path.join(self.project_dir, "project.json")
            if os.path.exists(project_json):
                with open(project_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Update project name label if it exists
                    if hasattr(self, 'project_name_lbl'):
                        self.project_name_lbl.setText(data.get("name", "未命名项目"))
                    return data.get("visual_style", "")
        except Exception as e:
            print(f"Error loading project style: {e}")
        return ""

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Sidebar (Shot List) ---
        left_sidebar = QFrame()
        left_sidebar.setFixedWidth(280)
        left_sidebar.setStyleSheet("background-color: #2c3e50; border-right: 1px solid #34495e;")
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Top Controls
        top_ctrls = QFrame()
        top_ctrls.setStyleSheet("background-color: #34495e; border-radius: 5px; padding: 5px;")
        tc_layout = QVBoxLayout(top_ctrls)
        
        # Project Name Label
        self.project_name_lbl = QLabel("")
        self.project_name_lbl.setStyleSheet("color: #f1c40f; font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        self.project_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tc_layout.addWidget(self.project_name_lbl)
        
        # Episode Selector (Visible only for Series)
        self.episode_frame = QFrame()
        self.episode_frame.setVisible(False)
        ep_layout = QHBoxLayout(self.episode_frame)
        ep_layout.setContentsMargins(0, 0, 0, 5)
        
        lbl_ep = QLabel("剧集:")
        lbl_ep.setStyleSheet("color: #bdc3c7;")
        ep_layout.addWidget(lbl_ep)
        
        self.episode_combo = QComboBox()
        self.episode_combo.setStyleSheet("background-color: #2c3e50; color: white; border: 1px solid #5d6d7e;")
        self.episode_combo.currentIndexChanged.connect(self.on_episode_changed)
        ep_layout.addWidget(self.episode_combo)
        
        tc_layout.addWidget(self.episode_frame)
        
        # Speed and Narrator info removed as requested
        
        left_layout.addWidget(top_ctrls)
        
        # Auto Identify Button
        auto_btn = QPushButton("自动识别分镜")
        auto_btn.setStyleSheet("background-color: #34495e; color: white; padding: 8px; margin-top: 10px;")
        auto_btn.clicked.connect(self.generate_panels)
        left_layout.addWidget(auto_btn)
        
        # List
        self.shot_list = QListWidget()
        self.shot_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; outline: none; }
            QListWidget::item { background-color: #2c3e50; margin-bottom: 5px; border-radius: 5px; }
            QListWidget::item:selected { background-color: #2980b9; border: 1px solid #f1c40f; }
        """)
        self.shot_list.currentRowChanged.connect(self.on_shot_selected)
        self.shot_list.itemClicked.connect(self.on_item_clicked)
        left_layout.addWidget(self.shot_list)
        
        main_layout.addWidget(left_sidebar)

        # --- Center Area (Canvas) ---
        center_area = QWidget()
        center_area.setStyleSheet("background-color: #1e272e;")
        center_layout = QVBoxLayout(center_area)
        center_layout.setContentsMargins(20, 20, 20, 20)
        
        # Splitter for Image Area vs History
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2c3e50;
                border-radius: 4px;
            }
            QSplitter::handle:hover {
                background-color: #3498db;
            }
        """)
        
        # Top Container (Image + Toolbar + Subtitle)
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top Container (Image + Toolbar + Subtitle)
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Preview Stack (Image / Video)
        self.preview_stack = QStackedWidget()
        self.preview_stack.setMinimumHeight(300)
        
        # Page 0: Image Display
        self.image_display = QLabel()
        self.image_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display.setStyleSheet("background-color: #000; border-radius: 5px;")
        self.preview_stack.addWidget(self.image_display)
        
        # Page 1: Video Display
        self.video_player = VideoPlayerWidget()
        self.preview_stack.addWidget(self.video_player)
        
        top_layout.addWidget(self.preview_stack, 1) # Stretch factor 1
        
        # History Controls (Version Navigation)
        self.history_ctrl_widget = QWidget()
        hc_layout = QHBoxLayout(self.history_ctrl_widget)
        hc_layout.setContentsMargins(0, 0, 0, 0)
        hc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.prev_ver_btn = QPushButton("◀ 上一版")
        self.prev_ver_btn.setFixedSize(80, 24)
        self.prev_ver_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e; 
                color: white; 
                border: 1px solid #5d6d7e; 
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #2c3e50;
                color: #7f8c8d;
                border: 1px solid #34495e;
            }
            QPushButton:hover:!disabled {
                background-color: #4e6d8d;
            }
        """)
        self.prev_ver_btn.clicked.connect(self.show_prev_version)
        hc_layout.addWidget(self.prev_ver_btn)
        
        self.ver_lbl = QLabel("Version 1/1")
        self.ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ver_lbl.setStyleSheet("color: #bdc3c7; font-weight: bold; margin: 0 10px;")
        hc_layout.addWidget(self.ver_lbl)
        
        self.next_ver_btn = QPushButton("下一版 ▶")
        self.next_ver_btn.setFixedSize(80, 24)
        self.next_ver_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e; 
                color: white; 
                border: 1px solid #5d6d7e; 
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #2c3e50;
                color: #7f8c8d;
                border: 1px solid #34495e;
            }
            QPushButton:hover:!disabled {
                background-color: #4e6d8d;
            }
        """)
        self.next_ver_btn.clicked.connect(self.show_next_version)
        hc_layout.addWidget(self.next_ver_btn)
        
        top_layout.addWidget(self.history_ctrl_widget)

        # View Toggle (Image | Video)
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 5, 0, 5)
        toggle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)
        
        self.btn_view_img = QPushButton("图片预览")
        self.btn_view_img.setCheckable(True)
        self.btn_view_img.setChecked(True)
        self.btn_view_img.setFixedSize(100, 30)
        self.btn_view_img.setStyleSheet("""
            QPushButton { background-color: #34495e; color: #bdc3c7; border: 1px solid #5d6d7e; border-top-left-radius: 15px; border-bottom-left-radius: 15px; }
            QPushButton:checked { background-color: #f1c40f; color: #2c3e50; font-weight: bold; border: 1px solid #f1c40f; }
        """)
        self.btn_view_img.clicked.connect(lambda: self.switch_preview_mode(0))
        
        self.btn_view_video = QPushButton("视频预览")
        self.btn_view_video.setCheckable(True)
        self.btn_view_video.setFixedSize(100, 30)
        self.btn_view_video.setStyleSheet("""
            QPushButton { background-color: #34495e; color: #bdc3c7; border: 1px solid #5d6d7e; border-top-right-radius: 15px; border-bottom-right-radius: 15px; border-left: none; }
            QPushButton:checked { background-color: #e67e22; color: white; font-weight: bold; border: 1px solid #e67e22; }
            QPushButton:disabled { background-color: #2c3e50; color: #4a6278; border-color: #34495e; }
        """)
        self.btn_view_video.clicked.connect(lambda: self.switch_preview_mode(1))
        
        self.view_group.addButton(self.btn_view_img)
        self.view_group.addButton(self.btn_view_video)
        
        toggle_layout.addWidget(self.btn_view_img)
        toggle_layout.addWidget(self.btn_view_video)
        
        top_layout.addWidget(toggle_container)
        
        # Subtitle Area
        sub_frame = QFrame()
        sub_frame.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")
        sub_layout = QHBoxLayout(sub_frame)
        self.subtitle_lbl = QLabel("字幕内容...")
        self.subtitle_lbl.setWordWrap(True)
        self.subtitle_lbl.setStyleSheet("color: white; font-size: 14px;")
        sub_layout.addWidget(self.subtitle_lbl)
        top_layout.addWidget(sub_frame)
        
        splitter.addWidget(top_container)
        
        # History Gallery
        history_scroll = QScrollArea()
        history_scroll.setMinimumHeight(100)
        history_scroll.setWidgetResizable(True)
        history_scroll.setStyleSheet("border: none; background: transparent;")
        
        self.history_widget = QWidget()
        self.history_layout = QHBoxLayout(self.history_widget)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        history_scroll.setWidget(self.history_widget)
        
        # Add Custom Image Button
        self.add_img_btn = QPushButton("+ Upload")
        self.add_img_btn.setFixedSize(80, 100)
        self.add_img_btn.setStyleSheet("background-color: #34495e; color: white; border: 1px dashed #7f8c8d;")
        self.add_img_btn.clicked.connect(self.upload_image)
        self.history_layout.addWidget(self.add_img_btn)
        
        splitter.addWidget(history_scroll)
        
        # Set initial sizes
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        
        center_layout.addWidget(splitter)
        
        main_layout.addWidget(center_area)

        # --- Right Sidebar (Controls) ---
        right_sidebar = QFrame()
        right_sidebar.setFixedWidth(300)
        right_sidebar.setStyleSheet("background-color: #2c3e50; border-left: 1px solid #34495e;")
        right_main_layout = QVBoxLayout(right_sidebar)
        right_main_layout.setContentsMargins(0, 0, 0, 0)
        right_main_layout.setSpacing(0)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #2c3e50; }")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        right_layout = QVBoxLayout(scroll_content)
        right_layout.setContentsMargins(15, 15, 15, 15)
        
        # Characters
        lbl_chars = QLabel("出镜角色")
        lbl_chars.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        right_layout.addWidget(lbl_chars)
        
        self.char_list_widget = QWidget()
        self.char_list_layout = QVBoxLayout(self.char_list_widget)
        self.char_list_layout.setContentsMargins(0, 0, 0, 0)
        self.char_list_layout.setSpacing(5)
        right_layout.addWidget(self.char_list_widget)

        self.char_btn = QPushButton("+ 增加角色")
        self.char_btn.setStyleSheet("background-color: #34495e; color: white; padding: 8px; border: 1px dashed #7f8c8d;")
        self.char_btn.clicked.connect(self.add_character)
        right_layout.addWidget(self.char_btn)
        
        # Reference Image Button
        self.add_ref_btn = QPushButton("+ 添加参考图")
        self.add_ref_btn.setStyleSheet("background-color: #34495e; color: white; padding: 8px; border: 1px dashed #7f8c8d; margin-top: 5px;")
        self.add_ref_btn.clicked.connect(self.add_reference_image)
        right_layout.addWidget(self.add_ref_btn)
        
        # Reference Image Display
        self.ref_img_widget = QWidget()
        self.ref_img_widget.setVisible(False)
        ref_layout = QHBoxLayout(self.ref_img_widget)
        ref_layout.setContentsMargins(0, 5, 0, 0)
        
        self.ref_img_lbl = QLabel()
        self.ref_img_lbl.setFixedSize(60, 60)
        self.ref_img_lbl.setStyleSheet("background-color: #000; border: 1px solid #5d6d7e;")
        self.ref_img_lbl.setScaledContents(True)
        ref_layout.addWidget(self.ref_img_lbl)
        
        self.ref_img_del_btn = QPushButton("×")
        self.ref_img_del_btn.setFixedSize(20, 20)
        self.ref_img_del_btn.setStyleSheet("color: #e74c3c; background: transparent; font-weight: bold; border: none;")
        self.ref_img_del_btn.clicked.connect(self.remove_reference_image)
        ref_layout.addWidget(self.ref_img_del_btn)
        
        ref_layout.addStretch()
        right_layout.addWidget(self.ref_img_widget)
        
        right_layout.addSpacing(10)

        # Scene Environment
        lbl_env = QLabel("场景环境")
        lbl_env.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        right_layout.addWidget(lbl_env)
        
        self.env_info_lbl = QLabel("Location: Unknown")
        self.env_info_lbl.setWordWrap(True)
        self.env_info_lbl.setStyleSheet("color: #95a5a6; font-size: 12px;")
        right_layout.addWidget(self.env_info_lbl)
        
        # Scene Selection Button
        self.scene_select_btn = QPushButton("已设置参考图 (点击更换)")
        self.scene_select_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; border: none; border-radius: 3px;")
        self.scene_select_btn.clicked.connect(self.open_scene_library)
        self.scene_select_btn.setVisible(False)
        right_layout.addWidget(self.scene_select_btn)
        
        self.env_img_btn = QPushButton("设置环境参考图")
        self.env_img_btn.setStyleSheet("background-color: #34495e; color: white; padding: 8px; border: 1px dashed #7f8c8d;")
        self.env_img_btn.clicked.connect(self.set_scene_environment)
        right_layout.addWidget(self.env_img_btn)
        
        right_layout.addSpacing(10)
        
        # Prompt
        prompt_header = QHBoxLayout()
        lbl_prompt = QLabel("提示词")
        lbl_prompt.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        prompt_header.addWidget(lbl_prompt)
        
        prompt_header.addStretch()
        
        self.edit_params_btn = QPushButton("🎨 提示词参数")
        self.edit_params_btn.setFixedSize(80, 24)
        self.edit_params_btn.setStyleSheet("background-color: #34495e; color: #f1c40f; border: 1px solid #f1c40f; border-radius: 3px; font-size: 11px;")
        self.edit_params_btn.clicked.connect(self.open_params_dialog)
        prompt_header.addWidget(self.edit_params_btn)
        
        right_layout.addLayout(prompt_header)
        
        # Tab Widget for Image/Video Prompts
        from PyQt6.QtWidgets import QTabWidget
        self.prompt_tabs = QTabWidget()
        self.prompt_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #5d6d7e; background-color: #34495e; }
            QTabBar::tab { background-color: #2c3e50; color: #bdc3c7; padding: 5px 10px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #34495e; color: white; font-weight: bold; }
        """)
        
        # Image Prompt Tab
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("输入画面描述 (Image Prompt)...")
        self.prompt_edit.setStyleSheet("background-color: #34495e; color: white; border: none; padding: 5px;")
        self.prompt_edit.setMaximumHeight(200) # Increased height since it now holds more info
        self.prompt_edit.textChanged.connect(self.save_current_prompt) # Auto-save changes
        self.prompt_tabs.addTab(self.prompt_edit, "图片提示词")
        
        # Video Prompt Tab
        self.video_prompt_edit = QTextEdit()
        self.video_prompt_edit.setPlaceholderText("输入视频描述 (Video Prompt)...")
        self.video_prompt_edit.setStyleSheet("background-color: #34495e; color: white; border: none; padding: 5px;")
        self.video_prompt_edit.setMaximumHeight(150)
        self.video_prompt_edit.textChanged.connect(self.on_video_prompt_changed)
        self.prompt_tabs.addTab(self.video_prompt_edit, "视频提示词")
        
        right_layout.addWidget(self.prompt_tabs)
        
        # API Config
        lbl_model = QLabel("生图模型")
        lbl_model.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        right_layout.addWidget(lbl_model)
        self.api_combo = QComboBox()
        self.refresh_api_list()
        right_layout.addWidget(self.api_combo)

        # Settings Button
        self.settings_btn = QPushButton("⚙️ 高级参数设置")
        self.settings_btn.setStyleSheet("background-color: #34495e; color: #bdc3c7; border: 1px solid #5d6d7e; padding: 5px;")
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        right_layout.addWidget(self.settings_btn)
        
        right_layout.addStretch()
        
        # End of scrollable content
        scroll_area.setWidget(scroll_content)
        right_main_layout.addWidget(scroll_area, 1)  # Stretch to fill
        
        # Fixed bottom section with action buttons
        bottom_separator = QFrame()
        bottom_separator.setFrameShape(QFrame.Shape.HLine)
        bottom_separator.setStyleSheet("background-color: #34495e;")
        bottom_separator.setFixedHeight(1)
        right_main_layout.addWidget(bottom_separator)
        
        bottom_container = QWidget()
        bottom_container.setStyleSheet("background-color: #2c3e50;")
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(15, 10, 15, 15)
        bottom_layout.setSpacing(10)
        
        # Regenerate
        self.regen_btn = QPushButton("⚡ 重绘画面")
        self.regen_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1c40f;
                color: #2c3e50;
                font-weight: bold;
                font-size: 16px;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #f39c12; }
        """)
        self.regen_btn.clicked.connect(self.regenerate_current_panel)
        bottom_layout.addWidget(self.regen_btn)
        
        # Retry fetch image button
        self.retry_image_btn = QPushButton("🔄 重新获取图片")
        self.retry_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.retry_image_btn.setVisible(False)
        self.retry_image_btn.clicked.connect(self.retry_fetch_image)
        bottom_layout.addWidget(self.retry_image_btn)
        
        # Motion
        motion_group = QFrame()
        motion_group.setStyleSheet("background-color: #34495e; border-radius: 5px; padding: 10px;")
        mg_layout = QVBoxLayout(motion_group)
        
        self.animate_btn = QPushButton("🎥 生成视频")
        self.animate_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        self.animate_btn.clicked.connect(self.open_batch_video_dialog)
        mg_layout.addWidget(self.animate_btn)
        
        self.retry_video_btn = QPushButton("🔄 重新获取视频")
        self.retry_video_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #7f8c8d;
            }
        """)
        self.retry_video_btn.setVisible(False)  # Hide by default
        self.retry_video_btn.clicked.connect(self.retry_fetch_video)
        mg_layout.addWidget(self.retry_video_btn)
        
        bottom_layout.addWidget(motion_group)
        
        right_main_layout.addWidget(bottom_container, 0)  # No stretch, fixed at bottom
        
        main_layout.addWidget(right_sidebar)

    def refresh_api_list(self):
        self.api_combo.clear()
        configs = self.config_manager.get("api_configs", [])
        img_configs = [c for c in configs if c.get("type") == "Image"]
        
        default_index = 0
        for i, config in enumerate(img_configs):
            self.api_combo.addItem(config.get("name", "Unnamed"), config)
            if config.get("is_default"):
                default_index = i
            
        if self.api_combo.count() == 0:
             self.api_combo.addItem("未配置 (使用默认/Mock)", {})
        else:
            self.api_combo.setCurrentIndex(default_index)

    def set_current_episode(self, episode_id):
        self.current_episode_id = episode_id
        # Update combo box without triggering signal loop
        self.episode_combo.blockSignals(True)
        index = self.episode_combo.findData(episode_id)
        if index >= 0:
            self.episode_combo.setCurrentIndex(index)
        self.episode_combo.blockSignals(False)
        
        self.load_existing_data()

    def on_episode_changed(self, index):
        if index < 0:
            return
        episode_id = self.episode_combo.itemData(index)
        if episode_id != self.current_episode_id:
            self.current_episode_id = episode_id
            self.load_existing_data()

    def load_existing_data(self):
        """Auto-loads script and storyboard if available."""
        if not self.project_dir:
            return

        # Check for Series
        series_path = os.path.join(self.project_dir, "series.json")
        if os.path.exists(series_path):
            self.episode_frame.setVisible(True)
            try:
                with open(series_path, 'r', encoding='utf-8') as f:
                    series_data = json.load(f)
                
                episodes = series_data.get("episodes", [])
                
                # Populate combo if empty or needs refresh
                # Simple check: count mismatch or just reload
                self.episode_combo.blockSignals(True)
                current_data = self.episode_combo.currentData()
                self.episode_combo.clear()
                
                for ep in episodes:
                    self.episode_combo.addItem(f"第{ep['id']}集: {ep['title']}", ep['id'])
                
                # Restore selection or default
                if self.current_episode_id:
                    idx = self.episode_combo.findData(self.current_episode_id)
                    if idx >= 0:
                        self.episode_combo.setCurrentIndex(idx)
                elif episodes:
                    # Default to first episode if none selected
                    self.current_episode_id = episodes[0]['id']
                    self.episode_combo.setCurrentIndex(0)
                    
                self.episode_combo.blockSignals(False)
                
            except Exception as e:
                print(f"Error loading series data: {e}")
        else:
            self.episode_frame.setVisible(False)
            self.current_episode_id = None

        # Determine paths based on episode
        if self.current_episode_id:
            script_path = os.path.join(self.project_dir, "scripts", f"episode_{self.current_episode_id}.json")
            sb_dir = os.path.join(self.project_dir, "storyboards")
            os.makedirs(sb_dir, exist_ok=True)
            sb_path = os.path.join(sb_dir, f"episode_{self.current_episode_id}.json")
        else:
            script_path = os.path.join(self.project_dir, "current_script.json")
            sb_path = os.path.join(self.project_dir, "storyboard.json")

        # Load Project Name
        try:
            project_json_path = os.path.join(self.project_dir, "project.json")
            if os.path.exists(project_json_path):
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    project_name = project_data.get("name", "未命名项目")
                    if hasattr(self, 'project_name_lbl'):
                        self.project_name_lbl.setText(project_name)
        except Exception as e:
            print(f"Error loading project name: {e}")

        # Load Script
        self.current_script = None
        if os.path.exists(script_path):
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    self.current_script = Script.from_json(f.read())
            except:
                pass

        # Load Storyboard
        self.current_storyboard = None
        self.shot_list.clear()
        if os.path.exists(sb_path):
            try:
                with open(sb_path, 'r', encoding='utf-8') as f:
                    self.current_storyboard = Storyboard.from_json(f.read())
                self.refresh_shot_list()
            except:
                pass

    def load_script_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "打开剧本", self.project_dir, "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.current_script = Script.from_json(f.read())
                QMessageBox.information(self, "已加载", f"已加载剧本: {self.current_script.title}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载剧本失败: {e}")

    def get_character_map(self):
        """Reads all characters and returns a dict {name: Character}."""
        char_map = {}
        try:
            resources_dir = os.path.dirname(os.path.dirname(self.project_dir))
            char_dir = os.path.join(resources_dir, "characters")
            
            if os.path.exists(char_dir):
                for root, dirs, files in os.walk(char_dir):
                    for file in files:
                        if file.endswith(".json"):
                            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                                c = Character.from_json(f.read())
                                char_map[c.name] = c
        except Exception as e:
            print(f"Error loading characters: {e}")
        return char_map

    def generate_panels(self):
        if not self.current_script:
            QMessageBox.warning(self, "错误", "请先加载剧本。")
            return

        # Check if storyboard already exists and has content
        if self.current_storyboard and self.current_storyboard.panels:
            has_content = any(p.image_path or p.video_path for p in self.current_storyboard.panels)
            if has_content:
                reply = QMessageBox.question(
                    self, 
                    "确认重新生成", 
                    "当前分镜中已包含生成的图片或视频。\n重新识别分镜将清空所有现有内容！\n\n是否继续？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

        # Show loading (Mock)
        progress = QProgressBar(self)
        progress.setWindowFlags(Qt.WindowType.Dialog)
        progress.setWindowTitle("智能拆解中...")
        progress.setRange(0, 0)
        progress.show()
        
        # Simulate delay
        QThread.msleep(500)
        progress.close()

        self.current_storyboard = Storyboard(script_title=self.current_script.title)
        char_map = self.get_character_map()
        
        # Group dialogues to optimize storyboard count
        grouped_shots = [] # List of (scene, [dialogue_list])
        
        for scene in self.current_script.scenes:
            if not scene.dialogues:
                continue
                
            current_group = []
            
            for dialogue in scene.dialogues:
                # Determine if this dialogue starts a new visual shot
                is_new_shot = False
                
                if not current_group:
                    current_group.append(dialogue)
                    continue
                
                last_dialogue = current_group[-1]
                
                # 优化的合并策略：尽量减少分镜数量
                # Heuristic 1: 显著的场景动作变化（长动作描述）
                has_significant_action = len(dialogue.action) > 20  # 提高阈值从10到20
                
                # Heuristic 2: 关键动作词检测
                # 只有当出现明显的视觉变化关键词时才分镜
                action_keywords = ['走向', '离开', '进入', '转身', '站起', '坐下', '打开', '关闭', 
                                   '拿起', '放下', '冲向', '跑向', '看向', '指向', '推开', '拉开']
                has_key_action = any(keyword in dialogue.action for keyword in action_keywords)
                
                # Heuristic 3: 说话人变化 + 长动作
                # 仅当说话人变化且有较长动作描述时才分镜
                speaker_changed = dialogue.role != last_dialogue.role
                has_long_action = len(dialogue.action) > 15
                
                # Heuristic 4: 对话内容长度检测
                # 如果对话内容很短（<10字）且没有动作，倾向于合并
                is_short_dialogue = len(dialogue.content) < 10
                
                # 决策逻辑：更倾向于合并
                if has_significant_action:
                    is_new_shot = True
                elif has_key_action and has_long_action:
                    is_new_shot = True
                elif speaker_changed and has_long_action:
                    is_new_shot = True
                elif len(current_group) >= 5:  # 提高合并阈值从4到5
                    is_new_shot = True
                # 短对话自动合并，不管说话人是否变化
                elif is_short_dialogue and not has_key_action:
                    is_new_shot = False
                
                if is_new_shot:
                    grouped_shots.append((scene, current_group))
                    current_group = [dialogue]
                else:
                    current_group.append(dialogue)
            
            if current_group:
                grouped_shots.append((scene, current_group))

        count = 0
        for i, (scene, dialogue_list) in enumerate(grouped_shots):
            count += 1
            
            primary_dialogue = dialogue_list[0]
            
            # Detect all characters in this shot (from ALL dialogues in group)
            present_chars = [] # List of (name, description)
            panel_char_ids = [] # List of IDs for the panel object
            seen_char_names = set()

            # Helper to add char
            def add_char(name):
                if name in seen_char_names: return
                
                # Filter out Narrator/Voiceover roles from visual characters
                if name in ["旁白", "画外音", "Narrator", "Voiceover", "OS", "字幕"]:
                    return

                seen_char_names.add(name)
                char_obj = char_map.get(name)
                if char_obj:
                    present_chars.append((char_obj.name, char_obj.appearance_features))
                    panel_char_ids.append(char_obj.id)
                else:
                    # Only add non-library characters if they seem like real names (simple heuristic)
                    # For now, just add them but we'll handle empty descriptions in the factory
                    present_chars.append((name, ""))

            # 1. Add speakers
            for d in dialogue_list:
                add_char(d.role)

            # 2. Detect others in Action or Content
            for d in dialogue_list:
                for char_name, char_obj in char_map.items():
                    if char_name in seen_char_names: continue
                    if char_name in d.action or char_name in d.content:
                        add_char(char_name)
            
            # Lookahead
            next_scene = None
            next_dialogue = None
            if i < len(grouped_shots) - 1:
                next_s, next_d_list = grouped_shots[i+1]
                next_scene = next_s
                next_dialogue = next_d_list[0]

            # Combine actions for the prompt
            combined_action = ". ".join([d.action for d in dialogue_list if d.action])
            
            # Create a proxy dialogue object for prompt generation
            proxy_dialogue = Dialogue(
                role=primary_dialogue.role, 
                content=primary_dialogue.content, 
                action=combined_action,
                expression=primary_dialogue.expression
            )
            
            # Generate prompts (Image and Video)
            # We call with for_video=True to get full params (including audio)
            _, full_params = generate_panel_prompt(scene, proxy_dialogue, next_scene, next_dialogue, present_chars, for_video=True, return_params=True)
            
            # Create distinct parameter sets
            image_params = full_params.copy()
            video_params = full_params.copy()
            
            # Refine Image Params: Remove Audio, Camera Movement, Shot Type, and Style (as requested)
            image_params['audio'] = ""
            image_params['camera_movement'] = ""
            image_params['shot_type'] = ""
            image_params['style'] = ""
            
            # Refine Video Params: Remove static visual descriptors (Subject, Context, Style, Composition, Viewpoint, Shot Type)
            # Video generation relies on the input image for these details.
            video_params['subject'] = ""
            video_params['context'] = ""
            video_params['style'] = ""
            video_params['composition'] = ""
            video_params['viewpoint'] = ""
            video_params['shot_type'] = ""
            
            # Construct prompts from their respective params
            # Build complete image prompt with scene context
            scene_context_parts = []
            if scene.location:
                scene_context_parts.append(scene.location)
            if scene.time:
                scene_context_parts.append(scene.time)
            if scene.description:
                scene_context_parts.append(scene.description)
            
            scene_context = " ".join(scene_context_parts) if scene_context_parts else ""
            action_desc = image_params.get('action', '')
            
            # Format: "场景: [Scene Context]. 画面: [Action]"
            image_prompt_parts = []
            if scene_context:
                image_prompt_parts.append(f"场景: {scene_context}")
            if action_desc:
                image_prompt_parts.append(f"画面: {action_desc}")
            
            image_prompt = ". ".join(image_prompt_parts) if image_prompt_parts else action_desc
            
            # Video prompt starts empty
            video_prompt = ""
            
            # Combine descriptions
            full_desc = "\n".join([f"{d.role}: {d.content}" + (f" ({d.action})" if d.action else "") for d in dialogue_list])
            
            panel = Panel(
                panel_id=f"p_{count}",
                scene_id=scene.scene_id,
                description=full_desc,
                image_prompt=image_prompt,
                video_prompt=video_prompt,
                prompt_params=image_params,
                video_params=video_params
            )
            
            panel.characters = panel_char_ids
            
            self.current_storyboard.panels.append(panel)
        
        self.refresh_shot_list()
        self.save_storyboard()

    def refresh_panel_metadata(self, panel_id):
        """Refreshes panel data from script without generating image."""
        # 1. Find Panel and Index
        idx = -1
        panel = None
        for i, p in enumerate(self.current_storyboard.panels):
            if p.panel_id == panel_id:
                idx = i
                panel = p
                break
        
        if idx < 0 or not panel:
            return

        # 2. Reload Script
        try:
            script_path = None
            possible_paths = []
            
            if self.current_episode_id:
                possible_paths.append(os.path.join(self.project_dir, "scripts", f"episode_{self.current_episode_id}.json"))
            
            possible_paths.append(os.path.join(self.project_dir, "current_script.json"))
            possible_paths.append(os.path.join(self.project_dir, "resources", "projects", "current_script.json"))
            possible_paths.append(os.path.join(self.project_dir, "projects", "current_script.json"))
                
            for p in possible_paths:
                if os.path.exists(p):
                    script_path = p
                    break
                    
            if script_path:
                with open(script_path, 'r', encoding='utf-8') as f:
                    self.current_script = Script.from_json(f.read())
            else:
                print(f"DEBUG: Script not found in refresh. Checked: {possible_paths}")
                
        except Exception as e:
            print(f"Error reloading script: {e}")
            return

        # 3. Sync Data from Script
        # Find corresponding scene and dialogue
        target_scene = None
        for s in self.current_script.scenes:
            if str(s.scene_id) == str(panel.scene_id):
                target_scene = s
                break
        
        if target_scene:
            # Find which shot index this is within the scene in the storyboard
            shot_idx = 0
            for p in self.current_storyboard.panels:
                if p.panel_id == panel_id:
                    break
                if str(p.scene_id) == str(panel.scene_id):
                    shot_idx += 1
            
            # Update if valid index
            if shot_idx < len(target_scene.dialogues):
                dialogue = target_scene.dialogues[shot_idx]
                # Update fields
                panel.description = dialogue.action
                # panel.dialogue = dialogue.content # If panel has dialogue field?
                # Note: Panel model might not have 'dialogue' field explicitly mirrored if it's just for generation
                # But we definitely update description (action)
                
                # Also update prompt header if needed? 
                # on_shot_selected will handle the UI update
                
                self.save_storyboard()
                QMessageBox.information(self, "刷新成功", "已从剧本同步最新信息。")
            else:
                QMessageBox.warning(self, "刷新失败", "无法在剧本中找到对应的分镜 (索引越界)。")
        else:
            QMessageBox.warning(self, "刷新失败", f"无法在剧本中找到场景 {panel.scene_id}。")

        # 4. Select and Update UI
        self.shot_list.setCurrentRow(idx)
        self.on_shot_selected(idx)

    def refresh_shot_list(self):
        # Preserve current selection
        current_row = self.shot_list.currentRow()
        
        self.shot_list.clear()
        if not self.current_storyboard:
            return

        scene_shot_counts = {} # scene_id -> count

        for i, panel in enumerate(self.current_storyboard.panels):
            # Calculate shot number in scene
            scene_id = panel.scene_id
            if scene_id not in scene_shot_counts:
                scene_shot_counts[scene_id] = 0
            scene_shot_counts[scene_id] += 1
            shot_num = scene_shot_counts[scene_id]

            item = QListWidgetItem(self.shot_list)
            item.setSizeHint(QSize(200, 100))
            widget = ShotListItem(i + 1, panel, shot_number_in_scene=shot_num)
            widget.deleted.connect(self.delete_panel)
            widget.regenerate.connect(self.refresh_panel_metadata)
            self.shot_list.setItemWidget(item, widget)
            
        if self.shot_list.count() > 0:
            # Restore selection if valid, otherwise select 0
            if current_row >= 0 and current_row < self.shot_list.count():
                self.shot_list.setCurrentRow(current_row)
            else:
                self.shot_list.setCurrentRow(0)

    def delete_panel(self, panel_id):
        if not self.current_storyboard:
            return
            
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个分镜吗？", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
            
        # Find index
        idx = -1
        for i, p in enumerate(self.current_storyboard.panels):
            if p.panel_id == panel_id:
                idx = i
                break
                
        if idx >= 0:
            self.current_storyboard.panels.pop(idx)
            self.save_storyboard()
            self.refresh_shot_list()
            
            # Adjust selection
            if self.shot_list.count() > 0:
                new_idx = min(idx, self.shot_list.count() - 1)
                self.shot_list.setCurrentRow(new_idx)
            else:
                self.current_panel_index = -1

    def on_item_clicked(self, item):
        """Handle click event explicitly to ensure UI updates even if selection state is tricky."""
        row = self.shot_list.row(item)
        if row >= 0:
            # Avoid double-triggering if currentRowChanged already handled it
            if row != self.current_panel_index:
                self.on_shot_selected(row)

    def switch_preview_mode(self, index):
        self.preview_stack.setCurrentIndex(index)
        if index == 1: # Video
            if self.current_panel_index >= 0:
                panel = self.current_storyboard.panels[self.current_panel_index]
                video_path = getattr(panel, 'video_path', None)
                if video_path and os.path.exists(video_path):
                    abs_path = os.path.abspath(video_path)
                    self.video_player.set_source(abs_path)
                    self.video_player.toggle_playback() # Auto play
                else:
                    print(f"DEBUG: No video found for panel {self.current_panel_index} at {video_path}")
                    self.video_player.show_placeholder()
        else:
            self.video_player.stop()
        
        # Update history controls for new mode
        self.update_history_controls()

    def save_current_prompt(self):
        if self.current_panel_index >= 0 and self.current_storyboard:
            panel = self.current_storyboard.panels[self.current_panel_index]
            panel.image_prompt = self.prompt_edit.toPlainText()
            self.save_storyboard()

    # def copy_scene_desc(self):
    #     text = self.scene_desc_lbl.text()
    #     if text.startswith("场景描述: "):
    #         text = text[6:]
    #     QApplication.clipboard().setText(text)
        
    #     # Optional: Show a small tooltip or feedback?
    #     # For now just copy is enough

    def on_shot_selected(self, row):
        try:
            if row < 0 or not self.current_storyboard:
                return
            
            if row >= len(self.current_storyboard.panels):
                return

            self.current_panel_index = row
            panel = self.current_storyboard.panels[row]
            
            # Reload script to ensure we have latest scene descriptions
            try:
                script_path = None
                possible_paths = []
                
                # 1. If episode ID is set, try that first
                if self.current_episode_id:
                    possible_paths.append(os.path.join(self.project_dir, "scripts", f"episode_{self.current_episode_id}.json"))
                
                # 2. Try current_script.json in various places (fallback)
                possible_paths.append(os.path.join(self.project_dir, "current_script.json"))
                possible_paths.append(os.path.join(self.project_dir, "resources", "projects", "current_script.json"))
                possible_paths.append(os.path.join(self.project_dir, "projects", "current_script.json"))
                
                # 3. If still nothing, and we have a panel with scene_id, maybe we can guess?
                # (Skipping dangerous guessing for now, but logging)
                
                print(f"DEBUG: Project Dir: {self.project_dir}")
                print(f"DEBUG: Current Episode ID: {self.current_episode_id}")
                
                for p in possible_paths:
                    if os.path.exists(p):
                        script_path = p
                        print(f"DEBUG: Found script at: {script_path}")
                        break
                        
                if script_path:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        # Handle potential BOM or encoding issues
                        content = f.read()
                        self.current_script = Script.from_json(content)
                        print(f"DEBUG: Loaded script with {len(self.current_script.scenes)} scenes")
                else:
                    print(f"DEBUG: Script file not found. Checked: {possible_paths}")
                    # Show error to user if we really can't find it
                    # QMessageBox.warning(self, "Debug", f"Script file not found.\nChecked:\n{possible_paths}")
                    
            except Exception as e:
                print(f"Error reloading script: {e}")
                import traceback
                traceback.print_exc()
                # QMessageBox.warning(self, "Debug", f"Error reloading script:\n{e}")

            # Update UI
            # self.prompt_edit.setText(panel.image_prompt) # Moved down
            
            # Update Source Info (Scene + Action)
            scene_desc = ""
            action_desc = ""
            subtitle_text = ""
            
            print(f"DEBUG: Panel Scene ID: {panel.scene_id}")
            if self.current_script:
                for scene in self.current_script.scenes:
                    # Loose matching for scene ID (handle "1", "scene_1", 1)
                    s_id = str(scene.scene_id).strip()
                    p_id = str(panel.scene_id).strip()
                    
                    match = False
                    if s_id == p_id: match = True
                    elif s_id == p_id.replace("scene_", ""): match = True
                    elif p_id == s_id.replace("scene_", ""): match = True
                    
                    if match:
                        # Construct full scene description from parts
                        parts = []
                        if scene.location: parts.append(f"{scene.location}")
                        if scene.time: parts.append(f"{scene.time}")
                        if scene.description: parts.append(scene.description)
                        
                        scene_desc = " ".join(parts)
                        print(f"DEBUG: Found Scene Desc: {scene_desc}")
                        
                        # Find specific dialogue/action for this shot
                        # Count how many panels in current_storyboard before this one have the same scene_id
                        shot_index = 0
                        for i in range(row):
                            p = self.current_storyboard.panels[i]
                            # Fuzzy match scene id
                            p_sid = str(p.scene_id).strip()
                            if p_sid == s_id or p_sid == s_id.replace("scene_", "") or s_id == p_sid.replace("scene_", ""):
                                shot_index += 1
                        
                        if shot_index < len(scene.dialogues):
                            dialogue = scene.dialogues[shot_index]
                            action_desc = dialogue.action
                            subtitle_text = f"{dialogue.role}: {dialogue.content}"
                            if dialogue.expression:
                                subtitle_text += f" ({dialogue.expression})"
                        
                        break
            else:
                print("DEBUG: No current script loaded")
                # Try to recover?
                pass
            
            # Update Subtitle Label
            if hasattr(self, 'subtitle_lbl'):
                self.subtitle_lbl.setText(subtitle_text if subtitle_text else "无字幕")
            
            # Construct Header Text
            # Use action_desc if available, otherwise fallback to panel.description (which might contain subtitle)
            visual_desc = action_desc if action_desc else panel.description
            
            header_text = ""
            if scene_desc:
                header_text += f"场景: {scene_desc}\n"
            if visual_desc:
                header_text += f"画面: {visual_desc}"
            header_text = header_text.strip()
            
            print(f"DEBUG: Header Text: {header_text}")
            
            # Determine Prompt Text
            current_prompt = (panel.image_prompt or "").strip()
            
            # Block signals to prevent auto-save loop while setting text
            self.prompt_edit.blockSignals(True)
            
            # Force update logic:
            # We want to ensure the prompt ALWAYS starts with the Scene Description and Action Description
            # Format:
            # 场景: [Scene Description]
            # 画面: [Action Description]
            # [User's extra prompt content if any]
            
            # 1. Build the "Standard Header"
            standard_header = ""
            if scene_desc:
                standard_header += f"场景: {scene_desc}\n"
            if visual_desc:
                standard_header += f"画面: {visual_desc}"
            standard_header = standard_header.strip()
            
            # 2. Determine if we should overwrite the prompt
            # We overwrite ONLY if:
            # a) The current prompt is empty
            # b) The current prompt is exactly equal to the raw visual description (legacy default)
            # c) The current prompt is exactly equal to the panel description (legacy default)
            
            should_overwrite = False
            if not current_prompt:
                should_overwrite = True
            elif visual_desc and current_prompt.strip() == visual_desc.strip():
                should_overwrite = True
            elif panel.description and current_prompt.strip() == panel.description.strip():
                should_overwrite = True
                
            if should_overwrite:
                new_text = standard_header
            else:
                # User has modified the prompt (or it's already in a complex format).
                # We respect the user's content 100%.
                new_text = current_prompt

            # Final cleanup of newlines
            new_text = new_text.strip()
            
            print(f"DEBUG: Setting Prompt Text: {new_text}")
            self.prompt_edit.setText(new_text)
            
            self.prompt_edit.blockSignals(False)
            
            # Update Image Preview
            if panel.image_path and os.path.exists(panel.image_path):
                pixmap = QPixmap(panel.image_path)
                self.image_display.setPixmap(pixmap.scaled(
                    self.image_display.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.image_display.setText("暂无图片")
                
            # Update Video Preview if active
            if self.preview_stack.currentIndex() == 1:
                if panel.video_path and os.path.exists(panel.video_path):
                    self.video_player.set_source(panel.video_path)
                else:
                    self.video_player.show_placeholder()
                    
        except Exception as e:
            print(f"Error selecting shot: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback UI updates in case of error
            self.prompt_edit.setText(panel.image_prompt)
            
            # Clean description for display (remove content in parentheses)
            import re
            clean_desc = re.sub(r'[\(（][^\)）]*[\)）]', '', panel.description)
            self.subtitle_lbl.setText(clean_desc)

        # --- Common UI Updates (Run regardless of success/failure) ---
        
        # Auto-fix: If no characters linked, try to detect from description
        if not panel.characters and panel.description and ":" in panel.description:
            role_name = panel.description.split(":", 1)[0].strip()
            # Try to find this character
            resources_dir = os.path.dirname(os.path.dirname(self.project_dir))
            char_dir = os.path.join(resources_dir, "characters")
            if os.path.exists(char_dir):
                for f in os.listdir(char_dir):
                    if f.endswith(".json"):
                        try:
                            with open(os.path.join(char_dir, f), 'r', encoding='utf-8') as file:
                                c = Character.from_json(file.read())
                                if c.name == role_name:
                                    panel.characters.append(c.id)
                                    self.save_storyboard() # Save the fix
                                    break
                        except: pass

        has_image = bool(panel.image_path and os.path.exists(panel.image_path))
        video_path = getattr(panel, 'video_path', None)
        has_video = bool(video_path and os.path.exists(video_path))
        
        # Update Center
        if has_image:
            # Only update image display if NOT already updated by try block
            # But checking that is hard. Re-updating is safe.
            pix = QPixmap(panel.image_path)
            self.image_display.setPixmap(pix.scaled(self.image_display.size(), Qt.AspectRatioMode.KeepAspectRatio))
            self.image_display.setStyleSheet("background-color: #000; border-radius: 5px;")
            
            # Button States: Image Exists
            self.regen_btn.setText("⚡ 重绘画面")
            self.animate_btn.setEnabled(True)
            self.animate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e67e22;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 5px;
                }
            """)
        else:
            self.image_display.setText("暂无图片")
            self.image_display.setStyleSheet("background-color: #000; color: #7f8c8d; font-size: 20px; border-radius: 5px;")
            
            # Button States: No Image
            self.animate_btn.setEnabled(False)
            self.animate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #7f8c8d;
                    color: #bdc3c7;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 5px;
                }
            """)
            self.regen_btn.setText("⚡ 生成图片")

        # Always enable buttons when switching shots (resets stuck states)
        self.regen_btn.setEnabled(True)
        self.animate_btn.setEnabled(True)
        self.animate_btn.setToolTip("批量生成动态视频")
        self.animate_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
            
        # Update Toggle State
        self.btn_view_video.setEnabled(has_video)
        if has_video:
            self.btn_view_video.setToolTip("预览生成的视频")
        else:
            self.btn_view_video.setToolTip("当前分镜暂无视频")
            
        # Reset to Image view by default when switching shots
        self.btn_view_img.setChecked(True)
        self.switch_preview_mode(0)
        
        # Update Right
        # Note: prompt_edit is updated in try block or except block fallback
        
        if hasattr(panel, 'video_prompt'):
            self.video_prompt_edit.setText(panel.video_prompt)
        else:
            self.video_prompt_edit.setText("")
            
        self.update_character_list_ui()
        self.update_environment_ui()
        
        # Update Reference Image UI
        if hasattr(panel, 'reference_image_path') and panel.reference_image_path and os.path.exists(panel.reference_image_path):
            self.ref_img_widget.setVisible(True)
            self.ref_img_lbl.setPixmap(QPixmap(panel.reference_image_path))
            self.add_ref_btn.setVisible(False)
        else:
            self.ref_img_widget.setVisible(False)
            self.add_ref_btn.setVisible(True)
        
        # Update History based on current preview mode
        # Clear history layout (preserve index 0: upload button)
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        
        # Check which preview mode is active (0=image, 1=video)
        is_video_mode = self.preview_stack.currentIndex() == 1
        
        if is_video_mode and panel.is_animated:
            # Show video history
            all_videos = self.get_sorted_history_videos(panel)
            print(f"Shot {row}: Video={panel.video_path}, History={len(panel.history_videos)}, Displaying {len(all_videos)} items.")
            
            for vid_path in all_videos:
                is_selected = (vid_path == panel.video_path)
                item = HistoryItemWidget(vid_path, is_selected, is_video=True)
                item.selected.connect(self.select_history_video)
                item.deleted.connect(self.delete_history_video)
                self.history_layout.addWidget(item)
        else:
            # Show image history (original logic)
            all_images = self.get_sorted_history_images(panel)
            print(f"Shot {row}: Image={panel.image_path}, History={len(panel.history_images)}, Displaying {len(all_images)} items.")

            for img_path in all_images:
                is_selected = (img_path == panel.image_path)
                item = HistoryItemWidget(img_path, is_selected, is_video=False)
                item.selected.connect(self.select_history_image)
                item.deleted.connect(self.delete_history_image)
                self.history_layout.addWidget(item)
            
        # Force layout update
        self.history_widget.update()
        self.history_widget.layout().update()
        
        self.update_history_controls()
        
        # Update retry buttons visibility
        # Only show retry buttons if we have task_id/url BUT the file doesn't exist (download failed)
        
        # Image retry button: show only if we have URL but no image file
        show_image_retry = (
            hasattr(panel, 'last_image_task_id') and 
            panel.last_image_task_id and 
            not has_image  # File doesn't exist or failed to load
        )
        if show_image_retry:
            self.retry_image_btn.setVisible(True)
            url_preview = panel.last_image_task_id[:30] + "..." if len(panel.last_image_task_id) > 30 else panel.last_image_task_id
            self.retry_image_btn.setToolTip(f"重新下载图片\nURL: {url_preview}")
        else:
            self.retry_image_btn.setVisible(False)
        
        # Video retry button: show only if we have task_id but no video file
        show_video_retry = (
            hasattr(panel, 'last_video_task_id') and 
            panel.last_video_task_id and 
            not has_video  # File doesn't exist or failed to load
        )
        if show_video_retry:
            self.retry_video_btn.setVisible(True)
            self.retry_video_btn.setToolTip(f"重新获取视频 (任务ID: {panel.last_video_task_id[:8]}...)")
        else:
            self.retry_video_btn.setVisible(False)

    def get_sorted_history_images(self, panel):
        """Helper to get all valid images for a panel, sorted by creation time."""
        all_imgs = panel.history_images + ([panel.image_path] if panel.image_path else [])
        valid_imgs = []
        seen = set()
        for p in all_imgs:
            if p and os.path.exists(p) and p not in seen:
                valid_imgs.append(p)
                seen.add(p)
        
        # Sort by creation time to ensure stable order
        try:
            valid_imgs.sort(key=lambda p: os.path.getctime(p))
        except Exception as e:
            print(f"Error sorting history images: {e}")
            
        return valid_imgs

    def update_history_controls(self):
        if self.current_panel_index < 0:
            self.history_ctrl_widget.setVisible(False)
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        
        # Check which preview mode is active (0=image, 1=video)
        is_video_mode = self.preview_stack.currentIndex() == 1
        
        if is_video_mode:
            # Video history control
            valid_vids = self.get_sorted_history_videos(panel)
            
            if len(valid_vids) <= 1:
                self.history_ctrl_widget.setVisible(False)
                return
                
            self.history_ctrl_widget.setVisible(True)
            
            # Find current index
            try:
                curr_idx = valid_vids.index(panel.video_path)
            except ValueError:
                curr_idx = len(valid_vids) - 1
                
            total = len(valid_vids)
            self.ver_lbl.setText(f"视频版本 {curr_idx + 1}/{total}")
            
            self.prev_ver_btn.setEnabled(curr_idx > 0)
            self.next_ver_btn.setEnabled(curr_idx < total - 1)
        else:
            # Image history control (original logic)
            valid_imgs = self.get_sorted_history_images(panel)
            
            if len(valid_imgs) <= 1:
                self.history_ctrl_widget.setVisible(False)
                return
                
            self.history_ctrl_widget.setVisible(True)
            
            # Find current index
            try:
                curr_idx = valid_imgs.index(panel.image_path)
            except ValueError:
                curr_idx = len(valid_imgs) - 1
                
            total = len(valid_imgs)
            self.ver_lbl.setText(f"图片版本 {curr_idx + 1}/{total}")
            
            self.prev_ver_btn.setEnabled(curr_idx > 0)
            self.next_ver_btn.setEnabled(curr_idx < total - 1)
        
    def show_prev_version(self):
        if self.current_panel_index < 0: return
        panel = self.current_storyboard.panels[self.current_panel_index]
        
        # Check which preview mode is active (0=image, 1=video)
        is_video_mode = self.preview_stack.currentIndex() == 1
        
        if is_video_mode:
            # Video history
            valid_vids = self.get_sorted_history_videos(panel)
            try:
                curr_idx = valid_vids.index(panel.video_path)
            except ValueError:
                return
                
            if curr_idx > 0:
                new_vid = valid_vids[curr_idx - 1]
                self.switch_to_history_video(panel, new_vid)
        else:
            # Image history (original logic)
            valid_imgs = self.get_sorted_history_images(panel)
            try:
                curr_idx = valid_imgs.index(panel.image_path)
            except ValueError:
                return
                
            if curr_idx > 0:
                new_img = valid_imgs[curr_idx - 1]
                self.switch_to_history_image(panel, new_img)

    def show_next_version(self):
        if self.current_panel_index < 0: return
        panel = self.current_storyboard.panels[self.current_panel_index]
        
        # Check which preview mode is active (0=image, 1=video)
        is_video_mode = self.preview_stack.currentIndex() == 1
        
        if is_video_mode:
            # Video history
            valid_vids = self.get_sorted_history_videos(panel)
            try:
                curr_idx = valid_vids.index(panel.video_path)
            except ValueError:
                return
                
            if curr_idx < len(valid_vids) - 1:
                new_vid = valid_vids[curr_idx + 1]
                self.switch_to_history_video(panel, new_vid)
        else:
            # Image history (original logic)
            valid_imgs = self.get_sorted_history_images(panel)
            try:
                curr_idx = valid_imgs.index(panel.image_path)
            except ValueError:
                return
                
            if curr_idx < len(valid_imgs) - 1:
                new_img = valid_imgs[curr_idx + 1]
                self.switch_to_history_image(panel, new_img)

    def switch_to_history_image(self, panel, new_img):
        """Common logic for switching images while preserving history pool."""
        # Ensure current image is in history before switching
        if panel.image_path and panel.image_path not in panel.history_images:
            panel.history_images.append(panel.image_path)
            
        # Set new image
        panel.image_path = new_img
        
        # We do NOT remove new_img from history_images here if we want to keep the pool intact?
        # But the original logic was swapping.
        # If we keep it in history_images, get_sorted_history_images will still work fine (it dedupes).
        # But for cleanliness, maybe we should remove it?
        # Actually, if we remove it, it might change the order if we rely on list order.
        # But we rely on getctime sort. So list order doesn't matter!
        # So we can remove it to keep history_images clean (only non-current images).
        
        if new_img in panel.history_images:
            panel.history_images.remove(new_img)
            
        self.save_storyboard()
        self.on_shot_selected(self.current_panel_index)

    def get_sorted_history_videos(self, panel):
        """Get sorted video history list (oldest to newest by file creation time)"""
        all_vids = panel.history_videos + ([panel.video_path] if panel.video_path else [])
        # Remove duplicates
        all_vids = list(dict.fromkeys(all_vids))
        
        # Filter out non-existent files
        valid_vids = [v for v in all_vids if os.path.exists(v)]
        
        # Sort by file creation time
        try:
            valid_vids.sort(key=lambda x: os.path.getctime(x))
        except Exception as e:
            print(f"Error sorting history videos: {e}")
            
        return valid_vids

    def switch_to_history_video(self, panel, new_vid):
        """Common logic for switching videos while preserving history pool."""
        # Ensure current video is in history before switching
        if panel.video_path and panel.video_path not in panel.history_videos:
            panel.history_videos.append(panel.video_path)
            
        # Set new video
        panel.video_path = new_vid
        
        # Remove from history_videos to keep it clean (only non-current videos)
        if new_vid in panel.history_videos:
            panel.history_videos.remove(new_vid)
            
        self.save_storyboard()
        self.on_shot_selected(self.current_panel_index)

    def select_history_video(self, path):
        """Switch to a selected video from history"""
        if self.current_panel_index < 0:
            return
        
        idx = self.current_panel_index
        panel = self.current_storyboard.panels[idx]
        
        # Save current video to history before switching, if it's not already there
        if panel.video_path and panel.video_path not in panel.history_videos and os.path.exists(panel.video_path):
            panel.history_videos.append(panel.video_path)
            
        panel.video_path = path
        panel.is_animated = True
        self.save_storyboard()
        
        # Update video display
        self.on_shot_selected(idx)

    def delete_history_video(self, path):
        """Delete a video from history"""
        if self.current_panel_index < 0:
            return
            
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个视频版本吗？", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        idx = self.current_panel_index
        panel = self.current_storyboard.panels[idx]
        
        # Remove from history list
        if path in panel.history_videos:
            panel.history_videos.remove(path)
            
        # If it was the current video, clear it or pick another
        if path == panel.video_path:
            panel.video_path = ""
            panel.is_animated = False
            if panel.history_videos:
                panel.video_path = panel.history_videos[-1]  # Pick last one
                panel.is_animated = True
        
        self.save_storyboard()
        self.on_shot_selected(idx)



    def select_history_image(self, path):
        if self.current_panel_index < 0:
            return
        
        # Capture index before any changes
        idx = self.current_panel_index
        
        panel = self.current_storyboard.panels[idx]
        
        # Save current image to history before switching, if it's not already there
        if panel.image_path and panel.image_path not in panel.history_images and os.path.exists(panel.image_path):
            panel.history_images.append(panel.image_path)
            
        panel.image_path = path
        self.save_storyboard()
        
        # Block signals to prevent auto-jumping or double-updates during list refresh
        self.shot_list.blockSignals(True)
        try:
            self.refresh_shot_list() # Update thumbnail in list
            # Ensure selection is restored to the correct index
            if idx < self.shot_list.count():
                self.shot_list.setCurrentRow(idx)
        finally:
            self.shot_list.blockSignals(False)
            
        self.on_shot_selected(idx) # Refresh UI manually

    def delete_history_image(self, path):
        if self.current_panel_index < 0:
            return
            
        reply = QMessageBox.question(self, "确认删除", "确定要删除这张图片吗？", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        idx = self.current_panel_index
        panel = self.current_storyboard.panels[idx]
        
        # Remove from history list
        if path in panel.history_images:
            panel.history_images.remove(path)
            
        # If it was the current image, clear it or pick another
        if path == panel.image_path:
            panel.image_path = ""
            if panel.history_images:
                panel.image_path = panel.history_images[-1] # Pick last one
        
        self.save_storyboard()
        
        # Block signals to prevent jumps
        self.shot_list.blockSignals(True)
        try:
            self.refresh_shot_list()
            if idx < self.shot_list.count():
                self.shot_list.setCurrentRow(idx)
        finally:
            self.shot_list.blockSignals(False)
            
        self.on_shot_selected(idx)

    def update_character_list_ui(self):
        # Clear existing
        for i in reversed(range(self.char_list_layout.count())): 
            self.char_list_layout.itemAt(i).widget().setParent(None)
            
        if self.current_panel_index < 0 or not self.current_storyboard:
            return

        panel = self.current_storyboard.panels[self.current_panel_index]
        
        # Read characters
        project_chars = []
        resources_dir = os.path.dirname(os.path.dirname(self.project_dir))
        char_dir = os.path.join(resources_dir, "characters")
        if os.path.exists(char_dir):
            for f in os.listdir(char_dir):
                if f.endswith(".json"):
                    try:
                        with open(os.path.join(char_dir, f), 'r', encoding='utf-8') as file:
                            project_chars.append(Character.from_json(file.read()))
                    except: pass
        
        for char_id in panel.characters:
            char = next((c for c in project_chars if c.id == char_id), None)
            if char:
                # Create UI row
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(5, 5, 5, 5)
                row_widget.setStyleSheet("background-color: #34495e; border-radius: 5px;")
                
                # Avatar
                avatar_lbl = QLabel()
                avatar_lbl.setFixedSize(30, 30)
                avatar_lbl.setStyleSheet("background-color: #7f8c8d; border-radius: 15px;")
                if char.avatar_path and os.path.exists(char.avatar_path):
                    pix = QPixmap(char.avatar_path)
                    avatar_lbl.setPixmap(pix.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
                row_layout.addWidget(avatar_lbl)
                
                # Name
                name_lbl = QLabel(char.name)
                name_lbl.setStyleSheet("color: white; font-weight: bold;")
                row_layout.addWidget(name_lbl)
                
                row_layout.addStretch()
                
                # Remove button
                del_btn = QPushButton("×")
                del_btn.setFixedSize(20, 20)
                del_btn.setStyleSheet("color: #e74c3c; background: transparent; font-weight: bold; border: none;")
                del_btn.clicked.connect(lambda checked, cid=char_id: self.remove_character(cid))
                row_layout.addWidget(del_btn)
                
                self.char_list_layout.addWidget(row_widget)

    def update_environment_ui(self):
        if self.current_panel_index < 0 or not self.current_storyboard:
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        scene_id = panel.scene_id
        
        # Find scene in script
        scene = None
        if self.current_script:
            scene = next((s for s in self.current_script.scenes if s.scene_id == scene_id), None)
            
        if scene:
            self.env_info_lbl.setText(f"Location: {scene.location}\nTime: {scene.time}")
            
            # Check for Scene Library Link
            if hasattr(scene, 'scene_library_id') and scene.scene_library_id:
                self.scene_select_btn.setVisible(True)
                self.scene_select_btn.setText("已关联场景库 (点击更换)")
                self.scene_select_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; border: none; border-radius: 3px;")
                self.env_img_btn.setVisible(False) # Hide manual upload if linked
            else:
                self.scene_select_btn.setVisible(True)
                self.scene_select_btn.setText("关联场景库")
                self.scene_select_btn.setStyleSheet("background-color: #34495e; color: white; padding: 8px; border: 1px dashed #7f8c8d;")
                self.env_img_btn.setVisible(True)

            if scene.environment_image and os.path.exists(scene.environment_image):
                self.env_img_btn.setText("已设置参考图 (点击更换)")
                self.env_img_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; border: 1px solid #27ae60;")
                self.env_img_btn.setToolTip(scene.environment_image)
            else:
                self.env_img_btn.setText("设置环境参考图")
                self.env_img_btn.setStyleSheet("background-color: #34495e; color: white; padding: 8px; border: 1px dashed #7f8c8d;")
                self.env_img_btn.setToolTip("上传一张图片作为该场景的环境参考")
        else:
            self.env_info_lbl.setText("Location: Unknown (No Script)")
            self.env_img_btn.setEnabled(False)
            self.scene_select_btn.setVisible(False)

    def set_scene_environment(self):
        if self.current_panel_index < 0 or not self.current_script:
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        scene = next((s for s in self.current_script.scenes if s.scene_id == panel.scene_id), None)
        
        if not scene:
            QMessageBox.warning(self, "错误", "找不到对应的场景信息。")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "选择环境参考图", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if file_path:
            # Copy to project/images/refs or just use path?
            # Better to copy to project folder to keep it self-contained
            ref_dir = os.path.join(self.project_dir, "images", "refs")
            os.makedirs(ref_dir, exist_ok=True)
            
            filename = f"env_{scene.scene_id}_{os.path.basename(file_path)}"
            dest_path = os.path.join(ref_dir, filename)
            
            try:
                import shutil
                shutil.copy2(file_path, dest_path)
                scene.environment_image = dest_path
                
                # Save script
                if self.current_episode_id:
                    script_path = os.path.join(self.project_dir, "scripts", f"episode_{self.current_episode_id}.json")
                else:
                    script_path = os.path.join(self.project_dir, "current_script.json")
                self.current_script.save(script_path)
                
                self.update_environment_ui()
                QMessageBox.information(self, "成功", "环境参考图已设置。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"设置参考图失败: {e}")

    def open_scene_library(self):
        if self.current_panel_index < 0 or not self.current_script:
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        scene = next((s for s in self.current_script.scenes if s.scene_id == panel.scene_id), None)
        
        if not scene:
            return

        # Path to scenes
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        scenes_dir = os.path.join(base_dir, "resources", "scenes")
        
        dialog = SceneSelectorDialog(scenes_dir, self)
        dialog.scene_selected.connect(lambda s: self.apply_scene_from_library(scene, s))
        dialog.exec()

    def apply_scene_from_library(self, script_scene, library_scene):
        # Link script scene to library scene
        script_scene.scene_library_id = library_scene.id
        
        # Update description if needed (optional, maybe append?)
        # script_scene.description += f" {library_scene.description}"
        
        # Use library image as environment image
        if library_scene.image_path and os.path.exists(library_scene.image_path):
            script_scene.environment_image = library_scene.image_path
            
        # Save script
        if self.current_episode_id:
            script_path = os.path.join(self.project_dir, "scripts", f"episode_{self.current_episode_id}.json")
        else:
            script_path = os.path.join(self.project_dir, "current_script.json")
            
        self.current_script.save(script_path)
        self.update_environment_ui()
        QMessageBox.information(self, "成功", f"已关联场景: {library_scene.name}")

    def set_scene_environment(self):
        if self.current_panel_index < 0 or not self.current_script:
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        scene = next((s for s in self.current_script.scenes if s.scene_id == panel.scene_id), None)
        
        if not scene:
            QMessageBox.warning(self, "错误", "找不到对应的场景信息。")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "选择环境参考图", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if file_path:
            # Copy to project folder
            env_dir = os.path.join(self.project_dir, "images", "environments")
            os.makedirs(env_dir, exist_ok=True)
            
            ext = os.path.splitext(file_path)[1]
            new_path = os.path.join(env_dir, f"env_{scene.scene_id}{ext}")
            
            import shutil
            shutil.copy2(file_path, new_path)
            
            scene.environment_image = new_path
            
            # Save script
            # We need to know where to save. 
            # If it's an episode, we save to episode file. If it's main script, save to current_script.json
            # StoryboardWindow loads script from file but doesn't store the path explicitly in a simple way?
            # Let's try to infer or just save to where we loaded it from.
            # Actually, `load_existing_data` logic:
            if self.current_episode_id:
                script_path = os.path.join(self.project_dir, "scripts", f"episode_{self.current_episode_id}.json")
            else:
                script_path = os.path.join(self.project_dir, "current_script.json")
                
            self.current_script.save(script_path)
            
            self.update_environment_ui()
            QMessageBox.information(self, "成功", "环境参考图已设置，该场景下的所有分镜将自动使用此参考图。")

    def add_character(self):
        if self.current_panel_index < 0:
            return
            
        # 1. Load Global Library
        global_chars = []
        resources_dir = os.path.dirname(os.path.dirname(self.project_dir))
        char_dir = os.path.join(resources_dir, "characters")
        if os.path.exists(char_dir):
            for f in os.listdir(char_dir):
                if f.endswith(".json"):
                    try:
                        with open(os.path.join(char_dir, f), 'r', encoding='utf-8') as file:
                            global_chars.append(Character.from_json(file.read()))
                    except: pass
        
        if not global_chars:
            QMessageBox.warning(self, "提示", "角色库为空，请先创建角色。")
            return

        # 2. Identify Project Characters
        # Load project.json to get 'cast'
        project_cast_ids = []
        project_json_path = os.path.join(self.project_dir, "project.json")
        if os.path.exists(project_json_path):
            try:
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    pj = json.load(f)
                    project_cast_ids = pj.get("cast", [])
            except: pass
            
        # If cast is empty, fallback to characters used in current storyboard
        if not project_cast_ids:
            used_ids = set()
            for p in self.current_storyboard.panels:
                used_ids.update(p.characters)
            project_cast_ids = list(used_ids)
            
        # Filter objects
        project_chars = [c for c in global_chars if c.id in project_cast_ids]
        
        # 3. Show Selection Dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("添加角色")
        dialog.setFixedSize(300, 400)
        dialog.setStyleSheet("background-color: #2c3e50; color: white;")
        
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel("选择角色:")
        layout.addWidget(lbl)
        
        list_widget = QListWidget()
        list_widget.setStyleSheet("background-color: #34495e; border: 1px solid #5d6d7e;")
        
        # Populate list
        for c in project_chars:
            # Don't show if already in panel
            panel = self.current_storyboard.panels[self.current_panel_index]
            if c.id in panel.characters:
                continue
                
            item = QListWidgetItem(c.name)
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            if c.avatar_path and os.path.exists(c.avatar_path):
                icon = QIcon(c.avatar_path)
                item.setIcon(icon)
            list_widget.addItem(item)
            
        layout.addWidget(list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_lib_btn = QPushButton("从库中添加...")
        add_lib_btn.setStyleSheet("background-color: #3498db; color: white; padding: 5px;")
        
        def on_add_lib():
            # Show full list
            names = [c.name for c in global_chars if c.id not in project_cast_ids]
            if not names:
                QMessageBox.information(dialog, "提示", "所有角色都已在项目中。")
                return
                
            name, ok = QInputDialog.getItem(dialog, "从库中添加", "选择角色加入项目:", names, 0, False)
            if ok and name:
                char = next(c for c in global_chars if c.name == name)
                # Add to project cast
                project_cast_ids.append(char.id)
                # Save to project.json
                if os.path.exists(project_json_path):
                    with open(project_json_path, 'r+', encoding='utf-8') as f:
                        data = json.load(f)
                        data['cast'] = project_cast_ids
                        f.seek(0)
                        json.dump(data, f, indent=4, ensure_ascii=False)
                        f.truncate()
                
                # Add to list widget
                item = QListWidgetItem(char.name)
                item.setData(Qt.ItemDataRole.UserRole, char.id)
                if char.avatar_path and os.path.exists(char.avatar_path):
                    item.setIcon(QIcon(char.avatar_path))
                list_widget.addItem(item)
                list_widget.setCurrentItem(item)

        add_lib_btn.clicked.connect(on_add_lib)
        btn_layout.addWidget(add_lib_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 5px;")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = list_widget.currentItem()
            if item:
                char_id = item.data(Qt.ItemDataRole.UserRole)
                panel = self.current_storyboard.panels[self.current_panel_index]
                panel.characters.append(char_id)
                self.update_character_list_ui()
                self.save_storyboard()

    def remove_character(self, char_id):
        if self.current_panel_index < 0:
            return
            
        reply = QMessageBox.question(self, "确认删除", "确定要移除这个角色吗？", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        panel = self.current_storyboard.panels[self.current_panel_index]
        if char_id in panel.characters:
            panel.characters.remove(char_id)
            self.update_character_list_ui()
            self.save_storyboard()

    def add_reference_image(self):
        if self.current_panel_index < 0:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "选择参考图", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if file_path:
            panel = self.current_storyboard.panels[self.current_panel_index]
            
            # Copy to project/images/refs
            ref_dir = os.path.join(self.project_dir, "images", "refs")
            os.makedirs(ref_dir, exist_ok=True)
            
            filename = f"ref_{panel.panel_id}_{os.path.basename(file_path)}"
            dest_path = os.path.join(ref_dir, filename)
            
            try:
                import shutil
                shutil.copy2(file_path, dest_path)
                panel.reference_image_path = dest_path
                self.save_storyboard()
                self.on_shot_selected(self.current_panel_index)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加参考图失败: {e}")

    def remove_reference_image(self):
        if self.current_panel_index < 0:
            return
            
        reply = QMessageBox.question(self, "确认删除", "确定要移除这张参考图吗？", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        panel = self.current_storyboard.panels[self.current_panel_index]
        panel.reference_image_path = ""
        self.save_storyboard()
        self.on_shot_selected(self.current_panel_index)

    def upload_image(self):
        if self.current_panel_index < 0:
            QMessageBox.warning(self, "提示", "请先选择一个分镜。")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "上传图片", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            try:
                # Copy to project images
                img_dir = os.path.join(self.project_dir, "images")
                os.makedirs(img_dir, exist_ok=True)
                
                panel = self.current_storyboard.panels[self.current_panel_index]
                filename = f"{panel.panel_id}_upload_{len(panel.history_images)}.png"
                dest_path = os.path.join(img_dir, filename)
                shutil.copy2(path, dest_path)
                
                # Update panel
                # Save current image to history if it's not already there
                if panel.image_path and panel.image_path not in panel.history_images:
                    panel.history_images.append(panel.image_path)
                panel.image_path = dest_path
                
                print(f"DEBUG: Uploaded image for panel {panel.panel_id} to {dest_path}")
                
                self.save_storyboard()
                
                # Force update thumbnail
                item = self.shot_list.item(self.current_panel_index)
                if item:
                    widget = self.shot_list.itemWidget(item)
                    if widget:
                        widget.update_thumb()
                
                self.on_shot_selected(self.current_panel_index)
            except Exception as e:
                print(f"Error uploading image: {e}")
                QMessageBox.warning(self, "错误", f"上传图片失败: {e}")
                self.save_storyboard()
                
                # Refresh list thumbnail
                item = self.shot_list.item(self.current_panel_index)
                widget = self.shot_list.itemWidget(item)
                widget.update_thumb()
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"上传失败: {e}")

    def open_params_dialog(self):
        if not self.current_storyboard or self.current_panel_index < 0:
            QMessageBox.warning(self, "提示", "请先选择一个分镜。")
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        
        # Ensure video_params exists (migration for old data)
        if not hasattr(panel, 'video_params') or not panel.video_params:
            panel.video_params = panel.prompt_params.copy()
        
        dialog = PromptParamsDialog(panel.prompt_params, panel.video_params, self)
        if dialog.exec():
            new_image_params = dialog.get_image_params()
            new_video_params = dialog.get_video_params()
            
            panel.prompt_params = new_image_params
            panel.video_params = new_video_params
            
            # Don't reconstruct prompts text here. 
            # The params are saved and will be used during generation.
            
            self.save_storyboard()

    def open_settings_dialog(self):
        # Reload project style to ensure it's up to date
        self.project_style = self.load_project_style()
        dialog = ImageGenSettingsDialog(self.image_gen_settings, self, project_style=self.project_style)
        if dialog.exec():
            self.image_gen_settings = dialog.get_settings()

    def regenerate_current_panel(self, checked=False, confirm=True):
        if self.current_panel_index < 0:
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        
        # Confirmation
        if confirm:
            action_name = "重绘画面" if panel.image_path else "生成图片"
            reply = QMessageBox.question(self, "确认", f"确定要{action_name}吗？", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Update prompt from edit
        panel.image_prompt = self.prompt_edit.toPlainText()
        
        # Combine user prompt with hidden params
        from core.storyboard.prompt_factory import construct_prompt_from_params
        params_prompt = construct_prompt_from_params(panel.prompt_params)
        
        # Assemble Full Prompt
        # Order: Action (User Prompt) -> Params
        prompt_components = []
        
        # Clean up user prompt (REMOVE "场景: xxx" and "画面: xxx" lines completely)
        user_prompt_clean = panel.image_prompt
        if user_prompt_clean:
            lines = user_prompt_clean.split('\n')
            cleaned_lines = []
            for line in lines:
                # Skip lines starting with "场景:" or "画面:"
                if line.startswith("场景:") or line.startswith("画面:"):
                    continue
                # Keep other lines
                if line.strip():
                    cleaned_lines.append(line.strip())
            user_prompt_clean = " ".join(cleaned_lines)

        if user_prompt_clean: 
            prompt_components.append(user_prompt_clean)
            
        # Only add params if it's not already in the user prompt
        if params_prompt and params_prompt not in user_prompt_clean: 
            prompt_components.append(params_prompt)
        
        full_prompt = ". ".join(prompt_components)
        
        # Create images directory
        img_dir = os.path.join(self.project_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        
        # Use UUID for unique filename to prevent overwriting history
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        output_path = os.path.join(img_dir, f"{panel.panel_id}_{unique_id}.png")
        
        selected_config = self.api_combo.currentData()
        
        # Get reference images
        ref_images = []
        if panel.characters:
            resources_dir = os.path.dirname(os.path.dirname(self.project_dir))
            char_dir = os.path.join(resources_dir, "characters")
            if os.path.exists(char_dir):
                for f in os.listdir(char_dir):
                    if f.endswith(".json"):
                        try:
                            with open(os.path.join(char_dir, f), 'r', encoding='utf-8') as file:
                                c = Character.from_json(file.read())
                                if c.id in panel.characters and c.avatar_path and os.path.exists(c.avatar_path):
                                    ref_images.append(c.avatar_path)
                        except: pass

        # Add Environment Reference
        if self.current_script:
            scene = next((s for s in self.current_script.scenes if s.scene_id == panel.scene_id), None)
            if scene and scene.environment_image and os.path.exists(scene.environment_image):
                print(f"Using environment reference: {scene.environment_image}")
                ref_images.append(scene.environment_image)

        # Add Panel Specific Reference Image
        if hasattr(panel, 'reference_image_path') and panel.reference_image_path and os.path.exists(panel.reference_image_path):
            print(f"Using panel reference image: {panel.reference_image_path}")
            ref_images.append(panel.reference_image_path)

        self.regen_btn.setEnabled(False)
        self.regen_btn.setText("生成中...")
        
        # Get Project Ratio and Resolution
        ratio = "16:9"
        resolution = "1080P"
        try:
            project_json_path = os.path.join(self.project_dir, "project.json")
            if os.path.exists(project_json_path):
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    ratio = project_data.get("ratio", "16:9")
                    resolution = project_data.get("resolution", "1080P")
        except: pass
        
        # Enforce project style if set
        # Reload project style to ensure it's up to date
        self.project_style = self.load_project_style()
        if self.project_style:
            self.image_gen_settings['style'] = self.project_style

        self.thread = ImageGenThread(panel.panel_id, full_prompt, output_path, selected_config, ref_images, self.image_gen_settings, ratio=ratio, resolution=resolution)
        self.thread.finished.connect(self.on_image_ready)
        self.thread.error.connect(self.on_image_error)
        self.thread.status.connect(self.on_image_status)
        self.thread.start()

    def on_image_status(self, msg):
        self.regen_btn.setText(msg)

    def on_video_prompt_changed(self):
        """Auto-save video prompt when edited"""
        if not self.current_storyboard or not hasattr(self, 'shot_list') or not self.shot_list.currentItem():
            return
        
        panel = self.current_storyboard.panels[self.shot_list.currentRow()]
        panel.video_prompt = self.video_prompt_edit.toPlainText()
        self.save_storyboard()
    
    def on_image_error(self, panel_id, error_msg, image_url=""):
        self.regen_btn.setEnabled(True)
        self.regen_btn.setText("⚡ 重绘画面") # Reset text
        
        # Save image URL even on error (for retry capability)
        panel = next((p for p in self.current_storyboard.panels if p.panel_id == panel_id), None)
        if panel and image_url:
            panel.last_image_task_id = image_url
            print(f"Saved image URL on error for panel {panel_id}: {image_url[:50]}...")
            self.save_storyboard()
            
            # Refresh UI to show retry button
            if self.current_storyboard.panels.index(panel) == self.current_panel_index:
                self.on_shot_selected(self.current_panel_index)
        
        QMessageBox.warning(self, "生成失败", f"图片生成出错:\n{error_msg}")

    def on_image_ready(self, panel_id, path, image_url=""):
        self.regen_btn.setEnabled(True)
        # Text update handled by on_shot_selected
        
        # Find panel
        panel = next((p for p in self.current_storyboard.panels if p.panel_id == panel_id), None)
        if panel:
            # Save image URL for retry capability
            if image_url:
                panel.last_image_task_id = image_url  # Reuse field to store URL
                print(f"Saved image URL for panel {panel_id}: {image_url[:50]}...")
            
            if panel.image_path:
                panel.history_images.append(panel.image_path)
            panel.image_path = path
            
            # Refresh UI if still selected
            if self.current_storyboard.panels.index(panel) == self.current_panel_index:
                self.on_shot_selected(self.current_panel_index)
                
            # Refresh list thumbnail
            item = self.shot_list.item(self.current_storyboard.panels.index(panel))
            widget = self.shot_list.itemWidget(item)
            widget.update_thumb()
            
        self.save_storyboard()

    def save_storyboard(self):
        if not self.current_storyboard:
            return
            
        if self.current_episode_id:
            sb_dir = os.path.join(self.project_dir, "storyboards")
            os.makedirs(sb_dir, exist_ok=True)
            path = os.path.join(sb_dir, f"episode_{self.current_episode_id}.json")
        else:
            path = os.path.join(self.project_dir, "storyboard.json")
            
        self.current_storyboard.save(path)

    def open_batch_video_dialog(self):
        print("DEBUG: open_batch_video_dialog called")
        try:
            if not self.current_storyboard:
                QMessageBox.warning(self, "提示", "请先生成分镜。")
                return
                
            print("DEBUG: Creating BatchVideoDialog...")
            dialog = BatchVideoDialog(self.current_storyboard, self.project_dir, self.current_panel_index, self)
            print("DEBUG: BatchVideoDialog created. Executing...")
            if dialog.exec():
                selected_ids = dialog.get_selected_panels()
                selected_config = dialog.get_selected_config()
                print(f"DEBUG: Dialog accepted. Selected {len(selected_ids)} panels. Config: {selected_config.get('name')}")
                if selected_ids:
                    self.run_batch_video_generation(selected_ids, selected_config)
        except Exception as e:
            print(f"ERROR in open_batch_video_dialog: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")

    def run_batch_video_generation(self, panel_ids, video_config=None):
        print(f"DEBUG: run_batch_video_generation called with {len(panel_ids)} panels")
        if not video_config:
            configs = self.config_manager.get("api_configs", [])
            video_config = next((c for c in configs if c.get("type") == "Video"), None)
            
            if not video_config:
                 print("DEBUG: No video config found, using mock")
                 video_config = {"provider": "mock", "api_key": "sk-placeholder"}
             
        self.current_video_config = video_config
        print(f"DEBUG: Using video config: {video_config}")
            
        video_dir = os.path.join(self.project_dir, "clips")
        os.makedirs(video_dir, exist_ok=True)
        
        self.video_queue = []
        for pid in panel_ids:
            panel = next((p for p in self.current_storyboard.panels if p.panel_id == pid), None)
            if panel and panel.image_path:
                # Use timestamp to create unique video filename, avoiding overwrite
                import time
                timestamp = int(time.time())
                output_path = os.path.join(video_dir, f"{panel.panel_id}_{timestamp}.mp4")
                self.video_queue.append((panel, output_path))
                
        if self.video_queue:
            print(f"DEBUG: Queue populated with {len(self.video_queue)} items. Starting process.")
            self.process_video_queue()
        else:
            print("DEBUG: Queue empty (no images found for selected panels)")
            QMessageBox.warning(self, "提示", "选中的分镜没有图片，无法生成视频。")

    def process_video_queue(self):
        try:
            if not self.video_queue:
                self.animate_btn.setText("🎥 生成视频")
                self.animate_btn.setEnabled(True)
                QMessageBox.information(self, "完成", "所有视频生成完毕！")
                self.save_storyboard()
                return
                
            panel, output_path = self.video_queue.pop(0)
            print(f"DEBUG: Processing panel {panel.panel_id}")
            
            self.animate_btn.setText(f"生成中... 剩余 {len(self.video_queue) + 1}")
            self.animate_btn.setEnabled(False)
            
            # Extract text (dialogue) from description
            text = panel.description
            role_name = None
            if text and ":" in text:
                parts = text.split(":", 1)
                role_name = parts[0].strip()
                text = parts[1].strip()
            elif not text:
                text = ""
                
            # Resolve voice_id and language
            voice_id = None 
            language = "English" # Default
            
            # Try to find character
            char_id = None
            if panel.characters:
                char_id = panel.characters[0]
            
            # Locate characters directory
            # self.project_dir is .../projects/ProjectName
            # characters_dir is .../resources/characters
            resources_dir = os.path.dirname(os.path.dirname(self.project_dir))
            characters_dir = os.path.join(resources_dir, "characters")
            
            found_char = None
            
            if os.path.exists(characters_dir):
                # If we have ID, look for it
                if char_id:
                    for f in os.listdir(characters_dir):
                        if f.endswith(".json") and char_id in f:
                            try:
                                with open(os.path.join(characters_dir, f), 'r', encoding='utf-8') as cf:
                                    found_char = Character.from_json(cf.read())
                                    break
                            except: pass
                
                # If not found by ID, try by role name
                if not found_char and role_name:
                    for f in os.listdir(characters_dir):
                        if f.endswith(".json"):
                            try:
                                with open(os.path.join(characters_dir, f), 'r', encoding='utf-8') as cf:
                                    c = Character.from_json(cf.read())
                                    if c.name == role_name:
                                        found_char = c
                                        break
                            except: pass
            
            if found_char:
                voice_id = found_char.voice_id
                if hasattr(found_char, 'language'):
                    language = found_char.language
                print(f"DEBUG: Found character {found_char.name}, Language: {language}, VoiceID: {voice_id}")
            
            # Get Project Ratio
            ratio = "16:9"
            try:
                project_json_path = os.path.join(self.project_dir, "project.json")
                if os.path.exists(project_json_path):
                    with open(project_json_path, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                        ratio = project_data.get("ratio", "16:9")
            except: pass
            
            # Get video prompt from user input
            prompt = getattr(panel, 'video_prompt', "").strip()
            
            # Ensure video_params exists (initialize from prompt_params if needed)
            if not hasattr(panel, 'video_params') or not panel.video_params:
                # Initialize video_params based on prompt_params but clear motion-related fields
                panel.video_params = panel.prompt_params.copy() if hasattr(panel, 'prompt_params') and panel.prompt_params else {}
                # Video-specific params should be empty initially
                panel.video_params.setdefault('camera_movement', '')
                panel.video_params.setdefault('action', '')
                panel.video_params.setdefault('environment_dynamics', '')
                panel.video_params.setdefault('lighting_dynamics', '')
                panel.video_params.setdefault('audio', '')
            
            # Construct video-specific prompt from parameters
            from core.storyboard.prompt_factory import construct_video_prompt
            # Use prompt_params for static base, video_params for dynamic instructions
            params_prompt = construct_video_prompt(panel.prompt_params if hasattr(panel, 'prompt_params') else {}, panel.video_params)
            
            # Combine user prompt with parameters
            if prompt:
                # User has provided custom video prompt
                final_prompt = prompt
                # Append video config suffix if configured
                if self.current_video_config and self.current_video_config.get("prompt_suffix"):
                    final_prompt += f" {self.current_video_config.get('prompt_suffix')}"
                # Append video parameters
                if params_prompt:
                    final_prompt += f". {params_prompt}"
                print(f"DEBUG: Using custom Video Prompt: {final_prompt}")
            else:
                # No custom prompt - generate from image prompt and description
                config_suffix = self.current_video_config.get("prompt_suffix") if self.current_video_config else None
                base_prompt = construct_veo_prompt(panel.image_prompt, panel.description, self.project_style, config_suffix)
                # Append video parameters
                final_prompt = base_prompt
                if params_prompt:
                    final_prompt += f". {params_prompt}"
                print(f"DEBUG: Generated Video Prompt (Fallback): {final_prompt}")
            
            prompt = final_prompt

            # Check for End Frame (Bridging)
            end_image_path = None
            if self.current_video_config and self.current_video_config.get("use_end_frame"):
                # Find next panel
                try:
                    current_idx = self.current_storyboard.panels.index(panel)
                    if current_idx < len(self.current_storyboard.panels) - 1:
                        next_panel = self.current_storyboard.panels[current_idx + 1]
                        if next_panel.image_path and os.path.exists(next_panel.image_path):
                            end_image_path = next_panel.image_path
                            print(f"DEBUG: Using end frame from panel {next_panel.panel_id}")
                except ValueError:
                    pass

            # Check for Video Extension
            input_video_path = None
            if self.current_video_config and self.current_video_config.get("extend_video"):
                # Find previous panel
                try:
                    current_idx = self.current_storyboard.panels.index(panel)
                    if current_idx > 0:
                        prev_panel = self.current_storyboard.panels[current_idx - 1]
                        if prev_panel.video_path and os.path.exists(prev_panel.video_path):
                            input_video_path = prev_panel.video_path
                            print(f"DEBUG: Extending video from panel {prev_panel.panel_id}")
                except ValueError:
                    pass

            print(f"DEBUG: Starting thread for panel {panel.panel_id}. Text: {text[:20]}... Ratio: {ratio}")
            self.video_thread = VideoGenThread(
                panel.panel_id, 
                panel.image_path, 
                prompt, 
                output_path, 
                self.current_video_config,
                text=text,
                voice_id=voice_id,
                ratio=ratio,
                language=language,
                end_image_path=end_image_path,
                input_video_path=input_video_path
            )
            self.video_thread.finished.connect(self.on_video_ready)
            self.video_thread.start()
            print("DEBUG: Thread started.")
        except Exception as e:
            print(f"ERROR in process_video_queue: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"处理队列失败: {str(e)}")
            self.animate_btn.setEnabled(True)
            self.animate_btn.setText("🎥 生成视频")
        
    def on_video_ready(self, panel_id, path, task_id=""):
        print(f"DEBUG: on_video_ready called for {panel_id}, path={path}, task_id={task_id}")
        
        # Validate file
        if path and os.path.exists(path):
            file_size = os.path.getsize(path)
            print(f"DEBUG: Video file size: {file_size} bytes")
            if file_size < 1000:
                print(f"WARNING: Video file is too small ({file_size} bytes), likely failed.")
                # Don't show error if we have task_id - user can retry
                if task_id:
                    QMessageBox.warning(self, "下载失败", f"视频文件下载失败或不完整。\n任务ID已保存: {task_id}\n\n您可以稍后点击\"重新获取\"按钮重试，无需重新生成。")
                else:
                    QMessageBox.warning(self, "生成失败", "生成的视频文件过小，可能已损坏。")
                path = None
        else:
            print(f"WARNING: Video file not found at {path}")
            if task_id:
                print(f"INFO: Task ID {task_id} saved for retry")
            path = None

        panel = next((p for p in self.current_storyboard.panels if p.panel_id == panel_id), None)
        if panel:
            # Save task_id for retry capability (even if download failed)
            if task_id:
                panel.last_video_task_id = task_id
                print(f"Saved task_id for panel {panel_id}: {task_id}")
                self.save_storyboard()
                
                # If download failed but we have task_id, refresh UI to show retry button
                if not path:
                    idx = self.current_storyboard.panels.index(panel)
                    if idx == self.current_panel_index:
                        self.on_shot_selected(idx)
            
            if path:
                # Save current video to history before updating (if it exists and is valid)
                if panel.video_path and os.path.exists(panel.video_path) and panel.video_path not in panel.history_videos:
                    print(f"Saving previous video to history: {panel.video_path}")
                    panel.history_videos.append(panel.video_path)
                
                panel.video_path = os.path.abspath(path)
                panel.is_animated = True
                
                # Update UI Thumbnail
                try:
                    idx = self.current_storyboard.panels.index(panel)
                    item = self.shot_list.item(idx)
                    if item:
                        widget = self.shot_list.itemWidget(item)
                        if widget:
                            # Assuming widget has update_thumb or similar. 
                            # If not, we might need to reload the item.
                            # Let's check if update_thumb exists, otherwise just refresh list
                            if hasattr(widget, 'update_thumb'):
                                widget.update_thumb()
                            else:
                                # Fallback: force refresh of the item widget
                                # This might be complex, so let's just try to update the label if possible
                                pass
                    
                    # If this is the currently selected panel, refresh the UI to enable the video button
                    if idx == self.current_panel_index:
                        self.on_shot_selected(idx)
                        # Auto-switch to video preview for better UX
                        self.btn_view_video.setChecked(True)
                        self.switch_preview_mode(1)
                        
                except Exception as e:
                    print(f"Error updating UI thumbnail: {e}")
        else:
            print(f"Video generation failed for panel {panel_id}")
            
        self.process_video_queue()

    def retry_fetch_video(self):
        """Retry fetching video using saved task_id"""
        if not self.current_storyboard or self.current_panel_index < 0:
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        
        if not hasattr(panel, 'last_video_task_id') or not panel.last_video_task_id:
            QMessageBox.warning(self, "无法重试", "未找到保存的任务ID，无法重新获取视频。")
            return
        
        task_id = panel.last_video_task_id
        
        # Confirm with user
        reply = QMessageBox.question(
            self, 
            "重新获取视频", 
            f"将使用保存的任务ID重新获取视频（无需重新生成）。\n\n任务ID: {task_id}\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable button during fetch
        self.retry_video_btn.setEnabled(False)
        self.retry_video_btn.setText("🔄 获取中...")
        
        # Create output path with timestamp to avoid overwrite
        import time
        timestamp = int(time.time())
        output_dir = os.path.join(self.project_dir, "videos")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{panel.panel_id}_retry_{timestamp}.mp4")
        
        # Start fetch thread (reuse VideoGenThread but with a special flag)
        from ai_engine.video_gen.video_client import VideoGenClient
        
        class RetryFetchThread(QThread):
            finished = pyqtSignal(str, str, str)  # panel_id, video_path, task_id
            
            def __init__(self, panel_id, task_id, output_path, api_config):
                super().__init__()
                self.panel_id = panel_id
                self.task_id = task_id
                self.output_path = output_path
                self.api_config = api_config
            
            def run(self):
                try:
                    client = VideoGenClient(
                        api_key=self.api_config.get("api_key"),
                        base_url=self.api_config.get("base_url"),
                        model=self.api_config.get("model"),
                        provider=self.api_config.get("provider"),
                        api_config=self.api_config
                    )
                    
                    video_path = client.retry_fetch_video(self.task_id, self.output_path)
                    self.finished.emit(self.panel_id, video_path or "", self.task_id)
                except Exception as e:
                    print(f"Error in retry fetch: {e}")
                    import traceback
                    traceback.print_exc()
                    self.finished.emit(self.panel_id, "", self.task_id)
        
        self.retry_thread = RetryFetchThread(panel.panel_id, task_id, output_path, self.current_video_config)
        self.retry_thread.finished.connect(self.on_retry_video_ready)
        self.retry_thread.start()
    
    def on_retry_video_ready(self, panel_id, path, task_id):
        """Handle retry fetch completion"""
        self.retry_video_btn.setEnabled(True)
        self.retry_video_btn.setText("🔄 重新获取视频")
        
        if path and os.path.exists(path):
            QMessageBox.information(self, "获取成功", "视频已成功获取！")
            self.on_video_ready(panel_id, path, task_id)
        else:
            QMessageBox.warning(self, "获取失败", "视频获取失败，请稍后再试或联系支持。")
    
    def retry_fetch_image(self):
        """Retry fetching image using saved URL"""
        if not self.current_storyboard or self.current_panel_index < 0:
            return
            
        panel = self.current_storyboard.panels[self.current_panel_index]
        
        if not hasattr(panel, 'last_image_task_id') or not panel.last_image_task_id:
            QMessageBox.warning(self, "无法重试", "未找到保存的图片URL，无法重新获取。")
            return
        
        image_url = panel.last_image_task_id
        
        # Confirm with user
        reply = QMessageBox.question(
            self, 
            "重新获取图片", 
            f"将使用保存的URL重新下载图片（无需重新生成）。\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable button during fetch
        self.retry_image_btn.setEnabled(False)
        self.retry_image_btn.setText("🔄 下载中...")
        
        # Also update main button to show status
        self.regen_btn.setEnabled(False)
        self.regen_btn.setText("正在下载...")
        
        # Create output path
        output_dir = os.path.join(self.project_dir, "images")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{panel.panel_id}_retry.png")
        
        # Get current API config
        selected_config = self.api_combo.currentData()
        if not selected_config:
            QMessageBox.warning(self, "配置错误", "未找到图片生成API配置")
            self.retry_image_btn.setEnabled(True)
            self.retry_image_btn.setText("🔄 重新获取图片")
            self.regen_btn.setEnabled(True)
            self.regen_btn.setText("⚡ 重绘画面")
            return
        
        # Start fetch thread
        from ai_engine.image_gen.image_client import ImageGenClient
        
        class RetryImageThread(QThread):
            finished = pyqtSignal(str, str, str)  # panel_id, image_path, image_url
            status = pyqtSignal(str)  # status message
            
            def __init__(self, panel_id, image_url, output_path, api_config):
                super().__init__()
                self.panel_id = panel_id
                self.image_url = image_url
                self.output_path = output_path
                self.api_config = api_config
            
            def run(self):
                try:
                    self.status.emit("正在连接服务器...")
                    client = ImageGenClient(
                        api_key=self.api_config.get("api_key"),
                        base_url=self.api_config.get("base_url"),
                        model=self.api_config.get("model"),
                        provider=self.api_config.get("provider")
                    )
                    
                    self.status.emit("正在下载图片...")
                    image_path = client.retry_download_image(self.image_url, self.output_path)
                    self.finished.emit(self.panel_id, image_path or "", self.image_url)
                except Exception as e:
                    print(f"Error in retry image fetch: {e}")
                    import traceback
                    traceback.print_exc()
                    self.finished.emit(self.panel_id, "", self.image_url)
        
        self.retry_image_thread = RetryImageThread(panel.panel_id, image_url, output_path, selected_config)
        self.retry_image_thread.finished.connect(self.on_retry_image_ready)
        self.retry_image_thread.status.connect(self.on_retry_image_status)
        self.retry_image_thread.start()
    
    def on_retry_image_status(self, msg):
        """Update status during retry"""
        self.regen_btn.setText(msg)
    
    def on_retry_image_ready(self, panel_id, path, image_url):
        """Handle retry image fetch completion"""
        self.retry_image_btn.setEnabled(True)
        self.retry_image_btn.setText("🔄 重新获取图片")
        self.regen_btn.setEnabled(True)
        self.regen_btn.setText("⚡ 重绘画面")
        
        if path and os.path.exists(path):
            QMessageBox.information(self, "获取成功", "图片已成功下载！")
            self.on_image_ready(panel_id, path, image_url)
        else:
            QMessageBox.warning(self, "获取失败", "图片下载失败，请检查网络连接或稍后再试。")


