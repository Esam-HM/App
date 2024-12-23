from qtpy import QtWidgets
from qtpy.QtCore import Qt, QTimer
from .. import __appname__
from os import path as osp


class OpenLabelFilesDialog(QtWidgets.QDialog):
    def __init__(self,selectedOption:int=0, dirPath:str=None, videoLblPath:str=None):
        super().__init__()
        self.selectedOption = selectedOption
        self.selectedPath = dirPath
        self.selectedLegendFile = None
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,200)
        self.initUI(videoLblPath)
        self.adjustSize()

    def initUI(self, videoLblPath):
        options = ["Default app format (.json)", "YOlO format (.txt)", "Label studio video format (.json)"]
        
        infoLbl = QtWidgets.QLabel(self)
        infoLbl.setText(
            '<p align="justify"> <strong>Info:</strong> Choose your label files format and directory of your images to load annotations when opening image/s.</p>'
        )
        infoLbl.setStyleSheet("color: #00f;")
        infoLbl.setWordWrap(True)

        ## Label file format selection
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

        ## Label files directory selection
        self.widget2 = QtWidgets.QWidget()
        layout2 = QtWidgets.QVBoxLayout()
        lbl2 = QtWidgets.QLabel()
        lbl2.setText("Select Label Files Directory:")
        hLayout2 = QtWidgets.QHBoxLayout()
        self.dirpathEditTxt = QtWidgets.QLineEdit()
        self.dirpathEditTxt.setPlaceholderText("*Your Label Files Directory Path")
        if self.selectedPath:
            self.dirpathEditTxt.setText(self.selectedPath)
        browseDirBtn = QtWidgets.QPushButton("Browse")
        self.dirPathErrorLbl = QtWidgets.QLabel()
        self.dirPathErrorLbl.setStyleSheet("color: #f00;")
        self.dirPathErrorLbl.setContentsMargins(0,0,0,0)
        self.dirPathErrorLbl.setVisible(False)
        hLayout2.addWidget(self.dirpathEditTxt)
        hLayout2.addWidget(browseDirBtn)
        hLayout2.setContentsMargins(0,0,0,0)
        layout2.addWidget(lbl2)
        layout2.addLayout(hLayout2)
        layout2.addWidget(self.dirPathErrorLbl)
        layout2.setContentsMargins(margins.left(),margins.top(),margins.right(),25)
        self.widget2.setLayout(layout2)

        ## Video Label file selection.
        self.widget3 = QtWidgets.QWidget()
        layout3 = QtWidgets.QVBoxLayout()
        lbl3 = QtWidgets.QLabel()
        lbl3.setText("Select Video Label File:")
        hLayout3 = QtWidgets.QHBoxLayout()
        self.videoPathEditTxt = QtWidgets.QLineEdit()
        self.videoPathEditTxt.setPlaceholderText("*Your Label File Path")
        if videoLblPath:
            self.videoPathEditTxt.setText(videoLblPath)
        browseVideoBtn = QtWidgets.QPushButton("Browse")
        self.videoPathErrorLbl = QtWidgets.QLabel()
        self.videoPathErrorLbl.setStyleSheet("color: #f00;")
        self.videoPathErrorLbl.setContentsMargins(0,0,0,0)
        self.videoPathErrorLbl.setVisible(False)
        hLayout3.addWidget(self.videoPathEditTxt)
        hLayout3.addWidget(browseVideoBtn)
        hLayout3.setContentsMargins(0,0,0,0)
        layout3.addWidget(lbl3)
        layout3.addLayout(hLayout3)
        layout3.addWidget(self.videoPathErrorLbl)
        layout3.setContentsMargins(margins.left(),margins.top(),margins.right(),25)
        self.widget3.setLayout(layout3)

        ## Legend file selection.
        self.widget4 = QtWidgets.QWidget()
        layout4 = QtWidgets.QVBoxLayout()
        lbl4 = QtWidgets.QLabel()
        lbl4.setText("Select Labels Legend File (.txt):")
        hLayout4 = QtWidgets.QHBoxLayout()
        self.legendPathEditTxt = QtWidgets.QLineEdit()
        self.legendPathEditTxt.setPlaceholderText("Your Legend File Path (*Optional)")
        browseLegendBtn = QtWidgets.QPushButton("Browse")
        self.legendPathErrorLbl = QtWidgets.QLabel()
        self.legendPathErrorLbl.setStyleSheet("color: #f00;")
        self.legendPathErrorLbl.setContentsMargins(0,0,0,0)
        self.legendPathErrorLbl.setVisible(False)
        hLayout4.addWidget(self.legendPathEditTxt)
        hLayout4.addWidget(browseLegendBtn)
        hLayout4.setContentsMargins(0,0,0,0)
        layout4.addWidget(lbl4)
        layout4.addLayout(hLayout4)
        layout4.addWidget(self.legendPathErrorLbl)
        layout4.setContentsMargins(margins.left(),margins.top(),margins.right(),10)
        self.widget4.setLayout(layout4)

        ## Buttons
        layout5 = QtWidgets.QHBoxLayout()
        self.applyBtn = QtWidgets.QPushButton("Apply")
        cancelBtn = QtWidgets.QPushButton("Cancel")
        layout5.addWidget(self.applyBtn)
        layout5.addWidget(cancelBtn)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(infoLbl)
        mainLayout.addLayout(layout1)
        mainLayout.addWidget(self.widget2)
        mainLayout.addWidget(self.widget3)
        mainLayout.addWidget(self.widget4)
        mainLayout.addLayout(layout5)
        self.setLayout(mainLayout)

        self.applyBtn.clicked.connect(self.applyChanges)
        cancelBtn.clicked.connect(lambda: self.reject())
        browseDirBtn.clicked.connect(self.selectLabelFilesDir)
        browseVideoBtn.clicked.connect(self.selectVideoLblFile)
        browseLegendBtn.clicked.connect(self.selectLegendFile)
        self.videoPathEditTxt.textChanged.connect(self.isVideoPathEmpty)
        self.dirpathEditTxt.textChanged.connect(self.isDirPathEmpty)
        self.comboBox.currentIndexChanged.connect(self.typeSelectionChanged)
        self.comboBox.currentIndexChanged.emit(self.comboBox.currentIndex())

        if self.widget2.isVisible():
            self.isDirPathEmpty()
        else:
            self.isVideoPathEmpty()

    @property
    def getCurrentOption(self):
        return self.selectedOption
    
    @property
    def getSelectedPath(self):
        return self.selectedPath

    @property
    def getSelectedLegend(self):
        return self.selectedLegendFile if self.selectedLegendFile!="" else None

    def applyChanges(self):
        path = ""
        ## check for visible widget.
        if self.widget2.isVisible():
            path = self.dirpathEditTxt.text()
            ## check existance.
            if not osp.exists(path):
                self.showError(self.dirpathEditTxt, self.dirPathErrorLbl, "*** Invalid Path")
                return
        else:
            path = self.videoPathEditTxt.text()
            ## check existance.
            if not osp.exists(path):
                self.showError(self.videoPathEditTxt, self.videoPathErrorLbl, "*** Invalid Path")
                return
            ## check extension.
            if osp.splitext(path)[1].lower()!=".json":
                self.showError(self.videoPathEditTxt, self.videoPathErrorLbl, "*** Only (.json) file accepted")  
                return
            
        legend = self.legendPathEditTxt.text()
        if legend:
            ## check existance.
            if not osp.exists(legend):
                self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Invalid Path")
                return
            ## check extension.
            if osp.splitext(legend)[1].lower()!=".txt":
                self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Only (.txt) file accepted.")
                return
            
        ## Save settings.
        self.selectedOption = self.comboBox.currentIndex()
        self.selectedPath = path
        self.selectedLegendFile = legend
        
        #print(self.selectedOption, self.selectedPath, self.selectedLegendFile)
        self.accept()


    def selectLabelFilesDir(self):
        defaultDirPath = self.selectedPath if self.selectedPath else "."
        targetPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Select Directory") % __appname__,
                defaultDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )

        self.dirpathEditTxt.setText(targetPath)

    def selectVideoLblFile(self):
        defaultDirPath = self.selectedPath if self.selectedPath else "."
        targetPath,_ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Choose Label file") % __appname__,
            defaultDirPath,
            self.tr("File (*.json)"),
        )

        self.videoPathEditTxt.setText(targetPath)

    def selectLegendFile(self):
        defaultDir = self.dirpathEditTxt.text() if self.dirpathEditTxt.text() else self.selectedPath
        defaultDir = defaultDir if defaultDir else "."

        selectedFilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Select Legend File") % __appname__,
            defaultDir,
            self.tr("File (*.txt)"),
        )

        self.legendPathEditTxt.setText(selectedFilePath)

    def isVideoPathEmpty(self):
        path = self.videoPathEditTxt.text()
        self.applyBtn.setEnabled(not path=="")

    def isDirPathEmpty(self):
        path = self.dirpathEditTxt.text()
        self.applyBtn.setEnabled(not path=="")

    def typeSelectionChanged(self):
        flag = self.comboBox.currentIndex()==2
        self.widget3.setVisible(flag)
        self.widget2.setVisible(not flag)

        self.widget4.setVisible(self.comboBox.currentIndex()==1)

        self.adjustSize()

    def hideError(self, label, editTxt):
        label.setVisible(False)
        editTxt.setStyleSheet("")
        self.adjustSize()

    def showError(self, editTxt, label, text):
        editTxt.setStyleSheet("border: 1px solid red")
        label.setText(text)
        label.setVisible(True)
        self.adjustSize()
        timer = QTimer()
        timer.singleShot(5000, lambda: self.hideError(label,editTxt))
