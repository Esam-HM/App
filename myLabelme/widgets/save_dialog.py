from qtpy.QtWidgets import QMessageBox, QFileDialog, QDialog, QLabel, QFrame, QComboBox, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
from qtpy.QtCore import Qt, QTimer
from .. import __appname__
from os import path as osp
from . import GenerateLegendDialog


class SaveDialog(QDialog):
    def __init__(self,
                 dialogType:int=0,
                 selectedOption:int=0,
                 dirPath:str=None,
                 legendPath:str=None,
                 labels:list=None,
                 legend:dict=None,
    ):
        super().__init__()
        self.selectedOption = selectedOption
        self.selectedDir = dirPath
        self.selectedLegend = legendPath
        self.toSave = None
        self.labels = labels
        self.outputLegend = legend if legend else {}
        self.setWindowTitle(" %s - Save Annotations" % __appname__)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,250)
        self.setMaximumSize(800,600)
        ## [title, discardBtnVisible]
        if dialogType == 0:
            titleTxt = "Save your annotations before closing?"
            discardBtnVisibilty = True
        else:
            titleTxt = "How to save your annotations?"
            discardBtnVisibilty = False

        options = ["Labelme format (.json)", "YOLO format (.txt)"]

        title = QLabel(titleTxt)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 10pt;")

        ## Save format.
        layout1 = QVBoxLayout()
        lbl1 = QLabel()
        lbl1.setText("Select a format to save your label files:")
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
        ## Left Line
        leftLine = QFrame()
        leftLine.setFrameShape(QFrame.HLine)
        leftLine.setFrameShadow(QFrame.Sunken)
        orLbl = QLabel("or")
        ## Right Line
        rightLine = QFrame()
        rightLine.setFrameShape(QFrame.HLine)
        rightLine.setFrameShadow(QFrame.Sunken)
        h_layoutLine = QHBoxLayout()
        h_layoutLine.addWidget(leftLine, 1)
        h_layoutLine.addWidget(orLbl, 0)
        h_layoutLine.addWidget(rightLine, 1)
        ## Generate Legend
        generateBtn = QPushButton("Generate Legend")
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

        btnsLayout = QHBoxLayout()
        self.saveBtn = QPushButton("Save")
        btnsLayout.addWidget(self.saveBtn)
        if discardBtnVisibilty:
            discardBtn = QPushButton("Discard")
            discardBtn.clicked.connect(self.discardBtnClicked)
            btnsLayout.addWidget(discardBtn)
        cancelBtn = QPushButton("Cancel")
        btnsLayout.addWidget(cancelBtn)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(title)
        mainLayout.addStretch()
        mainLayout.addLayout(layout1)
        mainLayout.addStretch()
        mainLayout.addWidget(lbl2)
        mainLayout.addWidget(widget2)
        mainLayout.addStretch()
        mainLayout.addWidget(self.widget3)
        mainLayout.addStretch()
        mainLayout.addLayout(btnsLayout)

        self.setLayout(mainLayout)

        self.saveBtn.clicked.connect(self.saveBtnClicked)
        cancelBtn.clicked.connect(self.reject)
        generateBtn.clicked.connect(self.generateLegend)
        browseDirBtn.clicked.connect(self.selectOutputDir)
        browseLegendBtn.clicked.connect(self.selectLegendFile)
        self.dirpathEditTxt.textChanged.connect(self.isDirPathEmpty)
        self.comboBox.currentIndexChanged.connect(self.formatSelectionChanged)
        
        self.adjustSize()
    
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

    def saveBtnClicked(self):
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
        self.toSave = True
        
        #print(self.selectedOption, self.selectedPath, self.selectedLegendFile)
        self.accept()

    def discardBtnClicked(self):
        self.toSave = False
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
                "Warning",
                "You already have generated a legend. Do you want to ignore it?",
                msg.Yes | msg.Cancel,
                msg.Yes,
            )
            if replay == msg.Cancel:
                return
            
        self.outputLegend.clear()
        self.retLbl.setVisible(False)
        self.adjustSize()
        
        defaultDir = self.legendPathEditTxt.text() if self.legendPathEditTxt.text() else self.dirpathEditTxt.text()
        defaultDir = defaultDir if defaultDir else "."
        #defaultDir = self.dirpathEditTxt.text() if self.dirpathEditTxt.text() else self.selectedDir
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
        self.retLbl.setVisible(self.outputLegend!={})
        self.formatSelectionChanged()
        self.isDirPathEmpty()