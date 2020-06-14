# -*- coding: utf-8 -*-
import logging
from typing import List, Dict, Iterable, Union
from enum import Enum, auto

from PyQt5.QtWidgets import (QWidget, QGridLayout, QPushButton,
                             QLabel, QFrame, QSplitter, QMenu)
from PyQt5.QtGui import QPen, QColor, QCursor
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from ..roi_widgets.roi_2d_rect_widget import Roi2DRect
from ..roi_widgets.roi_1d_widget import Roi1D

from ...app.fitting import Fit, FitObject
from ...app.rois.roi_data import Roi, RoiTypes
from ...app import App
from ..tools import center_widget, Icon
from ..basic_widgets import Custom1DPlot, CustomImageViewer, ParametersSlider
from .multi_fit import MultiFitWindow


class MoveSource(Enum):
    polar_roi = auto()
    sliders = auto()
    radial_viewer = auto()


class FitWidget(QWidget):
    sigFitApplied = pyqtSignal(object)

    def __init__(self, fit_object: FitObject, parent=None):
        super().__init__(parent=parent)
        self.setGeometry(0, 0, 1500, 700)
        self.setWindowTitle('Fitting parameters')
        self.setWindowIcon(Icon('fit'))
        self.setWindowFlag(Qt.Window, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.WindowModal)
        self.fit_object: FitObject = fit_object
        self._selected_fit: Fit = None
        self._rect_widgets: dict = {}
        self._init_ui()

        if self.fit_object:
            self._update_data()
            self._update_roi_widgets()

        self._fitted: bool = False
        center_widget(self)
        self.setWindowState(Qt.WindowMaximized)

        if App().debug_tracker:
            App().debug_tracker.add_object(self)

        self.show()

    def _init_ui(self):
        layout = QGridLayout(self)

        self.polar_viewer = CustomImageViewer(parent=self)
        self.radial_viewer = RadialFitWidget(parent=self)
        self.fit_plot = FitPlot(parent=self)
        self.sliders_widget = SlidersWidget(self.fit_object.PARAM_NAMES, self)
        self.fit_button = QPushButton('Fit')
        self.apply_button = QPushButton('Apply')
        self.multi_fit_window: MultiFitWindow = MultiFitWindow(self.fit_object, self)

        self.multi_fit_window.sigFitUpdated.connect(self.set_fit)
        self.multi_fit_window.sigClosed.connect(self._close_multi_fit)
        self.fit_button.clicked.connect(self._fit_clicked)
        self.apply_button.clicked.connect(self._apply)
        self.radial_viewer.sigUpdateFit.connect(self._radial_roi_moved)
        self.sliders_widget.sigValueChanged.connect(self._sliders_changed)

        q_splitter_v = QSplitter(orientation=Qt.Horizontal, parent=self)

        q_splitter_h1 = QSplitter(orientation=Qt.Vertical, parent=self)
        q_splitter_h2 = QSplitter(orientation=Qt.Vertical, parent=self)

        q_splitter_v.addWidget(self.multi_fit_window)
        q_splitter_v.addWidget(q_splitter_h1)
        q_splitter_v.addWidget(q_splitter_h2)

        q_splitter_h1.addWidget(self.polar_viewer)
        q_splitter_h1.addWidget(self.radial_viewer)
        q_splitter_h2.addWidget(self.fit_plot)
        q_splitter_h2.addWidget(self.sliders_widget)

        q_splitter_v.setSizes((300, 600, self.width() - 900))
        q_splitter_h1.setSizes((400, self.height() - 400))
        q_splitter_h2.setSizes((400, self.height() - 400))
        layout.addWidget(q_splitter_v, 0, 0, 2, 2)

        layout.addWidget(self.fit_button, 2, 0)
        layout.addWidget(self.apply_button, 2, 1)

    @pyqtSlot(name='closeMultiFit')
    def _close_multi_fit(self):
        self.multi_fit_window = None

    @pyqtSlot(object, name='setFit')
    def set_fit(self, fit_object: FitObject):
        self.fit_object = fit_object

        selected_fit = self.fit_object.fits.get(self.selected_key, None)
        self._selected_fit = None
        self.sliders_widget.set_param_names(fit_object.PARAM_NAMES)
        self._update_data()
        self._update_roi_widgets()

        if selected_fit:
            self._roi_selected(selected_fit.roi.key)
        else:
            self.fit_plot.remove_fit()
            self.radial_viewer.remove_fit()
            self.sliders_widget.remove_fit()

    def _update_data(self):
        self.polar_viewer.set_data(self.fit_object.polar_image)
        self.polar_viewer.set_x_axis(self.fit_object.r_axis.min(), self.fit_object.r_axis.max())
        self.polar_viewer.set_y_axis(self.fit_object.phi_axis.min(), self.fit_object.phi_axis.max())
        self.polar_viewer.view_box.setAspectLocked(True, self.fit_object.aspect_ratio)
        self.polar_viewer.set_auto_range()
        self.radial_viewer.set_data(self.fit_object.r_axis, self.fit_object.r_profile)

    def _update_roi_widgets(self):
        for fit in self.fit_object.fits.values():
            roi = fit.roi
            if roi.key in self._rect_widgets:
                self._rect_widgets[roi.key].set_roi(roi)
            else:
                rect_widget = Roi2DRect(roi, context_menu=self._rect_context)
                rect_widget.sigSelected.connect(self._roi_selected)
                rect_widget.sigRoiMoved.connect(self._roi_moved)
                self.polar_viewer.image_plot.addItem(rect_widget)
                self._rect_widgets[roi.key] = rect_widget
            if fit.fitted_params:
                self._fix(fit.roi)

        keys = list(self.fit_object.fits.keys())
        for key in list(self._rect_widgets.keys()):
            if key not in keys:
                widget = self._rect_widgets.pop(key)
                self.polar_viewer.image_plot.removeItem(widget)
                # widget.deleteLater()

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
        del self.fit_object.fits[roi.key]
        self.polar_viewer.image_plot.removeItem(self._rect_widgets.pop(roi.key))
        self.multi_fit_window.delete_roi(roi)

    @property
    def selected_key(self):
        return self._selected_fit.roi.key if self._selected_fit else None

    @pyqtSlot(name='updateFit')
    def _radial_roi_moved(self):
        self._basic_update(MoveSource.radial_viewer)

    def _basic_update(self, source: MoveSource):
        if source == MoveSource.polar_roi:
            self.fit_object.update_r_range(self._selected_fit)

        if source != MoveSource.sliders:
            self.fit_object.update_fit(self._selected_fit, update_bounds=True)
            self.sliders_widget.update_values()
        else:
            self.fit_object.update_fit(self._selected_fit, update_bounds=False)

        if source != MoveSource.polar_roi:
            self._rect_widgets[self.selected_key].move_roi()

        if source != MoveSource.radial_viewer:
            self.radial_viewer.update_roi()

        self.fit_plot.update_plot()
        self.multi_fit_window.update_fit(self._selected_fit)

    @pyqtSlot(int, name='roiMoved')
    def _roi_moved(self, key: int):
        if key != self.selected_key:
            self._roi_selected(key)
        roi = self._selected_fit.roi
        if roi.type == RoiTypes.ring and (roi.angle, roi.angle_std) != self.fit_object.bounds:
            roi.type = RoiTypes.segment

        self._basic_update(MoveSource.polar_roi)

    @pyqtSlot(name='slidersMoved')
    def _sliders_changed(self):
        self._basic_update(MoveSource.sliders)

    @pyqtSlot(name='apply')
    def _apply(self):
        self.sigFitApplied.emit(self.fit_object)
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
            fits = (self.fit_object.fits[roi.key],)
        elif roi:
            fits = (self.fit_object.fits[key] for key in roi)
        else:
            fits = self.fit_object.fits.values()

        keys_to_fix: List[int] = []

        for fit in fits:
            self.fit_object.do_fit(fit)
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
            self._selected_fit = self.fit_object.fits[key]
            self._select_roi(self._selected_fit.roi, True)
            self._add_selected_fit()

    def _add_selected_fit(self):
        self.radial_viewer.set_fit(self._selected_fit)
        self.fit_plot.set_fit(self._selected_fit)
        self.sliders_widget.set_fit(self._selected_fit)

    def _select_roi(self, roi: Roi, active: bool):
        roi.active = active
        self._rect_widgets[roi.key].update_color()

    def closeEvent(self, a0) -> None:
        self.multi_fit_window.close_widget()
        super().closeEvent(a0)


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

    def __init__(self, param_names: tuple, parent=None):
        super().__init__(parent=parent)
        self.fit: Fit = None
        self.param_names = param_names

        self._sliders: Dict[int, ParametersSlider] = {}
        self._labels: Dict[int, QLabel] = {}
        self._param_labels: Dict[int, QLabel] = {}

        self._init_ui()

    def _init_ui(self):
        self._layout = QGridLayout(self)

        for i, param_name in enumerate(self.param_names):
            self._add_parameter(i, param_name)

    def set_fit(self, fit: Fit):
        self.fit = fit
        self.update_values()

    def _add_parameter(self, i: int, param_name: str):
        self._param_labels[i] = pl = QLabel(param_name)
        self._sliders[i] = sl = ParametersSlider()
        self._labels[i] = ll = QLabel(self.DEFAULT_LABEL)
        self._layout.addWidget(pl, i, 0, alignment=Qt.AlignCenter)
        self._layout.addWidget(SliderWithLabels(sl, ll, self), i, 1)
        sl.sigLowerValueChanged.connect(lambda x, idx=i: self._send_value(x, 0, idx))
        sl.sigMiddleValueChanged.connect(lambda x, idx=i: self._send_value(x, 1, idx))
        sl.sigUpperValueChanged.connect(lambda x, idx=i: self._send_value(x, 2, idx))

        if App().debug_tracker:
            App().debug_tracker.add_object(pl)
            App().debug_tracker.add_object(sl)
            App().debug_tracker.add_object(ll)

    def _remove_parameter(self, i: int):
        pl = self._param_labels.pop(i)
        sl = self._sliders.pop(i)
        ll = self._labels.pop(i)
        self._layout.removeWidget(pl)
        self._layout.removeWidget(sl)
        self._layout.removeWidget(ll)
        pl.deleteLater()
        sl.deleteLater()
        ll.deleteLater()

    def set_param_names(self, param_names: tuple):
        if param_names == self.param_names:
            return
        i = 0
        for i, name in enumerate(param_names):
            if i == len(self._param_labels):
                self._add_parameter(i, name)
            else:
                self._param_labels[i].setTest(name)
        if i < len(self.param_names) - 1:
            for j in range(i + 1, len(self.param_names)):
                self._remove_parameter(j)

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
        self.plot_item.autoRange()

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
            self.roi_widget.deleteLater()
            self.range_widget.deleteLater()

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
