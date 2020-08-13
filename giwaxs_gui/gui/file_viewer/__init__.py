from PyQt5.QtWidgets import QTabWidget

from .viewer import FileViewer, FileManager
from .meta_roi_widget import RoiMetaWidget


class MainFileWidget(QTabWidget):
    def __init__(self, fm: FileManager, parent=None):
        super().__init__(parent)
        self.setTabPosition(QTabWidget.West)
        self.addTab(FileViewer(fm, self), 'Files')
        self.addTab(RoiMetaWidget(self), 'Rois')
