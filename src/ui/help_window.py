from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, 
                             QPushButton, QLineEdit, QFormLayout, QTextEdit, 
                             QMessageBox, QDialog, QHBoxLayout, QApplication)
from PyQt6.QtCore import Qt, QDate
import uuid
import hashlib
from datetime import datetime, timedelta
from core.config.config_manager import ConfigManager

class HelpWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.init_ui()
        self.check_trial_status()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #34495e; background: #313131; }
            QTabBar::tab { background: #34495e; color: #bdc3c7; padding: 10px 20px; }
            QTabBar::tab:selected { background: #313131; color: #f1c40f; border-bottom: 2px solid #f1c40f; }
            QWidget { background-color: #313131; }
        """)
        
        # Tab 1: About
        self.about_tab = QWidget()
        self.init_about_tab()
        self.tabs.addTab(self.about_tab, "关于")
        
        # Tab 2: Help
        self.help_tab = QWidget()
        self.init_help_tab()
        self.tabs.addTab(self.help_tab, "帮助")
        
        # Tab 3: Register
        self.register_tab = QWidget()
        self.init_register_tab()
        self.tabs.addTab(self.register_tab, "注册")
        
        layout.addWidget(self.tabs)

    def init_about_tab(self):
        layout = QVBoxLayout(self.about_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("马上短剧生成系统 (Horseplay)")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        version = QLabel("版本: v1.0.0 (Preview)")
        version.setStyleSheet("font-size: 14px; color: #bdc3c7;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc = QLabel("一款基于大语言模型的全流程AI短剧创作工具。\n\n"
                      "核心功能：\n"
                      "1. 剧本生成：一键生成分集剧情与对话\n"
                      "2. 角色定制：个性化角色形象与声音设定\n"
                      "3. 分镜制作：自动拆解剧本，生成AI绘画提示词\n"
                      "4. 视频合成：多模态融合，生成最终短剧视频\n\n"
                      "技术支持：\n"
                      "基于 PyQt6 + OpenAI/Claude + Veo/Sora 等先进技术构建。")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("margin: 20px; color: #ecf0f1; font-size: 14px; line-height: 1.5;")
        
        copyright = QLabel("© 2025 AI Drama Studio. All rights reserved.\n联系我们: support@aidrama.com")
        copyright.setStyleSheet("color: #7f8c8d; margin-top: 20px;")
        copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(desc)
        layout.addWidget(copyright)
        layout.addStretch()

    def init_help_tab(self):
        layout = QVBoxLayout(self.help_tab)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setStyleSheet("""
            QTextEdit {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        help_text.setMarkdown("""
# 马上短剧生成系统 (Horseplay) - 使用指南

## 1. 快速开始
- **新建项目**：在"项目管理"页点击"新建项目"，填写项目名称和简介。
- **生成大纲**：进入项目后，点击"生成大纲"获取初步故事结构。

## 2. 剧本创作流程
1. **分集剧情**：在左侧列表选择集数，输入本集摘要。
2. **智能生成**：点击"智能生成"按钮，AI将自动编写对话和动作。
3. **人工润色**：在右侧编辑器中直接修改内容，支持实时保存。

## 3. 角色设定
- **添加角色**：点击"添加角色"，填写姓名、性别、性格特征。
- **形象定制**：上传参考图或使用AI生成角色头像。
- **声音配置**：选择合适的音色（支持多种语言和情感）。

## 4. 分镜与画面
- **自动拆解**：系统自动将剧本拆解为分镜画面。
- **提示词优化**：支持手动修改每个分镜的绘画提示词。
- **批量生成**：一键生成所有分镜图片。

## 5. 视频合成
- **预览检查**：播放生成的语音和画面，确认同步效果。
- **导出视频**：点击"开始合成"，生成最终的MP4视频文件。

## 常见问题
- **Q: 生成速度慢？** A: 取决于网络状态和所选模型的响应速度。
- **Q: 图片不满意？** A: 尝试修改提示词或更换底图重新生成。
        """)
        layout.addWidget(help_text)

    def get_hardware_id(self):
        try:
            mac = uuid.getnode()
            return hashlib.md5(str(mac).encode()).hexdigest().upper()
        except:
            return "UNKNOWN-DEVICE-ID"

    def init_register_tab(self):
        layout = QFormLayout(self.register_tab)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Style for labels in FormLayout
        self.register_tab.setStyleSheet("""
            QLabel { color: white; font-size: 14px; }
            QLineEdit { 
                padding: 8px; 
                background-color: #34495e; 
                color: white; 
                border: 1px solid #5d6d7e; 
                border-radius: 4px;
            }
        """)
        
        # Hardware ID Display
        self.hw_id_display = QLineEdit()
        self.hw_id_display.setText(self.get_hardware_id())
        self.hw_id_display.setReadOnly(True)
        self.hw_id_display.setStyleSheet("background-color: #2c3e50; color: #95a5a6;")
        
        self.license_key = QLineEdit()
        self.license_key.setPlaceholderText("请输入您的序列号/激活码")
        
        self.email = QLineEdit()
        self.email.setPlaceholderText("注册邮箱")
        
        register_btn = QPushButton("激活 / 注册")
        register_btn.setFixedHeight(40)
        register_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px;")
        register_btn.clicked.connect(self.handle_register)
        
        self.status_label = QLabel("正在检查授权状态...")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        layout.addRow("机器码:", self.hw_id_display)
        layout.addRow("序列号:", self.license_key)
        layout.addRow("邮箱:", self.email)
        layout.addRow("", register_btn)
        layout.addRow("", self.status_label)

    def check_trial_status(self):
        first_run = self.config_manager.get("first_run_date")
        today = datetime.now().strftime("%Y-%m-%d")
        
        if not first_run:
            self.config_manager.set("first_run_date", today)
            first_run = today
            
        try:
            first_run_date = datetime.strptime(first_run, "%Y-%m-%d")
        except ValueError:
            # Reset if format is wrong
            self.config_manager.set("first_run_date", today)
            first_run_date = datetime.now()

        current_date = datetime.now()
        days_diff = (current_date - first_run_date).days
        
        trial_days = 180
        remaining = trial_days - days_diff
        
        is_activated = self.config_manager.get("is_activated", False)
        
        if is_activated:
            self.status_label.setText("当前状态: 已激活 (正式版)")
            self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
            self.license_key.setEnabled(False)
            self.email.setEnabled(False)
        else:
            if remaining > 0:
                self.status_label.setText(f"当前状态: 试用版 (剩余 {remaining} 天)")
                self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
            else:
                self.status_label.setText("当前状态: 试用期已结束，请激活")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                # Show popup if expired
                QMessageBox.critical(self, "试用期结束", "您的180天试用期已结束。\n请购买注册码以继续使用。")

    def handle_register(self):
        key = self.license_key.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请输入序列号")
            return
        
        # Simple mock validation (In real app, verify with server or algorithm)
        if key == "1234-5678-90AB-CDEF": # Backdoor for testing
            self.config_manager.set("is_activated", True)
            QMessageBox.information(self, "成功", "注册成功！感谢您的支持。")
            self.check_trial_status()
        else:
            QMessageBox.warning(self, "失败", "无效的序列号，请检查后重试。")
