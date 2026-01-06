from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QHBoxLayout, QHeaderView, QLabel, QAbstractItemView)
from PyQt6.QtCore import Qt

class SceneExtractionDialog(QDialog):
    def __init__(self, scenes, existing_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("从剧本提取场景")
        self.resize(600, 400)
        self.scenes = scenes # List of tuples (location, time) or just location strings
        self.existing_names = set(existing_names)
        self.selected_scenes = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("以下是从当前剧本中提取的场景："))
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["场景地点", "时间", "状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.table.setRowCount(len(self.scenes))
        
        for i, scene_info in enumerate(self.scenes):
            # scene_info is (location, time)
            location = scene_info[0]
            time = scene_info[1]
            
            # Construct a display name or key to check existence
            # Usually we check if a scene with this name exists
            
            self.table.setItem(i, 0, QTableWidgetItem(location))
            self.table.setItem(i, 1, QTableWidgetItem(time))
            
            if location in self.existing_names:
                status_item = QTableWidgetItem("已存在")
                status_item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(i, 2, status_item)
                self.table.setItem(i, 3, QTableWidgetItem("-"))
            else:
                status_item = QTableWidgetItem("新场景")
                status_item.setForeground(Qt.GlobalColor.green)
                self.table.setItem(i, 2, status_item)
                
                item = QTableWidgetItem("导入")
                item.setCheckState(Qt.CheckState.Checked)
                self.table.setItem(i, 3, item)

        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("导入选中场景")
        ok_btn.clicked.connect(self.accept_selection)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def accept_selection(self):
        self.selected_scenes = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 3)
            if item and item.checkState() == Qt.CheckState.Checked:
                location = self.table.item(i, 0).text()
                time = self.table.item(i, 1).text()
                self.selected_scenes.append((location, time))
        self.accept()

    def get_selected_scenes(self):
        return self.selected_scenes
