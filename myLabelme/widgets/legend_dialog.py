from os import path as osp
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QIntValidator
from qtpy.QtWidgets import (QVBoxLayout, QHBoxLayout, QLineEdit, QTableWidget, QHeaderView,
    QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QListWidget, QLabel, QDialog,
)

class GenerateLegendDialog(QDialog):
    def __init__(self, labels = None, dir:str="", prevLegend:dict=None):
        super().__init__()
        self.setWindowTitle("Labelme-ytu - Create Legend")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(300, 550)
        self.setMaximumSize(500,750)

        self.labels = labels if labels else []
        self.legend_data = {}         ## key: id , value: class name
        self.dir = dir if dir else ""
        self.savedLegendPath = None

        ## Input
        lbl1 = QLabel("Add Label Name and ID:")
        self.input_layout = QHBoxLayout()
        self.labelTxt = QLineEdit()
        self.labelTxt.setPlaceholderText("*Label Name")
        self.idTxt = QLineEdit()
        self.idTxt.setText("0")
        self.idTxt.setPlaceholderText("*ID")
        self.idTxt.setValidator(QIntValidator())
        self.addBtn = QPushButton("Add")
        self.addBtn.clicked.connect(self.addLabel)
        self.errorLbl = QLabel()
        self.errorLbl.setStyleSheet("color: #F00;")
        self.errorLbl.setVisible(False)
        self.input_layout.addWidget(self.labelTxt, 6)
        self.input_layout.addWidget(self.idTxt, 2)
        self.input_layout.addWidget(self.addBtn, 2)

        ## Labels List
        lbl2 = QLabel("Labels List:")
        self.labelList = QListWidget()
        self.labelList.setMinimumHeight(self.labelList.sizeHintForColumn(0) + 2)
        self.labelList.setFixedSize(self.width(),120)
        self.labelList.itemSelectionChanged.connect(self.addItemToTextWidget)

        ## Table
        lbl3 = QLabel("Legend Table:")
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setHorizontalHeaderLabels(["Label Name", "Label ID"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section {background-color: #0000FF; color: white; padding: 5px; border: 1px solid black;}"
        )
        ## Delete Button
        self.delete_button = QPushButton("Delete Selected Row/s")
        self.delete_button.clicked.connect(self.delete_selected_rows)

        ## Dialog buttons
        btnsLayout = QHBoxLayout()
        self.saveBtn = QPushButton("Save as txt")
        self.saveBtn.setEnabled(False)
        self.completeBtn = QPushButton("Done")
        self.completeBtn.setEnabled(False)
        cancelBtn = QPushButton("Cancel")
        btnsLayout.addWidget(self.saveBtn)
        btnsLayout.addWidget(self.completeBtn)
        btnsLayout.addWidget(cancelBtn)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(lbl1)
        mainLayout.addLayout(self.input_layout)
        mainLayout.addWidget(self.errorLbl)
        mainLayout.addStretch(2)
        mainLayout.addWidget(lbl2)
        mainLayout.addWidget(self.labelList)
        mainLayout.addStretch(2)
        mainLayout.addWidget(lbl3)
        mainLayout.addWidget(self.table)
        mainLayout.addWidget(self.delete_button)
        mainLayout.addStretch(2)
        mainLayout.addLayout(btnsLayout)

        self.setLayout(mainLayout)

        self.saveBtn.clicked.connect(self.saveFile)
        cancelBtn.clicked.connect(self.reject)
        self.completeBtn.clicked.connect(self.accept)

        if self.labels:
            self.labelList.addItems(self.labels)

        if prevLegend:
            print("(generateLegend) prevLegend: ",prevLegend)
            for key, val in prevLegend.items():
                self.createTableItems(str(val), key)
                self.legend_data[val] = key
                items = self.labelList.findItems(key, Qt.MatchExactly)
                if items:
                    row = self.labelList.row(items[0])
                    self.labelList.takeItem(row)
            print(f"legend generated: {self.legend_data}")

    def saveFile(self):
        self.savedLegendPath, _ = QFileDialog.getSaveFileName(self, "Save Legend File", self.dir, "TXT Files (*.txt)")
        if not self.savedLegendPath:
            return
        
        if osp.splitext(self.savedLegendPath)[1].lower() != ".txt":
            QMessageBox.critical(self, "Error", "Only .txt files accepted")
        
        keys = sorted(self.legend_data.keys())

        try:
            with open(self.savedLegendPath, "w") as f:
                for key in keys:
                    f.write(self.legend_data[key].title() + "\n")
                    # if i<len(keys):
                    #     f.write("\n")

        except Exception as e:
            QMessageBox.critical(self, "Error", "Could not save legend file in %s" % self.savedLegendPath)
            self.savedLegendPath = None

    def addItemToTextWidget(self):
        item = self.labelList.currentItem()
        if not item:
            return
        self.labelTxt.setText(item.text())
        self.labelTxt.setFocus()

    def addLabel(self):
        label = self.labelTxt.text().strip()
        id = self.idTxt.text()

        if not label:
            self.showError("Label Name cannot be empty!")
            return
        
        if not id:
            self.showError("ID cannot be empty!")
            return

        if id in self.legend_data:
            self.showError(f"ID: '{id}' already added!")
            return
        
        if label in self.legend_data.values():
            self.showError(f"Label: '{label}' already added!")
            return

        self.legend_data[int(id)] = label

        self.createTableItems(id,label)

        self.labelTxt.clear()
        self.idTxt.setText(str(int(self.table.rowCount())))

        if self.labelList.count()>0:
            self.labelList.takeItem(self.labelList.currentRow())
            self.labelList.setCurrentRow(0)

        self.toggleBtns()

    def createTableItems(self, id:str, label:str):
        ## Add to table
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        label_item = QTableWidgetItem(label)
        label_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Make unmodifiable
        id_item = QTableWidgetItem(id)
        id_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # Make unmodifiable
        self.table.setItem(row_position, 0, label_item)
        self.table.setItem(row_position, 1, id_item)

    def showError(self,msg:str):
        self.errorLbl.setText(msg)
        self.errorLbl.setVisible(True)
        QTimer.singleShot(4000, lambda: self.errorLbl.setVisible(False))

    def delete_selected_rows(self):
        selectedItems = self.table.selectedIndexes()
        for idx in selectedItems:
            if self.table.item(idx.row(),1):
                id = int(self.table.item(idx.row(),1).text())
                if len(self.labels)>0:
                    self.labelList.addItems([self.legend_data[id]])
                self.legend_data.pop(id)
                self.table.removeRow(idx.row())
        
        self.toggleBtns()

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            if self.labelTxt.hasFocus() or self.idTxt.hasFocus() or self.addBtn.hasFocus():
                self.addLabel()
        elif event.key() == Qt.Key_Delete:
            self.delete_selected_rows()

    def toggleBtns(self):
        flag = self.table.rowCount()>0
        self.saveBtn.setEnabled(flag)
        self.completeBtn.setEnabled(flag)