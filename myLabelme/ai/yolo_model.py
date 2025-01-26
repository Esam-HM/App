#import importlib
import ultralytics
import os.path as osp
from qtpy.QtWidgets import QMessageBox
#from qtpy.QtCore import QThread, Signal



class YoloModel():
    def __init__(self):
        self.modelPath=None
        self.model=None

    def resetState(self):
        self.model = None
    
    def loadModel(self):
        # if self.model is not None:
        #     return True
        try:
            #ultralytics = importlib.import_module("ultralytics")
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
                "<p>Make sure you selected a YOLO model file and try again.</p>",
                )
            return False
        
        return True
    
    @staticmethod
    def isFileValid(path):
        if not path.lower().endswith(".pt"):
            return False
        
        return True

    def setModelPath(self, path):
        self.modelPath=path

    def getUniqueName(self):
        parent_folder = osp.basename(osp.dirname(self.modelPath))
        file_name = osp.basename(self.modelPath)
        return f"{parent_folder}/{file_name}"

    def runModel(self, imagePath:str):
        '''Return predicted objects list on given image'''
        canContinue = True

        try:
            pred = self.model.predict(imagePath, verbose=False)[0]
        except Exception:
            print("Error happened when running model for image: '%s'." %imagePath)
            canContinue = False
        
        try:        ## Catch attribute exceptions when processing results.
            imgShapes = []
            if canContinue and len(pred.boxes)>0:
                for box in pred.boxes:
                    shape = {}
                    shape["group_id"] = None
                    shape["label"] = pred.names[int(box.cls[0])]
                    shape["description"] = None
                    shape["shape_type"] = "rectangle"
                    shape["flags"] = {}
                    shape["mask"] = None
                    shape["points"] = []
                    shape["other_data"] = {}
                        
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    shape["points"].append([x1,y1])
                    shape["points"].append([x2,y2])

                    imgShapes.append(shape)
        except AttributeError as e:
            QMessageBox.critical(
                None,
                "Error",
                "<p>Error happened when processing model results.<br>Make sure you loaded a valid yolo model from ultralytics.</p>",
                )
            return None
        
        return imgShapes

    def runModelWithTrack(self, imagePath:str , uniqueIDs:list):
        '''Return tracked objects list on given image'''
        canContinue = True

        try:
            pred = self.model.track(imagePath, verbose= False, persist=True)[0]
        except Exception:
            print("Error happened when running model for image: '%s'." %imagePath)
            canContinue = False
        
        try:        ## Catch attribute exceptions when processing results.
            imgShapes = []
            if canContinue and len(pred.boxes)>0:
                i=0
                for box in pred.boxes:
                    shape = {}
                    try:
                        id = int(pred.boxes.id[i])
                        shape["group_id"] = id
                        uniqueIDs.append(id)
                    except Exception:
                        pass
                    
                    shape["label"] = pred.names[int(box.cls[0])]
                    shape["description"] = None
                    shape["shape_type"] = "rectangle"
                    shape["flags"] = {}
                    shape["mask"] = None
                    shape["points"] = []
                    shape["other_data"] = {}
                        
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    shape["points"].append([x1,y1])
                    shape["points"].append([x2,y2])

                    imgShapes.append(shape)
                    i+=1
        except AttributeError as e:
            QMessageBox.critical(
                None,
                "Error",
                "<p>Error happened when processing model results.<br>Make sure you loaded a valid yolo model from ultralytics.</p>",
                )
            return None
        
        return imgShapes
            

        

        


        