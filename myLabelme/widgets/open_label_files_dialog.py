from qtpy import QtWidgets
from qtpy.QtCore import Qt, QTimer
from .. import __appname__
from os import path as osp


class OpenLabelFilesDialog(QtWidgets.QDialog):
    def __init__(self,selectedOption:int=0, dirPath:str=None):
        super().__init__()
        self.selectedOption = selectedOption
        self.selectedDir = dirPath
        self.selectedLegendFile = None
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,361)
        self.initUI()
        self.adjustSize()

    def initUI(self):
        options = ["Default app format (.json)", "YOlO format (.txt)", "YOLO video format (.json)"]
        
        infoLbl = QtWidgets.QLabel(self)
        infoLbl.setText(
            '<p align="justify"> <strong>Info:</strong> Choose your label files format and directory of your images to load annotations when opening image/s.</p>'
        )
        infoLbl.setStyleSheet("color: #00f;")
        infoLbl.setWordWrap(True)


        layout1 = QtWidgets.QVBoxLayout()
        lbl1 = QtWidgets.QLabel()
        lbl1.setText("Select Label File Format:")
        self.comboBox = QtWidgets.QComboBox()
        self.comboBox.addItems(options)
        self.comboBox.setCurrentIndex(self.selectedOption)
        layout1.addWidget(lbl1)
        layout1.addWidget(self.comboBox)
        margins = layout1.contentsMargins()
        layout1.setContentsMargins(margins.left(), 10, margins.right(), 25)

        layout2 = QtWidgets.QVBoxLayout()
        lbl2 = QtWidgets.QLabel()
        lbl2.setText("Select Label Files Directory:")
        hLayout2 = QtWidgets.QHBoxLayout()
        self.dirpathEditTxt = QtWidgets.QLineEdit()
        self.dirpathEditTxt.setPlaceholderText("*Your Label Files Directory Path")
        browseDirBtn = QtWidgets.QPushButton("Browse")
        self.dirPathErrorLbl = QtWidgets.QLabel()
        #self.dirPathErrorLbl.setText("*** Must choose directory")
        self.dirPathErrorLbl.setStyleSheet("color: #f00;")
        self.dirPathErrorLbl.setContentsMargins(0,0,0,0)
        self.dirPathErrorLbl.setVisible(False)
        hLayout2.addWidget(self.dirpathEditTxt)
        hLayout2.addWidget(browseDirBtn)
        hLayout2.setContentsMargins(0,0,0,0)
        layout2.addLayout(hLayout2)
        layout2.addWidget(self.dirPathErrorLbl)
        layout2.setContentsMargins(margins.left(),margins.top(),margins.right(),25)


        layout3 = QtWidgets.QVBoxLayout()
        lbl3 = QtWidgets.QLabel()
        lbl3.setText("Select Labels Legend File (.txt):")
        hLayout3 = QtWidgets.QHBoxLayout()
        self.legendPathEditTxt = QtWidgets.QLineEdit()
        self.legendPathEditTxt.setPlaceholderText("Your Legend File Path (*Optional)")
        browseLegendBtn = QtWidgets.QPushButton("Browse")
        self.legendPathErrorLbl = QtWidgets.QLabel()
        #self.legendPathErrorLbl.setText("*** Only (.txt) file accepted.")
        self.legendPathErrorLbl.setStyleSheet("color: #f00;")
        self.legendPathErrorLbl.setContentsMargins(0,0,0,0)
        self.legendPathErrorLbl.setVisible(False)
        hLayout3.addWidget(self.legendPathEditTxt)
        hLayout3.addWidget(browseLegendBtn)
        hLayout3.setContentsMargins(0,0,0,0)
        layout3.addLayout(hLayout3)
        layout3.addWidget(self.legendPathErrorLbl)
        layout3.setContentsMargins(margins.left(),margins.top(),margins.right(),10)

        layout4 = QtWidgets.QHBoxLayout()
        applyBtn = QtWidgets.QPushButton("Apply")
        cancelBtn = QtWidgets.QPushButton("Cancel")
        layout4.addWidget(applyBtn)
        layout4.addWidget(cancelBtn)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(infoLbl)
        mainLayout.addLayout(layout1)
        mainLayout.addWidget(lbl2)
        mainLayout.addLayout(layout2)
        mainLayout.addWidget(lbl3)
        mainLayout.addLayout(layout3)
        mainLayout.addLayout(layout4)
        self.setLayout(mainLayout)

        applyBtn.clicked.connect(self.applyChanges)
        cancelBtn.clicked.connect(lambda: self.reject())
        browseDirBtn.clicked.connect(self.selectLabelFilesDir)
        browseLegendBtn.clicked.connect(self.selectLegendFile)
        self.legendPathEditTxt.editingFinished.connect(self.checkLegendFileExt)


    @property
    def getCurrentOption(self):
        return self.selectedOption
    
    @property
    def getSelectedDir(self):
        return self.selectedDir

    @property
    def getSelectedLegend(self):
        return self.selectedLegendFile

    def applyChanges(self):
        ## Empty field
        if self.dirpathEditTxt.text()=="":
            self.showError(self.dirpathEditTxt, self.dirPathErrorLbl, "*** Directory must be chosen.")
            return
        
        if not osp.exists(self.dirpathEditTxt.text()):
            self.showError(self.dirpathEditTxt, self.dirPathErrorLbl, "*** Invalid Path")
            return
        
        if self.legendPathEditTxt.text() and not osp.exists(self.legendPathEditTxt.text()):
            self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Invalid Path")
            return
        
        self.selectedOption = self.comboBox.currentIndex()
        self.selectedDir= self.dirpathEditTxt.text()
        self.selectedLegendFile = self.legendPathEditTxt.text()

        #print(self.selectedOption, self.selectedDir, self.selectedLegendFile)
        self.accept()


    def selectLabelFilesDir(self):
        defaultDirPath = self.selectedDir if self.selectedDir else "."
        targetDirPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Select Directory") % __appname__,
                defaultDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        if targetDirPath:
            self.dirpathEditTxt.setText(targetDirPath)

    def selectLegendFile(self):
        defaultDir = self.dirpathEditTxt.text() if self.dirpathEditTxt.text() else self.selectedDir
        defaultDir = defaultDir if defaultDir else "."

        selectedFilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Select Legend File") % __appname__,
            defaultDir,
            self.tr("File (*.txt)"),

        )
        if selectedFilePath:
            self.legendPathEditTxt.setText(selectedFilePath)
            self.checkLegendFileExt()
    

    def checkLegendFileExt(self):
        path = self.legendPathEditTxt.text()
        if path and osp.splitext(path)[1].lower()!=".txt":
            self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Only (.txt) file accepted.")
            

    def hideError(self, label, editTxt):
        label.setVisible(False)
        editTxt.setStyleSheet("")

    def showError(self, editTxt, label, text):
        editTxt.setStyleSheet("border: 1px solid red")
        label.setText(text)
        label.setVisible(True)
        timer = QTimer()
        timer.singleShot(5000, lambda: self.hideError(label,editTxt))
