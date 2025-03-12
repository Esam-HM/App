import base64
import contextlib
import io
import json
import os.path as osp

import PIL.Image

from . import PY2
from . import QT4
from . import __version__
from . import utils
from .logger import logger
from abc import ABC, abstractmethod
from qtpy.QtWidgets import QMessageBox

PIL.Image.MAX_IMAGE_PIXELS = None


@contextlib.contextmanager
def open(name, mode):
    assert mode in ["r", "w"], f"file mode error in {__file__}"
    if PY2:
        mode += "b"
        encoding = None
    else:
        encoding = "utf-8"
    yield io.open(name, mode, encoding=encoding)
    return


def load_image_file(filename):
    try:
        image_pil = PIL.Image.open(filename)
    except IOError:
        logger.error("Failed opening image file: {}".format(filename))
        return

    # apply orientation to image according to exif
    image_pil = utils.apply_exif_orientation(image_pil)

    with io.BytesIO() as f:
        ext = osp.splitext(filename)[1].lower()
        if PY2 and QT4:
            format = "PNG"
        elif ext in [".jpg", ".jpeg"]:
            format = "JPEG"
        else:
            format = "PNG"
        image_pil.save(f, format=format)
        f.seek(0)
        return f.read()


class LabelFileError(Exception):
    pass


class LegendError(Exception):
    pass


class LabelFile(ABC):
    outputFormats = {"Labelme": ".json", "YOLO": ".txt"}
    outputSuffixes = {0: ".json", 1: ".txt"}

    def __init__(self):
        self.filename = None
        self.shapes = []
        #self.imageWidth = None
        #self.imageHeight = None

    @abstractmethod
    def load(self,filename:str):
        pass

    @abstractmethod
    def save(self,shapes,imageWidth, imageHeight):
        pass

    @staticmethod
    def is_label_file(filename, suffixId):
        return osp.splitext(filename)[1].lower() == LabelFile.outputSuffixes[suffixId]
    
    @staticmethod
    def getImageSize(image_path):
        img = PIL.Image.open(image_path)
        img = utils.apply_exif_orientation(img)
        return img.size
    
    

class LabelmeLabelFile(LabelFile):
    suffix = ".json"

    def __init__(self, filename=None):
        super().__init__()
        self.imagePath = None
        self.imageData = None
        if filename is not None:
            self.load(filename)
        self.filename = filename

    def load(self, filename):
        keys = [
            "version",
            "imageData",
            "imagePath",
            "shapes",  # polygonal annotations
            "flags",  # image level flags
            "imageHeight",
            "imageWidth",
        ]
        shape_keys = [
            "label",
            "points",
            "group_id",
            "shape_type",
            "flags",
            "description",
            "mask",
        ]
        try:
            with open(filename, "r") as f:
                data = json.load(f)

            if data["imageData"] is not None:
                imageData = base64.b64decode(data["imageData"])
                if PY2 and QT4:
                    imageData = utils.img_data_to_png_data(imageData)
            else:
                # relative path from label file to relative path from cwd
                imagePath = osp.join(osp.dirname(filename), data["imagePath"])
                imageData = load_image_file(imagePath)
            flags = data.get("flags") or {}
            imagePath = data["imagePath"]
            imageHeight, imageWidth = self._check_image_height_and_width(
                base64.b64encode(imageData).decode("utf-8"),
                data.get("imageHeight"),
                data.get("imageWidth"),
            )
            shapes = [
                dict(
                    label=s["label"],
                    points=s["points"],
                    shape_type=s.get("shape_type", "polygon"),
                    flags=s.get("flags", {}),
                    description=s.get("description"),
                    group_id=s.get("group_id"),
                    mask=utils.img_b64_to_arr(s["mask"]) if s.get("mask") else None,
                    other_data={k: v for k, v in s.items() if k not in shape_keys},
                )
                for s in data["shapes"]
            ]
        except Exception as e:
            logger.error(e)
            raise LabelFileError(e)

        otherData = {}
        for key, value in data.items():
            if key not in keys:
                otherData[key] = value

        # Only replace data after everything is loaded.
        self.flags = flags
        self.shapes = shapes
        self.imagePath = imagePath
        self.imageData = imageData
        self.filename = filename
        self.otherData = otherData
        self.imageHeight = imageHeight
        self.imageWidth = imageWidth

    @staticmethod
    def _check_image_height_and_width(imageData, imageHeight, imageWidth):
        img_arr = utils.img_b64_to_arr(imageData)
        if imageHeight is not None and img_arr.shape[0] != imageHeight:
            logger.error(
                "imageHeight does not match with imageData or imagePath, "
                "so getting imageHeight from actual image."
            )
            imageHeight = img_arr.shape[0]
        if imageWidth is not None and img_arr.shape[1] != imageWidth:
            logger.error(
                "imageWidth does not match with imageData or imagePath, "
                "so getting imageWidth from actual image."
            )
            imageWidth = img_arr.shape[1]
        return imageHeight, imageWidth

    def save(self, filename, shapes,imageWidth,imageHeight):
        if self.imageData is not None:
            self.imageData = base64.b64encode(self.imageData).decode("utf-8")
            imageHeight, imageWidth = self._check_image_height_and_width(
                self.imageData, imageHeight, imageWidth
            )
        if self.otherData is None:
            self.otherData = {}
        if self.flags is None:
            self.flags = {}
        data = dict(
            version=__version__,
            flags=self.flags,
            shapes=shapes,
            imagePath=self.imagePath,
            imageData=self.imageData,
            imageHeight=imageHeight,
            imageWidth=imageWidth,
        )
        for key, value in self.otherData.items():
            assert key not in data
            data[key] = value
        try:
            with open(filename, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.filename = filename
        except Exception as e:
            raise LabelFileError(e)
    
    def getGroupIds(self):
        ids = []
        for s in self.shapes:
            group_id = s.get("group_id")
            if group_id is not None:
                ids.append(group_id)

        return ids


## Yolo Format Label file
class YoloLabelFile(LabelFile):
    tempLegend = None
    inputlegendPath:str = None
    outputLegendPath:str = None
    inputLegend:list = []            ## Classes stored in indexes according to their ids
    outputLegend:dict = {}           ## key: class name, value: id
    selfLegend:dict = {}             ## self generated legend, key: class name, value: id
    generateLegend:bool = False
    def __init__(self):
        self.shapes = []
        super().__init__()

    def load(self, filename:str, imageWidth:int, imageHeight:int):
        with open(filename, "r") as f:
            lines = f.readlines()

        for line in lines:
            data = line.strip().split()
            if data:
                pp = self.formatYoloData(data, imageWidth, imageHeight)
                if pp is None:
                    YoloLabelFile.tempLegend = None
                    raise LabelFileError("Not valid yolo label file")

                shape = {}
                shape["group_id"] = None
                shape["label"] = str(pp[0])
                if YoloLabelFile.tempLegend is not None:
                    shape["label"] = YoloLabelFile.tempLegend[pp[0]] if len(YoloLabelFile.tempLegend)> pp[0] else str(pp[0])
                else:
                    shape["label"] = YoloLabelFile.inputLegend[pp[0]] if len(YoloLabelFile.inputLegend)> pp[0] else str(pp[0])
                shape["shape_type"] = "rectangle"
                shape["points"] = []

                for x,y in pp[1]:
                    shape["points"].append([x,y])

                self.shapes.append(shape)

        YoloLabelFile.tempLegend = None
        #self.filename = filename


    def formatYoloData(self, data:list, imageWidth:int, imageHeight:int):
        if len(data)!=5:
            return

        try:
            classID = int(data[0])
            x_center = float(data[1])*imageWidth
            y_center = float(data[2])*imageHeight
            box_width = float(data[3])*imageWidth
            box_height = float(data[4])*imageHeight
        except ValueError as e:
            logger.error(e)
            return

        x1 = int(x_center-box_width/2)
        y1 = int(y_center-box_height/2)
        x2 = int(x_center+box_width/2)
        y2 = int(y_center+box_height/2)

        return classID, [(x1,y1),(x2,y2)]

    def save(self,filename, shapes, imageWidth, imageHeight):
        ## class id, x_center, y_center, box width, box height,
        lines = []
        for shape in shapes:
            if shape.get("shape_type","") == "rectangle" and len(shape["points"])==2:
                x1, y1 = shape["points"][0]
                x2, y2 = shape["points"][1]

                # Calculate center, width, and height
                x_center = (x1+x2) / 2
                y_center = (y1+y2) / 2
                width = abs(x2-x1)
                height = abs(y2-y1)

                # Normalize
                x_center = x_center/imageWidth
                y_center = y_center/imageHeight
                width = width/imageWidth
                height = height/imageHeight

                if YoloLabelFile.tempLegend is not None:
                    classId = YoloLabelFile.tempLegend.get(shape["label"])
                    if classId is None:
                        QMessageBox.critical(
                            None,
                            "Error Saving File",
                            f"<p>Could not save {filename}.</p><p>Could not found label '{shape["label"]}' in the provided legend.<br> Please check and regenerate your legend from change save settings under file menu and try again.</p>",
                        )
                        YoloLabelFile.tempLegend = None
                        raise LegendError
                elif YoloLabelFile.outputLegend:
                    classId = YoloLabelFile.outputLegend.get(shape["label"])
                    if classId is None:
                        QMessageBox.critical(
                            None,
                            "Error Saving File",
                            f"<p>Could not save {filename}.</p><p>Could not found label '{shape["label"]}' in the provided legend.<br> Please check and regenerate your legend from change save settings under file menu and try again.</p>",
                        )
                        raise LegendError
                else:
                    classId = self.getClassID(shape["label"])

                assert classId is not None, f"Could not generate class id {shape["label"]}"

                lines.append(f"{classId} {x_center} {y_center} {width} {height}\n")

        YoloLabelFile.tempLegend = None
        try:
            with open(filename, "w") as f:
                f.writelines(lines)
        except Exception as e:
            raise LabelFileError(e)
        
        if YoloLabelFile.generateLegend:
            self.generateLegendFile(osp.join(osp.dirname(filename), "labelme-ytu-classes.txt"))
        
    def getClassID(self, label:str):
        classId = YoloLabelFile.selfLegend.get(label)
        if classId is None:        ## class not found in output legend
            classId = self.getNewClassID(YoloLabelFile.selfLegend)
            YoloLabelFile.selfLegend[label] = classId
        return classId
    
    def getNewClassID(self, legend:dict):
        YoloLabelFile.generateLegend = True
        ids = list(legend.values())
        
        if len(ids)== 0:
            return 0
        
        maxId = ids[0]
        for id in ids:
            if id>maxId:
                maxId = id

        return maxId+1
    
    def generateLegendFile(self, filename):
        classes = YoloLabelFile.selfLegend.keys()
        try:
            with open(filename, "w") as f:
                for key in classes:
                    f.write(key + "\n")
                    # if i<len(keys):
                    #     f.write("\n")
        except Exception as e:
            logger.error("Could not save new legend file")
        
        YoloLabelFile.generateLegend = False
    
    @staticmethod
    def loadLegendFile(filepath:str=None):
        if not filepath:
            return
        try:
            legend = {}
            with open(filepath, "r") as f:
                lines = f.readlines()
            
            for i in range(len(lines)):
                legend[lines[i].strip()] = i

            return legend
        except Exception as e:
            QMessageBox.critical(
                None, 
                "Error Loading Legend", 
                "<p>Please ensure that you have provided a valid legend file.<br>The legend file must be in <em>.txt</em> format, with each class written on a separate line.</p>"
            )
            #logger.error(
            #    "Error reading legend file."
            #)
            return
    

## Label Studio Format Label File.
class VideoLabelFile(LabelFile):
    labelFilePath = None
    objectsCount = None
    def __init__(self):
        super().__init__()
        pass
    def load(self, filename:str=None, imageWidth:int=0, imageHeight:int=0, frameIdx:int=0, framesCount:int=0):
        try:
            with open(VideoLabelFile.labelFilePath, "r") as f:
                data = json.load(f)

            totalObjects = data[0]["annotations"][0]["result"]

            if len(totalObjects)>0:
                totalFrames = totalObjects[0]["value"]["framesCount"]
                interval = round(totalFrames/framesCount)
                frameNo = frameIdx*interval + 1 ## current frame
            else:
                self.filename = VideoLabelFile.labelFilePath
                self.flags = None
                return

            # ids = []
            # for i in range(len(totalObjects)):
            #     ids[i] = totalObjects[i]["id"]

            for i,obj in enumerate(totalObjects):
                frames = obj["value"]["sequence"]
                idx = self.getFrameIdx(frames,frameNo)
                if idx !=-1: ## if -1 >> object not found in current frame.
                    shape = {}
                    shape["group_id"] = i
                    shape["label"] = obj["value"]["labels"][0]
                    shape["shape_type"] = "rectangle"
                    shape["points"] = []

                    koords = self.getVideoObjectKoords(frames[idx], imageWidth, imageHeight)

                    for x,y in koords:
                        shape["points"].append([x,y])

                    self.shapes.append(shape)

        except Exception as e:
            logger.error(e)
            raise LabelFileError(e)

    ## Binary search tree
    def getFrameIdx(self, arr, target):
        low, high = 0, len(arr) - 1
        while low <= high:
            mid = (low + high) // 2
            if int(arr[mid]["frame"]) == target:
                return mid
            elif int(arr[mid]["frame"]) < target:
                low = mid + 1
            else:
                high = mid - 1
        return -1

    def getVideoObjectKoords(self, koords, imageWidth, imageHeight):
        x = int(imageWidth*koords["x"]/100)
        y = int(imageHeight*koords["y"]/100)
        width = int(imageWidth*koords["width"]/100)
        height = int(imageHeight*koords["height"]/100)

        return [[x,y], [x+width,y+height]]

    @staticmethod
    def countObjects():
        try:
            with open(VideoLabelFile.labelFilePath, "r") as f:
                    data = json.load(f)

            VideoLabelFile.objectsCount = len(data[0]["annotations"][0]["result"])
            return VideoLabelFile.objectsCount
        except:
            return None
        
    def save():
        pass