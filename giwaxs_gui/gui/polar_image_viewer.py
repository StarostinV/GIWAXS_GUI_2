# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSlot

import numpy as np
from .basic_widgets import CustomImageViewer, BlackToolBar
from .roi_widgets.roi_2d_rect_widget import Roi2DRect
from .roi_widgets.abstract_roi_holder import AbstractRoiHolder

from ..app.app import App
from .tools import Icon


class PolarImageViewer(AbstractRoiHolder, QMainWindow):

    def __init__(self, parent=None):
        AbstractRoiHolder.__init__(self, 'PolarImageViewer')
        QMainWindow.__init__(self, parent)
        self.app = App()
        self._setup_window = None

        self._image_viewer = CustomImageViewer(self)
        self.setCentralWidget(self._image_viewer)
        self.app.image_holder.sigPolarImageChanged.connect(self._update_image)
        self.app.geometry_holder.sigScaleChanged.connect(self._on_scale_changed)
        # self.app.roi_dict.sig_roi_moved.connect(self._image_viewer.set_auto_range)

        self.__init_toolbar()

    def _on_scale_changed(self):
        self.set_axes()

    def _make_roi_widget(self, roi):
        roi_widget = Roi2DRect(roi)
        self._image_viewer.image_plot.addItem(roi_widget)
        return roi_widget

    def _delete_roi_widget(self, roi_widget):
        self._image_viewer.image_plot.removeItem(roi_widget)
        self._image_viewer.set_auto_range()

    def __init_toolbar(self):
        setup_toolbar = BlackToolBar('Setup', self)
        self.addToolBar(setup_toolbar)

        setup_action = setup_toolbar.addAction(Icon('setup'), 'Setup')
        setup_action.triggered.connect(self.open_setup_window)

    @pyqtSlot(name='updateImage')
    def _update_image(self):
        img = self.app.polar_image
        if img is not None:
            self._image_viewer.set_data(img)
            self.set_axes()

    def set_axes(self):
        if self._image_viewer.image_item.image is None:
            return
        p1, p2 = self.app.geometry.phi_range
        r1, r2 = self.app.geometry.r_axis.min(), self.app.geometry.r_axis.max()
        self._image_viewer.set_x_axis(r1, r2)
        self._image_viewer.set_y_axis(p1 * 180 / np.pi, p2 * 180 / np.pi)
        self._image_viewer.view_box.setAspectLocked(
            True, self.app.geometry.polar_aspect_ratio)
        self._image_viewer.set_auto_range()

    def open_setup_window(self):
        pass

    def set_parameters(self, params: dict):
        self.image.set_interpolation_parameters(params)
        self.update_image()

    def close_setup(self):
        self._setup_window = None
