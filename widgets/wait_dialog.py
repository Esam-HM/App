# from qtpy.QtWidgets import QDialog, QLabel, QVBoxLayout
# from qtpy.QtCore import Qt

from qtpy.QtWidgets import QProgressDialog
from qtpy.QtCore import Qt
from .. import __appname__

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

class ProgressDialog(QProgressDialog):
    def __init__(self, message, max_value, parent=None):
        super().__init__(message, "Cancel", 0, max_value, parent)

        self.setWindowTitle("%s" % __appname__)
        self.setFixedSize(250,110)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumDuration(0)
        self.adjustSize()
        self.setValue(0)
