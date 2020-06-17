# -*- coding: utf-8 -*-

import numpy as np

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidgetAction

from pyqtgraph import (GraphicsLayoutWidget, setConfigOptions,
                       ImageItem, HistogramLUTItem)
from pyqtgraph.graphicsItems.ViewBox.ViewBoxMenu import ViewBoxMenu

from giwaxs_gui.gui.basic_widgets.sliders import LabeledSlider


class CustomViewBoxMenu(ViewBoxMenu):
    sigSigmaChanged = pyqtSignal(float)
    sigRangeAsDefault = pyqtSignal()

    def __init__(self, view, sigma: float = 3):
        super().__init__(view)
        self.slider = LabeledSlider('Clip sigma factor', bounds=(0.001, 4),
                                    value=sigma, parent=self)
        self.slider.valueChanged.connect(self.sigSigmaChanged.emit)
        self.addAction('Set range as default', lambda *x: self.sigRangeAsDefault.emit())
        self.sigma_factor_menu = self.addMenu('Set sigma factor')
        action = QWidgetAction(self)

        action.setDefaultWidget(self.slider)
        self.sigma_factor_menu.addAction(action)


class CustomImageViewer(GraphicsLayoutWidget):
    @property
    def view_box(self):
        return self.image_plot.vb

    def __init__(self, parent=None, *, hist_range: tuple = None, sigma_factor: float = 3, **kwargs):
        setConfigOptions(imageAxisOrder='row-major')
        super(CustomImageViewer, self).__init__(parent)
        self._scale = (1., 1.)
        self._center = (0, 0)

        self._hist_range = hist_range
        self._sigma_factor = sigma_factor

        self._init_ui(**kwargs)

    def _init_ui(self, **kwargs):
        self.setWindowTitle('Image Viewer')
        self.image_plot = self.addPlot(**kwargs)
        self.image_plot.vb.setAspectLocked()
        self.image_plot.vb.invertY()
        self.image_item = ImageItem()
        self.image_plot.addItem(self.image_item)
        self.image_plot.setMenuEnabled(False)
        self.hist = HistogramLUTItem()
        self.hist.setImageItem(self.image_item)
        self.addItem(self.hist)
        self.hist.vb.menu = CustomViewBoxMenu(self.hist.vb)
        self.hist.vb.menu.sigSigmaChanged.connect(self.set_sigma_factor)
        self.hist.vb.menu.sigRangeAsDefault.connect(self.set_limit_as_default)

    def set_data(self, data, *, reset_axes: bool = False):
        if data is None:
            return
        self.image_item.setImage(data)
        self.set_levels()
        if reset_axes:
            self.image_item.resetTransform()
        self.set_default_range()

    def hist_params(self) -> dict:
        return dict(sigma_factor=self._sigma_factor, hist_range=self._hist_range)

    def clear_image(self):
        self.set_data(np.zeros((1, 1)))

    def set_default_range(self):
        if self.image_item.image is None:
            return
        # self.set_auto_range()
        axes = self.get_axes()
        self.image_plot.setRange(xRange=axes[1], yRange=axes[0])

    def set_auto_range(self):
        self.image_plot.autoRange()

    def set_levels(self):
        img = self.image_item.image
        if img is None:
            return

        if self._sigma_factor and self._sigma_factor > 0:
            m, s = img.flatten().mean(), img.flatten().std() * self._sigma_factor
            self.hist.setLevels(max(m - s, img.min()), min(m + s, img.max()))
        elif self._hist_range:
            self.hist.setLevels(*self._hist_range)
        else:
            self.hist.setLevels(self.image_item.image.min(),
                                self.image_item.image.max())

    def set_sigma_factor(self, sigma_factor: float):
        self._sigma_factor = sigma_factor
        self.set_levels()

    def set_limit_as_default(self):
        self._hist_range = self.hist.getLevels()
        self._sigma_factor = None
        self.set_levels()

    def get_levels(self):
        return self.hist.getLevels()

    def set_center(self, center: tuple, pixel_units: bool = True):
        if not pixel_units:
            scale = self.get_scale()
            center = (center[0] / scale[0], center[1] / scale[1])
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
            self.image_item.scale(*self._scale)
        self.image_item.translate(- center[0], - center[1])
        self._center = center
        self.set_default_range()

    def set_scale(self, scale: float or tuple):
        if isinstance(scale, float) or isinstance(scale, int):
            scale = (scale, scale)
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
        self.image_item.scale(*scale)
        if self._center != (0, 0):
            self.image_item.translate(- self._center[0], - self._center[1])
        self._scale = scale
        self.set_default_range()

    def get_scale(self):
        # scale property is occupied by Qt superclass.
        return self._scale

    def get_center(self):
        return self._center

    def set_x_axis(self, x_min, x_max):
        self._set_axis(x_min, x_max, 0)
        self.set_default_range()

    def set_y_axis(self, y_min, y_max):
        self._set_axis(y_min, y_max, 1)
        self.set_default_range()

    def _set_axis(self, min_: float, max_: float, axis_ind: int):
        shape = self.image_item.image.shape
        scale = np.array(self._scale)
        scale[axis_ind] = (max_ - min_) / shape[axis_ind]
        center = np.array(self._center)
        center[axis_ind] = - min_ / scale[axis_ind]
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
        self.image_item.scale(scale[0], scale[1])
        self.image_item.translate(- center[0], - center[1])
        self._scale = tuple(scale)
        self._center = tuple(center)

    def get_axes(self):
        shape = np.array(self.image_item.image.shape)
        scale = np.array(self._scale)
        min_ = - np.array((self._center[1], self._center[0])) * scale
        max_ = min_ + shape * scale
        return (min_[0], max_[0]), (min_[1], max_[1])


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = CustomImageViewer()
    image = np.random.randint(0, 100, (100, 150))
    window.set_data(image)
    window.set_center((100, 0))
    window.set_scale(0.01)
    window.show()
    sys.exit(app.exec_())
