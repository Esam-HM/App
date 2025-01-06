from qtpy.QtWidgets import QFileDialog, QDialog, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox
from qtpy.QtCore import Qt
from .. import __appname__
#from os import path as osp

class ExtractFramesDialog(QDialog):
    def __init__(self, dirPath:str, frameRate:int):
        super().__init__()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,180)
        self.setMaximumSize(800,250)

        lbl1 = QLabel("Select frames output directory:")
        
        hLayout1 = QHBoxLayout()
        self.outputDirEditTxt = QLineEdit()
        self.outputDirEditTxt.setPlaceholderText("*Your Frames Directory Path")
        self.outputDirEditTxt.setText(dirPath)
        browseDirBtn = QPushButton("Browse")
        hLayout1.addWidget(self.outputDirEditTxt)
        hLayout1.addWidget(browseDirBtn)

        hLayout2 = QHBoxLayout()
        frameRateLbl = QLabel(self.tr("Select frame rate (FPS):"))
        self.frameRatePicker = QSpinBox()
        self.frameRatePicker.setRange(1,100)
        self.frameRatePicker.setSingleStep(1)
        self.frameRatePicker.setValue(frameRate)
        hLayout2.addWidget(frameRateLbl)
        hLayout2.addWidget(self.frameRatePicker)

        self.extractBtn = QPushButton("Extract")

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(lbl1)
        mainLayout.addLayout(hLayout1)
        mainLayout.addStretch()
        mainLayout.addLayout(hLayout2)
        mainLayout.addWidget(self.extractBtn, alignment=Qt.AlignCenter)
        self.setLayout(mainLayout)
        
        browseDirBtn.clicked.connect(self.openDirectoryDialog)
        self.extractBtn.clicked.connect(self.accept)
        self.outputDirEditTxt.textChanged.connect(self.isEmpty)

        self.adjustSize()


    def getOutputPath(self):
        return self.outputDirEditTxt.text()
    
    def getSelectedFPS(self):
        return self.frameRatePicker.value()

    def openDirectoryDialog(self):
        defaultDirPath = self.getOutputPath() if self.getOutputPath() else "."
        targetPath = str(
            QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Select Output Directory") % __appname__,
                defaultDirPath,
                QFileDialog.ShowDirsOnly
                | QFileDialog.DontResolveSymlinks,
            )
        )

        if targetPath:
            self.outputDirEditTxt.setText(targetPath)

    def isEmpty(self):
        path = self.outputDirEditTxt.text()
        self.extractBtn.setEnabled(not path=="")