import os.path as osp
import cv2
#import threading
import ultralytics
#import sys
from qtpy.QtWidgets import QMessageBox


class YoloModel():
    def __init__(self):
        self.modelPath=None
        self.track=None
        self.model=None
        #self._thread = None
        #self._lock = threading.Lock()

    def resetState(self):
        self.track = False
        self.model = None
    
    def loadModel(self):
        # if self.model is not None:
        #     return True
        try:
            YOLO = getattr(ultralytics, 'YOLO')
            self.model = YOLO(self.modelPath)
        except AttributeError as e:
            QMessageBox.critical(
                None,
                "Error",
                "<p>Make sure you have ultralytics installed.<br/> Use 'pip install ultralytics' to install dependencies.</p>",
                )
            return False
        except Exception:
            QMessageBox.critical(
                None,
                "Error",
                "<p>Make sure you have selected a YOLO model file and try again.</p>",
                )
            return False
        
        return True

    def getUniqueName(self):
        parent_folder = osp.basename(osp.dirname(self.modelPath))
        file_name = osp.basename(self.modelPath)
        return f"{parent_folder}/{file_name}"

    def getFileName(self):
        return osp.basename(self.modelPath)
    
    @staticmethod
    def isFileValid(path):
        if not path.lower().endswith(".pt"):
            return False
        
        return True

    def setModelPath(self, path):
        self.modelPath=path

    def getResults(self, imagePath):
        if not self.track:
            results = self.model.predict(imagePath, verbose=False)
        else:
            img = cv2.imread(imagePath)
            results = self.model.track(img, persist=True)
        
        return results
    
    
            

        

        


        