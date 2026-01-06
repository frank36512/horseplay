from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QComboBox, QDialogButtonBox, QLabel, QCheckBox)

class ApiConfigDialog(QDialog):
    def __init__(self, parent=None, config_data=None):
        super().__init__(parent)
        self.setWindowTitle("API 配置")
        self.resize(400, 300)
        self.config_data = config_data or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_edit = QLineEdit(self.config_data.get("name", ""))
        self.name_edit.setPlaceholderText("给这个配置起个名字，如 '我的GPT-4'")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["LLM", "Embedding", "Image", "Video", "TTS", "ImageToVideo"])
        self.type_combo.setCurrentText(self.config_data.get("type", "LLM"))
        
        self.provider_edit = QComboBox()
        self.provider_edit.setEditable(True)
        self.provider_edit.addItems(["OpenAI", "Google", "Azure", "DeepSeek", "ElevenLabs", "Runway", "Luma", "Veo", "ComfyUI", "Local"])
        self.provider_edit.setCurrentText(self.config_data.get("provider", "openai"))
        self.provider_edit.setToolTip("选择或输入提供商名称")
        
        self.api_key_edit = QLineEdit(self.config_data.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.base_url_edit = QLineEdit(self.config_data.get("base_url", ""))
        self.base_url_edit.setPlaceholderText("可选，如本地部署地址")
        
        self.model_edit = QLineEdit(self.config_data.get("model", ""))
        self.model_edit.setPlaceholderText("可选，如 gpt-4, sd-xl")

        self.default_cb = QCheckBox("设为默认配置")
        self.default_cb.setChecked(self.config_data.get("is_default", False))
        self.default_cb.setToolTip("勾选后，此类型的API调用将优先使用该配置")

        form_layout.addRow("名称 (Name):", self.name_edit)
        form_layout.addRow("类型 (Type):", self.type_combo)
        form_layout.addRow("提供商 (Provider):", self.provider_edit)
        form_layout.addRow("API Key:", self.api_key_edit)
        form_layout.addRow("Base URL:", self.base_url_edit)
        form_layout.addRow("模型 (Model):", self.model_edit)
        form_layout.addRow("", self.default_cb)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "type": self.type_combo.currentText(),
            "provider": self.provider_edit.currentText(),
            "api_key": self.api_key_edit.text(),
            "base_url": self.base_url_edit.text(),
            "model": self.model_edit.text(),
            "is_default": self.default_cb.isChecked()
        }
