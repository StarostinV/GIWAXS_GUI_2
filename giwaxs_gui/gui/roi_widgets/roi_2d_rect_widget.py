from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from pyqtgraph import RectROI

from ...app.rois.roi import Roi
from .abstract_roi_widget import AbstractRoiWidget
from .rois_context_menu import RoiContextMenu


class Roi2DRect(AbstractRoiWidget, RectROI):
    sigRoiMoved = pyqtSignal(int)
    sigSelected = pyqtSignal(int)
    sigShiftSelected = pyqtSignal(int)

    def __init__(self, roi: Roi):
        AbstractRoiWidget.__init__(self, roi)
        RectROI.__init__(self, pos=(0, 0), size=(1, 1))
        self.handle = self.handles[0]['item']
        self.sigRegionChanged.connect(self._handle_is_moving)
        self.update_roi()

    def _handle_is_moving(self):
        if self.handle.isMoving:
            self.send_move()

    def send_move(self):
        size, pos = self.size(), self.pos()
        w, a_w = size
        r, a = abs(pos[0] + w / 2), pos[1] + a_w / 2
        self.roi.radius = r
        self.roi.width = w
        self.roi.angle = a
        self.roi.angle_std = a_w
        self.sigRoiMoved.emit(self.roi.key)

    @pyqtSlot(name='move_roi')
    def move_roi(self):
        r, w = self.roi.radius, abs(self.roi.width)
        a, a_w = self.roi.angle, abs(self.roi.angle_std)

        pos = [r - w / 2, a - a_w / 2]
        size = [w, a_w]
        self.setSize(size)
        self.setPos(pos)

    def set_color(self, color):
        self.setPen(color)

    def set_movable(self, movable: bool):
        self.translatable = movable

    def mouseDragEvent(self, ev):
        if self.roi.movable:
            RectROI.mouseDragEvent(self, ev)
            self.send_move()

    def mouseClickEvent(self, ev):
        if ev.button() == Qt.RightButton:
            ev.accept()
            self.show_context_menu(ev)
        elif ev.button() == Qt.LeftButton and ev.modifiers() == Qt.ShiftModifier:
            ev.accept()
            self.sigShiftSelected.emit(self.roi.key)
        elif ev.button() == Qt.LeftButton:
            # self.change_active()
            ev.accept()
            self.sigSelected.emit(self.roi.key)

    def show_context_menu(self, ev):
        RoiContextMenu(self.roi)

    def fix(self):
        super().fix()
        self.set_movable(False)
        self.handle.hide()

    def unfix(self):
        super().unfix()
        self.set_movable(True)
        self.handle.show()
