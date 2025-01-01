from qtpy import QtWidgets
from qtpy.QtCore import Qt, QTimer
from .. import __appname__
from os import path as osp


class SaveSettingDialog(QtWidgets.QDialog):
    def __init__(self,selectedOption:int=0, dirPath:str=None, legendPath:str=None, saveAuto:bool=True):
        super().__init__()
        self.selectedOption = selectedOption if selectedOption else 0
        self.selectedDir = dirPath
        self.selectedLegend = legendPath
        self.saveAuto = saveAuto
        self.setWindowTitle("%s - Save Settings" % __appname__)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400,200)
        self.setMaximumSize(800,400)
        self.initUI()
        self.adjustSize()

    def initUI(self):
        options = ["Labelme format (.json)", "YOLO format (.txt)"]
        
        infoLbl = QtWidgets.QLabel(
            '''<p align="justify">
            <strong>Info:</strong> Choose your output label files format and the output directory where to save them.</p>'''
        )
        infoLbl.setStyleSheet("color: #00f;")
        infoLbl.setWordWrap(True)

        ## Save format.
        lbl1 = QtWidgets.QLabel()
        lbl1.setText("Select a format to save your label files:")
        self.comboBox = QtWidgets.QComboBox()
        self.comboBox.addItems(options)
        self.comboBox.setCurrentIndex(self.selectedOption)

        ## output directory selection
                ## Label files directory selection
        widget2 = QtWidgets.QWidget()
        layout2 = QtWidgets.QVBoxLayout()
        lbl2 = QtWidgets.QLabel("Select Directory to save your label files in:")
        hLayout2 = QtWidgets.QHBoxLayout()
        self.dirpathEditTxt = QtWidgets.QLineEdit()
        self.dirpathEditTxt.setPlaceholderText("*Your Output Directory Path")
        if self.selectedDir:
            self.dirpathEditTxt.setText(self.selectedDir)
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
        margins = layout2.contentsMargins()
        layout2.setContentsMargins(margins.left(),margins.top(),margins.right(),25)
        widget2.setLayout(layout2)

        # self.widget3 = QtWidgets.QWidget()
        # layout3 = QtWidgets.QVBoxLayout()
        # lbl3 = QtWidgets.QLabel("Select Your Legend File (*.txt):")
        # hLayout3 = QtWidgets.QHBoxLayout()
        # self.legendPathEditTxt = QtWidgets.QLineEdit()
        # self.legendPathEditTxt.setPlaceholderText("*Your Legend File Path")
        # if self.selectedLegend:
        #     self.legendPathEditTxt.setText(self.selectedLegend)
        # browseLegendBtn = QtWidgets.QPushButton("Browse")
        # self.legendPathErrorLbl = QtWidgets.QLabel()
        # self.legendPathErrorLbl.setStyleSheet("color: #f00;")
        # self.legendPathErrorLbl.setContentsMargins(0,0,0,0)
        # self.legendPathErrorLbl.setVisible(False)
        # hLayout3.addWidget(self.legendPathEditTxt)
        # hLayout3.addWidget(browseLegendBtn)
        # hLayout3.setContentsMargins(0,0,0,0)
        # layout3.addWidget(lbl3)
        # layout3.addLayout(hLayout3)
        # layout3.addWidget(self.legendPathErrorLbl)
        # layout3.setContentsMargins(margins.left(),margins.top(),margins.right(),25)
        # self.widget3.setLayout(layout2)
        # self.widget3.setVisible(False)

        ## save automatically.
        self.checkbox = QtWidgets.QCheckBox("Save Label Files Automatically.")
        self.checkbox.setChecked(self.saveAuto)

        ## Buttons
        btnsLayout = QtWidgets.QHBoxLayout()
        self.saveBtn = QtWidgets.QPushButton("Set")
        cancelBtn = QtWidgets.QPushButton("Cancel")
        btnsLayout.addWidget(self.saveBtn)
        btnsLayout.addWidget(cancelBtn)

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(infoLbl)
        mainLayout.addWidget(lbl1)
        mainLayout.addWidget(self.comboBox)
        mainLayout.addWidget(lbl2)
        mainLayout.addWidget(widget2)
        #mainLayout.addWidget(self.widget3)
        mainLayout.addWidget(self.checkbox)
        mainLayout.addLayout(btnsLayout)
        self.setLayout(mainLayout)

        self.saveBtn.clicked.connect(self.saveBtnPressed)
        cancelBtn.clicked.connect(lambda: self.reject())
        browseDirBtn.clicked.connect(self.selectOutputDir)
        #browseLegendBtn.clicked.connect(self.selectLegendFile)
        self.dirpathEditTxt.textChanged.connect(self.isDirPathEmpty)
        #self.legendPathEditTxt.textChanged.connect(self.isFieldsEmpty)
        #self.comboBox.currentIndexChanged.connect(self.formatSelectionChanged)

    def getCurrentOption(self):
        return self.selectedOption
    
    def getSelectedDir(self):
        return self.selectedDir
    
    # def getSelectedLegend(self):
    #     return self.selectedLegend

    def isSaveAuto(self):
        return self.saveAuto

    def saveBtnPressed(self):
        path = self.dirpathEditTxt.text()
        if not osp.exists(path):
            self.showError(self.dirpathEditTxt, self.dirPathErrorLbl, "*** Invalid Path")
            return
        
        self.selectedDir = path

        # if self.widget3.isVisible():
        #     path = self.legendPathEditTxt.text()
        #     if not osp.exists(path):
        #         self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Invalid Path")
        #         return
            
        #     if not osp.splitext(path)[1].lower() !=".txt":
        #         self.showError(self.legendPathEditTxt, self.legendPathErrorLbl, "*** Only (.txt) file accepted.")
        #         return
            
        #     self.selectedLegend = path
        
        ## Save settings.
        self.selectedOption = self.comboBox.currentIndex()
        self.saveAuto = self.checkbox.isChecked()
        
        #print(self.selectedOption, self.selectedPath, self.selectedLegendFile)
        self.accept()


    def selectOutputDir(self):
        defaultDirPath = self.selectedDir if self.selectedDir else "."
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
            self.dirpathEditTxt.setText(targetPath)

    # def selectLegendFile(self):
    #     defaultDir = self.legendPathEditTxt.text() if self.legendPathEditTxt.text() else "."

    #     selectedFilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
    #         self,
    #         self.tr("%s - Select Legend File") % __appname__,
    #         defaultDir,
    #         self.tr("File (*.txt)"),
    #     )

    #     if selectedFilePath:
    #         self.legendPathEditTxt.setText(selectedFilePath)

    # def formatSelectionChanged(self):
    #     self.widget3.setVisible(self.comboBox.currentIndex==1)
    #     self.isFieldsEmpty()


    # def isFieldsEmpty(self):
    #     if self.widget3.isVisible():
    #         self.saveBtn.setEnabled(self.legendPathEditTxt.text()!="" and self.dirpathEditTxt.text!="")
    #     else:
    #         self.saveBtn.setEnabled(self.dirpathEditTxt.text!="")

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
        self.isDirPathEmpty()
