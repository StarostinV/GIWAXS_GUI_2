# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from .roi_widgets.roi_2d_rect_widget import Roi2DRect
from .roi_widgets.roi_1d_widget import Roi1D

from .basic_widgets import Custom1DPlot, CustomImageViewer
from ..app.fitting import Fit, GaussianFit
from ..app.rois.roi_data import RoiData, Roi, RoiTypes
from .tools import center_widget


class FitWidget(QWidget):

    def __init__(self, gaussian_fit: GaussianFit, parent=None):
        super().__init__(parent=parent)
        self.setGeometry(0, 0, 1000, 1000)
        self.g_fit = gaussian_fit
        self.rois = [fit.roi for fit in self.g_fit.fits.values()]
        self.roi_data = RoiData(self.rois)
        self._selected_fit: Fit = None
        self._rect_widgets: dict = {}
        self._init_ui()
        center_widget(self)
        self.show()

    def _init_ui(self):
        layout = QGridLayout(self)

        self.polar_viewer = CustomImageViewer(parent=self)
        self.radial_viewer = RadialFitWidget(parent=self)
        self.fit_plot = FitPlot(parent=self)

        self.polar_viewer.set_data(self.g_fit.polar_image)
        self.polar_viewer.set_x_axis(self.g_fit.r_axis.min(), self.g_fit.r_axis.max())
        self.polar_viewer.set_y_axis(self.g_fit.phi_axis.min(), self.g_fit.phi_axis.max())
        self.polar_viewer.view_box.setAspectLocked(True, self.g_fit.aspect_ratio)
        self.polar_viewer.set_auto_range()
        self.radial_viewer.set_data(self.g_fit.r_axis, self.g_fit.r_profile)
        self.radial_viewer.sigUpdateFit.connect(self._update_fit)

        for roi in self.rois:
            rect_widget = Roi2DRect(roi)
            rect_widget.sigSelected.connect(self._roi_selected)
            rect_widget.sigRoiMoved.connect(self._roi_moved)
            self.polar_viewer.image_plot.addItem(rect_widget)
            self._rect_widgets[roi.key] = rect_widget

        layout.addWidget(self.polar_viewer, 0, 0)
        layout.addWidget(self.radial_viewer, 1, 0)
        layout.addWidget(self.fit_plot, 0, 1)

    @property
    def selected_key(self):
        return self._selected_fit.roi.key if self._selected_fit else None

    @pyqtSlot(name='updateFit')
    def _update_fit(self):
        self.g_fit.update_fit(self._selected_fit)
        self.fit_plot.update_plot()

    @pyqtSlot(int, name='roiMoved')
    def _roi_moved(self, key: int):
        if key != self.selected_key:
            self._roi_selected(key)
        roi = self._selected_fit.roi
        if roi.type == RoiTypes.ring and (roi.angle, roi.angle_std) != self.g_fit.bounds:
            roi.type = RoiTypes.segment

        self.g_fit.update_r_range(self._selected_fit)
        self.g_fit.update_fit(self._selected_fit)
        self.fit_plot.update_plot()
        self.radial_viewer.update_roi()

    def _roi_selected(self, key: int):
        if key == self.selected_key:
            return
        else:
            if self._selected_fit:
                self._select_roi(self._selected_fit.roi, False)
            self._selected_fit = self.g_fit.fits[key]
            self._select_roi(self._selected_fit.roi, True)
            self._add_selected_fit()

    def _add_selected_fit(self):
        self.radial_viewer.set_fit(self._selected_fit)
        self.fit_plot.set_fit(self._selected_fit)

    def _select_roi(self, roi: Roi, active: bool):
        roi.active = active
        self._rect_widgets[roi.key].update_color()


class RadialFitWidget(Custom1DPlot):
    sigUpdateFit = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.fit: Fit = None
        self.roi_widget: Roi1D = None
        self.range_roi: Roi = None
        self.range_widget: Roi1D = None

    @pyqtSlot(object, name='addFit')
    def set_fit(self, fit: Fit):
        self.remove_fit()

        self.fit = fit
        self.roi_widget = Roi1D(fit.roi)
        r1, r2 = fit.r_range

        self.range_roi = Roi(radius=(r1 + r2) / 2, width=r2 - r1, key=-1)
        self.range_widget = Roi1D(self.range_roi)
        self.range_widget.set_color(QColor(255, 255, 255, 50))
        self.plot_item.addItem(self.range_widget)
        self.plot_item.addItem(self.roi_widget)

        self.range_widget.sigRoiMoved.connect(self._update_fit)
        self.roi_widget.sigRoiMoved.connect(self._update_fit)

    def update_roi(self):
        if not self.fit:
            return
        self.roi_widget.move_roi()
        r1, r2 = self.fit.r_range
        self.range_roi.radius = (r1 + r2) / 2
        self.range_roi.width = r2 - r1
        self.range_widget.move_roi()

    def _update_fit(self, key: int):
        if key == -1:
            r, w = self.range_roi.radius, self.range_roi.width
            self.fit.r_range = r - w / 2, r + w / 2
        self.sigUpdateFit.emit()

    @pyqtSlot(name='removeFit')
    def remove_fit(self):
        if self.fit:
            self.plot_item.removeItem(self.roi_widget)
            self.plot_item.removeItem(self.range_widget)
            self.fit = None
            self.roi_widget = None
            self.range_roi = None
            self.range_widget = None


class FitPlot(Custom1DPlot):
    log = logging.getLogger(__name__)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.fit: Fit = None
        self.fit_plot = self.plot_item.plot()
        self.fit_plot.setPen(self._get_fit_pen())

    def set_fit(self, fit: Fit):
        self.fit = fit
        self.update_plot()

    def update_plot(self):
        if not self.fit:
            return
        # self.clear()
        try:
            self.plot.setData(self.fit.x, self.fit.y)
            self.fit_plot.setData(self.fit.x, self.fit.init_curve)
        except Exception as err:
            self.log.exception(err)

    def remove_fit(self):
        self.fit = None
        self.clear()

    def clear(self):
        self.fit_plot.clear()
        self.plot.clear()

    @staticmethod
    def _get_fit_pen():
        pen = QPen(QColor('red'))
        pen.setStyle(Qt.DashDotLine)
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCosmetic(True)
        return pen
