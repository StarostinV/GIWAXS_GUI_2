import numpy as np

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPainter, QPen, QPainterPath

from pyqtgraph import ROI

from ...app import Roi, App
from .abstract_roi_widget import AbstractRoiWidget


class Roi2DRing(AbstractRoiWidget, ROI):
    sigRoiMoved = pyqtSignal(int)
    sigSelected = pyqtSignal(int)
    sigShiftSelected = pyqtSignal(int)

    def __init__(self, roi: Roi, parent=None):
        AbstractRoiWidget.__init__(self, roi)
        ROI.__init__(self, (0, 0), (roi.radius, roi.radius),
                     movable=False, parent=parent)
        self._radius = roi.radius
        self._center = (0, 0)
        self._width = roi.width
        self._angle = roi.angle
        self._angle_std = roi.angle_std

        self.aspectLocked = True

        self.set_radius(self._radius)
        self.update_roi()

        if App().debug_tracker:
            App().debug_tracker.add_object(self, roi.name)

    @pyqtSlot(name='move_roi')
    def move_roi(self):
        self.set_radius(self.roi.radius)
        self.set_width(self.roi.width)
        if self.roi.angle is not None:
            self.set_angle(self.roi.angle)
        if self.roi.angle_std is not None:
            self.set_angle_std(self.roi.angle_std)

    def send_move(self):
        pass

    def set_color(self, color):
        self.setPen(color)

    def set_center(self, center: tuple):
        self._center = center
        d = self._radius + self._width / 2
        pos = (center[1] - d, center[0] - d)
        self.setPos(pos)

    def set_radius(self, radius):
        self._radius = radius
        s = 2 * radius + self._width
        self.setSize((s, s))
        self.set_center(self._center)

    def set_width(self, width):
        self._width = width
        self.set_radius(self._radius)

    def set_angle(self, angle):
        self._angle = angle
        self.set_center(self._center)

    def set_angle_std(self, angle):
        self._angle_std = angle
        self.set_center(self._center)

    def paint(self, p, opt, widget):
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(self.currentPen)

        x1, y1 = 0, 0
        x2, y2 = x1 + self._width, y1 + self._width
        x3, y3 = x1 + self._width / 2, y1 + self._width / 2
        d1, d2, d3 = (2 * self._radius + self._width,
                      2 * self._radius - self._width,
                      2 * self._radius)

        # p.scale(self._radius, self._radius)
        r1 = QRectF(x1, y1, d1, d1)
        r2 = QRectF(x2, y2, d2, d2)
        r3 = QRectF(x3, y3, d3, d3)
        angle = - self._angle or 0
        angle_std = self._angle_std or 360
        a1, a2 = int((angle - angle_std / 2) * 16), int(angle_std * 16)
        p.drawArc(r1, a1, a2)
        p.drawArc(r2, a1, a2)
        dash_pen = QPen(self.currentPen)
        dash_pen.setStyle(Qt.DashLine)
        p.setPen(dash_pen)
        p.drawArc(r3, a1, a2)

    def getArrayRegion(self, arr, img=None, axes=(0, 1), **kwds):
        """
        Return the result of ROI.getArrayRegion()
        masked by the elliptical shape
        of the ROI. Regions outside the ellipse are set to 0.
        """
        # Note: we could use the same method as used by PolyLineROI, but this
        # implementation produces a nicer mask.
        arr = ROI.getArrayRegion(self, arr, img, axes, **kwds)
        if arr is None or arr.shape[axes[0]] == 0 or arr.shape[axes[1]] == 0:
            return arr
        w = arr.shape[axes[0]]
        h = arr.shape[axes[1]]
        ## generate an ellipsoidal mask
        mask = np.fromfunction(
            lambda x, y: (((x + 0.5) / (w / 2.) - 1) ** 2 + ((y + 0.5) / (h / 2.) - 1) ** 2) ** 0.5 < 1, (w, h))

        # reshape to match array axes
        if axes[0] > axes[1]:
            mask = mask.T
        shape = [(n if i in axes else 1) for i, n in enumerate(arr.shape)]
        mask = mask.reshape(shape)

        return arr * mask

    def shape(self):
        self.path = QPainterPath()
        self.path.addEllipse(self.boundingRect())
        return self.path
