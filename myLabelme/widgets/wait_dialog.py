# from qtpy.QtWidgets import QDialog, QLabel, QVBoxLayout
# from qtpy.QtCore import Qt

from qtpy.QtWidgets import QProgressDialog
from qtpy.QtCore import Qt

class WaitDialog(QProgressDialog):
    def __init__(self, label, max_value, parent=None):
        super().__init__(label, "", 0, max_value, parent)
        
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumDuration(0)
        self.setValue(0)
        self.setFixedSize(250,150)

        self.setCancelButton(None)

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)

    def closeEvent(self, event):
        event.ignore()

    def update_progress(self, value):
        self.setValue(value)