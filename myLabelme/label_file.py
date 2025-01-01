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


class LabelFileError(Exception):
    pass


class LabelFile(object):
    suffix = ".json"
    outputFormats = {"Labelme": ".json", "YOLO": ".txt"}
    outputSuffixes = {0: ".json", 1: ".txt"}

    def __init__(self, filename=None):
        self.shapes = []
        self.imagePath = None
        self.imageData = None
        if filename is not None:
            self.load(filename)
        self.filename = filename
        self.imageHeight = None
        self.imageWidth = None

    @staticmethod
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
                imageData = self.load_image_file(imagePath)
            flags = data.get("flags") or {}
            imagePath = data["imagePath"]
            self._check_image_height_and_width(
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

    def save(
        self,
        filename,
        shapes,
        imagePath,
        imageHeight,
        imageWidth,
        imageData=None,
        otherData=None,
        flags=None,
    ):
        if imageData is not None:
            imageData = base64.b64encode(imageData).decode("utf-8")
            imageHeight, imageWidth = self._check_image_height_and_width(
                imageData, imageHeight, imageWidth
            )
        if otherData is None:
            otherData = {}
        if flags is None:
            flags = {}
        data = dict(
            version=__version__,
            flags=flags,
            shapes=shapes,
            imagePath=imagePath,
            imageData=imageData,
            imageHeight=imageHeight,
            imageWidth=imageWidth,
        )
        for key, value in otherData.items():
            assert key not in data
            data[key] = value
        try:
            with open(filename, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.filename = filename
        except Exception as e:
            raise LabelFileError(e)

    @staticmethod
    def is_label_file(filename, suffixId):
        return osp.splitext(filename)[1].lower() == LabelFile.outputSuffixes[suffixId]
        
    def getImageShapes(self):
        imgArr = utils.img_data_to_arr(self.imageData)
        return imgArr.shape[:2]

## Yolo Format Label file
class YoloLabelFile(LabelFile):
    #LabelFile.suffix = ".txt"
    legend = []
    def __init__(self):
        super().__init__(None)

    def loadTxtFileData(self, filename):
        with open(filename, "r") as f:
            lines = f.readlines()
        pp = {}
        
        for line in lines:
            data = line.strip().split()
            if data and len(data)==5:
                try:
                    classID = int(data[0])
                    x_center = float(data[1])*self.imageWidth
                    y_center = float(data[2])*self.imageHeight
                    box_width = float(data[3])*self.imageWidth
                    box_height = float(data[4])*self.imageHeight
                except ValueError:
                    logger.error("Error reading %s file" % filename)
                    return {}
                 
                x1 = int(x_center-box_width/2)
                y1 = int(y_center-box_height/2)
                x2 = int(x_center+box_width/2)
                y2 = int(y_center+box_height/2)
                
                if pp.get(classID) is None:
                    pp[classID] = []
                pp[classID].append([(x1,y1),(x2,y2)])
        
        return pp
    

    def loadTxtFile(self, filename:str):
        data = self.loadTxtFileData(filename)
        ## convert to application format
        for key, values in data.items():
            for value in values:
                shape = {}
                shape["group_id"] = None
                shape["label"] = YoloLabelFile.legend[key] if len(YoloLabelFile.legend)> key else str(key)
                shape["description"] = None
                shape["shape_type"] = "rectangle"
                shape["flags"] = {}
                shape["mask"] = None
                shape["points"] = []
                shape["other_data"] = {}

                for x,y in value:
                    shape["points"].append([x,y])
                
                self.shapes.append(shape)

        self.filename = filename
        self.flags = None

    @staticmethod
    def loadLegendFile(filepath:str=None):
        if not filepath:
            return False
        try:
            legend = []
            with open(filepath, "r") as f:
                lines = f.readlines()
            for line in lines:
                legend.append(line.strip())

            YoloLabelFile.legend = legend
            return True
        except Exception as e:
            logger.error(
                "Error reading legend file."
            )
            return False
    
    ## Override
    def save(self,filename, shapes, imageSize):
        ## class id, group id, x_center, y_center, box width, box height,
        # shape_keys = [
        #     "label",
        #     "points",
        #     "group_id",
        #     "shape_type",
        #     "flags",
        #     "description",
        #     "mask",
        # ]
        print("saving")
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
                x_center = str(x_center/imageSize[0])
                y_center = str(y_center/imageSize[1])
                width = str(width/imageSize[0])
                height = str(height/imageSize[1])

                lines.append(f"{shape["label"]} {x_center} {y_center} {width} {height}\n")

        try:
            with open(filename, "w") as f:
                f.writelines(lines)
        except:
            raise LabelFileError    


## Label Studio Format Label File.
class VideoLabelFile(LabelFile):
    labelFilePath = None
    def __init__(self):
        super().__init__(None)

    def loadVideoLabelFile(self, frameIdx:int, framesCount:int):
        try:
            with open(VideoLabelFile.labelFilePath, "r") as f:
                data = json.load(f)
            
            totalObjects = data[0]["annotations"][0]["result"]

            if len(totalObjects)>0:
                totalFrames = totalObjects[0]["value"]["framesCount"]
                interval = round(totalFrames/framesCount)
                frameNo = frameIdx*interval + 1 ## current frame
            else:    
                print("No annotations in current frame")
                self.filename = VideoLabelFile.labelFilePath
                self.flags = None
                return
            
            # ids = []
            # for i in range(len(totalObjects)):
            #     ids[i] = totalObjects[i]["id"]
                
            imgShape = self.getImageShapes()
            for i,obj in enumerate(totalObjects):
                frames = obj["value"]["sequence"]
                idx = self.getFrameIdx(frames,frameNo)
                if idx !=-1: ## if -1 >> object not found in current frame.
                    shape = {}
                    shape["group_id"] = i
                    shape["label"] = obj["value"]["labels"][0]
                    shape["description"] = None
                    shape["shape_type"] = "rectangle"
                    shape["flags"] = {}
                    shape["mask"] = None
                    shape["points"] = []
                    shape["other_data"] = {}

                    koords = self.getVideoObjectKoords(frames[idx], imgShape)
                    
                    for x,y in koords:
                        shape["points"].append([x,y])
                    
                    self.shapes.append(shape)
            
            self.filename = VideoLabelFile.labelFilePath
            self.flags = None
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

    def getVideoObjectKoords(self, koords, imgShape):
        x = int(imgShape[1]*koords["x"]/100)
        y = int(imgShape[0]*koords["y"]/100)
        width = int(imgShape[1]*koords["width"]/100)
        height = int(imgShape[0]*koords["height"]/100)

        return [[x,y], [x+width,y+height]]