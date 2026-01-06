from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QHBoxLayout, QHeaderView, QLabel, QAbstractItemView)
from PyQt6.QtCore import Qt

class CharacterExtractionDialog(QDialog):
    def __init__(self, roles, existing_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("从剧本提取角色")
        self.resize(500, 400)
        self.roles = roles
        self.existing_names = set(existing_names)
        self.selected_roles = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("以下是从当前剧本中提取的角色："))
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["角色名", "状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.table.setRowCount(len(self.roles))
        
        for i, role in enumerate(self.roles):
            self.table.setItem(i, 0, QTableWidgetItem(role))
            
            if role in self.existing_names:
                status_item = QTableWidgetItem("已存在")
                status_item.setForeground(Qt.GlobalColor.gray)
                self.table.setItem(i, 1, status_item)
                self.table.setItem(i, 2, QTableWidgetItem("-"))
            else:
                status_item = QTableWidgetItem("新角色")
                status_item.setForeground(Qt.GlobalColor.green)
                self.table.setItem(i, 1, status_item)
                
                # Checkbox for selection (simulated with item check state or just select all by default)
                # Actually, let's just select all new ones by default
                item = QTableWidgetItem("导入")
                item.setCheckState(Qt.CheckState.Checked)
                self.table.setItem(i, 2, item)

        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("导入选中角色")
        ok_btn.clicked.connect(self.accept_selection)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def accept_selection(self):
        self.selected_roles = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 2)
            if item and item.checkState() == Qt.CheckState.Checked:
                role_name = self.table.item(i, 0).text()
                self.selected_roles.append(role_name)
        self.accept()

    def get_selected_roles(self):
        return self.selected_roles
