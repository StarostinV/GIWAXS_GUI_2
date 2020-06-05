# -*- coding: utf-8 -*-
import logging
from enum import Enum

import numpy as np

from PyQt5.QtWidgets import (QMainWindow, QWidget,
                             QFrame, QHBoxLayout,
                             QVBoxLayout, QPushButton,
                             QRadioButton)
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtCore import Qt, pyqtSignal

from pyqtgraph import GraphicsLayoutWidget, LinearRegionItem
from .sliders import AnimatedSlider
from .toolbars import BlackToolBar
from ..basic_widgets import RoundedPushButton
from ..tools import Icon, show_error
from ...app.profiles import BasicProfile

logger = logging.getLogger(__name__)


class Custom1DPlot(GraphicsLayoutWidget):
    def __init__(self, *args, parent=None):
        super().__init__(parent)
        self.plot_item = self.addPlot()
        self.plot_item.setMenuEnabled(False)
        self.plot = self.plot_item.plot(*args)
        self.set_pen()

    def set_data(self, *args):
        self.plot.setData(*args)

    def clear_plot(self):
        self.plot.clear()

    def set_x(self, x):
        x = np.array(x)
        y = self.plot.yData
        if y is None or y.shape != x.shape:
            return
        self.plot.setData(x, y)

    def set_pen(self, width: int = 3, color: str or QColor = 'white'):
        if isinstance(color, str):
            color = QColor(color)
        pen = QPen(color)
        pen.setStyle(Qt.SolidLine)
        pen.setWidth(width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCosmetic(True)
        self.plot.setPen(pen)


class Smooth1DPlot(QMainWindow):
    _MaximumSliderWidth = 200
    _MaximumSliderHeight = 30

    def __init__(self, profile: BasicProfile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.image_view = Custom1DPlot()
        self.setCentralWidget(self.image_view)
        self.__init_toolbars()

        self.profile.sigDataUpdated.connect(self.plot)

    @property
    def x(self):
        return self.profile.x

    @property
    def y(self) -> np.ndarray or None:
        return self.profile.y

    def __init_toolbars(self):
        param_toolbar = BlackToolBar('Parameters', self)
        self.addToolBar(param_toolbar)

        self.__init_sigma_slider(param_toolbar)

    def __init_sigma_slider(self, toolbar):
        sigma_slider = AnimatedSlider('𝞼', (0, 10), self.profile.sigma,
                                      decimals=2)
        sigma_slider.setMaximumWidth(self._MaximumSliderWidth)
        sigma_slider.setMaximumHeight(self._MaximumSliderHeight)
        sigma_slider.valueChanged.connect(self.update_sigma)
        sigma_slider.setStyleSheet('background-color: white;')
        sigma_slider.shadow.setColor(QColor('blue'))
        self.sigma_slider = sigma_slider
        frame = QFrame()
        layout = QHBoxLayout()
        frame.setLayout(layout)
        frame.setGeometry(0, 0, self._MaximumSliderWidth, toolbar.height() * 0.9)
        layout.addWidget(sigma_slider, alignment=Qt.AlignHCenter)
        toolbar.addWidget(frame)

    def set_sigma(self, value: float):
        self.update_sigma(value)
        self.sigma_slider.set_value(value, change_bounds=True)

    def update_sigma(self, value: float):
        self.profile.set_sigma(value)
        self.plot()

    def auto_range(self):
        self.image_view.plot_item.autoRange()

    def plot(self):
        if self.x is not None and self.y is not None:
            self.image_view.set_data(self.x, self.y)
            self.auto_range()

    def clear_plot(self):
        self.image_view.clear_plot()


class PlotBC(Smooth1DPlot):

    def __init__(self, profile: BasicProfile, parent=None):
        super().__init__(profile, parent)
        self._status = BaseLineStatus.no_baseline
        self._baseline_setup_widget = None
        self.baseline_plot = None
        self.__init_roi()
        self.profile.sigDataToBeUpdated.connect(self._clear_baseline)

    @property
    def y(self):
        if self._status == BaseLineStatus.baseline_subtracted:
            return self.profile.y - self.profile.baseline
        else:
            return self.profile.y

    def update_data(self):
        self.profile.update()

    def is_shown(self, shown: bool):
        self.profile.is_shown = shown

    def __init_toolbars(self):
        super().__init_toolbars()

        baseline_toolbar = BlackToolBar('Baseline Correction')
        self.addToolBar(baseline_toolbar)

        baseline_button = RoundedPushButton(parent=baseline_toolbar, icon=Icon('baseline'),
                                            radius=30)
        baseline_button.clicked.connect(self.open_baseline_setup)
        baseline_toolbar.addWidget(baseline_button)

    def __init_roi(self):
        self._roi = LinearRegionItem()
        self._roi.hide()
        self._roi.setBrush(QColor(255, 255, 255, 50))
        self.image_view.plot_item.addItem(self.roi)

    def open_baseline_setup(self):
        if self.y is None:
            return
        self._baseline_setup_widget = setup = BaseLineSetup(
            self._status, **self.profile.get_parameters())
        if self.profile.x_range is None:
            self._set_default_bounds()

        setup.calculate_signal.connect(self._on_calculate_baseline)
        setup.subtract_signal.connect(self._on_subtracting_baseline)
        setup.restore_signal.connect(self._on_restoring_data)
        setup.close_signal.connect(self._on_closing_setup)
        setup.show()
        self.roi.show()

    def _set_default_bounds(self):
        if self.x is None:
            self.profile.x_range = (0, 1)
        else:
            self.profile.x_range = (self.x.min(), self.x.max())

    def _update_bounds(self):
        self.profile.x_range = self.roi.getRegion()

    def _set_status(self, status: 'BaseLineStatus'):
        self._status = status
        if self._baseline_setup_widget:
            self._baseline_setup_widget.set_status(status)

    def _on_calculate_baseline(self, params: dict):
        self.profile.set_parameters(**params)
        self.update_bounds()
        try:
            self.profile.update_baseline()
        except Exception as err:
            logger.exception(err)
            show_error('Failed calculating baseline. Change roi region or parameters and try again.',
                       'Baseline calculation error')
            return
        self._set_status(BaseLineStatus.baseline_calculated)
        self._plot_baseline()

    def _on_subtracting_baseline(self):
        self._remove_baseline_from_plot()
        self._set_status(BaseLineStatus.baseline_subtracted)
        self.plot()

    def _on_restoring_data(self):
        self._set_status(BaseLineStatus.baseline_restored)
        self._plot_baseline()
        self.plot()

    def _on_closing_setup(self):
        self._baseline_setup_widget = None
        self.roi.hide()
        if (self.status == BaseLineStatus.baseline_calculated or
                self.status == BaseLineStatus.baseline_restored):
            self._clear_baseline()

    def _plot_baseline(self):
        if not self.baseline_plot:
            self.baseline_plot = self.image_view.plot_item.plot()

        self.baseline_plot.setData(self.x, self.profile.baseline, pen=self._get_baseline_pen())

    @staticmethod
    def _get_baseline_pen():
        pen = QPen(QColor('red'))
        pen.setStyle(Qt.DashDotLine)
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCosmetic(True)
        return pen

    def _remove_baseline_from_plot(self):
        if self.baseline_plot:
            self.image_view.plot_item.removeItem(self.baseline_plot)
            self.baseline_plot = None

    def _clear_baseline(self):
        self._set_status(BaseLineStatus.no_baseline)
        self._remove_baseline_from_plot()


class BaseLineStatus(Enum):
    no_baseline = 1
    baseline_calculated = 2
    baseline_restored = 3
    baseline_subtracted = 4


class BaseLineSetup(QWidget):
    calculate_signal = pyqtSignal(dict)
    subtract_signal = pyqtSignal()
    restore_signal = pyqtSignal()
    close_signal = pyqtSignal()

    def __init__(self, status: BaseLineStatus, smoothness: float, asymmetry: float):
        super().__init__()
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(self.NAME)
        self.setWindowIcon(Icon('baseline'))
        self._status = None
        self.__init_ui(smoothness, asymmetry)
        self.set_status(status)

    def __init_ui(self, smoothness: float, asymmetry: float):
        layout = QVBoxLayout(self)

        self.smoothness_slider = AnimatedSlider('Smoothness parameter', (1e2, 1e4), smoothness,
                                                self, Qt.Horizontal, disable_changing_status=True, decimals=3)

        self.asymmetry_slider = AnimatedSlider('Asymmetry parameter', (0.001, 0.1), asymmetry,
                                               self, Qt.Horizontal, disable_changing_status=True, decimals=3)

        self.save_params_box = QRadioButton('Save as default')
        self.save_params_box.setChecked(True)
        self.calculate_button = QPushButton('Calculate baseline')
        self.calculate_button.clicked.connect(self.emit_calculate)
        self.subtract_button = QPushButton('Subtract baseline')
        self.subtract_button.clicked.connect(self.subtract_signal.emit)
        self.restore_button = QPushButton('Restore line')
        self.restore_button.clicked.connect(self.restore_signal.emit)

        layout.addWidget(self.smoothness_slider)
        layout.addWidget(self.asymmetry_slider)
        layout.addWidget(self.save_params_box)
        layout.addWidget(self.calculate_button)
        layout.addWidget(self.subtract_button)
        layout.addWidget(self.restore_button)

    def set_status(self, status: BaseLineStatus):
        if status == BaseLineStatus.no_baseline:
            self.calculate_button.setEnabled(True)
            self.subtract_button.setEnabled(False)
            self.restore_button.setEnabled(False)
        elif status == BaseLineStatus.baseline_calculated:
            self.subtract_button.setEnabled(True)
            self.restore_button.setEnabled(False)
            self.calculate_button.setEnabled(True)
        elif status == BaseLineStatus.baseline_subtracted:
            self.subtract_button.setEnabled(False)
            self.restore_button.setEnabled(True)
            self.calculate_button.setEnabled(False)
        elif status == BaseLineStatus.baseline_restored:
            self.subtract_button.setEnabled(True)
            self.restore_button.setEnabled(False)
            self.calculate_button.setEnabled(True)
        else:
            logger.error(f'Unknown status {status}')
            return
        self._status = status

    def get_params_dict(self):
        return dict(smoothness_param=self.smoothness_slider.value,
                    asymmetry_param=self.asymmetry_slider.value)

    def emit_calculate(self):
        self.calculate_signal.emit(self.get_params_dict())

    def closeEvent(self, a0) -> None:
        # if self.save_params_box.isChecked():
        #     save_config(self.NAME, self.get_params_dict())
        self.close_signal.emit()
        super().closeEvent(a0)
