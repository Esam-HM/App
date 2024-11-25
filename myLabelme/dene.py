# from PyQt5 import QtCore
# from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow

# def fmtShortcut(text):
#     mod, key = text.split("+", 1)
#     return "<b>%s</b>+<b>%s</b>" % (mod, key)

# app = QApplication([])

# # Create main window
# window = QMainWindow()
# window.setWindowTitle("Shortcut Example")
# window.setGeometry(700, 300, 400, 200)

# # Create label and set HTML text
# label = QLabel(fmtShortcut("Ctrl+S"), window)
# label.setGeometry(50, 50, 200, 50)  # Position label
# label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)  # Make the label interactable

# # Show the window
# ##window.show()

# ##app.exec_()

# import PIL.Image as pl

# try:
#     img = pl.open("../images/sperm.jpg")
#     try:
#         exif = img._getexif()
#         print(exif)
#     except AttributeError:
#         print("exif not found")
# except FileNotFoundError:
#     print("file not found")

# arr = [1]

# if not arr:
#     print("Empty")
# else:
#     print("Not empty")

# from PyQt5 import QtWidgets, QtGui
# from qtpy.QtCore import Qt
# import utils
# import PIL

# class ColorDialog(QtWidgets.QColorDialog):
#     def __init__(self, parent=None):
#         super(ColorDialog, self).__init__(parent)
#         self.setOption(QtWidgets.QColorDialog.ShowAlphaChannel)
#         # The Mac native dialog does not support our restore button.
#         self.setOption(QtWidgets.QColorDialog.DontUseNativeDialog)
#         # Add a restore defaults button.
#         # The default is set at invocation time, so that it
#         # works across dialogs for different elements.
#         self.default = None
#         self.bb = self.layout().itemAt(1).widget()
#         self.bb.addButton(QtWidgets.QDialogButtonBox.RestoreDefaults)
#         self.bb.clicked.connect(self.checkRestore)

#     def getColor(self, value=None, title=None, default=None):
#         self.default = default
#         if title:
#             self.setWindowTitle(title)
#         if value:
#             self.setCurrentColor(value)
#         return self.currentColor() if self.exec_() else None

#     def checkRestore(self, button):
#         if (
#             self.bb.buttonRole(button) & QtWidgets.QDialogButtonBox.ResetRole
#             and self.default
#         ):
#             self.setCurrentColor(self.default)

# def open_color_dialog():
#     dialog = ColorDialog()
#     color = dialog.getColor(title="Select Color", default=QtGui.QColor("red"))
#     if color:
#         print(f"Selected Color: {color.name()}")
#     else:
#         print("No color selected.")

# ##open_color_dialog()

# arr = []

# class MyClass():
#     def __init__(self,name,id):
#         self.name = name
#         self.id = id
#         self.job = None
    
#     def printVairables(self):
#         if self.job is not None:
#             print(self.name + " , " + self.id + " , " + self.job)
#         else:
#             print(self.name + " , " + self.id + " , No Job")

#     def setJob(self,job):
#         self.job = job

# my = MyClass("Esam", "32233")
# #my.setJob("Engineer")
# my.printVairables()   

# arr = []
# sss = ""
# if sss:
#     print("nottt empty")
# else:
#     print("Eeempty")


from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWidgets import QWidget, QLabel

# class Canvas(QWidget):
#     def __init__(self):
#         super().__init__()

#     def paintEvent(self, event):
#         # Custom drawing code goes here
#         painter = QPainter(self)
#         painter.drawLine(10, 10, 300, 10)  # Draw a line on the canvas


# class ExampleWindow(QtWidgets.QWidget):
#     def __init__(self):
#         super().__init__()

#         # Create a button
#         self.button = QtWidgets.QPushButton("Click Me", self)
#         pixmap = QPixmap("labelme/icons/icon.png")  # Load an image into a pixmap
#         label = QLabel()
#         label.setPixmap(pixmap)  # Set the pixmap on a label to display
#         # Set "What's This?" help text for the button
#         self.button.setWhatsThis("This button allows you to perform an action when clicked.")
#         canvas = Canvas()
#         canvas.setFocus()
#         # Layout setup
#         layout = QtWidgets.QVBoxLayout()
#         layout.addWidget(self.button)
#         layout.addWidget(label)
#         layout.addWidget(canvas)
#         self.setLayout(layout)

# # Main part of the application
# app = QtWidgets.QApplication([])
# window = ExampleWindow()
# window.show()
# app.exec_()

import os

# extensions = tuple([
#             ".%s" % fmt.data().decode().lower()
#             for fmt in QtGui.QImageReader.supportedImageFormats()
#         ])

# folderPath = str("./examples/classification/data_annotated")
# images = []

# if os.path.exists(folderPath):
#     print("Exist")

# for root, dirs, files in os.walk(folderPath):
#     for file in files:
#         if file.lower().endswith(extensions):
#             relativePath = os.path.normpath(os.path.join(root,file))
#             ##print(relativePath)
#             images.append(relativePath)  

# import re

# images.append("exapmles/classification/data_annotated/img1.png")
# images.append("exapmles/classification/data_annotated/img2.png")
# #print(images)

# imgs = [ f for f in images if re.search(".jpg",f)]
# #print(imgs)

# print(images)
# print(images[-1])

# print(os.path.basename(os.path.splitext(imgs[0])[1]))
# print(os.path.normpath(os.path.splitext(imgs[0])[0]))

# ff = [False, False, True, False]

# if all(ff):
#     print("accepted")
# else:
#     print("Not accepted")

import sys
import importlib

ultralytics = importlib.import_module('ultralytics')
YOLO = getattr(ultralytics, 'YOLO')
mPath = "../Models/Morphologic_Model_1.pt"
imgPath = "../OkulerImages/Boya1/images/2ac5ed57-IMG_20230821_133706.jpg"
if not os.path.exists(mPath) or not os.path.exists(imgPath):
    sys.exit(0)

model = YOLO(mPath)
results = model(imgPath)

#print(results[0].names)


