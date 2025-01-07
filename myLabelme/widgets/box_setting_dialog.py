from qtpy.QtWidgets import (
    QDialog, QLabel, QLineEdit, QDialogButtonBox, QVBoxLayout, QPushButton, QHBoxLayout
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QIntValidator
from .. import __appname__

class BoxSettingsDialog(QDialog):
    def __init__(self, width:int, height:int ):
        super().__init__()
        self.setWindowTitle("%s - Set Box Size" % __appname__)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(300,180)
        self.setMaximumSize(400,300)

        validator = QIntValidator()
        
        self.lbl1 = QLabel("Enter box width:")
        self.widthTxt = QLineEdit()
        self.widthTxt.setPlaceholderText("*Box Width")
        self.widthTxt.setValidator(validator)
        if width is not None:
            self.widthTxt.setText(str(width))
        
        self.lbl2 = QLabel("Enter box height:")
        self.heightTxt = QLineEdit()
        self.heightTxt.setPlaceholderText("*Box Height")
        self.heightTxt.setValidator(validator)
        if height is not None:
            self.heightTxt.setText(str(height))
        

        btnsLayout = QHBoxLayout()
        setBtn = QPushButton("Set")
        cancelBtn = QPushButton("Cancel")
        btnsLayout.addWidget(setBtn)
        btnsLayout.addWidget(cancelBtn)
        btnsLayout.setAlignment(Qt.AlignCenter)
        setBtn.clicked.connect(self.accept)
        cancelBtn.clicked.connect(self.reject)
        
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.lbl1)
        mainLayout.addWidget(self.widthTxt)
        mainLayout.addStretch()
        mainLayout.addWidget(self.lbl2)
        mainLayout.addWidget(self.heightTxt)
        mainLayout.addLayout(btnsLayout)
        self.setLayout(mainLayout)

        self.adjustSize()