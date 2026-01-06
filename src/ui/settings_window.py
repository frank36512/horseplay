from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QAbstractItemView, QTabWidget,
                             QFormLayout, QLineEdit, QCheckBox, QFileDialog)
from PyQt6.QtCore import Qt
from core.config.config_manager import ConfigManager
from ui.api_config_dialog import ApiConfigDialog
import os
import uuid

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.api_configs = self.config_manager.get("api_configs", [])
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #34495e; background: #2c3e50; }
            QTabBar::tab { background: #34495e; color: #bdc3c7; padding: 10px 20px; }
            QTabBar::tab:selected { background: #2c3e50; color: #f1c40f; border-bottom: 2px solid #f1c40f; }
        """)
        layout.addWidget(self.tabs)
        
        # Tab 1: API Settings
        self.api_tab = QWidget()
        self.init_api_tab()
        self.tabs.addTab(self.api_tab, "API 服务配置")
        
        # Tab 2: General Settings
        self.general_tab = QWidget()
        self.init_general_tab()
        self.tabs.addTab(self.general_tab, "通用设置")

        # Tab 3: Path Settings
        self.path_tab = QWidget()
        self.init_path_tab()
        self.tabs.addTab(self.path_tab, "路径设置")

    def init_api_tab(self):
        layout = QVBoxLayout(self.api_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Table
        self.api_table = QTableWidget()
        self.api_table.setColumnCount(5)
        self.api_table.setHorizontalHeaderLabels(["名称", "类型", "提供商", "模型", "ID"])
        
        # Evenly distribute columns
        header = self.api_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.api_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.api_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.api_table.hideColumn(4) # Hide ID column
        self.api_table.setStyleSheet("background-color: #34495e; color: white; gridline-color: #5d6d7e;")
        self.api_table.verticalHeader().setVisible(False)
        
        self.refresh_table()
        
        layout.addWidget(self.api_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加配置")
        add_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px;")
        add_btn.clicked.connect(self.add_config)
        
        edit_btn = QPushButton("编辑配置")
        edit_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        edit_btn.clicked.connect(self.edit_config)
        
        del_btn = QPushButton("删除配置")
        del_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px;")
        del_btn.clicked.connect(self.delete_config)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

    def init_general_tab(self):
        self.general_tab.setStyleSheet("background-color: #2c3e50; color: white;")
        layout = QFormLayout(self.general_tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        lang_lbl = QLabel("简体中文")
        lang_lbl.setStyleSheet("color: white;")
        layout.addRow(self.create_label("界面语言:"), lang_lbl)
        
        # Embedding Model Setting
        self.embed_model_edit = QLineEdit()
        self.embed_model_edit.setText(self.config_manager.get("embedding_model", "text-embedding-3-small"))
        self.embed_model_edit.setPlaceholderText("默认: text-embedding-3-small")
        self.embed_model_edit.setStyleSheet("padding: 5px; color: #ecf0f1; background-color: #2c3e50; border: 1px solid #34495e;")
        self.embed_model_edit.editingFinished.connect(self.save_general_settings)
        layout.addRow(self.create_label("Embedding 模型:"), self.embed_model_edit)
        
        auto_save = QCheckBox("开启")
        auto_save.setChecked(True)
        auto_save.setStyleSheet("color: white;")
        layout.addRow(self.create_label("自动保存:"), auto_save)
        
        theme_lbl = QLabel("深色模式")
        theme_lbl.setStyleSheet("color: white;")
        layout.addRow(self.create_label("主题颜色:"), theme_lbl)

    def init_path_tab(self):
        self.path_tab.setStyleSheet("background-color: #2c3e50; color: white;")
        layout = QFormLayout(self.path_tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        self.project_path_edit = self.create_path_selector(layout, "项目默认路径:", os.path.abspath("projects"))
        self.resource_path_edit = self.create_path_selector(layout, "素材库路径:", os.path.abspath("resources"))
        self.output_path_edit = self.create_path_selector(layout, "输出路径:", os.path.abspath("output"))

    def create_path_selector(self, layout, label_text, default_path):
        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        edit = QLineEdit(default_path)
        edit.setStyleSheet("padding: 8px; background-color: #34495e; color: white; border: 1px solid #5d6d7e;")
        h_layout.addWidget(edit)
        
        btn = QPushButton("选择")
        btn.setFixedSize(60, 35)
        btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 4px;")
        btn.clicked.connect(lambda: self.browse_path(edit))
        h_layout.addWidget(btn)
        
        layout.addRow(self.create_label(label_text), container)
        return edit

    def browse_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "选择文件夹", line_edit.text())
        if path:
            line_edit.setText(path)

    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #bdc3c7; font-size: 14px; font-weight: bold;")
        return lbl

    def refresh_table(self):
        self.api_table.setRowCount(0)
        for config in self.api_configs:
            row = self.api_table.rowCount()
            self.api_table.insertRow(row)
            
            name = config.get("name", "")
            if config.get("is_default"):
                name = f"★ {name} (默认)"
                
            item_name = QTableWidgetItem(name)
            if config.get("is_default"):
                item_name.setForeground(Qt.GlobalColor.yellow)
                
            self.api_table.setItem(row, 0, item_name)
            self.api_table.setItem(row, 1, QTableWidgetItem(config.get("type", "")))
            self.api_table.setItem(row, 2, QTableWidgetItem(config.get("provider", "")))
            self.api_table.setItem(row, 3, QTableWidgetItem(config.get("model", "")))
            self.api_table.setItem(row, 4, QTableWidgetItem(config.get("id", "")))

    def add_config(self):
        dialog = ApiConfigDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            data["id"] = str(uuid.uuid4())
            
            # Handle default exclusivity
            if data.get("is_default"):
                for config in self.api_configs:
                    if config.get("type") == data.get("type"):
                        config["is_default"] = False
            
            self.api_configs.append(data)
            self.save_configs()
            self.refresh_table()

    def edit_config(self):
        selected_items = self.api_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择一项配置")
            return
            
        row = selected_items[0].row()
        config_id = self.api_table.item(row, 4).text()
        
        config = next((c for c in self.api_configs if c["id"] == config_id), None)
        if config:
            dialog = ApiConfigDialog(self, config)
            if dialog.exec():
                new_data = dialog.get_data()
                new_data["id"] = config_id # Keep ID
                
                # Handle default exclusivity
                if new_data.get("is_default"):
                    for c in self.api_configs:
                        if c.get("type") == new_data.get("type") and c.get("id") != config_id:
                            c["is_default"] = False
                
                # Update in list
                for i, c in enumerate(self.api_configs):
                    if c["id"] == config_id:
                        self.api_configs[i] = new_data
                        break
                
                self.save_configs()
                self.refresh_table()
                
                self.save_configs()
                self.refresh_table()

    def delete_config(self):
        selected_items = self.api_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择一项配置")
            return
            
        row = selected_items[0].row()
        config_id = self.api_table.item(row, 4).text()
        
        confirm = QMessageBox.question(self, "确认", "确定要删除这个配置吗？", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.api_configs = [c for c in self.api_configs if c["id"] != config_id]
            self.save_configs()
            self.refresh_table()

    def save_configs(self):
        self.config_manager.set("api_configs", self.api_configs)

    def save_general_settings(self):
        model = self.embed_model_edit.text().strip()
        if not model:
            model = "text-embedding-3-small"
        self.config_manager.set("embedding_model", model)
        print(f"Saved embedding model: {model}")
