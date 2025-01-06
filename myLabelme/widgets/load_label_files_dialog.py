from qtpy.QtWidgets import QFileDialog, QDialog, QLabel, QCheckBox, QComboBox, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QDialogButtonBox, QPushButton
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QPixmap
from .. import __appname__
from os import path as osp


class LoadLabelFilesDialog(QDialog):
    def __init__(self,selectedOption:int=0, dirPath:str=None, videoLblPath:str=None):
        super().__init__()
        self.selectedOption = selectedOption
        self.selectedPath = dirPath
        self.selectedLegendFile = None
        self.setWindowTitle("%s - Load Label Files" % __appname__)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,200)
        self.initUI(videoLblPath)
        self.adjustSize()

    def initUI(self, videoLblPath):
        options = ["Default labelme app format (.json)", "YOLO format (.txt)", "Label studio video format (.json)"]
        
        infoLbl = QLabel(
            '<p align="justify"><strong>Info:</strong>Choose your label files format and directory to load annotations.</p>'
        )

        infoLbl.setStyleSheet("color: #00f;")
        infoLbl.setWordWrap(True)
        # image = QtWidgets.QLabel()
        # icons_dir = osp.join(osp.dirname(osp.abspath(__file__)), "../icons")
        # pixmap = QPixmap(osp.join(icons_dir,"legend_format.png"))
        # pixmap = pixmap.scaled(150,150,Qt.KeepAspectRatio)
        # image.setPixmap(pixmap)
        # image.setAlignment(Qt.AlignCenter)

        ## Label file format selection
        layout1 = QVBoxLayout()
        lbl1 = QLabel("Select Label File Format:")
        self.comboBox = QComboBox()
        self.comboBox.addItems(options)
        self.comboBox.setCurrentIndex(self.selectedOption)
        layout1.addWidget(lbl1)
        layout1.addWidget(self.comboBox)
        margins = layout1.contentsMargins()
        layout1.setContentsMargins(margins.left(), 10, margins.right(), 25)

        ## Label files directory selection
        self.widget2 = QWidget()
        layout2 = QVBoxLayout()
        lbl2 = QLabel("Select Label Files Directory:")
        hLayout2 = QHBoxLayout()
        self.dirpathEditTxt = QLineEdit()
        self.dirpathEditTxt.setPlaceholderText("*Your Label Files Directory Path")
        if self.selectedPath:
            self.dirpathEditTxt.setText(self.selectedPath)
        browseDirBtn = QPushButton("Browse")
        self.dirPathErrorLbl = QLabel()
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
        self.widget3 = QWidget()
        layout3 = QVBoxLayout()
        lbl3 = QLabel("Select Video Label File:")
        hLayout3 = QHBoxLayout()
        self.videoPathEditTxt = QLineEdit()
        self.videoPathEditTxt.setPlaceholderText("*Your Label File Path")
        if videoLblPath:
            self.videoPathEditTxt.setText(videoLblPath)
        browseVideoBtn = QPushButton("Browse")
        self.videoPathErrorLbl = QLabel()
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
        self.widget4 = QWidget()
        layout4 = QVBoxLayout()
        lbl4 = QLabel("Select Labels Legend File (*.txt):")
        hLayout4 = QHBoxLayout()
        self.legendPathEditTxt = QLineEdit()
        self.legendPathEditTxt.setPlaceholderText("Your Legend File Path (*Optional)")
        browseLegendBtn = QPushButton("Browse")
        self.legendPathErrorLbl = QLabel()
        self.legendPathErrorLbl.setStyleSheet("color: #f00;")
        self.legendPathErrorLbl.setContentsMargins(0,0,0,0)
        self.legendPathErrorLbl.setVisible(False)
        notLbl = QLabel("<strong>Not:</strong> Classes must be in seperated lines.")
        hLayout4.addWidget(self.legendPathEditTxt)
        hLayout4.addWidget(browseLegendBtn)
        hLayout4.setContentsMargins(0,0,0,0)
        layout4.addWidget(lbl4)
        layout4.addLayout(hLayout4)
        layout4.addWidget(self.legendPathErrorLbl)
        layout4.addWidget(notLbl)
        layout4.setContentsMargins(margins.left(),margins.top(),margins.right(),10)
        self.widget4.setLayout(layout4)

        ## Buttons
        layout5 = QHBoxLayout()
        self.loadBtn = QPushButton("Load")
        cancelBtn = QPushButton("Cancel")
        layout5.addWidget(self.loadBtn)
        layout5.addWidget(cancelBtn)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(infoLbl)
        #mainLayout.addWidget(image)
        mainLayout.addLayout(layout1)
        mainLayout.addWidget(self.widget2)
        mainLayout.addWidget(self.widget3)
        mainLayout.addWidget(self.widget4)
        mainLayout.addLayout(layout5)
        self.setLayout(mainLayout)

        self.loadBtn.clicked.connect(self.applyChanges)
        cancelBtn.clicked.connect(lambda: self.reject())
        browseDirBtn.clicked.connect(self.selectLabelFilesDir)
        browseVideoBtn.clicked.connect(self.selectVideoLblFile)
        browseLegendBtn.clicked.connect(self.selectLegendFile)
        self.videoPathEditTxt.textChanged.connect(self.isVideoPathEmpty)
        self.dirpathEditTxt.textChanged.connect(self.isDirPathEmpty)
        self.comboBox.currentIndexChanged.connect(self.typeSelectionChanged)


    def getCurrentOption(self):
        return self.selectedOption
    
    def getSelectedPath(self):
        return self.selectedPath

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
            QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Select Directory") % __appname__,
                defaultDirPath,
                QFileDialog.ShowDirsOnly
                | QFileDialog.DontResolveSymlinks,
            )
        )
        if targetPath:
            self.dirpathEditTxt.setText(targetPath)

    def selectVideoLblFile(self):
        if self.videoPathEditTxt.text() and osp.exists(self.videoPathEditTxt.text()):
            defaultDirPath = self.videoPathEditTxt.text()
        else:
            if self.selectedPath:
                defaultDirPath = self.selectedPath
            else:
                defaultDirPath="."

        targetPath,_ = QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Choose Label file") % __appname__,
            defaultDirPath,
            self.tr("File (*.json)"),
        )
        
        if targetPath:
            self.videoPathEditTxt.setText(targetPath)

    def selectLegendFile(self):
        defaultDir = self.dirpathEditTxt.text() if self.dirpathEditTxt.text() else self.selectedPath
        defaultDir = defaultDir if defaultDir else "."

        selectedFilePath, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Select Legend File") % __appname__,
            defaultDir,
            self.tr("File (*.txt)"),
        )

        if selectedFilePath:
            self.legendPathEditTxt.setText(selectedFilePath)

    def isVideoPathEmpty(self):
        path = self.videoPathEditTxt.text()
        self.loadBtn.setEnabled(not path=="")

    def isDirPathEmpty(self):
        path = self.dirpathEditTxt.text()
        self.loadBtn.setEnabled(not path=="")

    def typeSelectionChanged(self):
        flag = self.comboBox.currentIndex()==2
        self.widget3.setVisible(flag)
        self.widget2.setVisible(not flag)

        self.widget4.setVisible(self.comboBox.currentIndex()==1)
        self.adjustSize()
        if flag:
            self.isVideoPathEmpty()
        else:
            self.isDirPathEmpty()
        

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

    def showEvent(self, event):
        super().showEvent(event)
        self.typeSelectionChanged()
