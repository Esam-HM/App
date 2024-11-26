from qtpy import QtWidgets
from qtpy.QtCore import Qt


class LabelFileTypeDialog(QtWidgets.QDialog):
    def __init__(self,selectedOption:int=0):
        super().__init__()
        self.selectedOption = selectedOption
        self.setFixedWidth(350)  
        self.initUI()
        self.adjustSize()

    def initUI(self):
        options = ["Default app .json format", "YOlO .txt format", "Video label file .json format"]

        infoLbl = QtWidgets.QLabel(self)
        infoLbl.setText(
            '<p align="justify">Note: Choose label file format of your images to load annotations when opening image/images</p>'
        )
        infoLbl.setStyleSheet("color: #f00;")
        infoLbl.setAlignment(Qt.AlignLeft)
        infoLbl.setWordWrap(True)
        textLbl = QtWidgets.QLabel(self)
        textLbl.setText("Select format:")
        
        self.comboBox = QtWidgets.QComboBox(self)
        self.comboBox.addItems(options)
        self.comboBox.setCurrentIndex(self.selectedOption)

        saveBtn = QtWidgets.QPushButton("Save",self)
        resetBtn = QtWidgets.QPushButton("Reset",self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(infoLbl)
        layout.addWidget(textLbl)
        layout.addWidget(self.comboBox)
        btnsLayout = QtWidgets.QHBoxLayout()
        btnsLayout.addWidget(saveBtn)
        btnsLayout.addWidget(resetBtn)
        layout.addLayout(btnsLayout)
        self.setLayout(layout)

        saveBtn.clicked.connect(self.saveSelectedOption)
        resetBtn.clicked.connect(self.resetFileFormat)

    @property
    def getCurrentOption(self):
        return self.selectedOption
    
    def saveSelectedOption(self):
        self.selectedOption = self.comboBox.currentIndex()
        self.accept()

    def resetFileFormat(self):
        self.comboBox.setCurrentIndex(0)
        self.selectedOption = 0