from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QProgressBar, QMessageBox, 
                             QFileDialog, QCheckBox, QGroupBox, QStackedWidget,
                             QFrame, QLineEdit, QGridLayout, QDialog, QRadioButton,
                             QButtonGroup, QScrollArea, QSlider, QListWidgetItem,
                             QFontComboBox, QSpinBox, QFormLayout, QComboBox)
from PyQt6.QtGui import QPixmap, QFont, QColor, QAction, QIcon, QPainter, QPen
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QRect
import os
import shutil
import json
from core.storyboard.storyboard_model import Storyboard
from core.character.character_model import Character
from ai_engine.audio.tts_client import TTSClient
from ai_engine.veo_service import VeoService
from core.config.config_manager import ConfigManager
from core.synthesis.video_composer import VideoComposer
from core.subtitle.subtitle_generator import SubtitleGenerator
from ai_engine.utils.prompt_utils import construct_veo_prompt

class SynthesisThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, storyboard, project_dir, config):
        super().__init__()
        self.storyboard = storyboard
        self.project_dir = project_dir
        self.config = config # {ratio, resolution, bgm, title_style, ...}

    def run(self):
        print("SynthesisThread started")
        try:
            self.progress.emit(5, "正在初始化合成引擎...")
            
            # 1. Setup Directories
            audio_dir = os.path.join(self.project_dir, "audio")
            clips_dir = os.path.join(self.project_dir, "clips")
            os.makedirs(audio_dir, exist_ok=True)
            os.makedirs(clips_dir, exist_ok=True)
            
            # Load Project Settings for Ratio/Resolution
            # This ensures we use the project's settings even if config passed from dialog is partial
            # (Though dialog should pass correct values now)
            project_style = None
            try:
                project_json_path = os.path.join(self.project_dir, "project.json")
                if os.path.exists(project_json_path):
                    with open(project_json_path, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                        # If config doesn't have them (e.g. direct call), use project settings
                        if "ratio" not in self.config:
                            self.config["ratio"] = project_data.get("ratio", "16:9")
                        if "resolution" not in self.config:
                            self.config["resolution"] = project_data.get("resolution", "1080p")
                        project_style = project_data.get("visual_style")
            except: pass
            
            composer = VideoComposer()
            tts = TTSClient()
            sub_gen = SubtitleGenerator()
            
            # Check for Veo configuration
            config_manager = ConfigManager()
            veo_config = None
            openai_config = None
            
            print(f"Checking API configs: {config_manager.get('api_configs', [])}")
            
            # First pass: look for defaults
            for api in config_manager.get("api_configs", []):
                if api.get("is_default"):
                    if api.get("type") == "Veo" or "veo" in api.get("model", "").lower():
                        veo_config = api
                    elif api.get("type") == "LLM" or api.get("provider") in ["openai", "302", "azure"]:
                        openai_config = api

            for api in config_manager.get("api_configs", []):
                # Match Veo by type, provider, or model name
                is_veo = False
                if api.get("type") == "Veo":
                    is_veo = True
                elif "veo" in api.get("model", "").lower():
                    is_veo = True
                elif api.get("provider") == "google" and "veo" in api.get("model", "").lower():
                    is_veo = True
                
                if is_veo and not veo_config:
                    veo_config = api
                    print(f"Found Veo config: {api.get('name')}")
                
                # Match OpenAI/Whisper compatible config
                if (api.get("provider") in ["openai", "302", "azure"] or api.get("type") == "LLM") and not openai_config:
                     openai_config = api
            
            veo_service = None
            if veo_config:
                print("Initializing VeoService...")
                try:
                    veo_service = VeoService(veo_config.get("api_key"), veo_config.get("base_url", "https://api.veo.ai/v1"))
                    print("VeoService initialized")
                except Exception as e:
                    print(f"Failed to init VeoService: {e}")
            else:
                print("No Veo config found")
            
            clip_paths = []
            total_panels = len(self.storyboard.panels)
            
            # Load Characters for Voice Mapping
            char_map = {}
            try:
                # Assuming project_dir is .../projects/ProjectName
                # Characters are in .../resources/characters
                root_resources = os.path.abspath(os.path.join(self.project_dir, "..", "..", "characters"))
                if os.path.exists(root_resources):
                    for f in os.listdir(root_resources):
                        if f.endswith(".json"):
                            try:
                                with open(os.path.join(root_resources, f), 'r', encoding='utf-8') as file:
                                    c = Character.from_json(file.read())
                                    char_map[c.id] = c
                                    char_map[c.name] = c
                            except: pass
            except Exception as e:
                print(f"Error loading characters for voice mapping: {e}")
            
            # Try to import aligner (Initialize before loop)
            try:
                from core.subtitle.subtitle_aligner import SubtitleAligner
                use_aligner = True
            except ImportError:
                use_aligner = False
                print("SubtitleAligner not available")

            # Calculate Dimensions
            ratio_str = self.config.get("ratio", "16:9")
            res_str = self.config.get("resolution", "1080p")
            
            # Base size (short side)
            base_size = 1080 if res_str.lower() == "1080p" else 720
            
            if ratio_str == "9:16":
                target_width = base_size
                target_height = int(base_size * 16 / 9)
            elif ratio_str == "3:4":
                target_width = base_size
                target_height = int(base_size * 4 / 3)
            elif ratio_str == "16:9":
                target_height = base_size
                target_width = int(base_size * 16 / 9)
            elif ratio_str == "4:3":
                target_height = base_size
                target_width = int(base_size * 4 / 3)
            else:
                # Default 16:9
                target_height = base_size
                target_width = int(base_size * 16 / 9)
            
            # Ensure even dimensions for codecs
            if target_width % 2 != 0: target_width += 1
            if target_height % 2 != 0: target_height += 1
            
            print(f"Target Resolution: {target_width}x{target_height} ({ratio_str})")
            
            quality = self.config.get('quality', 'high')

            # 2. Handle Cover (Optional)
            cover_duration = 0.0
            if self.config.get('cover_image') and os.path.exists(self.config['cover_image']):
                self.progress.emit(10, "正在生成封面...")
                cover_path = self.config['cover_image']
                cover_clip_path = os.path.join(clips_dir, "cover_clip.mp4")
                # Create 3s static clip
                path, dur = composer.create_clip(cover_path, None, cover_clip_path, duration=3.0, width=target_width, height=target_height, quality=quality)
                if path:
                    clip_paths.append(path)
                    cover_duration = 3.0
            
            # 3. Process Panels
            for i, panel in enumerate(self.storyboard.panels):
                progress_pct = 10 + int((i / total_panels) * 50)
                self.progress.emit(progress_pct, f"正在处理分镜 {i+1}/{total_panels}...")
                
                output_clip = os.path.join(clips_dir, f"clip_{panel.panel_id}.mp4")
                
                # Determine text and voice
                text_content = panel.description
                voice_id = None
                if ":" in panel.description:
                    parts = panel.description.split(":", 1)
                    speaker_name = parts[0].strip()
                    text_content = parts[1].strip()
                    if speaker_name in char_map:
                        voice_id = char_map[speaker_name].voice_id
                if not voice_id and panel.characters:
                    first_char_id = panel.characters[0]
                    if first_char_id in char_map:
                        voice_id = char_map[first_char_id].voice_id

                path = None
                dur = 0
                
                # Determine Voice Description for Veo
                voice_desc = None
                if panel.characters:
                    # Use the first character's voice description
                    char_id = panel.characters[0]
                    if char_id in char_map:
                        voice_desc = getattr(char_map[char_id], 'voice_description', None)

                # Veo Path
                # Check if panel already has a generated video (from "One-click to dynamic")
                if hasattr(panel, 'video_path') and panel.video_path and os.path.exists(panel.video_path):
                    print(f"Using existing Veo video for panel {i}: {panel.video_path}")
                    path = panel.video_path
                    dur = composer.get_audio_duration(path)
                
                # If no existing video, but Veo service is active, generate it now (Legacy/Fallback path)
                elif veo_service and panel.image_path and os.path.exists(panel.image_path):
                    print(f"Using Veo for panel {i}")
                    if os.path.exists(output_clip) and os.path.getsize(output_clip) > 1000:
                         path = output_clip
                         dur = composer.get_audio_duration(output_clip)
                    else:
                         # Use optimized prompt construction
                         visual_prompt = construct_veo_prompt(panel.image_prompt, panel.description, project_style)
                         print(f"DEBUG: Optimized Veo Prompt for Synthesis: {visual_prompt}")
                         
                         # Determine language from config or default to Chinese
                         veo_lang = veo_config.get("language", "Chinese") if veo_config else "Chinese"
                         
                         path = veo_service.generate_scene(
                             image_path=panel.image_path,
                             text=text_content, # Dialogue
                             voice_id=voice_id,
                             prompt=visual_prompt,
                             output_path=output_clip,
                             aspect_ratio=ratio_str,
                             voice_description=voice_desc,
                             language=veo_lang
                         )
                         if path:
                             dur = composer.get_audio_duration(path)

                # Standard Path (Fallback if Veo failed or not used)
                if not path:
                    # A. Audio
                    audio_path = os.path.join(audio_dir, f"{panel.panel_id}.wav")
                    if os.path.exists(audio_path) and os.path.getsize(audio_path) < 1000:
                        os.remove(audio_path)
                        
                    if not os.path.exists(audio_path):
                        print(f"Generating audio for panel {i}: {text_content} (Voice: {voice_id})")
                        tts.generate_audio(text_content, voice_id, audio_path)
                    else:
                        print(f"Using existing audio for panel {i}: {audio_path}")
                    
                    # B. Clip
                    if hasattr(panel, 'video_path') and panel.video_path and os.path.exists(panel.video_path):
                        path, dur = composer.create_video_clip(panel.video_path, audio_path, output_clip, width=target_width, height=target_height, quality=quality)
                    elif panel.image_path and os.path.exists(panel.image_path):
                        path, dur = composer.create_clip(panel.image_path, audio_path, output_clip, width=target_width, height=target_height, quality=quality)
                    else:
                        print(f"Skipping panel {i}: No image/video")
                        continue
                    
                if path:
                    # Update duration from actual file to prevent drift
                    actual_dur = composer.get_audio_duration(path)
                    if actual_dur > 0:
                        dur = actual_dur
                        print(f"Updated panel {i} duration from file: {dur}s")
                    
                    clip_paths.append(path)
                    panel.duration = dur # Store for subtitle generation
                    panel.final_clip_path = path # Store for alignment
                    
                    # Ensure we have extracted audio for alignment if it's a video file
                    if path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                         temp_audio_check = os.path.join(self.project_dir, f"temp_audio_{i}.wav")
                         extracted = composer.extract_audio(path, temp_audio_check)
                         if extracted and os.path.exists(extracted):
                             # Use this specific extracted audio for alignment later
                             panel.extracted_audio_path = extracted
                             print(f"Extracted audio for panel {i} to {extracted}")
                         else:
                             print(f"Failed to extract audio for panel {i}")

                    # --- PER-CLIP SUBTITLE BURNING (Fix for Sync Issues) ---
                    # Instead of global SRT, we align and burn subtitles into THIS clip immediately.
                    
                    # 1. Determine Text
                    text_to_burn = panel.description
                    if ":" in text_to_burn:
                        text_to_burn = text_to_burn.split(":", 1)[1].strip()
                    
                    # 2. Determine Timing (Relative to this clip)
                    start_rel = 0.0
                    end_rel = dur
                    
                    # Try precise alignment
                    if use_aligner:
                        target_audio = None
                        if hasattr(panel, 'extracted_audio_path') and panel.extracted_audio_path:
                            target_audio = panel.extracted_audio_path
                        elif hasattr(panel, 'final_clip_path') and os.path.exists(panel.final_clip_path):
                            # Fallback extraction
                            temp_audio = os.path.join(self.project_dir, "temp_align.wav")
                            composer.extract_audio(panel.final_clip_path, temp_audio)
                            if os.path.exists(temp_audio):
                                target_audio = temp_audio

                        if target_audio:
                            try:
                                api_key = None
                                base_url = None
                                if openai_config:
                                    api_key = openai_config.get("api_key")
                                    base_url = openai_config.get("base_url")
                                
                                transcript = SubtitleAligner.transcribe(target_audio, api_key=api_key, base_url=base_url)
                                if transcript and transcript.get("segments"):
                                    s = transcript["segments"][0]["start"]
                                    e = transcript["segments"][-1]["end"]
                                    if e > 0:
                                        start_rel = s
                                        end_rel = e
                                        print(f"Aligned panel {i} (Relative): {s:.2f}s - {e:.2f}s")
                                
                                if target_audio == os.path.join(self.project_dir, "temp_align.wav"):
                                    os.remove(target_audio)
                            except Exception as e:
                                print(f"Alignment failed for panel {i}: {e}")

                    # 3. Create Temp SRT for this clip
                    temp_srt = os.path.join(self.project_dir, f"temp_sub_{i}.srt")
                    with open(temp_srt, 'w', encoding='utf-8') as f:
                        f.write("1\n")
                        s_str = sub_gen.format_timestamp(start_rel).replace('.', ',')
                        e_str = sub_gen.format_timestamp(end_rel).replace('.', ',')
                        f.write(f"{s_str} --> {e_str}\n")
                        f.write(f"{text_to_burn}\n")
                    
                    # 4. Burn into clip
                    subbed_clip_path = os.path.join(clips_dir, f"clip_{panel.panel_id}_subbed.mp4")
                    print(f"Burning subtitle into clip {i}...")
                    
                    style = self.config.get('subtitle_style', {})
                    # Only burn if style is not "transparent"
                    if style.get('color') != 'transparent':
                        burned_path = composer.burn_subtitles(path, temp_srt, subbed_clip_path, style)
                        if burned_path and os.path.exists(burned_path):
                            # Replace the clip path in the list with the subbed version
                            clip_paths[-1] = burned_path
                            print(f"Replaced clip {i} with subbed version: {burned_path}")
                        else:
                            print(f"Failed to burn subtitle for clip {i}, keeping original.")
                    
                    if os.path.exists(temp_srt):
                        os.remove(temp_srt)
                    # -------------------------------------------------------
            
            # 4. Generate Subtitles (Global SRT - Optional/Backup)
            # We still generate it for reference, but we won't burn it globally if we did per-clip.
            # Actually, if we burned per-clip, we should NOT burn again.
            
            self.progress.emit(70, "正在合并视频...")
            temp_video = os.path.join(self.project_dir, "temp_concat.mp4")
            
            # BGM
            bgm_path = None
            bgm_name = self.config.get('bgm_name')
            # TODO: Resolve bgm_name to actual path
            
            # Enable Cross-Dissolve Transition (0.5s)
            result_path = composer.concat_clips(clip_paths, temp_video, bgm_path, quality=quality, transition_duration=0.5)
            
            if not result_path or not os.path.exists(result_path):
                raise Exception("Video concatenation failed. Check console logs for FFmpeg errors.")

            # 6. Final Output
            self.progress.emit(90, "完成...")
            final_output = os.path.join(self.project_dir, "final_output.mp4")
            
            if os.path.exists(final_output): os.remove(final_output)
            
            os.rename(result_path, final_output)
                
            self.finished.emit(final_output)
            return

            # Legacy Global Subtitle Logic (Disabled/Skipped)
            """
            srt_path = os.path.join(self.project_dir, "subtitles.srt")
            
            # Try to import aligner
            try:
                from core.subtitle.subtitle_aligner import SubtitleAligner
                use_aligner = True
            except ImportError:
                use_aligner = False
                print("SubtitleAligner not available")
            
            with open(srt_path, 'w', encoding='utf-8') as f:
            ...
            """

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class VideoExportDialog(QDialog):
    def __init__(self, project_dir=None, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir
        self.setWindowTitle("导出视频设置")
        self.resize(600, 500)
        self.setStyleSheet("background-color: #1e272e; color: white;")
        self.init_ui()
        self.load_project_settings()

    def load_project_settings(self):
        if not self.project_dir:
            return
            
        try:
            project_json_path = os.path.join(self.project_dir, "project.json")
            if os.path.exists(project_json_path):
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    ratio = project_data.get("ratio", "16:9")
                    resolution = project_data.get("resolution", "1080p")
                    # print(f"DEBUG: VideoExportDialog loaded settings: Ratio={ratio}, Resolution={resolution}")
                    
                    # Auto-select based on project setting
                    if ratio == "9:16":
                        self.r9_16.setChecked(True)
                    elif ratio == "3:4":
                        self.r3_4.setChecked(True)
                    elif ratio == "16:9":
                        self.r16_9.setChecked(True)
                    elif ratio == "4:3":
                        self.r4_3.setChecked(True)
                        
                    # Disable ratio selection as it's determined by project
                    self.r9_16.setEnabled(False)
                    self.r3_4.setEnabled(False)
                    self.r16_9.setEnabled(False)
                    self.r4_3.setEnabled(False)
                        
                    # Auto-select resolution
                    if resolution == "720p":
                        self.res720.setChecked(True)
                    else:
                        self.res1080.setChecked(True)
                        
                    # Add a label to indicate project setting
                    self.project_ratio_lbl.setText(f"当前项目设定: {ratio} / {resolution}")

                    # Update Resolution Labels with explicit dimensions
                    if ratio == "16:9":
                        self.res720.setText("标清 (1280x720)")
                        self.res1080.setText("高清 (1920x1080)")
                    elif ratio == "9:16":
                        self.res720.setText("标清 (720x1280)")
                        self.res1080.setText("高清 (1080x1920)")
                    elif ratio == "4:3":
                        self.res720.setText("标清 (960x720)")
                        self.res1080.setText("高清 (1440x1080)")
                    elif ratio == "3:4":
                        self.res720.setText("标清 (720x960)")
                        self.res1080.setText("高清 (1080x1440)")
                    else:
                        # Fallback
                        self.res720.setText("标清 (720p)")
                        self.res1080.setText("高清 (1080p)")

        except Exception as e:
            print(f"Error loading project settings in export dialog: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Ratio
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("视频比例"))
        self.project_ratio_lbl = QLabel("")
        self.project_ratio_lbl.setStyleSheet("color: #f1c40f; font-weight: bold;")
        header_layout.addWidget(self.project_ratio_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self.ratio_group = QButtonGroup(self)
        
        # Vertical Group
        v_group = QGroupBox("竖屏 (Portrait)")
        v_group.setStyleSheet("QGroupBox { border: 1px solid #5d6d7e; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        v_layout = QHBoxLayout(v_group)
        
        self.r9_16 = self.create_option_btn("9:16", True)
        self.r3_4 = self.create_option_btn("3:4")
        
        v_layout.addWidget(self.r9_16)
        v_layout.addWidget(self.r3_4)
        
        self.ratio_group.addButton(self.r9_16, 1)
        self.ratio_group.addButton(self.r3_4, 2)
        
        layout.addWidget(v_group)

        # Horizontal Group
        h_group = QGroupBox("横屏 (Landscape)")
        h_group.setStyleSheet("QGroupBox { border: 1px solid #5d6d7e; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        h_layout = QHBoxLayout(h_group)
        
        self.r16_9 = self.create_option_btn("16:9")
        self.r4_3 = self.create_option_btn("4:3")
        
        h_layout.addWidget(self.r16_9)
        h_layout.addWidget(self.r4_3)
        
        self.ratio_group.addButton(self.r16_9, 3)
        self.ratio_group.addButton(self.r4_3, 4)
        
        layout.addWidget(h_group)
        
        # Resolution
        layout.addWidget(QLabel("视频尺寸 (分辨率)"))
        res_layout = QHBoxLayout()
        self.res_group = QButtonGroup(self)
        
        self.res720 = self.create_option_btn("标清 (720p)", True)
        self.res1080 = self.create_option_btn("高清 (1080p)")
        
        self.res_group.addButton(self.res720, 1)
        self.res_group.addButton(self.res1080, 2)
        
        res_layout.addWidget(self.res720)
        res_layout.addWidget(self.res1080)
        layout.addLayout(res_layout)
        
        # Video Quality (Bitrate)
        layout.addWidget(QLabel("视频质量 (影响文件大小)"))
        quality_layout = QHBoxLayout()
        self.quality_group = QButtonGroup(self)
        
        self.q_high = self.create_option_btn("高画质 (~10M/s)", True)
        self.q_med = self.create_option_btn("中等 (~5M/s)")
        self.q_low = self.create_option_btn("低画质 (~2M/s)")
        
        self.quality_group.addButton(self.q_high, 1)
        self.quality_group.addButton(self.q_med, 2)
        self.quality_group.addButton(self.q_low, 3)
        
        quality_layout.addWidget(self.q_high)
        quality_layout.addWidget(self.q_med)
        quality_layout.addWidget(self.q_low)
        layout.addLayout(quality_layout)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("background-color: #7f8c8d; padding: 10px; border-radius: 5px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("确定")
        btn_ok.setStyleSheet("background-color: #f1c40f; color: #2c3e50; font-weight: bold; padding: 10px; border-radius: 5px;")
        btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def create_option_btn(self, text, checked=False):
        btn = QRadioButton(text)
        btn.setChecked(checked)
        btn.setStyleSheet("""
            QRadioButton {
                background-color: #34495e;
                padding: 15px;
                border-radius: 5px;
                font-size: 14px;
            }
            QRadioButton::indicator { width: 0; height: 0; }
            QRadioButton:checked {
                border: 2px solid #f1c40f;
                background-color: #2c3e50;
            }
        """)
        return btn

    def get_config(self):
        rid = self.ratio_group.checkedId()
        ratio_map = {1: "9:16", 2: "3:4", 3: "16:9", 4: "4:3"}
        
        qid = self.quality_group.checkedId()
        quality_map = {1: "high", 2: "medium", 3: "low"}
        
        return {
            "ratio": ratio_map.get(rid, "9:16"),
            "resolution": "720p" if self.res_group.checkedId() == 1 else "1080p",
            "quality": quality_map.get(qid, "high")
        }

class CoverPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 533)
        self.image_path = None
        self.mode = "cover" # cover or subtitle
        self.current_font_size = 30
        self.current_color = "#ffffff"
        self.subtitle_pos = "bottom" # bottom, center, top
        self.title_pos = "top" # top, center, bottom
        
        # Background Label
        self.bg_label = QLabel(self)
        self.bg_label.setGeometry(0, 0, 300, 533)
        self.bg_label.setStyleSheet("background-color: #000; border: 1px solid #5d6d7e;")
        self.bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title Label (Overlay)
        self.title_label = QLabel(self)
        self.update_text_pos()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.update_style()
        
    def set_mode(self, mode):
        self.mode = mode
        self.update_text_pos()
        self.update_style()
        
    def set_subtitle_pos(self, pos):
        self.subtitle_pos = pos
        self.update_text_pos()

    def set_title_pos(self, pos):
        self.title_pos = pos
        self.update_text_pos()

    def update_text_pos(self):
        if self.mode == "cover":
            h = 300 # Height of text area
            w = self.width() - 40
            x = 20
            
            if self.title_pos == "bottom":
                y = self.height() - h - 40
            elif self.title_pos == "center":
                y = (self.height() - h) // 2
            else: # top
                y = 60
                
            self.title_label.setGeometry(x, y, w, h)
        else:
            # Subtitle mode
            h = 100 # Height of text area
            w = self.width() - 40
            x = 20
            
            if self.subtitle_pos == "bottom":
                y = self.height() - 133
            elif self.subtitle_pos == "center":
                y = (self.height() - h) // 2
            elif self.subtitle_pos == "top":
                y = 40
            else:
                y = self.height() - 133
                
            self.title_label.setGeometry(x, y, w, h)

    def set_ratio(self, ratio_str):
        """Adjusts widget size based on aspect ratio."""
        # print(f"DEBUG: CoverPreviewWidget.set_ratio called with {ratio_str}")
        if ratio_str == "16:9":
            self.setFixedSize(533, 300)
        elif ratio_str == "9:16":
            self.setFixedSize(300, 533)
        elif ratio_str == "4:3":
            self.setFixedSize(400, 300)
        elif ratio_str == "3:4":
            self.setFixedSize(300, 400)
        else:
            self.setFixedSize(300, 533) # Default
            
        # Update background scaling
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        if self.image_path:
            self.set_image(self.image_path)
            
        self.update_text_pos()
        self.repaint()

    def set_image(self, path):
        self.image_path = path
        if path and os.path.exists(path):
            pix = QPixmap(path)
            self.bg_label.setPixmap(pix.scaled(self.width(), self.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        else:
            self.bg_label.setText("No Image")
            
    def set_title(self, text):
        self.title_label.setText(text)
        
    def set_font(self, font):
        self.title_label.setFont(font)
        # Re-apply size because setFont might reset it or we need to ensure it matches
        font = self.title_label.font()
        font.setPointSize(self.current_font_size)
        self.title_label.setFont(font)

    def set_font_size(self, size):
        self.current_font_size = size
        font = self.title_label.font()
        font.setPointSize(size)
        self.title_label.setFont(font)

    def set_text_style(self, color, outline_color=None):
        self.current_color = color
        self.update_style()

    def update_style(self):
        style = f"color: {self.current_color}; font-weight: bold; background: transparent;"
        # Note: Font size is handled by setFont/setPointSize for better control than stylesheet
        self.title_label.setStyleSheet(style)
        
        font = self.title_label.font()
        font.setPointSize(self.current_font_size)
        self.title_label.setFont(font)

class SynthesisWindow(QWidget):
    def __init__(self, project_dir):
        super().__init__()
        self.project_dir = project_dir
        self.current_storyboard = None
        self.current_episode_id = None
        self.init_ui()

    def set_current_episode(self, episode_id):
        self.current_episode_id = episode_id
        self.load_existing_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Top Bar ---
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #2c3e50; border-bottom: 1px solid #34495e;")
        top_layout = QHBoxLayout(top_bar)
        
        # Tabs
        self.tabs = QButtonGroup(self)
        self.tab_btns = []
        for i, name in enumerate(["封面设置", "字幕设置", "背景音乐"]):
            btn = QPushButton(name)
            btn.setCheckable(True)
            if i == 0: btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #bdc3c7;
                    font-size: 16px;
                    border: none;
                    padding: 10px 20px;
                }
                QPushButton:checked {
                    color: #f1c40f;
                    font-weight: bold;
                    border-bottom: 2px solid #f1c40f;
                }
            """)
            self.tabs.addButton(btn, i)
            self.tab_btns.append(btn)
            top_layout.addWidget(btn)
            
        self.tabs.idClicked.connect(self.switch_tab)
        
        top_layout.addStretch()
        
        # Export Button
        self.gen_btn = QPushButton("导出视频")
        self.gen_btn.setStyleSheet("background-color: #f1c40f; color: #2c3e50; font-weight: bold; padding: 8px 20px; border-radius: 5px;")
        self.gen_btn.clicked.connect(self.open_export_dialog)
        top_layout.addWidget(self.gen_btn)
        
        layout.addWidget(top_bar)
        
        # --- Content Area ---
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #1e272e;")
        
        # Page 1: Cover
        self.page_cover = self.create_cover_page()
        self.stack.addWidget(self.page_cover)
        
        # Page 2: Subtitles
        self.page_subs = self.create_subs_page()
        self.stack.addWidget(self.page_subs)
        
        # Page 3: Music
        self.page_music = self.create_music_page()
        self.stack.addWidget(self.page_music)
        
        layout.addWidget(self.stack)

    def create_cover_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setSpacing(15)
        
        # Project Info Label
        self.project_info_lbl = QLabel("")
        self.project_info_lbl.setStyleSheet("color: #e74c3c; font-weight: bold; font-size: 16px; margin-bottom: 10px;")
        self.project_info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.project_info_lbl)
        
        # 1. Preview Area (Top)
        preview_container = QWidget()
        preview_layout = QHBoxLayout(preview_container)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_preview = CoverPreviewWidget()
        self.cover_preview.set_title("标题样式")
        preview_layout.addWidget(self.cover_preview)
        layout.addWidget(preview_container)
        
        # 2. Cover Selection Gallery (Middle)
        gallery_container = QWidget()
        gallery_layout = QHBoxLayout(gallery_container)
        gallery_layout.setContentsMargins(0, 0, 0, 0)
        
        upload_btn = QPushButton("上传封面图")
        upload_btn.setFixedSize(100, 80)
        upload_btn.setStyleSheet("background-color: #34495e; color: white; border: 1px dashed #7f8c8d; border-radius: 5px;")
        upload_btn.clicked.connect(self.upload_cover_image)
        gallery_layout.addWidget(upload_btn)
        
        self.cover_scroll = QScrollArea()
        self.cover_scroll.setFixedHeight(100)
        self.cover_scroll.setWidgetResizable(True)
        self.cover_scroll.setStyleSheet("border: none; background: transparent;")
        
        self.cover_gallery_widget = QWidget()
        self.cover_gallery_layout = QHBoxLayout(self.cover_gallery_widget)
        self.cover_gallery_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.cover_gallery_layout.setContentsMargins(0, 0, 0, 0)
        self.cover_scroll.setWidget(self.cover_gallery_widget)
        
        gallery_layout.addWidget(self.cover_scroll)
        
        # Wrap gallery in a frame to limit width
        gallery_frame = QFrame()
        gallery_frame.setFixedWidth(600)
        gallery_frame_layout = QVBoxLayout(gallery_frame)
        gallery_frame_layout.addWidget(gallery_container)
        layout.addWidget(gallery_frame)
        
        # 3. Settings Area (Bottom)
        form_frame = QFrame()
        form_frame.setFixedWidth(600)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(10)
        
        # Title Input
        form_layout.addWidget(QLabel("封面标题"))
        self.title_input = QLineEdit("标题样式")
        self.title_input.setStyleSheet("background-color: #34495e; color: white; padding: 10px; border-radius: 5px; font-size: 14px;")
        self.title_input.textChanged.connect(lambda t: self.cover_preview.set_title(t))
        form_layout.addWidget(self.title_input)
        
        # Font Settings
        font_layout = QHBoxLayout()
        
        # Font Family
        font_layout.addWidget(QLabel("标题字体:"))
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.cover_preview.set_font)
        self.font_combo.setStyleSheet("background-color: #34495e; color: white; padding: 5px;")
        font_layout.addWidget(self.font_combo)
        
        # Font Size
        font_layout.addWidget(QLabel("标题大小:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 100)
        self.size_spin.setValue(30)
        self.size_spin.valueChanged.connect(self.cover_preview.set_font_size)
        self.size_spin.setStyleSheet("background-color: #34495e; color: white; padding: 5px;")
        font_layout.addWidget(self.size_spin)
        
        # Title Position
        font_layout.addWidget(QLabel("位置:"))
        self.title_pos_combo = QComboBox()
        self.title_pos_combo.addItems(["顶部 (Top)", "居中 (Center)", "底部 (Bottom)"])
        self.title_pos_combo.setCurrentText("顶部 (Top)") # Default
        self.title_pos_combo.setStyleSheet("background-color: #34495e; color: white; padding: 5px;")
        self.title_pos_combo.currentIndexChanged.connect(self.update_title_pos)
        font_layout.addWidget(self.title_pos_combo)
        
        font_layout.addStretch()
        form_layout.addLayout(font_layout)
        
        # Style Selection
        form_layout.addWidget(QLabel("选择标题样式"))
        style_grid = QGridLayout()
        style_grid.setSpacing(10)
        
        styles = [
            {'color': '#ffffff', 'name': '标题样式'},
            {'color': '#f1c40f', 'name': '标题样式'},
            {'color': '#e74c3c', 'name': '标题样式'},
            {'color': '#3498db', 'name': '标题样式'},
            {'color': '#2ecc71', 'name': '标题样式'},
            {'color': '#9b59b6', 'name': '标题样式'},
            {'color': '#e67e22', 'name': '标题样式'},
            {'color': '#95a5a6', 'name': '标题样式'},
        ]
        
        for i, style in enumerate(styles):
            btn = QPushButton(style['name'])
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {style['color']};
                    font-weight: bold;
                    font-size: 16px;
                    background-color: #34495e;
                    border: 1px solid #5d6d7e;
                    padding: 15px;
                    border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: #2c3e50;
                    border: 1px solid {style['color']};
                }}
            """)
            # Use default argument to capture loop variable
            btn.clicked.connect(lambda checked, c=style['color']: self.cover_preview.set_text_style(c))
            style_grid.addWidget(btn, i // 4, i % 4)
            
        form_layout.addLayout(style_grid)
        form_layout.addStretch() # Push everything up
        
        layout.addWidget(form_frame)
        layout.addStretch() # Push form frame up
        return page

    def upload_cover_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择封面图片", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.cover_preview.set_image(path)

    def create_subs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setSpacing(10)
        
        # Preview
        preview_container = QWidget()
        preview_layout = QHBoxLayout(preview_container)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_preview = CoverPreviewWidget()
        self.sub_preview.set_mode("subtitle")
        self.sub_preview.set_title("这里是字幕的显示效果预览")
        preview_layout.addWidget(self.sub_preview)
        layout.addWidget(preview_container)
        
        # Set initial ratio if project loaded
        if self.project_dir:
             try:
                project_json_path = os.path.join(self.project_dir, "project.json")
                if os.path.exists(project_json_path):
                    with open(project_json_path, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                        ratio = project_data.get("ratio", "9:16")
                        self.sub_preview.set_ratio(ratio)
             except: pass
             
        # Settings Frame
        form_frame = QFrame()
        form_frame.setFixedWidth(600)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(5)
        
        # Subtitle Position and Size
        pos_size_layout = QHBoxLayout()
        
        # Position
        pos_size_layout.addWidget(QLabel("字幕位置:"))
        self.sub_pos_combo = QComboBox()
        self.sub_pos_combo.addItems(["底部 (Bottom)", "居中 (Center)", "顶部 (Top)"])
        self.sub_pos_combo.setStyleSheet("background-color: #34495e; color: white; padding: 5px;")
        self.sub_pos_combo.currentIndexChanged.connect(self.update_subtitle_pos)
        pos_size_layout.addWidget(self.sub_pos_combo)
        
        # Size
        pos_size_layout.addWidget(QLabel("字幕大小:"))
        self.sub_size_spin = QSpinBox()
        self.sub_size_spin.setRange(10, 100)
        self.sub_size_spin.setValue(30)
        self.sub_size_spin.setStyleSheet("background-color: #34495e; color: white; padding: 5px;")
        self.sub_size_spin.valueChanged.connect(self.sub_preview.set_font_size)
        pos_size_layout.addWidget(self.sub_size_spin)
        
        pos_size_layout.addStretch()
        form_layout.addLayout(pos_size_layout)
        
        form_layout.addWidget(QLabel("选择字幕样式"))
        
        # Style Grid
        style_grid = QGridLayout()
        style_grid.setSpacing(10)
        
        sub_styles = [
            {'name': '无字幕', 'color': 'transparent'},
            {'name': '标准白', 'color': '#ffffff'},
            {'name': '活力黄', 'color': '#f1c40f'},
            {'name': '描边白', 'color': '#ffffff', 'outline': '#000'}, 
            {'name': '阴影白', 'color': '#ffffff', 'shadow': True},
            {'name': '暖阳橙', 'color': '#e67e22'},
            {'name': '天空蓝', 'color': '#3498db'},
            {'name': '烈焰红', 'color': '#e74c3c'},
        ]
        
        for i, style in enumerate(sub_styles):
            btn = QPushButton(style['name'])
            if style['color'] == 'transparent':
                btn.setText("🚫 无字幕")
                
            # Simulate visual style in button
            btn_style = f"""
                QPushButton {{
                    color: {style.get('color', 'white')};
                    font-weight: bold;
                    font-size: 14px;
                    background-color: #34495e;
                    border: 1px solid #5d6d7e;
                    padding: 8px;
                    border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: #2c3e50;
                    border: 1px solid #f1c40f;
                }}
            """
            btn.setStyleSheet(btn_style)
            # Store style on click
            btn.clicked.connect(lambda checked, s=style: self.set_subtitle_style(s))
            style_grid.addWidget(btn, i // 4, i % 4)
            
        form_layout.addLayout(style_grid)
        form_layout.addStretch() # Push everything up
        
        layout.addWidget(form_frame)
        layout.addStretch() # Push form frame up towards preview
        
        return page

    def update_title_pos(self, index):
        # 0: Top, 1: Center, 2: Bottom
        pos_map = {0: "top", 1: "center", 2: "bottom"}
        self.cover_preview.set_title_pos(pos_map[index])

    def update_subtitle_pos(self, index):
        # 0: Bottom, 1: Center, 2: Top
        pos_map = {0: "bottom", 1: "center", 2: "top"}
        self.sub_preview.set_subtitle_pos(pos_map[index])

    def set_subtitle_style(self, style):
        self.selected_subtitle_style = style
        self.sub_preview.set_text_style(style.get('color'))
        # You might want to pass more style info to preview if it supported it

    def create_music_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 20)
        
        # Volume Control Frame
        vol_frame = QFrame()
        vol_frame.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")
        vol_layout = QHBoxLayout(vol_frame)
        
        vol_layout.addWidget(QLabel("背景音乐音量:"))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(50)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #5d6d7e;
                height: 8px;
                background: #34495e;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #f1c40f;
                border: 1px solid #f1c40f;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        self.vol_lbl = QLabel("50 %")
        self.vol_lbl.setFixedWidth(50)
        self.vol_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.vol_slider.valueChanged.connect(lambda v: self.vol_lbl.setText(f"{v} %"))
        
        vol_layout.addWidget(self.vol_slider)
        vol_layout.addWidget(self.vol_lbl)
        layout.addWidget(vol_frame)
        
        layout.addSpacing(20)
        layout.addWidget(QLabel("背景音乐"))
        
        # Music List
        self.music_list = QListWidget()
        self.music_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; }
            QListWidget::item { 
                background-color: #34495e; 
                margin-bottom: 5px; 
                border-radius: 5px; 
                padding: 5px;
                color: white;
            }
            QListWidget::item:selected { 
                background-color: #2c3e50; 
                border: 1px solid #f1c40f; 
            }
        """)
        
        musics = [
            "无声", "甜甜恋爱", "回忆治愈", "伤感虐恋", "遗憾释怀", 
            "恐怖悬疑", "古风修仙", "轻松惬意", "紧张刺激", "超燃战斗",
            "热血胜利", "逆风翻盘", "末世惨烈"
        ]
        
        for m in musics:
            item = QListWidgetItem(self.music_list)
            item.setSizeHint(QSize(0, 60))
            item.setData(Qt.ItemDataRole.UserRole, m) # Store music name
            
            # Custom widget for item
            widget = QWidget()
            w_layout = QHBoxLayout(widget)
            w_layout.setContentsMargins(10, 5, 10, 5)
            
            icon_lbl = QLabel("🎵")
            icon_lbl.setStyleSheet("font-size: 20px;")
            w_layout.addWidget(icon_lbl)
            
            name_lbl = QLabel(m)
            name_lbl.setStyleSheet("font-weight: bold; font-size: 16px; color: white;")
            w_layout.addWidget(name_lbl)
            
            w_layout.addStretch()
            
            if m == "遗憾释怀": # Mock selected
                badge = QLabel("推荐")
                badge.setStyleSheet("background-color: #e74c3c; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;")
                w_layout.addWidget(badge)
            
            play_btn = QPushButton("▶")
            play_btn.setFixedSize(30, 30)
            play_btn.setStyleSheet("background-color: #f1c40f; color: black; border-radius: 15px; font-weight: bold;")
            w_layout.addWidget(play_btn)
            
            self.music_list.setItemWidget(item, widget)
            
        layout.addWidget(self.music_list)
        return page

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

    def load_existing_data(self):
        # Load storyboard to get cover image candidate
        if not self.project_dir:
            return
            
        # Load Project Settings (Ratio)
        try:
            project_json_path = os.path.join(self.project_dir, "project.json")
            if os.path.exists(project_json_path):
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    ratio = project_data.get("ratio", "9:16")
                    # mtime = os.path.getmtime(project_json_path)
                    # print(f"DEBUG: SynthesisWindow loaded ratio from {project_json_path} (mtime={mtime}): {ratio}")
                    self.cover_preview.set_ratio(ratio)
                    if hasattr(self, 'sub_preview'):
                        self.sub_preview.set_ratio(ratio)
                    
                    # Set Project Name
                    project_name = project_data.get("name", "未命名项目")
                    if hasattr(self, 'project_info_lbl'):
                        ep_text = f"第{self.current_episode_id}集" if self.current_episode_id else "第1集"
                        self.project_info_lbl.setText(f"{project_name} / {ep_text}")
            else:
                print(f"DEBUG: project.json not found at {project_json_path}")
        except Exception as e:
            print(f"DEBUG: Error loading project settings for preview: {e}")

        sb_path = os.path.join(self.project_dir, "storyboard.json")
        if self.current_episode_id:
            sb_path = os.path.join(self.project_dir, "storyboards", f"episode_{self.current_episode_id}.json")

        if os.path.exists(sb_path):
            try:
                with open(sb_path, 'r', encoding='utf-8') as f:
                    self.current_storyboard = Storyboard.from_json(f.read())
                
                self.load_cover_gallery()
                
                # Use first image as cover preview
                if self.current_storyboard.panels:
                    # Find first panel with an image
                    first_img_panel = next((p for p in self.current_storyboard.panels if p.image_path and os.path.exists(p.image_path)), None)
                    
                    if first_img_panel:
                        self.cover_preview.set_image(first_img_panel.image_path)
                        # Also set for subtitle preview if available
                        if hasattr(self, 'sub_preview'):
                            self.sub_preview.set_image(first_img_panel.image_path)
                        
            except Exception as e:
                print(f"Error loading storyboard for synthesis: {e}")

    def load_cover_gallery(self):
        # Clear existing
        if not hasattr(self, 'cover_gallery_layout'):
            return

        for i in reversed(range(self.cover_gallery_layout.count())):
            item = self.cover_gallery_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
                
        if not self.current_storyboard:
            return
            
        for panel in self.current_storyboard.panels:
            if panel.image_path and os.path.exists(panel.image_path):
                btn = QPushButton()
                btn.setFixedSize(80, 100) # Aspect ratio roughly matches cover
                btn.setStyleSheet(f"""
                    QPushButton {{
                        border: 2px solid #34495e;
                        background-color: black;
                        border-radius: 5px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #f1c40f;
                    }}
                """)
                
                # Set icon
                pix = QPixmap(panel.image_path)
                icon = QIcon(pix)
                btn.setIcon(icon)
                btn.setIconSize(QSize(76, 96))
                
                # Connect click
                btn.clicked.connect(lambda checked, path=panel.image_path: self.cover_preview.set_image(path))
                
                self.cover_gallery_layout.addWidget(btn)
                
        self.cover_gallery_layout.addStretch()

    def get_cover_image_path(self):
        """Saves the current cover preview to a temp file and returns path."""
        try:
            temp_path = os.path.join(self.project_dir, "temp_cover.png")
            self.cover_preview.grab().save(temp_path)
            return temp_path
        except Exception as e:
            print(f"Error saving cover: {e}")
            return None

    def open_export_dialog(self):
        dialog = VideoExportDialog(self.project_dir, self)
        if dialog.exec():
            config = dialog.get_config()
            
            # Add other settings
            config['cover_image'] = self.get_cover_image_path()
            
            # Music
            if self.music_list.currentItem():
                config['bgm_name'] = self.music_list.currentItem().data(Qt.ItemDataRole.UserRole)
            else:
                config['bgm_name'] = None
                
            config['bgm_volume'] = self.vol_slider.value() / 100.0
            
            # Subtitles
            config['subtitle_style'] = getattr(self, 'selected_subtitle_style', {})
            
            self.start_synthesis(config)

    def start_synthesis(self, config):
        if not self.current_storyboard:
            QMessageBox.warning(self, "提示", "请先加载分镜数据。")
            return
            
        self.gen_btn.setEnabled(False)
        self.gen_btn.setText("生成中...")
        
        self.thread = SynthesisThread(self.current_storyboard, self.project_dir, config)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def on_finished(self, path):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("导出视频")
        QMessageBox.information(self, "完成", f"视频已生成: {path}")

    def on_error(self, msg):
        self.gen_btn.setEnabled(True)
        self.gen_btn.setText("导出视频")
        QMessageBox.critical(self, "错误", msg)
