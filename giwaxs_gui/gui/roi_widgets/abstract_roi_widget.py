from abc import abstractmethod

from PyQt5.QtGui import QColor
from ...app.rois.roi import Roi

COLOR_DICT = dict(
    default=QColor(0, 0, 255),
    active=QColor(0, 128, 255),
    fixed=QColor(0, 255, 0),
    fixed_active=QColor(255, 0, 255)
)


def _color_key(roi: Roi) -> str:
    if roi.active and roi.movable:
        return 'active'
    if not roi.active and roi.movable:
        return 'default'
    if roi.active and not roi.movable:
        return 'fixed_active'
    return 'fixed'


class AbstractRoiWidget(object):
    BRIGHT_COLOR: bool = True

    def __init__(self, roi: Roi):
        self._roi = roi

    def update_color(self):
        color = COLOR_DICT[_color_key(self.roi)]
        if not self.BRIGHT_COLOR:
            color.setAlpha(150)
        self.set_color(color)

    def update_roi(self):

        self.move_roi()

        if not self.roi.movable:
            self.fix()
        else:
            self.unfix()
        self.update_color()

    @abstractmethod
    def move_roi(self):
        pass

    @abstractmethod
    def send_move(self):
        pass

    @property
    def roi(self):
        return self._roi

    @abstractmethod
    def set_color(self, color):
        pass

    def update_select(self):
        self.update_color()

    def fix(self):
        self.update_color()

    def unfix(self):
        self.update_color()

    # def show_roi(self):
    #     self.show()
    #
    # def hide_roi(self):
    #     self.hide()
