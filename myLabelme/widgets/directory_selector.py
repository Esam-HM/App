from qtpy.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog

class DirectorySelector(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()

        self.dir_edit = QLineEdit()
        layout.addWidget(self.dir_edit)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.openDirectoryDialog)
        layout.addWidget(self.browse_button)

        self.setLayout(layout)

    def setPath(self,path):
        self.dir_edit.setText(path)

    def getPath(self):
        return self.dir_edit.text()

    def openDirectoryDialog(self):
        dir_dialog = QFileDialog()
        dir_dialog.setFileMode(QFileDialog.Directory)
        if dir_dialog.exec_():
            dir_path = dir_dialog.selectedFiles()[0]
            self.dir_edit.setText(dir_path)