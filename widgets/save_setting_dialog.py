from qtpy.QtWidgets import QMessageBox, QFileDialog, QDialog, QLabel, QCheckBox, QComboBox, QFrame, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from qtpy.QtCore import Qt, QTimer
from . import GenerateLegendDialog
from .. import __appname__
from os import path as osp


class SaveSettingDialog(QDialog):
    def __init__(self,selectedOption:int=0,
                 dirPath:str=None,
                 legendPath:str=None,
                 saveAuto:bool=True,
                 labels:list=None,
                 legend:dict=None
        ):
        super().__init__()
        self.selectedOption = selectedOption if selectedOption else 0
        self.selectedDir = dirPath
        self.selectedLegend = legendPath
        self.saveAuto = saveAuto
        self.labels = labels
        self.outputLegend = legend if legend else {}
        self.setWindowTitle("%s - Save Settings" % __appname__)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,250)
        self.setMaximumSize(800,700)
        self.initUI()
        self.adjustSize()

    def initUI(self):
        options = ["Labelme format (.json)", "YOLO format (.txt)"]
        
        infoLbl = QLabel(
            '<p align="justify"><strong>Info:</strong> Choose your output label files format and the output directory.</p>'
        )
        infoLbl.setStyleSheet("color: #00f;")
        infoLbl.setWordWrap(True)

        ## Save format.
        layout1 = QVBoxLayout()
        lbl1 = QLabel("Select a format to save your label files:")
        self.comboBox = QComboBox()
        self.comboBox.addItems(options)
        self.comboBox.setCurrentIndex(self.selectedOption)
        layout1.addWidget(lbl1)
        layout1.addWidget(self.comboBox)
        margins = layout1.contentsMargins()
        layout1.setContentsMargins(margins.left(), 10, margins.right(), 10)

        ## output directory selection
        widget2 = QWidget()
        layout2 = QVBoxLayout()
        lbl2 = QLabel("Select Directory to save your label files in:")
        hLayout2 = QHBoxLayout()
        self.dirpathEditTxt = QLineEdit()
        self.dirpathEditTxt.setPlaceholderText("*Your Output Directory Path")
        if self.selectedDir:
            self.dirpathEditTxt.setText(self.selectedDir)
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
        layout2.setContentsMargins(margins.left(),margins.top(),margins.right(),10)
        widget2.setLayout(layout2)

        self.widget3 = QWidget()
        layout3 = QVBoxLayout()
        lbl3 = QLabel("Select Your Legend File (*.txt):")
        hLayout3 = QHBoxLayout()
        self.legendPathEditTxt = QLineEdit()
        self.legendPathEditTxt.setPlaceholderText("Your Legend File Path (*Optional)")
        if self.selectedLegend:
            self.legendPathEditTxt.setText(self.selectedLegend)
        browseLegendBtn = QPushButton("Browse")
        self.legendPathErrorLbl = QLabel()
        self.legendPathErrorLbl.setStyleSheet("color: #f00;")
        self.legendPathErrorLbl.setContentsMargins(0,0,0,0)
        self.legendPathErrorLbl.setVisible(False)
        ## Left line
        leftLine = QFrame()
        leftLine.setFrameShape(QFrame.HLine)
        leftLine.setFrameShadow(QFrame.Sunken)
        orLbl = QLabel("or")
        #orLbl.setStyleSheet("padding: 0 5px;")
        rightLine = QFrame()
        rightLine.setFrameShape(QFrame.HLine)
        rightLine.setFrameShadow(QFrame.Sunken)
        h_layoutLine = QHBoxLayout()
        h_layoutLine.addWidget(leftLine, 1)
        h_layoutLine.addWidget(orLbl, 0)
        h_layoutLine.addWidget(rightLine, 1)
        ## Generate Legend
        generateBtn = QPushButton("Generate Legend")
        #self.retLbl = QLabel("Your Legend has been generated successfully")
        self.retLbl = QLabel("You have generated a class legend")
        self.retLbl.setStyleSheet("color: #6bb24f;")
        self.retLbl.setAlignment(Qt.AlignCenter)
        self.retLbl.setVisible(False)
        notLbl = QLabel("<strong>Note:</strong> Classes must be in seperated lines.")
        hLayout3.addWidget(self.legendPathEditTxt)
        hLayout3.addWidget(browseLegendBtn)
        hLayout3.setContentsMargins(0,0,0,0)
        layout3.addWidget(lbl3)
        layout3.addLayout(hLayout3)
        layout3.addWidget(self.legendPathErrorLbl)
        layout3.addWidget(notLbl)
        layout3.addLayout(h_layoutLine)
        layout3.addWidget(generateBtn)
        layout3.addWidget(self.retLbl)
        layout3.setContentsMargins(margins.left(),margins.top(),margins.right(),10)
        self.widget3.setLayout(layout3)
        self.widget3.setVisible(False)

        ## save automatically.
        layout4 = QVBoxLayout()
        self.checkbox = QCheckBox("Save Label Files Automatically.")
        self.checkbox.setChecked(self.saveAuto)
        layout4.addWidget(self.checkbox)
        layout4.setContentsMargins(margins.left(),margins.top(),margins.right(),10)

        ## Buttons
        btnsLayout = QHBoxLayout()
        self.saveBtn = QPushButton("Set")
        cancelBtn = QPushButton("Cancel")
        btnsLayout.addWidget(self.saveBtn)
        btnsLayout.addWidget(cancelBtn)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(infoLbl)
        mainLayout.addStretch()
        mainLayout.addLayout(layout1)
        mainLayout.addStretch()
        mainLayout.addWidget(lbl2)
        mainLayout.addWidget(widget2)
        mainLayout.addStretch()
        mainLayout.addWidget(self.widget3)
        mainLayout.addStretch()
        mainLayout.addLayout(layout4)
        mainLayout.addLayout(btnsLayout)
        self.setLayout(mainLayout)

        self.saveBtn.clicked.connect(self.saveBtnPressed)
        cancelBtn.clicked.connect(lambda: self.reject())
        browseDirBtn.clicked.connect(self.selectOutputDir)
        browseLegendBtn.clicked.connect(self.selectLegendFile)
        self.dirpathEditTxt.textChanged.connect(self.isDirPathEmpty)
        generateBtn.clicked.connect(self.generateLegend)
        self.comboBox.currentIndexChanged.connect(self.formatSelectionChanged)

    def getCurrentOption(self):
        return self.selectedOption
    
    def getSelectedDir(self):
        return self.selectedDir
    
    def getSelectedLegend(self):
        return self.selectedLegend

    def isSaveAuto(self):
        return self.saveAuto
    
    def generateLegend(self):
        if self.legendPathEditTxt.text():
            msg = QMessageBox
            replay = msg.warning(
                None,
                "Attention",
                "There is a specified legend file path. Do you want to ignore it?",
                msg.Yes | msg.Cancel,
                msg.Yes,
            )
            if replay == msg.Cancel:
                return
        self.selectedLegend = None
        self.legendPathEditTxt.setText("")

        dialog = GenerateLegendDialog(self.labels, self.selectedDir, self.outputLegend)

        if dialog.exec_() == QDialog.Accepted:
            self.outputLegend = {}
            if dialog.legend_data:
                for key, val in dialog.legend_data.items():
                    self.outputLegend[val] = key
        
        if self.outputLegend:
            self.retLbl.setVisible(True)
        else:
            self.retLbl.setVisible(False)
        self.adjustSize()

    def saveBtnPressed(self):
        path = self.dirpathEditTxt.text()
        if not osp.exists(path):
            self.showError(self.dirpathEditTxt, self.dirPathErrorLbl, "*** Invalid Path")
            return
        
        self.selectedDir = path

        if self.widget3.isVisible():
            path = self.legendPathEditTxt.text()
            if path:
                if not osp.exists(path):
                    self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Invalid Path")
                    return
                
                if osp.splitext(path)[1].lower() !=".txt":
                    self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Only (.txt) file accepted.")
                    return
                
                self.selectedLegend = path
            else:
                self.selectedLegend = None
        else:
            self.selectedLegend = None

        ## Save settings.
        self.selectedOption = self.comboBox.currentIndex()
        self.saveAuto = self.checkbox.isChecked()
        
        #print(self.selectedOption, self.selectedPath, self.selectedLegendFile)
        self.accept()


    def selectOutputDir(self):
        defaultDirPath = self.selectedDir if self.selectedDir else "."
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
            self.dirpathEditTxt.setText(targetPath)

    def selectLegendFile(self):
        if self.retLbl.isVisible():
            msg = QMessageBox
            replay = msg.warning(
                None,
                "Attention",
                "You already have generated a legend. Do you want to ignore it?",
                msg.Yes | msg.Cancel,
                msg.Yes,
            )
            if replay == msg.Cancel:
                return
            
        self.outputLegend.clear()
        self.retLbl.setVisible(False) 
        self.adjustSize()

        #defaultDir = self.legendPathEditTxt.text() if self.legendPathEditTxt.text() else "."
        defaultDir = self.legendPathEditTxt.text() if self.legendPathEditTxt.text() else self.dirpathEditTxt.text()
        defaultDir = defaultDir if defaultDir else "."
        selectedFilePath, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Select Legend File") % __appname__,
            defaultDir,
            self.tr("File (*.txt)"),
        )
        
        if selectedFilePath:    
            self.legendPathEditTxt.setText(selectedFilePath)
            

    def formatSelectionChanged(self):
        self.widget3.setVisible(self.comboBox.currentIndex()==1)
        self.adjustSize()

    def isDirPathEmpty(self):
        self.saveBtn.setEnabled(not self.dirpathEditTxt.text()=="")


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
        self.retLbl.setVisible(self.outputLegend!={} and not self.selectedLegend)
        self.formatSelectionChanged()
        self.isDirPathEmpty()

