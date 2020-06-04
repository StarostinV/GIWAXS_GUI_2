from abc import abstractmethod
from ..app.rois.roi import Roi


class AbstractRoi:
    def __init__(self, roi: Roi):
        self.roi = roi

    @abstractmethod
    def set_color(self, color):
        pass

    @abstractmethod
    def fix(self):
        pass

    @abstractmethod
    def unfix(self):
        pass

    @abstractmethod
    def show_roi(self):
        pass

    @abstractmethod
    def hide_roi(self):
        pass

    
