from qtpy import QtWidgets
from qtpy.QtCore import Qt
from .. import __appname__
#from os import path as osp

class ExtractFramesDialog(QtWidgets.QDialog):
    def __init__(self, dirPath:str):
        super().__init__()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,180)
        self.setMaximumSize(800,250)
        self.initUI(dirPath)
        self.adjustSize()

    def initUI(self, dirpath):
        lbl1 = QtWidgets.QLabel()
        lbl1.setText("Select output directory:")
        
        #margins = lbl1.contentsMargins()
        #lbl1.setContentsMargins(margins.left(), 0, margins.right(), 0)
        
        hLayout1 = QtWidgets.QHBoxLayout()
        self.outputDirEditTxt = QtWidgets.QLineEdit()
        self.outputDirEditTxt.setPlaceholderText("*Select Output Directory")
        self.outputDirEditTxt.setText(dirpath)
        browseDirBtn = QtWidgets.QPushButton("Browse")
        hLayout1.addWidget(self.outputDirEditTxt)
        hLayout1.addWidget(browseDirBtn)
        #hLayout1.setContentsMargins(margins.left(), 0, margins.right(), 0)
        
        # self.errorLbl = QtWidgets.QLabel()
        # self.errorLbl.setStyleSheet("color: #f00;")
        # self.errorLbl.setVisible(False)
        # self.errorLbl.setContentsMargins(margins.left(),0,margins.right(),margins.bottom())
        
        hLayout2 = QtWidgets.QHBoxLayout()
        frameRateLbl = QtWidgets.QLabel(self.tr("Select frame rate (FPS):"))
        self.frameRatePicker = QtWidgets.QSpinBox()
        self.frameRatePicker.setRange(1,100)
        self.frameRatePicker.setSingleStep(1)
        self.frameRatePicker.setValue(10)
        hLayout2.addWidget(frameRateLbl)
        hLayout2.addWidget(self.frameRatePicker)

        self.extractBtn = QtWidgets.QPushButton("Extract")

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(lbl1)
        mainLayout.addLayout(hLayout1)
        #mainLayout.addWidget(self.errorLbl)
        mainLayout.addStretch()
        mainLayout.addLayout(hLayout2)
        mainLayout.addWidget(self.extractBtn, alignment=Qt.AlignCenter)
        self.setLayout(mainLayout)
        
        browseDirBtn.clicked.connect(self.openDirectoryDialog)
        self.extractBtn.clicked.connect(self.accept)
        self.outputDirEditTxt.textChanged.connect(self.isEmpty)

    def getOutputPath(self):
        return self.outputDirEditTxt.text()
    
    def getSelectedFPS(self):
        return self.frameRatePicker.value()

    def openDirectoryDialog(self):
        defaultDirPath = self.getOutputPath() if self.getOutputPath() else "."
        targetPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Select Output Directory") % __appname__,
                defaultDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )

        if targetPath:
            self.outputDirEditTxt.setText(targetPath)

    def isEmpty(self):
        path = self.outputDirEditTxt.text()
        self.extractBtn.setEnabled(not path=="")
    

    # def applyChanges(self):
    #     path = self.outputDirEditTxt.text()

    #     if not osp.exists(path):
    #         self.outputDirEditTxt.setStyleSheet("border: 1px solid red;")
    #         self.errorLbl.setText("*** Invalid Path")
    #         self.errorLbl.setVisible(True)
    #         timer = QTimer()
    #         timer.singleShot(5000, lambda: self.hideError())
    #         return
        
    #     self.accept()
            

    # def hideError(self):
    #     self.outputDirEditTxt.setStyleSheet("")
    #     self.errorLbl.setVisible(False)