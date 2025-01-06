from qtpy.QtWidgets import QFileDialog, QDialog, QLabel, QCheckBox, QComboBox, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QDialogButtonBox, QPushButton
from qtpy.QtCore import Qt, QTimer
from .. import __appname__
from os import path as osp


class SaveDialog(QDialog):
    def __init__(self,selectedOption:int=0, dirPath:str=None, legendPath:str=None):
        super().__init__()
        self.selectedOption = selectedOption if selectedOption else 0
        self.selectedDir = dirPath
        self.selectedLegend = legendPath
        self.toSave = None
        self.setWindowTitle("%s - Save Annotations" % __appname__)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,250)
        self.setMaximumSize(800,600)
        self.initUI()
        self.adjustSize()

    def initUI(self):
        options = ["Labelme format (.json)", "YOLO format (.txt)"]

        title = QLabel("Save Your Annotations Before Closing?")
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
        self.legendPathEditTxt.setPlaceholderText("*Your Legend File Path")
        if self.selectedLegend:
            self.legendPathEditTxt.setText(self.selectedLegend)
        browseLegendBtn = QPushButton("Browse")
        self.legendPathErrorLbl = QLabel()
        self.legendPathErrorLbl.setStyleSheet("color: #f00;")
        self.legendPathErrorLbl.setContentsMargins(0,0,0,0)
        self.legendPathErrorLbl.setVisible(False)
        notLbl = QLabel("<strong>Not:</strong> Classes must be in seperated lines.")
        hLayout3.addWidget(self.legendPathEditTxt)
        hLayout3.addWidget(browseLegendBtn)
        hLayout3.setContentsMargins(0,0,0,0)
        layout3.addWidget(lbl3)
        layout3.addLayout(hLayout3)
        layout3.addWidget(self.legendPathErrorLbl)
        layout3.addWidget(notLbl)
        layout3.setContentsMargins(margins.left(),margins.top(),margins.right(),10)
        self.widget3.setLayout(layout3)
        self.widget3.setVisible(False)

        btnsLayout = QHBoxLayout()
        self.saveBtn = QPushButton("Save")
        discardBtn = QPushButton("Discard")
        cancelBtn = QPushButton("Cancel")
        btnsLayout.addWidget(self.saveBtn)
        btnsLayout.addWidget(discardBtn)
        btnsLayout.addWidget(cancelBtn)
        

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(title)
        mainLayout.addStretch()
        mainLayout.addLayout(layout1)
        mainLayout.addStretch()
        mainLayout.addWidget(lbl2)
        mainLayout.addWidget(widget2)
        mainLayout.addWidget(self.widget3)
        mainLayout.addLayout(btnsLayout)
        self.setLayout(mainLayout)


        self.saveBtn.clicked.connect(self.saveBtnClicked)
        discardBtn.clicked.connect(self.discardBtnClicked)
        cancelBtn.clicked.connect(self.reject)
        browseDirBtn.clicked.connect(self.selectOutputDir)
        browseLegendBtn.clicked.connect(self.selectLegendFile)
        #self.dirpathEditTxt.textChanged.connect(self.isDirPathEmpty)
        self.dirpathEditTxt.textChanged.connect(self.isFieldsEmpty)
        self.legendPathEditTxt.textChanged.connect(self.isFieldsEmpty)
        self.comboBox.currentIndexChanged.connect(self.formatSelectionChanged)

    def getCurrentOption(self):
        return self.selectedOption
    
    def getSelectedDir(self):
        return self.selectedDir
    
    def getSelectedLegend(self):
        return self.selectedLegend


    def saveBtnClicked(self):
        path = self.dirpathEditTxt.text()
        if not osp.exists(path):
            self.showError(self.dirpathEditTxt, self.dirPathErrorLbl, "*** Invalid Path")
            return
        
        self.selectedDir = path

        if self.widget3.isVisible():
            path = self.legendPathEditTxt.text()
            if not osp.exists(path):
                self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Invalid Path")
                return
            
            if osp.splitext(path)[1].lower() !=".txt":
                self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Only (.txt) file accepted.")
                return
            
            self.selectedLegend = path
        
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
        defaultDir = self.legendPathEditTxt.text() if self.legendPathEditTxt.text() else "."

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
        self.isFieldsEmpty()


    def isFieldsEmpty(self):
        if self.widget3.isVisible():
            self.saveBtn.setEnabled(self.legendPathEditTxt.text()!="" and self.dirpathEditTxt.text!="")
        else:
            self.saveBtn.setEnabled(self.dirpathEditTxt.text!="")

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
        self.isFieldsEmpty()
        # self.isDirPathEmpty()