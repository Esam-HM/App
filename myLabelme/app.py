import functools
import html
import math
import os
import os.path as osp
import re
import webbrowser
from qtpy.QtCore import QTimer
import cv2
import imgviz
import natsort
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

from . import PY2, __appname__
from .ai import MODELS, YoloModel
from .config import get_config
from .label_file import LabelFile, LabelFileError, YoloLabelFile, VideoLabelFile
from .logger import logger
from .shape import Shape
from .widgets import (BrightnessContrastDialog, Canvas,
                             LabelDialog, LabelListWidget, LabelListWidgetItem, ToolBar,
                             UniqueLabelQListWidget,
                             ZoomWidget, ExtractFramesDialog,
                             LoadLabelFilesDialog, SaveDialog, SaveSettingDialog,
                             BoxSettingsDialog,)
from . import utils


LABEL_COLORMAP = imgviz.label_colormap()

class MainWindow(QtWidgets.QMainWindow):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    def __init__(self, config, filename, output_file, output_dir, output=None):
        super(MainWindow, self).__init__()
        if output is not None:
            logger.warning("argument output is deprecated, use output_file instead")
            if output_file is None:
                output_file = output

        if config is None:
            config = get_config()

        self.setWindowTitle(__appname__)
        self._config = config
        self.dirty = False
        self.allDirty = False
        self._noSelectionSlot = False
        self._copied_shapes = None
        self.lastOpenDir = None
        self.output_file = output_file

        # Application state.
        self.setAcceptDrops(True)
        self.image = QtGui.QImage()
        self.imagePath = None
        self.recentFiles = []
        self.maxRecent = 7
        self.otherData = None
        self.zoomMode = self.FIT_WINDOW
        self.zoom_values = {}  # key=filename, value=(zoom_mode, zoom_value)
        self.brightnessContrast_values = {}
        self.scroll_values = {
            Qt.Horizontal: {},
            Qt.Vertical: {},
        }  # key=filename, value=scroll_value
        self.loadShapesFromFile=False
        self.buffer = {}  ## key=imagePath, value={"shapes": [], "flags": {}, "undo": [], "image_size": [width, height], "dirty": bool}
        self.labelFileType = 0  ## 0: labelme, 1: yolo format, 2: video label studio format.
        self.labelFilesDir = None
        self.output_dir = output_dir
        self.outputFileFormat = None     ## 0:labelme, 1: yolo format.
        self.outputFileExtension = None
        self.fileListEditMode=False

        self.lblFileLoaders = {
            0: lambda x,y,z=False: self.loadLabelmeLblFile(x,y,z),
            1: lambda x,y,z=False: self.loadYoloLblFile(x,y,z),
            2: lambda x,_,z=False: self.loadVideoLblFile(x,z),
        }

        if self._config["auto_save"]:
            logger.info(
                "auto_save from config is deprecated. Can be checked only when opening app."
            )

        if output_file is not None and self._config["auto_save"]:
            logger.warning(
                "If `auto_save` argument is True, `output_file` argument "
                "is ignored and output filename is automatically "
                "set as IMAGE_BASENAME.json."
            )

        if filename is not None and os.path.isdir(filename):
            self.importDirImages(filename, load=False)
        else:
            self.filename = filename

        ### Setting Shape parameters.
        Shape.line_color = QtGui.QColor(*self._config["shape"]["line_color"])
        Shape.fill_color = QtGui.QColor(*self._config["shape"]["fill_color"])
        Shape.select_line_color = QtGui.QColor(
            *self._config["shape"]["select_line_color"]
        )
        Shape.select_fill_color = QtGui.QColor(
            *self._config["shape"]["select_fill_color"]
        )
        Shape.vertex_fill_color = QtGui.QColor(
            *self._config["shape"]["vertex_fill_color"]
        )
        Shape.hvertex_fill_color = QtGui.QColor(
            *self._config["shape"]["hvertex_fill_color"]
        )
        # Set point size from config file
        Shape.point_size = self._config["shape"]["point_size"]

        #############  Widgets  ############

        ## PopUp Label Dialog
        self.labelDialog = LabelDialog(
            parent=self,
            labels=self._config["labels"],
            sort_labels=self._config["sort_labels"],
            show_text_field=self._config["show_label_text_field"],
            completion=self._config["label_completion"],
            fit_to_content=self._config["fit_to_content"],
            flags=self._config["label_flags"],
        )

        ## Polygon Labels List
        self.labelList = LabelListWidget()
        self.shape_dock = QtWidgets.QDockWidget(self.tr("Polygon Labels"), self)
        self.shape_dock.setObjectName("Labels")
        self.shape_dock.setWidget(self.labelList)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        self.labelList.itemChanged.connect(self.labelItemChanged)
        self.labelList.itemDropped.connect(self.labelOrderChanged)

        ### menu when right click on label list item
        labelMenu = QtWidgets.QMenu()
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(self.popLabelListMenu)

        ## self.flag_dock = self.flag_widget = None
        self.flag_dock = QtWidgets.QDockWidget(self.tr("Flags"), self)
        self.flag_dock.setObjectName("Flags")
        self.flag_widget = QtWidgets.QListWidget()
        self.flag_dock.setWidget(self.flag_widget)
        self.flag_widget.itemChanged.connect(self.setDirty)
        ### Add flags from config
        if config["flags"]:
            self.loadFlags({k: False for k in config["flags"]})

        ## unique Labels List
        self.uniqLabelList = UniqueLabelQListWidget()
        self.uniqLabelList.setToolTip(
            self.tr(
                "Select label to start annotating for it. " "Press 'Esc' to deselect."
            )
        )
        self.label_dock = QtWidgets.QDockWidget(self.tr("Label List"), self)
        self.label_dock.setObjectName("Label List")
        self.label_dock.setWidget(self.uniqLabelList)
        ### add labels from config
        if self._config["labels"]:
            for label in self._config["labels"]:
                item = self.uniqLabelList.createItemFromLabel(label)
                self.uniqLabelList.addItem(item)
                rgb = self._get_rgb_by_label(label)
                self.uniqLabelList.setItemLabel(item, label, rgb)

        ## File list
        self.fileListDeleteBtn = utils.newButton("","recycle_bin",
                                             self.removeSelectedFiles,
                                             False,"Remove selected items.")

        self.fileListEditBtn = utils.newButton("","edit_icon",
                                           self.editFileListWidget,
                                           False,"Edit list items.(Hold right-click and drag to select consecutive items.)")

        self.fileListCancelBtn = utils.newButton("","cancel",
                                             lambda: self.resetFileListWidget(),
                                             False,"Cancel edit.")

        fileListBtnsLayout = QtWidgets.QHBoxLayout()
        fileListBtnsLayout.addWidget(self.fileListDeleteBtn)
        fileListBtnsLayout.addWidget(self.fileListEditBtn)
        fileListBtnsLayout.addWidget(self.fileListCancelBtn)
        fileListBtnsLayout.setContentsMargins(0,0,0,0)
        fileListBtnsLayout.setSpacing(0)
        fileListBtnsWidget = QtWidgets.QWidget()
        fileListBtnsWidget.setLayout(fileListBtnsLayout)

        self.fileSearch = QtWidgets.QLineEdit()
        self.fileSearch.setPlaceholderText(self.tr("Search Filename"))
        self.fileListWidget = QtWidgets.QListWidget()
        fileListLayout = QtWidgets.QVBoxLayout()
        fileListLayout.setContentsMargins(0, 0, 0, 0)
        fileListLayout.setSpacing(0)
        fileListLayout.addWidget(fileListBtnsWidget)
        fileListLayout.addWidget(self.fileSearch)
        fileListLayout.addWidget(self.fileListWidget)
        self.file_dock = QtWidgets.QDockWidget(self.tr("File List"), self)
        self.file_dock.setObjectName("Files")
        fileListWidget = QtWidgets.QWidget()
        fileListWidget.setLayout(fileListLayout)
        self.file_dock.setWidget(fileListWidget)
        self.fileListWidget.itemSelectionChanged.connect(self.fileSelectionChanged)
        self.fileSearch.textChanged.connect(self.fileSearchChanged)

        ## config
        if config["file_search"]:
           self.fileSearch.setText(config["file_search"])
           self.fileSearchChanged()

        ## Scroll Widget
        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scrollArea.verticalScrollBar(),
            Qt.Horizontal: scrollArea.horizontalScrollBar(),
        }
        self.setCentralWidget(scrollArea)

        ## Canvas Widget
        self.canvas = self.labelList.canvas = Canvas(
            epsilon=self._config["epsilon"],
            double_click=self._config["canvas"]["double_click"],
            num_backups=self._config["canvas"]["num_backups"],
            crosshair=self._config["canvas"]["crosshair"],
        )
        scrollArea.setWidget(self.canvas)

        self.canvas.zoomRequest.connect(self.zoomRequest)
        self.canvas.scrollRequest.connect(self.scrollRequest)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.newShape.connect(self.newShape)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)



        ## Zoom Widget
        self.zoomWidget = ZoomWidget()
        zoom = QtWidgets.QWidgetAction(self)
        zoomBoxLayout = QtWidgets.QVBoxLayout()
        zoomLabel = QtWidgets.QLabel("Zoom")
        zoomLabel.setAlignment(Qt.AlignCenter)
        zoomBoxLayout.addWidget(zoomLabel)
        zoomBoxLayout.addWidget(self.zoomWidget)
        zoom.setDefaultWidget(QtWidgets.QWidget())
        zoom.defaultWidget().setLayout(zoomBoxLayout)
        self.zoomWidget.setEnabled(False)
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        ####   AI Widgets
        selectAiModel = QtWidgets.QWidgetAction(self)
        selectAiModel.setDefaultWidget(QtWidgets.QWidget())
        selectAiModel.defaultWidget().setLayout(QtWidgets.QVBoxLayout())

        selectAiModelLabel = QtWidgets.QLabel(self.tr("AI Segmentation Model"))
        selectAiModelLabel.setAlignment(QtCore.Qt.AlignCenter)
        selectAiModel.defaultWidget().layout().addWidget(selectAiModelLabel)

        self._selectAiModelComboBox = QtWidgets.QComboBox()
        selectAiModel.defaultWidget().layout().addWidget(self._selectAiModelComboBox)
        model_names = [model.name for model in MODELS]
        self._selectAiModelComboBox.addItems(model_names)
        if self._config["ai"]["default"] in model_names:
            model_index = model_names.index(self._config["ai"]["default"])
        else:
            logger.warning(
                "Default AI model is not found: %r",
                self._config["ai"]["default"],
            )
            model_index = 0
        self._selectAiModelComboBox.setCurrentIndex(model_index)
        self._selectAiModelComboBox.currentIndexChanged.connect(
            lambda: self.canvas.initializeAiModel(
                name=self._selectAiModelComboBox.currentText()
            )
            if self.canvas.createMode in ["ai_polygon", "ai_mask"]
            else None
        )

        self.yoloModel = YoloModel()
        yoloMainWidget = QtWidgets.QWidget()
        yoloMainWidgetLayout = QtWidgets.QVBoxLayout()
        yoloMainWidgetLayout.setContentsMargins(0,10,0,10)
        yoloMainWidgetLayout.setSpacing(0)
        #
        #_warningLabel = QtWidgets.QLabel(self.tr("Warning: These methods will overwrite the existing labels!"))
        #_warningLabel.setStyleSheet("color:red;")
        #_warningLabel.setAlignment(QtCore.Qt.AlignCenter)
        #runYolo.defaultWidget().layout().addWidget(_warningLabel)

        self.yoloModelLabel = QtWidgets.QLabel("No Model")
        self.yoloModelLabel.setAlignment(QtCore.Qt.AlignCenter)

        self._runYoloButton = utils.newButton(self.tr("Image Detection"),
                                         slot=self.runYolo,
                                         enable=False)
        self._runYoloVidButton = utils.newButton(self.tr("Video Detection"),
                                         slot=self.runYoloVid,
                                         enable=False)
        self._runYoloTrackButton = utils.newButton(self.tr("Track Detection"),
                                         slot=self.runYoloTrack,
                                         enable=False)

        yoloMainWidgetLayout.addWidget(self.yoloModelLabel)
        yoloMainWidgetLayout.addWidget(self._runYoloButton)
        yoloMainWidgetLayout.addWidget(self._runYoloVidButton)
        yoloMainWidgetLayout.addWidget(self._runYoloTrackButton)
        yoloMainWidget.setLayout(yoloMainWidgetLayout)
        yoloMainWidget.setToolTip("This method will overwrite existing labels.")
        yoloMainAction = QtWidgets.QWidgetAction(self)
        yoloMainAction.setDefaultWidget(yoloMainWidget)

        ## Tool Bar
        self.tools = self.toolbar("Tools")

        ## Menu Bar and other Menus
        self.menus = utils.struct(
            file = self.menu(self.tr("&File")),
            edit = self.menu(self.tr("&Edit")),
            view = self.menu(self.tr("&View")),
            ai = self.menu(self.tr("&AI")),
            help = self.menu(self.tr("&Help")),
            labelList = labelMenu,
            recentFiles = QtWidgets.QMenu(self.tr("Open &Recent")),
        )
        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        #############################

        ### Adding docks to right side of window
        features = QtWidgets.QDockWidget.DockWidgetFeatures()
        for dock in ["flag_dock", "label_dock", "shape_dock", "file_dock"]:
            if self._config[dock]["closable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetClosable
            if self._config[dock]["floatable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetFloatable
            if self._config[dock]["movable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetMovable
            getattr(self, dock).setFeatures(features)
            if self._config[dock]["show"] is False:
                getattr(self, dock).setVisible(False)

        self.addDockWidget(Qt.RightDockWidgetArea, self.flag_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.label_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.shape_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)

        ### Getting saved vairables from settings.
        self.settings = QtCore.QSettings("labelme", "labelme")
        self.recentFiles = self.settings.value("recentFiles", []) or []
        state = self.settings.value("window/state", QtCore.QByteArray())
        self.restoreGeometry(self.settings.value("window/geometry", QtCore.QByteArray()))
        self.restoreState(state)

        ################################################

        ########  Defining Actions  #########
        action = functools.partial(utils.newAction,self)
        shortcuts = self._config["shortcuts"]
        open_ = action(
            self.tr("&Open\n"),
            self.openFile,
            shortcuts["open"],
            "open",
            self.tr("Open image or label file"),
        )
        openNextImg = action(
            self.tr("&Next Image"),
            self.openNextImg,
            shortcuts["open_next"],
            "next",
            self.tr("Open next (hold Ctrl+Shift to copy labels)"),
            enabled=False,
        )
        openPrevImg = action(
            self.tr("&Prev Image"),
            self.openPrevImg,
            shortcuts["open_prev"],
            "prev",
            self.tr("Open prev (hold Ctrl+Shift to copy labels)"),
            enabled= False,
        )
        opendir = action(
            self.tr("Open Dir"),
            self.openDirDialog,
            shortcuts["open_dir"],
            "open",
            self.tr("Open Dir"),
        )
        deleteFile = action(
            self.tr("&Delete File"),
            self.deleteFile,
            shortcuts["delete_file"],
            "delete",
            self.tr("Delete current label file"),
            enabled=False,
        )
        changeSaveSettings = action(
            self.tr("&Change Save Settings"),
            slot = self.setSaveSettings,
            shortcut=shortcuts["save_to"],
            icon = "save_settings",
            tip = self.tr("Change output files format and where to save."),
        )
        close = action(
            "&Close",
            self.closeFile,
            shortcuts["close"],
            "close",
            "Close current file",
            enabled=False,
        )
        toggle_keep_prev_mode = action(
            self.tr("Keep Previous Annotation"),
            self.toggleKeepPrevMode,
            shortcuts["toggle_keep_prev_mode"],
            None,
            self.tr('Toggle "keep pevious annotation" mode'),
            checkable=True,
            checked= self._config["keep_prev"]
        )
        editMode = action(
            self.tr("Edit Polygons"),
            self.setEditMode,
            shortcuts["edit_polygon"],
            "edit",
            self.tr("Move and edit the selected polygons"),
            enabled=False,
        )
        createMode = action(
            self.tr("Create Polygons"),
            lambda: self.toggleDrawMode(False, createMode="polygon"),
            shortcuts["create_polygon"],
            "objects",
            self.tr("Start drawing polygons"),
            enabled=False,
        )
        createRectangleMode = action(
            self.tr("Create Rectangle"),
            lambda: self.toggleDrawMode(False, createMode="rectangle"),
            shortcuts["create_rectangle"],
            "objects",
            self.tr("Start drawing rectangles"),
            enabled=False,
        )
        createBoxMode = action(
            self.tr("Create Box"),
            lambda: self.toggleDrawMode(False, createMode="box"),
            None,
            "objects",
            self.tr("Start drawing fixed rectangles"),
            enabled=False,
        )
        createCircleMode = action(
            self.tr("Create Circle"),
            lambda: self.toggleDrawMode(False, createMode="circle"),
            shortcuts["create_circle"],
            "objects",
            self.tr("Start drawing circles"),
            enabled=False,
        )
        createLineMode = action(
            self.tr("Create Line"),
            lambda: self.toggleDrawMode(False, createMode="line"),
            shortcuts["create_line"],
            "objects",
            self.tr("Start drawing lines"),
            enabled=False,
        )
        createPointMode = action(
            self.tr("Create Point"),
            lambda: self.toggleDrawMode(False, createMode="point"),
            shortcuts["create_point"],
            "objects",
            self.tr("Start drawing points"),
            enabled=False,
        )
        createLineStripMode = action(
            self.tr("Create LineStrip"),
            lambda: self.toggleDrawMode(False, createMode="linestrip"),
            shortcuts["create_linestrip"],
            "objects",
            self.tr("Start drawing linestrip. Ctrl+LeftClick ends creation."),
            enabled=False,
        )
        createAiPolygonMode = action(
            self.tr("Create AI-Polygon"),
            lambda: self.toggleDrawMode(False, createMode="ai_polygon"),
            None,
            "objects",
            self.tr("Start drawing ai_polygon. Ctrl+LeftClick ends creation."),
            enabled=False,
        )
        createAiPolygonMode.changed.connect(
            lambda: self.canvas.initializeAiModel(
                name=self._selectAiModelComboBox.currentText()
            )
            if self.canvas.createMode == "ai_polygon"
            else None
        )
        createAiMaskMode = action(
            self.tr("Create AI-Mask"),
            lambda: self.toggleDrawMode(False, createMode="ai_mask"),
            None,
            "objects",
            self.tr("Start drawing ai_mask. Ctrl+LeftClick ends creation."),
            enabled=False,
        )
        createAiMaskMode.changed.connect(
            lambda: self.canvas.initializeAiModel(
                name=self._selectAiModelComboBox.currentText()
            )
            if self.canvas.createMode == "ai_mask"
            else None
        )
        hideAll = action(
            self.tr("&Hide\nPolygons"),
            functools.partial(self.togglePolygons, False),
            shortcuts["hide_all_polygons"],
            icon="eye",
            tip=self.tr("Hide all polygons"),
            enabled=False,
        )
        showAll = action(
            self.tr("&Show\nPolygons"),
            functools.partial(self.togglePolygons, True),
            shortcuts["show_all_polygons"],
            icon="eye",
            tip=self.tr("Show all polygons"),
            enabled=False,
        )
        toggleAll = action(
            self.tr("&Toggle\nPolygons"),
            functools.partial(self.togglePolygons, None),
            shortcuts["toggle_all_polygons"],
            icon="eye",
            tip=self.tr("Toggle all polygons"),
            enabled=False,
        )
        save = action(
            self.tr("&Save\n"),
            self.saveFile,
            shortcuts["save"],
            "save",
            self.tr("Save labels to file"),
            enabled=False,
        )
        saveAll = action(
            self.tr("&Save All"),
            self.saveAllOutputFiles,
            shortcuts["save_all"],
            "save_all",
            self.tr("Save all label files"),
            enabled= False,
        )
        saveAs = action(
            self.tr("&Save As"),
            self.saveFileAs,
            shortcuts["save_as"],
            "save-as",
            self.tr("Save labels to a different file"),
            enabled=False,
        )
        saveAuto = action(
            text=self.tr("Save &Automatically"),
            slot=self.setSaveAuto,
            tip=self.tr("Save automatically"),
            checkable=True,
            enabled=True,
        )
        saveWithImageData = action(
            text="Save With Image Data",
            slot=self.enableSaveImageWithData,
            tip="Save image data in label file",
            checkable=True,
            checked=self._config["store_data"],
        )
        edit = action(
            self.tr("&Edit Label"),
            self.editLabel,
            shortcuts["edit_label"],
            "edit",
            self.tr("Modify the label of the selected polygon"),
            enabled=False,
        )
        delete = action(
            self.tr("Delete Polygons"),
            self.deleteSelectedShape,
            shortcuts["delete_polygon"],
            "cancel",
            self.tr("Delete the selected polygons"),
            enabled=False,
        )
        deleteAll = action(
            self.tr("Delete All Polygons"),
            self.deleteAllShapes,
            shortcuts["delete_all"],
            "delete",
            self.tr("Delete all polygons in image (Shift+Delete)"),
            enabled=False,
        )
        duplicate = action(
            self.tr("Duplicate Polygons"),
            self.duplicateSelectedShape,
            shortcuts["duplicate_polygon"],
            "copy",
            self.tr("Create a duplicate of the selected polygons"),
            enabled=False,
        )
        copy = action(
            self.tr("Copy Polygons"),
            self.copySelectedShape,
            shortcuts["copy_polygon"],
            "copy_clipboard",
            self.tr("Copy selected polygons to clipboard"),
            enabled=False,
        )
        paste = action(
            self.tr("Paste Polygons"),
            self.pasteSelectedShape,
            shortcuts["paste_polygon"],
            "paste",
            self.tr("Paste copied polygons"),
            enabled=False,
        )
        undoLastPoint = action(
            self.tr("Undo last point"),
            self.canvas.undoLastPoint,
            shortcuts["undo_last_point"],
            "undo",
            self.tr("Undo last drawn point"),
            enabled=False,
        )
        removePoint = action(
            text="Remove Selected Point",
            slot=self.removeSelectedPoint,
            shortcut=shortcuts["remove_selected_point"],
            icon="edit",
            tip="Remove selected point from polygon",
            enabled=False,
        )
        undo = action(
            self.tr("Undo\n"),
            self.undoShapeEdit,
            shortcuts["undo"],
            "undo",
            self.tr("Undo last add and edit of shape"),
            enabled=False,
        )
        fill_drawing = action(
            self.tr("Fill Drawing Polygon"),
            self.canvas.setFillDrawing,
            None,
            "color",
            self.tr("Fill polygon while drawing"),
            checkable=True,
            enabled=True,
        )
        if self._config["canvas"]["fill_drawing"]:
            fill_drawing.trigger()

        quit = action(
            self.tr("&Quit"), self.close,
            shortcuts["quit"], "quit",
            self.tr("Quit application"),
        )
        help = action(
            self.tr("&Tutorial"),
            self.tutorial,
            icon="help",
            tip=self.tr("Show tutorial page"),
        )
        ## Zoom actions
        zoomIn = action(
            self.tr("Zoom &In"),
            functools.partial(self.addZoom, 1.1),
            shortcuts["zoom_in"],
            "zoom-in",
            self.tr("Increase zoom level"),
            enabled= False,
        )
        zoomOut = action(
            self.tr("&Zoom Out"),
            functools.partial(self.addZoom, 0.9),
            shortcuts["zoom_out"],
            "zoom-out",
            self.tr("Decrease zoom level"),
            enabled= False,
        )
        zoomOrg = action(
            self.tr("&Original size"),
            functools.partial(self.setZoom, 100),
            shortcuts["zoom_to_original"],
            "zoom",
            self.tr("Zoom to original size"),
            enabled=False,
        )
        fitWindow = action(
            self.tr("&Fit Window"),
            self.setFitWindow,
            shortcuts["fit_window"],
            "fit-window",
            self.tr("Zoom follows window size"),
            checkable=True,
            enabled=False,
        )
        fitWindow.setChecked(Qt.Checked)
        fitWidth = action(
            self.tr("Fit &Width"),
            self.setFitWidth,
            shortcuts["fit_width"],
            "fit-width",
            self.tr("Zoom follows window width"),
            checkable=True,
            enabled=False,
        )
        keepPrevScale = action(
            self.tr("&Keep Previous Scale"),
            self.enableKeepPrevScale,
            tip=self.tr("Keep previous zoom scale"),
            checkable=True,
            checked=self._config["keep_prev_scale"],
            enabled=True,
        )
        brightnessContrast = action(
            "&Brightness Contrast",
            self.brightnessContrast,
            None,
            "color",
            "Adjust brightness and contrast",
            enabled=False,
        )
        setBoxSize = action(
            self.tr("&Set Box Size"),
            self.setBoxSize,
            None,
            "edit_icon",
            self.tr("Set or change box width and height."),
        )
        ## XXX
        fillGapVideo = action(
            self.tr("&Fill Video Gaps"),
            None,
            tip=self.tr("Fill gaps in video between two non-empty frames(only for labels with same ID numbers)"),
            enabled=False,
        )
        extractFrames = action(
            self.tr("Extract Frames"),
            self.openExtractFramesDialog,
            None,
            "extract_frames",
            self.tr("Extract frames of a video to a directory"),
        )
        loadLblFiles = action(
            self.tr("Load Label Files"),
            self.loadLabelFiles,
            tip=self.tr("Select specific label file type to open it when load images"),
        )
        loadAnnotationFile = action(
            self.tr("Load Annotations From File"),
            self.openAnnotationFile,
            None,
            "objects",
            self.tr("Select label file to load annotations to current image"),
            enabled=False,
        )
        selectAiModelFile = action(
            self.tr("&Select Object Detection Model"),
            self.selectObjModel,
            icon="ai",
            tip=self.tr("Select a model for object detection"),
        )

        # Store actions for further handling.
        self.actions = utils.struct(
            open=open_,
            openNextImg=openNextImg,
            openPrevImg=openPrevImg,
            close=close,
            changeSaveSettings = changeSaveSettings,
            save=save,
            saveAll = saveAll,
            saveAs=saveAs,
            saveAuto=saveAuto,
            saveWithImageData=saveWithImageData,
            deleteFile=deleteFile,
            createMode=createMode,
            editMode=editMode,
            createRectangleMode=createRectangleMode,
            createBoxMode = createBoxMode,
            createCircleMode=createCircleMode,
            createLineMode=createLineMode,
            createPointMode=createPointMode,
            createLineStripMode=createLineStripMode,
            createAiPolygonMode=createAiPolygonMode,
            createAiMaskMode=createAiMaskMode,
            toggleKeepPrevMode=toggle_keep_prev_mode,
            edit=edit,
            delete=delete,
            deleteAll=deleteAll,
            duplicate=duplicate,
            copy=copy,
            paste=paste,
            undoLastPoint=undoLastPoint,
            undo=undo,
            removePoint=removePoint,
            zoom=zoom,
            zoomIn=zoomIn,
            zoomOut=zoomOut,
            zoomOrg=zoomOrg,
            keepPrevScale=keepPrevScale,
            fitWindow=fitWindow,
            fitWidth=fitWidth,
            brightnessContrast=brightnessContrast,
            zoomActions=(),
            fileMenuActions=(open_, opendir, save, saveAll, saveAs, close, quit),
            tool=(),
            # XXX: need to add some actions here to activate the shortcut
            editMenu=(
                edit,
                duplicate,
                copy,
                paste,
                delete,
                deleteAll,
                None,
                undo,
                undoLastPoint,
                None,
                removePoint,
                None,
                setBoxSize,
                toggle_keep_prev_mode,
            ),
            # menu shown at right click
            menu=(
                createMode,
                createRectangleMode,
                createBoxMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                createAiPolygonMode,
                createAiMaskMode,
                loadAnnotationFile,
                editMode,
                edit,
                duplicate,
                copy,
                paste,
                delete,
                undo,
                undoLastPoint,
                removePoint,
            ),
            onLoadActive=(
                close,
                createMode,
                createRectangleMode,
                createBoxMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                createAiPolygonMode,
                createAiMaskMode,
                editMode,
                brightnessContrast,
                loadAnnotationFile,
            ),
            onShapesPresent=(saveAs, deleteAll, hideAll, showAll, toggleAll),
            extractFrames=extractFrames,
            loadLblFiles=loadLblFiles,
            loadAnnotationFile=loadAnnotationFile,
            selectAiModelFile=selectAiModelFile,
        )


        ## Grouping toolBar's actions.
        self.actions.tool = (
            open_,
            opendir,
            openPrevImg,
            openNextImg,
            save,
            saveAll,
            deleteFile,
            None,
            createRectangleMode,
            createBoxMode,
            editMode,
            delete,
            deleteAll,
            undo,
            None,
            brightnessContrast,
            None,
            fitWindow,
            zoom,
            None,
            yoloMainAction,
        )
        # Group zoom controls into a list for easier toggling.
        self.actions.zoomActions = (
            self.zoomWidget,
            zoomIn,
            zoomOut,
            zoomOrg,
            fitWindow,
            fitWidth,
        )
        ## other settings for zoom widget.
        self.zoomWidget.setWhatsThis(
            str(
                self.tr(
                    "Zoom in or out of the image. Also accessible with "
                    "{} and {} from the canvas."
                )
            ).format(
                utils.fmtShortcut(
                    "{},{}".format(shortcuts["zoom_in"], shortcuts["zoom_out"])
                ),
                utils.fmtShortcut(self.tr("Ctrl+Wheel")),
            )
        )
        ### scalers-methods Dict.
        self.scalers = {
            self.FIT_WINDOW : self.scaleFitWindow,
            self.FIT_WIDTH : self.scaleFitWidth,
            self.MANUAL_ZOOM : lambda: 1,
        }

        #######  Adding Actions  #######
        ## label menu popUp
        utils.addActions(labelMenu, (edit, delete))
        utils.addActions(self.menus.file,(
            open_,
            openNextImg,
            openPrevImg,
            opendir,
            self.menus.recentFiles,
            loadLblFiles,
            extractFrames,
            save,
            saveAll,
            saveAs,
            saveAuto,
            changeSaveSettings,
            saveWithImageData,
            close,
            deleteFile,
            None,
            quit,
        ))
        utils.addActions(self.menus.view,(
            self.flag_dock.toggleViewAction(),
            self.label_dock.toggleViewAction(),
            self.shape_dock.toggleViewAction(),
            self.file_dock.toggleViewAction(),
            None,
            fill_drawing,
            None,
            hideAll,
            showAll,
            toggleAll,
            None,
            zoomIn,
            zoomOut,
            zoomOrg,
            keepPrevScale,
            None,
            fitWindow,
            fitWidth,
            None,
            brightnessContrast,
        ))

        utils.addActions(self.menus.ai, [selectAiModelFile, selectAiModel])
        utils.addActions(self.menus.help, [help])
        utils.addActions(self.tools,self.actions.tool)
        # Custom context menu for the canvas widget:
        utils.addActions(self.canvas.menus[0], self.actions.menu)
        utils.addActions(
            self.canvas.menus[1],
            (
                action("&Copy here", self.copyShape),
                action("&Move here", self.moveShape),
            ),
        )
        self.canvas.vertexSelected.connect(self.actions.removePoint.setEnabled)

        # Since loading the file may take some time,
        # make sure it runs in the background.
        #self.filename = self.settings.value("filename",None)
        if self.filename:
            self.queueEvent(functools.partial(self.loadFile, self.filename))

        self.populateModeActions()

        ## Status Bar
        self.statusBar().showMessage(str(self.tr("%s started.")) % __appname__)
        self.statusBar().show()

    ## Adding actions
    def populateModeActions(self):
        tool, menu = self.actions.tool, self.actions.menu
        self.tools.clear()
        utils.addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        utils.addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (
            self.actions.createMode,
            self.actions.createRectangleMode,
            self.actions.createCircleMode,
            self.actions.createLineMode,
            self.actions.createPointMode,
            self.actions.createLineStripMode,
            self.actions.createAiPolygonMode,
            self.actions.createAiMaskMode,
            self.actions.editMode,
        )
        utils.addActions(self.menus.edit, actions + self.actions.editMenu)


    ##########  Open image/dir Functions  ######

    ## Open Dir Dialog
    def openDirDialog(self, _value=False, dirpath=None):
        ## ask if self.dirty or self.allDirty
        ## if saved reset everything.
        if not self.mayContinue():
            return

        defaultOpenDirPath = dirpath if dirpath else "."
        if self.lastOpenDir and osp.exists(self.lastOpenDir):
            defaultOpenDirPath = self.lastOpenDir
        else:
            defaultOpenDirPath = osp.dirname(self.filename) if self.filename else "."

        targetDirPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Open Directory") % __appname__,
                defaultOpenDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )

        self.importDirImages(targetDirPath)

    ## Load images to file list.
    ## Also used to search specific files
    def importDirImages(self, dirpath, load=True):
        if not self.mayContinue() or not dirpath:
            return

        self.lastOpenDir = dirpath
        self.filename = None
        self.fileListWidget.clear()
        self.resetApplicationState()
        

        filenames = self.scanAllImages(dirpath)
        if not filenames:   ## FIXED
            return
        
        self.resetFileListWidget(load=False)
        self.addFilesToFileList(filenames)

        self.openNextImg(load=load)

    def addFilesToFileList(self, filenames):
        '''
        ADD Files To FileListWidget.
        Mark file item if already has output label file.
        '''
        for filename in filenames:
            item = QtWidgets.QListWidgetItem(filename)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Unchecked)
            if self.output_dir and self.outputFileFormat:
                labelfile = osp.splitext(filename)[0] + LabelFile.outputSuffixes.get(self.outputFileFormat)
                labelfile = osp.join(self.output_dir, osp.basename(labelfile))
                if osp.exists(labelfile) and LabelFile.is_label_file(labelfile, self.outputFileFormat):
                    item.setCheckState(Qt.Checked)
                
            self.fileListWidget.addItem(item)


    def scanAllImages(self, folderPath):
        '''
        Get All images from given dir path.
        '''
        extensions = tuple([
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ])

        images = []
        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(extensions):
                    relativePath = osp.normpath(osp.join(root,file))
                    images.append(relativePath)
                    self.buffer[relativePath] = {}

        images = natsort.os_sorted(images)
        return images

    ## open dropped images.
    def importDroppedImageFiles(self, imageFiles):
        '''
        Open dropped images. add them to file list.
        Does not clear file list widget.
        '''
        extensions = tuple([
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ])

        self.filename = None
        self.resetFileListWidget(load=False)

        for file in imageFiles:
            if file not in self.buffer and file.lower().endswith(extensions):
                item = QtWidgets.QListWidgetItem(file)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setCheckState(Qt.Unchecked)
                if self.output_dir and self.outputFileFormat:
                    label_file = osp.splitext(file)[0] + LabelFile.outputSuffixes[self.outputFileFormat]
                    label_file = osp.join(self.output_dir, osp.basename(label_file))
                    if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(label_file, self.outputFileFormat):
                        item.setCheckState(Qt.Checked)
                    
                self.fileListWidget.addItem(item)
                self.buffer[file] = {}

            if len(imageFiles) > 1:
                self.actions.openNextImg.setEnabled(True)
                self.actions.openPrevImg.setEnabled(True)

        self.openNextImg()

    ## Create open file dialog to open single file.
    def openFile(self, _value=False):
        ## ask if self.dirty or allDirty.
        # if saved, continue.
        if not self.mayContinue():
            return

        path = osp.dirname(str(self.filename)) if self.filename else "."

        formats = [
            "*.{}".format(fmt.data().decode())
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        
        filters = self.tr("Image files (%s)") % " ".join(
            formats
        )
        selectedFilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Choose Image") % __appname__,
            path,
            filters,
        )
        if selectedFilePath:
            if self.fileListWidget.count()>0:
                self.fileListWidget.clear()
                self.resetApplicationState()
                self.actions.openNextImg.setEnabled(False)
                self.actions.openPrevImg.setEnabled(False)
            self.loadFile(selectedFilePath)

    ## Closing opened file.
    def closeFile(self, _value=False, ask=True):
        if ask and not self.mayContinue(True):
            return False
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)
        self.actions.undo.setEnabled(False)
        self.actions.undoLastPoint.setEnabled(False)
        self.actions.delete.setEnabled(False)
        for action in self.actions.onShapesPresent:
            action.setEnabled(False)
        self.toggleRunYoloBtns()
        return True

    ## Delete currently opened image's label file.
    def deleteFile(self):
        mb = QtWidgets.QMessageBox
        msg = self.tr(
            "You are about to permanently delete this label file, " "proceed anyway?"
        )
        answer = mb.warning(self, self.tr("Attention"), msg, mb.Yes | mb.No)
        if answer != mb.Yes:
            return

        label_file = self.getOutputFile()
        if osp.exists(label_file):
            os.remove(label_file)
            logger.info("Label file is removed: {}".format(label_file))

            item = self.fileListWidget.currentItem()
            item.setCheckState(Qt.Unchecked)

            #self.resetState()

    ## Set filename with the next file if found
    ## else, stay in the last one.
    def openNextImg(self, _value=False, load=True):
        keep_prev = self._config["keep_prev"]   ## copy prev annotations.
        if QtWidgets.QApplication.keyboardModifiers() == (
            Qt.ControlModifier | Qt.ShiftModifier
        ):
            self._config["keep_prev"] = True

        if self.fileListWidget.count() <=0:
            return

        #filename = None
        nextIndex = -1
        if self.filename is None:     ### initial load of dir.
            nextIndex = 0
        else:           ### open next one.
            try:
                currIndex = self.fileListWidget.currentRow()
            except Exception:
                self.errorMessage("Error Opening Image","Can not open next image.")
                self._config["keep_prev"] = keep_prev
                return
            
            if currIndex+1 < self.fileListWidget.count():
                nextIndex = currIndex+1

        if nextIndex!=-1 and load:
            self.fileListWidget.setCurrentRow(nextIndex)
            self.fileListWidget.repaint()

        self._config["keep_prev"] = keep_prev

    ## Get prev img index and call loadFile.
    def openPrevImg(self, _value=False):
        keep_prev = self._config["keep_prev"]
        if QtWidgets.QApplication.keyboardModifiers() == (
            Qt.ControlModifier | Qt.ShiftModifier
        ):
            self._config["keep_prev"] = True

        if not self.filename or self.fileListWidget.count()<=0:
            return

        try:    #### fixed
            prevIndex = self.fileListWidget.currentRow()-1
        except Exception:
            self.errorMessage("Error Opening Image","Can not open previous image")
            self._config["keep_prev"] = keep_prev
            return
        if prevIndex >= 0:
            self.fileListWidget.setCurrentRow(prevIndex)
            self.fileListWidget.repaint()
                
        self._config["keep_prev"] = keep_prev

    ## Used to load label/image file.
    def loadFile(self, filename=None):
        """Load the specified file, or the last opened file if None."""

        self.resetState()
        self.canvas.setEnabled(False)
        for action in self.actions.onShapesPresent:
            action.setEnabled(False)
        self.actions.undo.setEnabled(False)

        if filename is None:
            filename = self.settings.value("filename", "")
        filename = str(filename)
        if not QtCore.QFile.exists(filename):
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr("No such file: <b>%s</b>") % filename,
            )
            return False

        # assumes same name, but json extension
        self.status(str(self.tr("Loading %s...")) % osp.basename(str(filename)))

        self.imageData = LabelFile.load_image_file(filename)

        image = QtGui.QImage.fromData(self.imageData)

        if image.isNull():
            formats = [
                "*.{}".format(fmt.data().decode())
                for fmt in QtGui.QImageReader.supportedImageFormats()
            ]
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr(
                    "<p>Make sure <i>{0}</i> is a valid image file.<br/>"
                    "Supported image formats: {1}</p>"
                ).format(filename, ",".join(formats)),
            )
            self.status(self.tr("Error reading %s") % filename)
            return False

        self.imagePath = filename
        self.filename = filename
        self.image = image
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(image))

        if self._config["keep_prev"]: ## Previous image shapes.
            prev_shapes = self.canvas.shapes
        flags = {k: False for k in self._config["flags"] or []}

        if filename not in self.buffer:
            self.buffer[filename] = {}

        ## search for current shapes/flags in buffer.
        ## if found load them. if not, search for label file if provided.
        ## if label file provided, load from label file 
        if self.buffer[filename].get("shapes",None) is not None:
            print("load from buffer")
            bufferedData = self.buffer[filename]
            self.loadShapes(bufferedData.get("shapes",[]))      ## load shapes from buffer.
            flags.update(bufferedData.get("flags",{}))          ## update flags from buffer.

            if bufferedData.get("dirty",False):
                self.setDirty()
            else:
                self.setClean()

            # if bufferedData.get("undo"):
            #     self.canvas.shapesBackups = bufferedData.get("undo",[])
            #     self.actions.undo.setEnabled(True)

        else:
            self.buffer[filename]["image_size"] = [image.width(), image.height()]

            if self.loadShapesFromFile:         ## is label files provided
                assert self.labelFilesDir or VideoLabelFile.labelFilePath, "label files path is not specified"
                print("load from label file")
                self.lblFileLoaders.get(self.labelFileType)(filename,None)

            if self.labelFile:
                self.loadLabels(self.labelFile.shapes)       ## draw shapes from file and add them to buffer 
                if self.labelFile.flags is not None:
                    flags.update(self.labelFile.flags)       ## update flags.
                    self.buffer[self.imagePath]["flags"] = flags    ## add flags to buffer
                
            self.setClean()
        
        self.loadFlags(flags)   ## load to flags widget

        if self._config["keep_prev"] and self.noShapes(): ## Load previous shapes.
            self.loadShapes(prev_shapes, replace=False)
            self.setDirty()
        
        self.canvas.setEnabled(True)
        # set zoom values
        is_initial_load = not self.zoom_values
        if self.filename in self.zoom_values:
            self.zoomMode = self.zoom_values[self.filename][0]
            self.setZoom(self.zoom_values[self.filename][1])
        elif is_initial_load or not self._config["keep_prev_scale"]:
            self.adjustScale(initial=True)
        # set scroll values
        for orientation in self.scroll_values:
            if self.filename in self.scroll_values[orientation]:
                self.setScroll(
                    orientation, self.scroll_values[orientation][self.filename]
                )
        # set brightness contrast values
        dialog = BrightnessContrastDialog(
            utils.img_data_to_pil(self.imageData),
            self.onNewBrightnessContrast,
            parent=self,
        )
        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )
        if self._config["keep_prev_brightness"] and self.recentFiles:
            brightness, _ = self.brightnessContrast_values.get(
                self.recentFiles[0], (None, None)
            )
        if self._config["keep_prev_contrast"] and self.recentFiles:
            _, contrast = self.brightnessContrast_values.get(
                self.recentFiles[0], (None, None)
            )
        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
        self.brightnessContrast_values[self.filename] = (brightness, contrast)
        if brightness is not None or contrast is not None:
            dialog.onNewValue(None)

        self.paintCanvas()
        self.addRecentFile(self.filename)
        self.toggleActions(True)
        self.toggleRunYoloBtns()
        #self.canvas.setFocus()
        self.status(str(self.tr("Loaded %s")) % osp.basename(str(filename)))
        return True

    def loadLabelmeLblFile(self, filename:str, label_file:str=None, load:bool=False):
        if label_file is None:
            label_file = osp.splitext(filename)[0] + ".json"
            label_file = osp.join(self.labelFilesDir,osp.basename(label_file))
        if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(label_file, 0):
            try:
                self.labelFile = LabelFile(label_file)
            except LabelFileError as e:
                self.errorMessage(
                    self.tr("Error opening label file"),
                    self.tr(
                        "<p><b>%s</b></p>"
                        "<p>Make sure <i>%s</i> is a valid label file."
                    )
                    % (e, label_file),
                )
                self.status(self.tr("Error reading %s") % label_file)
                return False
            
            self.otherData = self.labelFile.otherData
            if load:
                self.loadLabels(self.labelFile.shapes)
                self.loadFlags(self.labelFile.flags)
                self.buffer[self.imagePath]["flags"] = self.labelFile.flags

        else:
            self.labelFile = None

    def loadYoloLblFile(self, filename:str=None, label_file:str=None, loadAnnOnly=False):
        if label_file is None:
            label_file = osp.splitext(filename)[0] + ".txt"
            label_file = osp.join(self.labelFilesDir,osp.basename(label_file))

        if osp.exists(label_file) and osp.splitext(label_file)[1]==".txt":
            self.labelFile = YoloLabelFile()
            self.labelFile.imageData = self.imageData
            self.labelFile.imagePath = self.imagePath
            self.labelFile.imageWidth = self.buffer[self.imagePath]["image_size"][0]
            self.labelFile.imageHeight = self.buffer[self.imagePath]["image_size"][1]
            
            try:
                self.labelFile.load(label_file)
            except LabelFileError as e:
                self.errorMessage("Error Reading Label File",
                                  "Make sure the label file '%s' has a correct Yolo format." % label_file
                )
                self.labelFile = None
                return
            
            # self.labelFile.loadTxtFile(label_file)
            if loadAnnOnly:
                self.loadLabels(self.labelFile.shapes)
        else:
            self.labelFile = None

    def loadVideoLblFile(self, filename:str, loadAnnOnly= False):

        if osp.exists(VideoLabelFile.labelFilePath) and osp.splitext(VideoLabelFile.labelFilePath)[1]==".json":
            self.labelFile = VideoLabelFile()
            self.labelFile.imageData = self.imageData
            self.labelFile.imagePath = self.imagePath
            id = self.fileListWidget.currentRow()
            ## to handle key errors.
            try:
                self.labelFile.loadVideoLabelFile(id, self.fileListWidget.count())
            except:
                self.errorMessage("Error Reading Label File",
                                  "Make sure the video label file '%s' has a correct format." % VideoLabelFile.labelFilePath
                )
                self.labelFile = None
        else:
            self.labelFile = None

    ## Used when openning file from recent files menu.
    def loadRecent(self, filename):
        if self.mayContinue():
            if self.fileListWidget.count()>0:
                self.fileListWidget.clear()
                self.resetApplicationState()
                self.actions.openNextImg.setEnabled(False)
                self.actions.openPrevImg.setEnabled(False)
            self.loadFile(filename)

    ## Add every opened file to recent files.
    def addRecentFile(self, filename):
        if filename in self.recentFiles:
            self.recentFiles.remove(filename)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filename)

    ## Open Video File
    def openExtractFramesDialog(self):
        defaultDirPath = osp.dirname(str(self.filename)) if self.filename else "."
        formats = [
            ".mp4",
            ".mkv",
            ".avi",
        ]
        filters = self.tr("Video files (%s)") % " ".join(
            ["*%s" % f for f in formats]
        )
        selectedFilePath,_ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Choose Video File") % __appname__,
            defaultDirPath,
            filters,
        )
        if selectedFilePath:
            if osp.splitext(selectedFilePath)[1].lower() in formats:
                cap = cv2.VideoCapture(selectedFilePath)
                if not cap.isOpened():
                    self.errorMessage("Error Opening Video","Error: Could not open video file.")
                    return
                
                videoDialog = ExtractFramesDialog(osp.splitext(selectedFilePath)[0], int(cap.get(cv2.CAP_PROP_FPS)))
                
                if videoDialog.exec() == QtWidgets.QDialog.Accepted:
                    self.extractFrames(cap,
                                       osp.basename(osp.splitext(selectedFilePath)[0]), 
                                       videoDialog.getOutputPath(), 
                                       videoDialog.getSelectedFPS())
            else:
                self.errorMessage(
                    "Invalid Video File",
                    "<p>Make sure the selected file extension is supported.<br> Supported Formats: {}</p>".format(", ".join("*" + format for format in formats))
                )


    def extractFrames(self, cap, videoname, dirpath, framerate):
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        fps = cap.get(cv2.CAP_PROP_FPS)
        # Calculate frame interval based on desired framerate
        frame_interval = int(round(fps / framerate))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        frame_num = 0
        progress = QtWidgets.QProgressDialog("Extracting Video", "Cancel", 0, (int)(total_frames/frame_interval),self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)      ## show progress
        # Read and save frames
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if progress.wasCanceled():
                break

            # Save frame if it's within the desired frame interval
            if frame_num % frame_interval == 0 and frame is not None:
                frame_filename = os.path.join(dirpath, f"{videoname}_frame_{frame_count}.jpg")
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imgviz.io.imsave(frame_filename,image)  ##FIXED
                #cv2.imwrite(frame_filename, frame) # not working well.
                frame_count += 1
                progress.setValue(frame_count)

            frame_num += 1
        cap.release()
        progress.setValue(int(total_frames/frame_interval))
        self.status("Frames saved succesfully to %s" % dirpath)

        #self.importDirImages(dirpath)

    ## Used to update recent files menu.
    def updateFileMenu(self):
        current = self.filename

        def exists(filename):
            return osp.exists(str(filename))

        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f != current and exists(f)]
        for i, f in enumerate(files):
            icon = utils.newIcon("labels")
            action = QtWidgets.QAction(
                icon, "&%d %s" % (i+1, QtCore.QFileInfo(f).fileName()),self)
            action.triggered.connect(functools.partial(self.loadRecent,f))
            menu.addAction(action)

    ###############   Shapes  ###################

    ## Has/Not shapes.
    def noShapes(self):
        return not len(self.labelList)

    ## Add labels to lists and draw on canvas.
    def loadShapes(self, shapes, replace=True):
        self._noSelectionSlot = True
        self.buffer[self.imagePath]["shapes"] = []
        for shape in shapes:
            self.addLabel(shape)
            self.buffer[self.imagePath]["shapes"].append(shape)
        self.labelList.clearSelection()
        self._noSelectionSlot = False
        self.canvas.loadShapes(shapes, replace=replace)  ## draw on canvas

    ## Update drawn shape color.
    def _update_shape_color(self, shape):
        r, g, b = self._get_rgb_by_label(shape.label)
        shape.line_color = QtGui.QColor(r, g, b)
        shape.vertex_fill_color = QtGui.QColor(r, g, b)
        shape.hvertex_fill_color = QtGui.QColor(255, 255, 255)
        shape.fill_color = QtGui.QColor(r, g, b, 128)
        shape.select_line_color = QtGui.QColor(255, 255, 255)
        shape.select_fill_color = QtGui.QColor(r, g, b, 155)

    ## Copy multiple selected shapes.
    def copyShape(self):
        self.canvas.endMove(copy=True)
        for shape in self.canvas.selectedShapes:
            self.addLabel(shape)
        self.labelList.clearSelection()
        self.setDirty()

    ## Move multiple selected shapes.
    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    ## Undo the edit made on canvas.
    def undoShapeEdit(self):
        self.canvas.restoreShape()
        self.labelList.clear()
        self.loadShapes(self.canvas.shapes)
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)

    def deleteSelectedShape(self):
        yes, no = QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        msg = self.tr(
            "You are about to permanently delete {} polygons, " "proceed anyway?"
        ).format(len(self.canvas.selectedShapes))
        if yes == QtWidgets.QMessageBox.warning(
            self, self.tr("Attention"), msg, yes | no, yes
        ):
            self.remLabels(self.canvas.deleteSelected())
            self.setDirty()
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)

    def deleteAllShapes(self):
        yes, no = QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        msg = self.tr(
            "You are about to permanently delete polygons, " "proceed anyway?"
        )
        if yes == QtWidgets.QMessageBox.warning(
            self, self.tr("Attention"), msg, yes | no, yes
        ):
            self.remLabels(self.canvas.deleteAllShapes())
            self.setDirty()
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)
            self.actions.delete.setEnabled(False)

    def duplicateSelectedShape(self):
        added_shapes = self.canvas.duplicateSelectedShapes()
        for shape in added_shapes:
            self.addLabel(shape)
        self.setDirty()

    def pasteSelectedShape(self):
        shapes = [s.copy() for s in self._copied_shapes]
        self.loadShapes(shapes, replace=False)
        self.setDirty()

    def copySelectedShape(self):
        self._copied_shapes = [s.copy() for s in self.canvas.selectedShapes]
        self.actions.paste.setEnabled(len(self._copied_shapes) > 0)

    def removeSelectedPoint(self):
        self.canvas.removeSelectedPoint()
        self.canvas.update()
        if not self.canvas.hShape.points:
            self.canvas.deleteShape(self.canvas.hShape)
            self.remLabels([self.canvas.hShape])
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)
        self.setDirty()

    ###############   Labels   ##################

    ## Setting shape objects to load it
    def loadLabels(self, shapes):
        s = []
        for shape in shapes:
            label = shape["label"]
            points = shape["points"]
            shape_type = shape["shape_type"]
            flags = shape["flags"]
            description = shape.get("description", "")
            group_id = shape["group_id"]
            other_data = shape["other_data"]

            if not points:
                # skip point-empty shape
                continue

            shape = Shape(
                label=label,
                shape_type=shape_type,
                group_id=group_id,
                description=description,
                mask = shape["mask"],
            )

            for x, y in points:
                shape.addPoint(QtCore.QPointF(x, y))
            shape.close()

            default_flags = {}
            if self._config["label_flags"]:
                for pattern, keys in self._config["label_flags"].items():
                    if re.match(pattern, label):
                        for key in keys:
                            default_flags[key] = False
            shape.flags = default_flags
            shape.flags.update(flags)
            shape.other_data = other_data
            s.append(shape)

        self.loadShapes(s)

    ## Ask user to replace current shapes or not
    def replaceShapes(self):
        mb = QtWidgets.QMessageBox
        replay = mb.question(
            self,
            "Overwrite Annotations",
            "This process will overwrite current annotations. Do you want to continue?",
            mb.Yes | mb.Cancel,
            mb.Yes,
        )

        if replay == mb.Yes:
            return True
        else:
            return False

    ## add labels to label and uniqLabel list.
    def addLabel(self, shape):
        if shape.group_id is None:
            text = shape.label
        else:
            text = "{} ({})".format(shape.label, shape.group_id)
        label_list_item = LabelListWidgetItem(text, shape)
        self.labelList.addItem(label_list_item) ### add label to labelList.
        if self.uniqLabelList.findItemByLabel(shape.label) is None:
            item = self.uniqLabelList.createItemFromLabel(shape.label)
            self.uniqLabelList.addItem(item) ### add label to uniqLabel list.
            rgb = self._get_rgb_by_label(shape.label)
            self.uniqLabelList.setItemLabel(item, shape.label, rgb)
        self.labelDialog.addLabelHistory(shape.label)

        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

        ### Updating shape object's color of current label.
        self._update_shape_color(shape)
        label_list_item.setText(
            '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                html.escape(text), *shape.fill_color.getRgb()[:3]
            )
        )

    def hasLabels(self):
        if self.noShapes():
            self.errorMessage(
                "No objects labeled",
                "You must label at least one object to save the file.",
            )
            return False
        return True

    ## Get label color.
    def _get_rgb_by_label(self, label):
        if self._config["shape_color"] == "auto":
            item = self.uniqLabelList.findItemByLabel(label)
            if item is None:
                item = self.uniqLabelList.createItemFromLabel(label)
                self.uniqLabelList.addItem(item)
                rgb = self._get_rgb_by_label(label)
                self.uniqLabelList.setItemLabel(item, label, rgb)
            label_id = self.uniqLabelList.indexFromItem(item).row() + 1
            label_id += self._config["shift_auto_shape_color"]
            return LABEL_COLORMAP[label_id % len(LABEL_COLORMAP)]
        elif (
            self._config["shape_color"] == "manual"
            and self._config["label_colors"]
            and label in self._config["label_colors"]
        ):
            return self._config["label_colors"][label]
        elif self._config["default_shape_color"]:
            return self._config["default_shape_color"]
        return (0, 255, 0)

    ## FIXME: Not Holding output dir change statement !!!!
    # def getLabelFile(self):
    #     if self.filename.lower().endswith(".json"):
    #         label_file = self.filename
    #     else:
    #         label_file = osp.splitext(self.filename)[0] + ".json"

    #     return label_file

    ###############   Flags    ###################

    def loadFlags(self, flags):
        self.flag_widget.clear()
        for key, flag in flags.items():
            item = QtWidgets.QListWidgetItem(key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if flag else Qt.Unchecked)
            self.flag_widget.addItem(item)

    ############## Label List Widget ########################

    ## show/hide shapes
    def togglePolygons(self, value):
        flag = value
        for item in self.labelList:
            if value is None:
                flag = item.checkState() == Qt.Unchecked
            item.setCheckState(Qt.Checked if flag else Qt.Unchecked)

    ## triggered when label list item selected
    def labelSelectionChanged(self):
        if self._noSelectionSlot:
            return
        if self.canvas.editing():
            selected_shapes = []
            for item in self.labelList.selectedItems():
                selected_shapes.append(item.shape())
            if selected_shapes:
                self.canvas.selectShapes(selected_shapes)
            else:
                self.canvas.deSelectShape()

    ## double click to edit label.
    def editLabel(self, item=None):
        if item and not isinstance(item, LabelListWidgetItem):
            raise TypeError("item must be LabelListWidgetItem type")

        if not self.canvas.editing():
            return
        if not item:
            item = self.currentItem()
        if item is None:
            return
        shape = item.shape()
        if shape is None:
            return
        text, flags, group_id, description = self.labelDialog.popUp(
            text=shape.label,
            flags=shape.flags,
            group_id=shape.group_id,
            description=shape.description,
        )
        if text is None:
            return
        if not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._config["validate_label"]
                ),
            )
            return
        shape.label = text
        shape.flags = flags
        shape.group_id = group_id
        shape.description = description

        self._update_shape_color(shape)
        if shape.group_id is None:
            item.setText(
                '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                    html.escape(shape.label), *shape.fill_color.getRgb()[:3]
                )
            )
        else:
            item.setText("{} ({})".format(shape.label, shape.group_id))
        self.setDirty()
        if self.uniqLabelList.findItemByLabel(shape.label) is None:
            item = self.uniqLabelList.createItemFromLabel(shape.label)
            self.uniqLabelList.addItem(item)
            rgb = self._get_rgb_by_label(shape.label)
            self.uniqLabelList.setItemLabel(item, shape.label, rgb)

    def labelItemChanged(self, item):
        shape = item.shape()
        self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    def labelOrderChanged(self):
        self.setDirty()
        self.canvas.loadShapes([item.shape() for item in self.labelList])

    def remLabels(self, shapes):
        for shape in shapes:
            item = self.labelList.findItemByShape(shape)
            self.labelList.removeItem(item)


    ## Label validation
    def validateLabel(self, label):
        # no validation
        if self._config["validate_label"] is None:
            return True

        for i in range(self.uniqLabelList.count()):
            label_i = self.uniqLabelList.item(i).data(Qt.UserRole)
            if self._config["validate_label"] in ["exact"]:
                if label_i == label:
                    return True
        return False

    ## PopUp label menu (on right click over label list item)
    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    ################## File list Widget Functions  ################

    def fileSearchChanged(self):
        self.fileListWidget.clear()
        filenames = self.buffer.keys()
        text = self.fileSearch.text()
        if text:
            try:
                filenames = [f for f in filenames if re.search(text,f)]
            except re.error:
                pass
        
        self.addFilesToFileList(filenames)

    ## triggered when selecting new file item
    ## to load it.
    def fileSelectionChanged(self):
        ## Enable and Disable File list widget buttons.
        isEnable = len(self.fileListWidget.selectedItems())>0
        self.fileListDeleteBtn.setEnabled(isEnable)
        self.fileListEditBtn.setEnabled(isEnable and not self.fileListEditMode)

        if not self.fileListEditMode:   ## Do not load image when editing file list.
            #print("File Selection Changed")
            items = self.fileListWidget.selectedItems()
            if not items:
                return

            item = items[0]
            currIndex = self.fileListWidget.row(item)
            if currIndex < self.fileListWidget.count():
                filename = item.text()
                if filename:
                    self.actions.saveAll.setEnabled(self.isAllDirty())
                    self.loadFile(filename)

    ## Adding all files from fileList to image list.
    @property
    def imageList(self):
        lst = []
        for i in range(self.fileListWidget.count()):
            item = self.fileListWidget.item(i)
            lst.append(item.text())
        return lst

    ## Toggle file list state to default.
    def resetFileListWidget(self, load=True):
        self.fileListEditMode=False
        self.fileListCancelBtn.setEnabled(False)
        self.actions.openNextImg.setEnabled(True)
        self.actions.openPrevImg.setEnabled(True)
        self.fileListWidget.setSelectionMode(QtWidgets.QListWidget.SingleSelection)
        if load:
            if self.fileListWidget.count()<=0:
                self.actions.openNextImg.setEnabled(False)
                self.actions.openPrevImg.setEnabled(False)
                return
            ## If current file not removed >> just mark it as current row without reloading image.
            items = self.fileListWidget.findItems(self.filename, Qt.MatchExactly)
            if not items:
                return
            row = self.fileListWidget.row(items[0])
            self.fileListWidget.itemSelectionChanged.disconnect(self.fileSelectionChanged)
            self.fileListDeleteBtn.setEnabled(True)
            self.fileListEditBtn.setEnabled(True)
            self.fileListWidget.setCurrentRow(row)
            self.fileListWidget.itemSelectionChanged.connect(self.fileSelectionChanged)


    ## Change file list mode to edit to select multiple items.
    def editFileListWidget(self):
        self.fileListEditMode=True      ## Disable signal when selecting multiple items.
        self.fileListWidget.clearSelection()
        self.fileListWidget.setSelectionMode(QtWidgets.QListWidget.MultiSelection)
        self.fileListEditBtn.setEnabled(False)
        self.fileListCancelBtn.setEnabled(True)
        self.actions.openNextImg.setEnabled(False)
        self.actions.openPrevImg.setEnabled(False)

    ## Remove selected item/s.
    def removeSelectedFiles(self):
        items = self.fileListWidget.selectedItems()

        mb = QtWidgets.QMessageBox
        replay = mb.question(
            self,
            "Remove Files",
            "%s files will be removed from list. Are you sure?" % len(items),
            mb.Yes | mb.No | mb.Cancel,
            mb.Yes,
        )
        if replay == mb.Cancel:     ## list to default.
            self.resetFileListWidget()
            return
        if replay == mb.No: ## Do no thing.
            return
        else:       ## Delete items.
            #currItemRow = None
            for item in items:
                row = self.fileListWidget.row(item)
                self.fileListWidget.takeItem(row)
                self.buffer.pop(item.text())
                if self.filename == item.text():
                    self.closeFile(False)
                # if self.filename == item.text():
                #     currItemRow = row
                # else:
                #     self.fileListWidget.takeItem(row)

            # if currItemRow is not None and self.closeFile():
            #     self.fileListWidget.takeItem(currItemRow)

            self.resetFileListWidget()

    ##############  utils  #############

    ## Check for unsaved data. (when dirty is true)
    def mayContinue(self, singleFile=False):
        #print("May continue?")
        # if not self.filename:
        #     return True

        if not self.dirty and not self.allDirty:
            return True
        
        if not singleFile:
            singleFile = self.fileListWidget.count()<=0

        if self.outputFileFormat is None or self.output_dir is None:
            defPath = osp.dirname(self.imagePath) if self.imagePath else "."
            if YoloLabelFile.outputLegendPath:
                legendPath = YoloLabelFile.outputLegendPath
            else:
                legendPath = YoloLabelFile.inputlegendPath
            dialog = SaveDialog(dirPath= defPath, legendPath=legendPath)
            if dialog.exec_() != QtWidgets.QDialog.Rejected:

                if dialog.toSave == True:      ## save
                    self.outputFileFormat = dialog.selectedOption
                    self.output_dir = dialog.selectedDir
                    legend = YoloLabelFile.loadLegendFile(dialog.selectedLegend)
                    if legend is not None:
                        YoloLabelFile.outputLegendPath = dialog.selectedLegend
                        YoloLabelFile.outputLegend = legend
                    if singleFile:
                        #print("Save single file")
                        self.saveFile()
                    else:
                        #print("save all files")
                        self.saveAllOutputFiles()
                else:       ## discard
                    self.dirty = False
                    self.allDirty = False

                return True

            else:           ## cancel

                return False
            
        else:
            #print("setting already done")
            mb = QtWidgets.QMessageBox
            msg = self.tr('Save all annotations to "{}" before closing?').format(self.output_dir)
            answer = mb.question(
                self,
                self.tr("Save annotations?"),
                msg,
                mb.Save | mb.Discard | mb.Cancel,
                mb.Save,
            )
            if answer == mb.Discard:
                #self.setClean()
                self.dirty = False
                self.allDirty = False
                return True
            elif answer == mb.Save:
                if singleFile:
                    #print("Saved single file")
                    self.saveFile()
                else:
                    self.saveAllOutputFiles()
                return True
            else:  # answer == mb.Cancel
                return False
            

    def setDirty(self):
        # Even if we autosave the file, we keep the ability to undo
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)
        
        if self.actions.saveAuto.isChecked():
            assert self.output_dir or self.outputFileFormat is not None, "Output directory or format not specified." 
            ext = LabelFile.outputSuffixes[self.outputFileFormat]
            label_file = osp.splitext(self.imagePath)[0] + ext
            label_file = osp.join(self.output_dir, osp.basename(label_file))
            self.bufferCurrentStatus()
            self.saveLabels(label_file, self.imagePath)
            #print("saved automatically.")
            return
        self.dirty = True
        self.bufferCurrentStatus()
        self.actions.save.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}*".format(title, self.filename)
        self.setWindowTitle(title)

        if self.fileListWidget.count()>0:
            self.fileListWidget.currentItem().setCheckState(Qt.Unchecked)

    def setClean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.createMode.setEnabled(True)
        self.actions.createRectangleMode.setEnabled(True)
        self.actions.createCircleMode.setEnabled(True)
        self.actions.createLineMode.setEnabled(True)
        self.actions.createPointMode.setEnabled(True)
        self.actions.createLineStripMode.setEnabled(True)
        self.actions.createAiPolygonMode.setEnabled(True)
        self.actions.createAiMaskMode.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}".format(title, self.filename)
        self.setWindowTitle(title)

        if self.hasLabelFile():
            self.actions.deleteFile.setEnabled(True)
        else:
            self.actions.deleteFile.setEnabled(False)

    ## Reset vairables.
    def resetState(self):
        self.labelList.clear()
        self.filename = None
        self.imagePath = None
        self.imageData = None
        self.labelFile = None
        self.otherData = None
        self.canvas.resetState()

    def resetApplicationState(self, clearDataOnly:bool=False):
        if clearDataOnly:
            for file in self.buffer.keys():
                self.buffer[file] = {}
        else:
            self.buffer.clear()

        self.labelFilesDir = None
        self.labelFileType = 0
        self.loadShapesFromFile = False
        self.actions.saveAuto.setChecked(False)
        YoloLabelFile.legend = []
        VideoLabelFile.labelFilePath = None
        self.output_dir = None
        self.outputFileFormat = None
        YoloLabelFile.outputLegend = []
        self.uniqLabelList.clear()
        self.uniqLabelList.labels = []
        self.labelDialog.deleteAllLabels()

    def toggleActions(self, value=True):
        '''Enable/Disable widgets which depend on an opened image.'''
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    ## Save image data in label file.
    def enableSaveImageWithData(self, enabled):
        self._config["store_data"] = enabled
        self.actions.saveWithImageData.setChecked(enabled)

    def getOutputFile(self):
        ext = LabelFile.outputSuffixes[self.outputFileFormat]
        if self.output_file:
            return self.output_file
        if self.output_dir:
            label_file = osp.splitext(self.filename)[0] + ext
            label_file = osp.join(self.output_dir, osp.basename(label_file))
        else:
            label_file = osp.splitext(self.filename)[0] + ext

        return label_file

    def hasLabelFile(self):
        if self.filename is None:
            return False
        
        if self.outputFileFormat is None:
            return False

        label_file = self.getOutputFile()
        return osp.exists(label_file)

    ## Get current path.
    def currentPath(self):
        return osp.dirname(str(self.filename)) if self.filename else "."

    ## to keep previous shapes to next/prev image.
    def toggleKeepPrevMode(self):
        self._config["keep_prev"] = not self._config["keep_prev"]

    ## Adding Menu to menuBar...
    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            utils.addActions(menu, actions)
        return menu

    ## Adding Tool bar to MainWindow
    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName("%sToolBar" % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            utils.addActions(toolbar, actions)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        return toolbar

    ## Show message in status bar
    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def tutorial(self):
        url = "https://github.com/wkentaro/labelme/tree/main/examples/tutorial"  # NOQA
        webbrowser.open(url)

    def queueEvent(self, function):
        QtCore.QTimer.singleShot(0, function)

    def dragEnterEvent(self, event):
        extensions = tuple([
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ])
        if event.mimeData().hasUrls():
            items = [i.toLocalFile() for i in event.mimeData().urls()]
            if (any([i.lower().endswith(extensions) for i in items])) or (osp.isdir(items[0]) and osp.exists(items[0])):
                event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self.mayContinue():
            event.ignore()
            return

        items = [i.toLocalFile() for i in event.mimeData().urls()]
        if osp.isdir(items[0]):
            self.importDirImages(items[0])
        else:
            self.importDroppedImageFiles(items)

    ## override main window resize event.
    def resizeEvent(self, event):
        if (
            self.canvas
            and not self.image.isNull()
            and self.zoomMode != self.MANUAL_ZOOM
        ):
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    ## Save window Geometry and status when app closed.
    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()

        self.settings.setValue("filename", self.filename if self.filename else "")
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("recentFiles", self.recentFiles)
        # ask the use for where to save the labels
        self.settings.setValue('window/geometry', self.saveGeometry())


    ## Pop up dialog with error message.
    def errorMessage(self, title, message):
        return QtWidgets.QMessageBox.critical(
            self, title, "<p><b>%s</b></p>%s" % (title, message)
        )

    ###### Save actions  #######

    def setSaveSettings(self):
        if self.output_dir:
            defaultDir = self.output_dir
        else:
            defaultDir = osp.dirname(self.imagePath) if self.imagePath else None

        if YoloLabelFile.outputLegendPath:
            legendPath = YoloLabelFile.outputLegendPath
        else:
            legendPath = YoloLabelFile.inputlegendPath

        dialog = SaveSettingDialog(self.outputFileFormat, defaultDir, legendPath, self.actions.saveAuto.isChecked())

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.outputFileFormat = dialog.selectedOption
            self.output_dir = dialog.selectedDir
            self.actions.saveAuto.setChecked(dialog.saveAuto)

            legend = YoloLabelFile.loadLegendFile(dialog.selectedLegend)
            if legend is not None:
                YoloLabelFile.outputLegendPath = dialog.selectedLegend
                YoloLabelFile.outputLegend = legend
                if self.labelDialog.labelList.count()>0:
                    self.labelDialog.deleteAllLabels()
                self.labelDialog.addLabels(legend)

            self.statusBar().showMessage(
                self.tr("Annotations will be saved in '%s'")
                % (self.output_dir)
            )
            self.statusBar().show()
            return True

        return False

    def setSaveAuto(self, enabled):
        if enabled:
            if self.outputFileFormat is None or not self.output_dir:
                if not self.setSaveSettings():
                    self.actions.saveAuto.setChecked(not enabled)
        else:
            self.actions.saveAuto.setChecked(enabled)

    def saveFile(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        #print("saveFile")
        if self.output_file:
            self._saveFile(self.output_file)
            self.close()
            return
        
        if self.outputFileFormat is None or not self.output_dir:
            if self.setSaveSettings():
                label_file = osp.splitext(self.imagePath)[0] + LabelFile.outputSuffixes[self.outputFileFormat]
                label_file = osp.join(self.output_dir, osp.basename(label_file))
                #print(label_file)
                self._saveFile(label_file)
        
        else:
            label_file = osp.splitext(self.imagePath)[0] + LabelFile.outputSuffixes[self.outputFileFormat]
            label_file = osp.join(self.output_dir, osp.basename(label_file))
            self._saveFile(label_file)

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = self.tr("%s - Choose File") % __appname__
        filters = ";;".join(
            [f"{fmt} Format (*{ext})" for fmt, ext in LabelFile.outputFormats.items()]
        )
        defaultSuffix = LabelFile.outputSuffixes.get(0,".json")
        basename = osp.basename(osp.splitext(self.imagePath)[0])
        if self.output_dir:
            dlg = QtWidgets.QFileDialog(self, caption, self.output_dir, filters)
            default_labelfile_name = osp.join(self.output_dir, basename + defaultSuffix)
        else:
            dlg = QtWidgets.QFileDialog(self, caption, self.currentPath(), filters)
            default_labelfile_name = osp.join(self.currentPath(), basename + defaultSuffix)

        dlg.setDefaultSuffix(defaultSuffix)
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite, False)
        dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, False)

        filename,_ = dlg.getSaveFileName(
            self,
            self.tr("Choose File"),
            default_labelfile_name,
            filters,
        )

        return filename

    def _saveFile(self, filename):
        if filename and self.saveLabels(filename, self.imagePath):
            self.setClean()

    def saveLabels(self, filename:str, imgPath:str, showMessage:bool=True):
        '''
        Save labels to output file.
        '''
        #print("saveLabels")
        def format_shape(s):
            data = s.other_data.copy()
            data.update(
                dict(
                    label=s.label.encode("utf-8") if PY2 else s.label,
                    points=[(p.x(), p.y()) for p in s.points],
                    group_id=s.group_id,
                    description=s.description,
                    shape_type=s.shape_type,
                    flags=s.flags,
                    mask=None if s.mask is None else utils.img_arr_to_b64(s.mask),
                )
            )
            return data
        
        shapes = [format_shape(shape) for shape in self.buffer[imgPath].get("shapes")]
        flags = self.buffer[imgPath].get("flags",{})
        imgSize = self.buffer[imgPath].get("image_size")
        if not imgSize:
            imgSize = LabelFile.getSizes(imgPath)
            self.buffer[imgPath]["image_size"] = imgSize

        if osp.dirname(filename) and not osp.exists(osp.dirname(filename)):
                    os.makedirs(osp.dirname(filename))

        fileSuffix = osp.splitext(filename)[1].lower()
        try:
            if  fileSuffix == LabelFile.outputSuffixes[0]:
                lf = LabelFile()
                imagePath = osp.relpath(imgPath, osp.dirname(filename))
                imageData = None
                if self.actions.saveWithImageData.isChecked():
                    imageData = LabelFile.load_image_file(imgPath)
                    if not imageData:
                        logger.error("Could not save image data of %s" % imgPath)
                
                lf.save(
                    filename=filename,
                    shapes=shapes,
                    imagePath=imagePath,
                    imageData=imageData,
                    imageHeight=imgSize[1],
                    imageWidth=imgSize[0],
                    otherData=self.otherData,
                    flags=flags,
                )

            else:
                if fileSuffix == LabelFile.outputSuffixes[1]:
                    lf = YoloLabelFile()
                    classList = []
                    if YoloLabelFile.outputLegend:
                        classList = YoloLabelFile.outputLegend
                    else:
                        classList = self.uniqLabelList.labels
                    lf.save(filename, shapes, imgSize, classList)
            self.buffer[imgPath]["dirty"] = False
            ##self.labelFile = lf
            items = self.fileListWidget.findItems(imgPath, Qt.MatchExactly)
                
            if len(items) > 0:
                if len(items) != 1:
                    raise RuntimeError("There are duplicate files.")
                items[0].setCheckState(Qt.Checked)
            # disable allows next and previous image to proceed
            # self.filename = filename
            return True
            
        except LabelFileError as e:
            if showMessage:
                self.errorMessage(
                    self.tr("Error saving label data"), self.tr("<b>%s</b>") % e
                )
            return False
        
    def isAllDirty(self):
        i=0
        dirty = False
        while not dirty and i<self.fileListWidget.count():
            image_path = self.fileListWidget.item(i).text()
            dirty = self.buffer[image_path].get("dirty",False)
            i+=1

        return dirty
    
    def allNoShapes(self):
        next = True
        images = list(self.buffer.keys())
        i=0
        while next and i<len(images):
            if self.buffer[images[i]].get("shapes",None):
                next=False
            i+=1
        return next


    def saveAllOutputFiles(self):
        '''
        Save all images found in files list
        '''
        #print("All files saved")
        if self.outputFileFormat is None or not self.output_dir:
            if not self.setSaveSettings():
                return
        
        progress_dialog = QtWidgets.QProgressDialog("Please wait...", None, 0, 0, self)
        progress_dialog.setWindowTitle("%s - Save Files" % __appname__)
        progress_dialog.setCancelButton(None)  # Disable cancel button
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setWindowFlags(Qt.WindowTitleHint)
        progress_dialog.show()
        #waitDialog = WaitDialog()
        #waitDialog.show()
        i=0
        noErr = True
        while noErr and i<self.fileListWidget.count():
            image_path = self.fileListWidget.item(i).text()
            #print(i)
            if self.buffer[image_path].get("dirty", False):
                #print("Saving")
                labelFile = osp.splitext(image_path)[0] + LabelFile.outputSuffixes[self.outputFileFormat]
                labelFile = osp.join(self.output_dir,osp.basename(labelFile))
                if self.saveLabels(labelFile, image_path, False):
                    self.fileListWidget.item(i).setCheckState(Qt.Checked)
                else:
                    noErr = False
            i+=1

        if not noErr:
            progress_dialog.close()
            self.errorMessage(
                self.tr("Error saving label data"), self.tr("<b>%s</b>") % image_path
            )
            return

        
        self.allDirty = False
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.saveAll.setEnabled(False)
        progress_dialog.close()


    def bufferCurrentStatus(self):
        assert self.imagePath, "Can not Buffer empty image."

        shapes = [item.shape() for item in self.labelList]

        flags = {}
        for i in range(self.flag_widget.count()):
            item = self.flag_widget.item(i)
            key = item.text()
            flag = item.checkState() == Qt.Checked
            flags[key] = flag

        self.buffer[self.imagePath]["shapes"] = shapes      # list
        self.buffer[self.imagePath]["flags"] = flags        # dict
        self.buffer[self.imagePath]["dirty"] = self.dirty   # bool
        self.buffer[self.imagePath]["undo"] = self.canvas.shapesBackups # list

    ##############   Canvas   #############

    ## drawing new shape on canvas
    def newShape(self):
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        items = self.uniqLabelList.selectedItems()
        text = None
        if items:
            text = items[0].data(Qt.UserRole)
        flags = {}
        group_id = None
        description = ""
        print("new shape")
        if self._config["display_label_popup"] or not text:
            previous_text = self.labelDialog.edit.text()
            text, flags, group_id, description = self.labelDialog.popUp(text)
            if not text:
                self.labelDialog.edit.setText(previous_text)

        if text and not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._config["validate_label"]
                ),
            )
            text = ""
        if text:
            self.labelList.clearSelection()
            shape = self.canvas.setLastLabel(text, flags)
            shape.group_id = group_id
            shape.description = description
            self.addLabel(shape)
            self.actions.editMode.setEnabled(True)
            self.actions.undoLastPoint.setEnabled(False)
            self.actions.undo.setEnabled(True)
            self.setDirty()
        else:
            self.canvas.undoLastLine()
            self.canvas.shapesBackups.pop()

    ## triggered when select or deselect shape on canvas.
    def shapeSelectionChanged(self, selected_shapes):
        self._noSelectionSlot = True
        for shape in self.canvas.selectedShapes:
            shape.selected = False
        self.labelList.clearSelection()
        self.canvas.selectedShapes = selected_shapes
        for shape in self.canvas.selectedShapes:
            shape.selected = True
            item = self.labelList.findItemByShape(shape)
            self.labelList.selectItem(item)
            self.labelList.scrollToItem(item)
        self._noSelectionSlot = False
        n_selected = len(selected_shapes)
        self.actions.delete.setEnabled(n_selected)
        self.actions.duplicate.setEnabled(n_selected)
        self.actions.copy.setEnabled(n_selected)
        self.actions.edit.setEnabled(n_selected == 1)

    ## Update canvas size after zoom value changed.
    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def toggleDrawingSensitive(self, drawing=True):
        """Toggle drawing sensitive.

        In the middle of drawing, toggling between modes should be disabled.
        """
        self.actions.editMode.setEnabled(not drawing)
        self.actions.undoLastPoint.setEnabled(drawing)
        self.actions.undo.setEnabled(not drawing)
        self.actions.delete.setEnabled(not drawing)

    ## enable/disable actions according to create mode or edit mode.
    def toggleDrawMode(self, edit=True, createMode="polygon"):
        draw_actions = {
            "polygon": self.actions.createMode,
            "rectangle": self.actions.createRectangleMode,
            "circle": self.actions.createCircleMode,
            "point": self.actions.createPointMode,
            "line": self.actions.createLineMode,
            "linestrip": self.actions.createLineStripMode,
            "ai_polygon": self.actions.createAiPolygonMode,
            "ai_mask": self.actions.createAiMaskMode,
            "box": self.actions.createBoxMode,
        }
        if not edit and createMode == "box":
            if self.canvas.fixedRectWidth is None and self.canvas.fixedRectHeight is None:
                if not self.setBoxSize():
                    return

        self.canvas.setEditing(edit)
        
        self.canvas.createMode = createMode
        if edit:
            for draw_action in draw_actions.values():
                draw_action.setEnabled(True)
        else:
            for draw_mode, draw_action in draw_actions.items():
                draw_action.setEnabled(createMode != draw_mode)
        self.actions.editMode.setEnabled(not edit)

    ## Set mode to edit.
    def setEditMode(self):
        self.toggleDrawMode(True)

    def setBoxSize(self):
        dialog = BoxSettingsDialog(self.canvas.fixedRectWidth, self.canvas.fixedRectHeight)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.canvas.fixedRectWidth = int(dialog.widthTxt.text())
            self.canvas.fixedRectHeight = int(dialog.heightTxt.text())
            return True
        
        return False

    ############### Zoom Funtions ###############

    ## For adjusting zoom via shortcuts
    def zoomRequest(self, delta, pos):
        canvas_width_old = self.canvas.width()
        units = 1.1
        if delta < 0:
            units = 0.9
        self.addZoom(units)

        canvas_width_new = self.canvas.width()
        if canvas_width_old != canvas_width_new:
            canvas_scale_factor = canvas_width_new / canvas_width_old

            x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
            y_shift = round(pos.y() * canvas_scale_factor) - pos.y()

            self.setScroll(
                Qt.Horizontal,
                self.scrollBars[Qt.Horizontal].value() + x_shift,
            )
            self.setScroll(
                Qt.Vertical,
                self.scrollBars[Qt.Vertical].value() + y_shift,
            )
    ## To calculate zoom value after request.
    def addZoom(self, increment=1.1):
        zoom_value = self.zoomWidget.value() * increment
        if increment > 1:
            zoom_value = math.ceil(zoom_value)
        else:
            zoom_value = math.floor(zoom_value)
        self.setZoom(zoom_value)
    ## setting zoom value in zoom widget.
    def setZoom(self, value = 100):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
            self.zoomMode = self.FIT_WINDOW
        else:
            self.zoomMode = self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
            self.zoomMode = self.FIT_WIDTH
        else:
            self.zoomMode = self.MANUAL_ZOOM
        self.adjustScale()
    ## to adjust scale.
    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        value = int(100 *value)
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)
    ## Calculate canvas size.
    def scaleFitWindow(self):
        """Figure out the size of the pixmap to fit the main widget."""
        e = 2.0 # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2
    ## Calculate canvas size.
    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    ## Do not doing anything !!!!
    def enableKeepPrevScale(self, enabled):
        self._config["keep_prev_scale"] = enabled
        self.actions.keepPrevScale.setChecked(enabled)

    ##############  Scroll Functions #############

    ## scroll request on canvas.
    def scrollRequest(self, delta, orientation):
        units = -delta * 0.1  # natural scroll
        bar = self.scrollBars[orientation]
        value = bar.value() + bar.singleStep() * units
        self.setScroll(orientation, value)
    ## set scroll values.
    def setScroll(self, orientation, value):
        self.scrollBars[orientation].setValue(int(value))
        self.scroll_values[orientation][self.filename] = value

    ##############  Brightness Functions  ############

    def onNewBrightnessContrast(self, qimage):
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(qimage), clear_shapes=False)

    ## Open brightness/contrast dialog.
    def brightnessContrast(self, value):
        dialog = BrightnessContrastDialog(
            utils.img_data_to_pil(self.imageData),
            self.onNewBrightnessContrast,
            parent=self,
        )
        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )

        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
        dialog.exec_()

        brightness = dialog.slider_brightness.value()
        contrast = dialog.slider_contrast.value()
        self.brightnessContrast_values[self.filename] = (brightness, contrast)

    ##################################  New Methods   ################################

    ## to open specific types of label files.
    def loadLabelFiles(self):
        ## Ask if self.dirty or self.allDirty.
        ## if saved reset all and continue.
        if not self.mayContinue():
            return
        
        dirPath = osp.dirname(self.imagePath) if self.imagePath else None
        if self.labelFilesDir:
            dirPath = self.labelFilesDir
        dialog = LoadLabelFilesDialog(self.labelFileType, dirPath, VideoLabelFile.labelFilePath)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.resetApplicationState(True)
            self.labelFileType = dialog.getCurrentOption()

            legend = YoloLabelFile.loadLegendFile(dialog.getSelectedLegend())
            if legend is not None:
                YoloLabelFile.inputlegendPath = dialog.getSelectedLegend()
                YoloLabelFile.legend = legend
                # if self.labelDialog.labelList.count()>0:
                #     self.labelDialog.labelList.clear()
                self.labelDialog.addLabels(YoloLabelFile.legend)
                #self.addLabelsFromLegend(YoloLabelFile.legend)
            # if YoloLabelFile.loadLegendFile(dialog.getSelectedLegend()):
            #     self.labelDialog.addLabels(YoloLabelFile.legend)

            if self.labelFileType==2:
                VideoLabelFile.labelFilePath = dialog.getSelectedPath()
                self.labelFilesDir = None
            else:
                self.labelFilesDir = dialog.getSelectedPath()
                VideoLabelFile.labelFilePath = None

            self.loadShapesFromFile = True

            if self.imagePath:   ## Load annotations if image/s is open.
                self.loadFile(self.imagePath)

    def addLabelsFromLegend(self, legend:list):
        self.uniqLabelList.clear()
        self.labelDialog.deleteAllLabels()
        for label in legend:
                # item = self.uniqLabelList.createItemFromLabel(label)
                # self.uniqLabelList.addItem(item)
                # rgb = self._get_rgb_by_label(label)
                # self.uniqLabelList.setItemLabel(item, label, rgb)
                self.labelDialog.addLabelHistory(label)

    def openAnnotationFile(self):
        if not self.noShapes():
            if not self.replaceShapes():
                return
            
        self.labelList.clear()
        dirpath = osp.dirname(self.imagePath) if self.imagePath else "."
        filters = ";;".join(
            [f"{fmt} Format (*{ext})" for fmt, ext in LabelFile.outputFormats.items()]
        )

        selectedFilePath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Choose Label file") % __appname__,
            dirpath,
            filters,
        )
        if not selectedFilePath:
            return
        self.labelList.clear()
        if osp.splitext(selectedFilePath)[1] == ".txt":
            self.lblFileLoaders.get(1)(None,selectedFilePath,True)
        else:
            self.lblFileLoaders.get(0)(None,selectedFilePath,True)
        # if selectedFilePath:
        #     self.lblFileLoaders.get(self.labelFileType)(None,selectedFilePath,True)

    ##########  AI Actions ###########

    ## Object detection on single image
    def runYolo(self):
        # if not self.mayContinue(True):
        #     return
        if not self.imagePath:
            self.errorMessage("Error",
                              "<p>Image not found.<br>Please load image to make detection.</p>")
            return
        
        self._runYoloButton.setEnabled(False)

        if not self.noShapes():
            if not self.replaceShapes():
                return

        self.status("Making predictions....")

        if not self.yoloModel.loadModel():
            self._runYoloButton.setEnabled(True)
            return

        res = self.yoloModel.runModel(self.imagePath)
        if not res:
            self.status("No Object detected on current image")
            self._runYoloButton.setEnabled(True)
            return

        self.labelList.clear()
        self.loadShapes(self.formatPredictedShapes(res))

        self._runYoloButton.setEnabled(True)
        self.actions.editMode.setEnabled(True)
        self.actions.undo.setEnabled(True)
        self.setDirty()
        self.yoloModel.resetPredictions()

    def runYoloVid(self):
        self._runYoloVidButton.setEnabled(False)

        if not self.imagePath:
            self._runYoloVidButton.setEnabled(True)
            return

        if self.fileListWidget.count()<=0:
            self.errorMessage("Error","<p>Files list is empty.</p>")
            self._runYoloVidButton.setEnabled(True)
            return
        
        if not self.allNoShapes():
            if not self.replaceShapes():
                self._runYoloVidButton.setEnabled(True)
                return

        if not self.yoloModel.loadModel():
            self._runYoloVidButton.setEnabled(True)
            return
        
        progress = QtWidgets.QProgressDialog("Running Model on images", "Cancel", 0, self.fileListWidget.count(), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        images = self.buffer.keys()

        self.yoloModel.resetPredictions()

        for i, image in enumerate(images):
            
            progress.setValue(i)
            if not progress.wasCanceled():
                self.yoloModel.runModelOnVideo(image)
                anns = self.formatPredictedShapes(self.yoloModel.predictions[i])
                self.buffer[image]["shapes"] = anns
                self.buffer[image]["dirty"] = True
                self.buffer[image]["undo"] = []

        #print(len(self.yoloModel.predictions))
        self.labelList.clear()
        self.loadShapes(self.buffer[self.imagePath].get("shapes",[]))
        progress.setValue(self.fileListWidget.count())

        self._runYoloVidButton.setEnabled(True)
        #self.actions.editMode.setEnabled(True)
        self.actions.undo.setEnabled(True)
        self.actions.saveAll.setEnabled(True)
        self.setDirty()

    def runYoloTrack(self):
        self._runYoloTrackButton.setEnabled(False)

        if not self.imagePath:
            self._runYoloTrackButton.setEnabled(True)
            return

        if self.fileListWidget.count()<=0:
            self.errorMessage("Error","<p>Files list is empty.</p>")
            self._runYoloTrackButton.setEnabled(True)
            return
        
        if not self.allNoShapes():
            if not self.replaceShapes():
                self._runYoloTrackButton.setEnabled(True)
                return

        if not self.yoloModel.loadModel():
            self._runYoloTrackButton.setEnabled(True)
            return

        progress = QtWidgets.QProgressDialog("Running Model on Frames", "Cancel", 0, self.fileListWidget.count(), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        images = self.buffer.keys()
        self.yoloModel.resetPredictions()

        for i, image in enumerate(images):
            progress.setValue(i)

            if not progress.wasCanceled():
                self.yoloModel.runModelWithTrack(image)
                anns = self.formatPredictedShapes(self.yoloModel.predictions[i])
                self.buffer[image]["shapes"] = anns
                self.buffer[image]["dirty"] = True
                self.buffer[image]["undo"] = []

        self.labelList.clear()
        self.loadShapes(self.buffer[self.imagePath].get("shapes",[]))
        progress.setValue(self.fileListWidget.count())

        self._runYoloTrackButton.setEnabled(True)
        #self.actions.editMode.setEnabled(True)
        self.actions.undo.setEnabled(True)
        self.actions.saveAll.setEnabled(True)
        self.setDirty()

    def formatPredictedShapes(self, shapes):
        s = []
        for shape in shapes:
            label = shape["label"]
            points = shape["points"]
            shape_type = shape["shape_type"]
            group_id = shape["group_id"]

            if not points:
                # skip point-empty shape
                continue

            shape = Shape(
                label=label,
                shape_type=shape_type,
                group_id=group_id,
                description="",
                mask = shape["mask"],
            )

            for x, y in points:
                shape.addPoint(QtCore.QPointF(x, y))
            shape.close()

            shape.flags = {}
            shape.other_data = {}
            s.append(shape)

        return s

    def selectObjModel(self):
        defaultPath = osp.dirname(self.yoloModel.modelPath) if self.yoloModel.modelPath else "."
        model_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("%s - Choose AI Model File") % __appname__,
            defaultPath,
            self.tr("Model Files (*.pt)"),
        )
        if not model_path:
            return
        if not YoloModel.isFileValid(model_path):
            self.errorMessage("Error",
                              ("<p>Make sure <i>{0}</i> is a valid model file.<br/>"
                              "Supported model formats: (*.pt)</p>").format(model_path))
            return

        self.yoloModel.resetState()
        self.yoloModel.setModelPath(model_path)
        self.yoloModelLabel.setText(self.yoloModel.getUniqueName())
        self.toggleRunYoloBtns()

    def toggleRunYoloBtns(self):
        flag1 = True if self.fileListWidget.count()>0 else False
        flag2 = True if self.filename else False
        flag3 = True if self.yoloModel.modelPath else False

        self._runYoloButton.setEnabled(flag2 and flag3)
        self._runYoloVidButton.setEnabled(flag1 and flag2 and flag3)
        self._runYoloTrackButton.setEnabled(flag1 and flag2 and flag3)