# -*- coding: utf-8 -*-
import logging
from typing import List, Dict, Iterable, Union

from PyQt5.QtWidgets import (QWidget, QGridLayout, QPushButton,
                             QLabel, QFrame, QSplitter, QMenu)
from PyQt5.QtGui import QPen, QColor, QCursor
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from .roi_widgets.roi_2d_rect_widget import Roi2DRect
from .roi_widgets.roi_1d_widget import Roi1D

from .basic_widgets import Custom1DPlot, CustomImageViewer, ParametersSlider
from ..app.fitting import Fit, GaussianFit
from ..app.rois.roi_data import RoiData, Roi, RoiTypes
from .tools import center_widget, Icon


class FitWidget(QWidget):

    sigFitApplied = pyqtSignal(object)

    def __init__(self, gaussian_fit: GaussianFit, parent=None):
        super().__init__(parent=parent)
        self.setGeometry(0, 0, 1200, 700)
        self.setWindowTitle('Fitting parameters')
        self.setWindowIcon(Icon('fit'))
        self.g_fit: GaussianFit = gaussian_fit
        self.rois: List[Roi] = [fit.roi for fit in self.g_fit.fits.values()]
        self.roi_data = RoiData(self.rois)
        self._selected_fit: Fit = None
        self._rect_widgets: dict = {}
        self._init_ui()
        self._fitted: bool = False
        center_widget(self)
        self.show()

    def _init_ui(self):
        layout = QGridLayout(self)

        self.polar_viewer = CustomImageViewer(parent=self)
        self.radial_viewer = RadialFitWidget(parent=self)
        self.fit_plot = FitPlot(parent=self)
        self.sliders_widget = SlidersWidget(self.g_fit.PARAM_NAMES, self)
        self.fit_button = QPushButton('Fit')
        self.fit_button.clicked.connect(self._fit_clicked)
        self.apply_button = QPushButton('Apply')
        self.apply_button.clicked.connect(self._apply)

        self.polar_viewer.set_data(self.g_fit.polar_image)
        self.polar_viewer.set_x_axis(self.g_fit.r_axis.min(), self.g_fit.r_axis.max())
        self.polar_viewer.set_y_axis(self.g_fit.phi_axis.min(), self.g_fit.phi_axis.max())
        self.polar_viewer.view_box.setAspectLocked(True, self.g_fit.aspect_ratio)
        self.polar_viewer.set_auto_range()
        self.radial_viewer.set_data(self.g_fit.r_axis, self.g_fit.r_profile)
        self.radial_viewer.sigUpdateFit.connect(self._update_fit)
        self.sliders_widget.sigValueChanged.connect(self._sliders_changed)

        for roi in self.rois:
            rect_widget = Roi2DRect(roi, context_menu=self._rect_context)
            rect_widget.sigSelected.connect(self._roi_selected)
            rect_widget.sigRoiMoved.connect(self._roi_moved)
            self.polar_viewer.image_plot.addItem(rect_widget)
            self._rect_widgets[roi.key] = rect_widget

        q_splitter_v = QSplitter(orientation=Qt.Horizontal, parent=self)
        q_splitter_h1 = QSplitter(orientation=Qt.Vertical, parent=self)
        q_splitter_h2 = QSplitter(orientation=Qt.Vertical, parent=self)
        q_splitter_v.addWidget(q_splitter_h1)
        q_splitter_v.addWidget(q_splitter_h2)

        q_splitter_h1.addWidget(self.polar_viewer)
        q_splitter_h1.addWidget(self.radial_viewer)
        q_splitter_h2.addWidget(self.fit_plot)
        q_splitter_h2.addWidget(self.sliders_widget)

        q_splitter_v.setSizes((800, self.width() - 800))
        q_splitter_h1.setSizes((400, self.height() - 400))
        q_splitter_h2.setSizes((400, self.height() - 400))
        layout.addWidget(q_splitter_v, 0, 0, 2, 2)

        layout.addWidget(self.fit_button, 2, 0)
        layout.addWidget(self.apply_button, 2, 1)

    def _rect_context(self, roi: Roi):
        menu = QMenu()
        menu.addAction('Delete', lambda *x, r=roi: self._delete_roi(roi))
        if roi.movable:
            menu.addAction('Fix', lambda *x, r=roi: self._fix(roi))
            menu.addAction('Fit', lambda *x, r=roi: self._fit(roi))
        else:
            menu.addAction('Unfix', lambda *x, r=roi: self._unfix(roi))
        menu.exec_(QCursor.pos())

    def _delete_roi(self, roi: Roi):
        if roi.key == self.selected_key:
            self.fit_plot.remove_fit()
            self.radial_viewer.remove_fit()
            self.sliders_widget.remove_fit()
            self._selected_fit = None
        del self.g_fit.fits[roi.key]
        self.rois.remove(roi)
        self.polar_viewer.image_plot.removeItem(self._rect_widgets[roi.key])

    @property
    def selected_key(self):
        return self._selected_fit.roi.key if self._selected_fit else None

    @pyqtSlot(name='updateFit')
    def _update_fit(self):
        self.g_fit.update_fit(self._selected_fit)
        self._rect_widgets[self.selected_key].move_roi()
        self.fit_plot.update_plot()
        self.sliders_widget.update_values()

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
        self.sliders_widget.update_values()

    @pyqtSlot(name='slidersMoved')
    def _sliders_changed(self):
        self.g_fit.update_fit(self._selected_fit, update_bounds=False)
        self._rect_widgets[self.selected_key].move_roi()
        self.fit_plot.update_plot()
        self.radial_viewer.update_roi()

    @pyqtSlot(name='apply')
    def _apply(self):
        self.sigFitApplied.emit(self.g_fit)
        self.close()

    @pyqtSlot(name='fitButtonClicked')
    def _fit_clicked(self):
        if not self._fitted:
            self._fit()
            self._fitted = True
            self.fit_button.setText('Unfix')
        else:
            self._unfix()
            self._fitted = False
            self.fit_button.setText('Fit')

    def _unfix(self, roi: Union[Roi, Iterable[int]] = None):
        if isinstance(roi, Roi):
            widgets = (self._rect_widgets[roi.key],)
        elif roi:
            widgets = (self._rect_widgets[key] for key in roi)
        else:
            widgets = self._rect_widgets.values()

        for widget in widgets:
            roi = widget.roi
            roi.active = False
            roi.movable = True
            roi.fitted_parameters = None
            widget.unfix()
            if roi.key == self.selected_key:
                self.radial_viewer.roi_widget.unfix()

        # self.radial_viewer.update_roi()
        # self.fit_plot.update_plot()
        # self.sliders_widget.update_values()

    def _fix(self, roi: Union[Roi, Iterable[int]] = None):
        if isinstance(roi, Roi):
            widgets = (self._rect_widgets[roi.key],)
        elif roi:
            widgets = (self._rect_widgets[key] for key in roi)
        else:
            widgets = self._rect_widgets.values()

        for widget in widgets:
            roi = widget.roi
            roi.active = False
            roi.movable = False
            widget.fix()
            if roi.key == self.selected_key:
                self.radial_viewer.roi_widget.fix()

        # self.radial_viewer.update_roi()
        # self.fit_plot.update_plot()
        # self.sliders_widget.update_values()

    def _fit(self, roi: Union[Roi, Iterable[int]] = None):
        if isinstance(roi, Roi):
            fits = (self.g_fit.fits[roi.key], )
        elif roi:
            fits = (self.g_fit.fits[key] for key in roi)
        else:
            fits = self.g_fit.fits.values()

        keys_to_fix: List[int] = []

        for fit in fits:
            self.g_fit.do_fit(fit)
            roi_ = fit.roi
            key = roi_.key
            roi_.active = False
            if fit.fitted_params:
                keys_to_fix.append(key)

            if key == self.selected_key:
                self.fit_plot.update_plot()
                self.radial_viewer.update_roi()
                self.sliders_widget.update_values()

        self._fix(keys_to_fix)

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
        self.sliders_widget.set_fit(self._selected_fit)

    def _select_roi(self, roi: Roi, active: bool):
        roi.active = active
        self._rect_widgets[roi.key].update_color()
        self.radial_viewer.plot_item.autoRange()


class SliderWithLabels(QFrame):
    def __init__(self, slider: ParametersSlider, label: QLabel, parent=None):
        super().__init__(parent=parent)
        self.slider = slider
        self.label = label
        self._init_ui()

    def _init_ui(self):
        layout = QGridLayout(self)
        layout.addWidget(self.label, 0, 0, alignment=Qt.AlignHCenter)
        layout.addWidget(self.slider, 1, 0)


class SlidersWidget(QWidget):
    sigValueChanged = pyqtSignal()
    DEFAULT_LABEL = 'lower bound; init value; upper bound'

    def __init__(self, param_names: Iterable[str], parent=None):
        super().__init__(parent=parent)
        self.fit: Fit = None
        self._init_ui(param_names)

    def _init_ui(self, param_names):
        layout = QGridLayout(self)

        self._sliders: Dict[int, ParametersSlider] = {}
        self._labels: Dict[int, QLabel] = {}

        for i, param_name in enumerate(param_names):
            layout.addWidget(QLabel(param_name), i, 0, alignment=Qt.AlignCenter)
            self._sliders[i] = sl = ParametersSlider()
            self._labels[i] = ll = QLabel(self.DEFAULT_LABEL)
            layout.addWidget(SliderWithLabels(sl, ll, self), i, 1)
            sl.sigLowerValueChanged.connect(lambda x, idx=i: self._send_value(x, 0, idx))
            sl.sigMiddleValueChanged.connect(lambda x, idx=i: self._send_value(x, 1, idx))
            sl.sigUpperValueChanged.connect(lambda x, idx=i: self._send_value(x, 2, idx))

    def set_fit(self, fit: Fit):
        self.fit = fit
        self.update_values()

    def update_values(self):
        if not self.fit:
            return
        fit = self.fit
        for idx, (l, i, u) in enumerate(zip(fit.lower_bounds, fit.init_params, fit.upper_bounds)):
            self._sliders[idx].setValues(l, i, u, new_range=(l, u))
            self._update_label(idx, l, i, u)

    def _update_label(self, idx: int, l: float, i: float, u: float):
        self._labels[idx].setText(f'lower bound = {l:0.3f}; init value = {i:0.3f}; upper bound = {u:0.3f}')

    def _send_value(self, value: float, place: int, idx: int):
        if not self.fit:
            return
        if place == 0:
            params = self.fit.lower_bounds
        elif place == 1:
            params = self.fit.init_params
        else:
            params = self.fit.upper_bounds
        params[idx] = value

        self._update_label(
            idx, self.fit.lower_bounds[idx], self.fit.init_params[idx], self.fit.upper_bounds[idx])

        self.sigValueChanged.emit()

    def remove_fit(self):
        self.fit = None
        for l in self._labels.values():
            l.setText(self.DEFAULT_LABEL)


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
        self.roi_widget = Roi1D(fit.roi, enable_context=False)
        r1, r2 = fit.r_range

        self.range_roi = Roi(radius=(r1 + r2) / 2, width=r2 - r1, key=-1)
        self.range_widget = Roi1D(self.range_roi, enable_context=False)
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
        try:
            self.plot.setData(self.fit.x, self.fit.y)
            self.fit_plot.setData(self.fit.x, self.fit.init_curve)
            self.plot_item.autoRange()

        except Exception as err:
            self.log.exception(err)
            self.clear_plot()

    def remove_fit(self):
        self.fit = None
        self.clear_plot()

    def clear_plot(self):
        self.plot.clear()
        self.fit_plot.clear()

    @staticmethod
    def _get_fit_pen():
        pen = QPen(QColor('red'))
        pen.setStyle(Qt.DashDotLine)
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCosmetic(True)
        return pen
