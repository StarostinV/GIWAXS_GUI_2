import logging
from typing import Dict
from enum import Enum

from PyQt5.QtWidgets import (QWidget, QGridLayout, QPushButton,
                             QLabel, QFrame, QSplitter,
                             QComboBox, QScrollArea,
                             QSizePolicy)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject

from ..roi_widgets.roi_1d_widget import Roi1D
from ..roi_widgets.confidence_level_widget import ConfidenceOptionsList
from ..roi_widgets import AbstractRoiWidget, AbstractRoiHolder
from ...app.fitting import (
    Fit,
    FittingType,
    BackgroundType,
)
from ...app.fitting.fit_holder import FitHolder
from ...app.rois.roi_data import Roi
from ...app import App
from ..tools import get_pen
from ..basic_widgets import (
    Custom1DPlot,
    ParametersSlider,
    LabeledSlider
)


# TODO combine in-place fit and multi-fit (or remove multifit)


class DummyRoiWidget(AbstractRoiWidget):
    def move_roi(self):
        pass

    def send_move(self):
        pass

    def set_color(self, color):
        pass


class RoiFitWidget(AbstractRoiHolder, QWidget):
    def __init__(self, parent=None):
        self.app = App()
        QWidget.__init__(self, parent)
        self._init_ui()
        self.fit_holder = FitHolder()
        AbstractRoiHolder.__init__(self, 'RoiFitWidget')

    @property
    def selected_fit(self):
        return self.fit_holder.fit

    @property
    def selected_roi(self):
        fit = self.selected_fit
        if not fit:
            return
        return fit.roi

    @property
    def selected_key(self):
        roi = self.selected_roi
        if not roi:
            return
        return roi.key

    def _update_data(self):
        self.fit_holder.update_data()
        self._update()

    def _init_ui(self):
        self.fit_plot = FitPlot(self)
        self.sliders_widget = SlidersWidget(parent=self)
        self.next_roi_btn = QPushButton('Next ROI', self)
        self.prev_roi_btn = QPushButton('Previous ROI', self)
        self.fit_current_button = QPushButton(CurrentFitButtonStatus.fit.value, self)
        self.confidence_list = ConfidenceOptionsList('Not set', self, horizontal=True)
        self.update_bounds_btn = QPushButton('Update bounds', self)

        q_scroll_area = QScrollArea(self)
        q_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        q_scroll_area.setWidgetResizable(True)
        q_scroll_area.setGeometry(0, 0, 300, 400)

        options_widget = QWidget(self)
        q_scroll_area.setWidget(options_widget)

        options_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        scroll_layout = QGridLayout(options_widget)

        scroll_layout.addWidget(self.prev_roi_btn, 0, 0)
        scroll_layout.addWidget(self.next_roi_btn, 0, 1)
        scroll_layout.addWidget(self.fit_current_button, 1, 0, 1, 2)
        scroll_layout.addWidget(self.update_bounds_btn, 2, 0, 1, 2)
        scroll_layout.addWidget(self.confidence_list, 3, 0, 1, 2)
        scroll_layout.addWidget(self.sliders_widget, 4, 0, 1, 2)

        q_splitter_h2 = QSplitter(orientation=Qt.Vertical, parent=self)
        q_splitter_h2.addWidget(self.fit_plot)
        q_splitter_h2.addWidget(q_scroll_area)
        q_splitter_h2.setSizes((400, self.height() - 400))

        layout = QGridLayout(self)
        layout.addWidget(q_splitter_h2)

    def _delete_roi_widget(self, roi_widget) -> None:
        self._update()

    def _make_roi_widget(self, roi: Roi) -> AbstractRoiWidget:
        return DummyRoiWidget(roi)

    def _init_connect(self):
        self.app.image_holder.sigPolarImageChanged.connect(self._update_data)
        self.app.image_holder.sigEmptyImage.connect(self._clear)
        self.app.geometry_holder.sigScaleChanged.connect(self._update_data)

        self.app.roi_dict.sig_roi_moved.connect(self._update_move)
        self.app.roi_dict.sig_selected.connect(self._update)
        self.app.roi_dict.sig_one_selected.connect(self._update)
        self.app.roi_dict.sig_fixed.connect(self._fix)
        self.app.roi_dict.sig_unfixed.connect(self._unfix)
        self.app.roi_dict.sigConfLevelChanged.connect(self._change_confidence)

        self.next_roi_btn.clicked.connect(self.app.roi_dict.select_next)
        self.prev_roi_btn.clicked.connect(self.app.roi_dict.select_previous)
        self.fit_current_button.clicked.connect(self._fit_current_clicked)
        self.update_bounds_btn.clicked.connect(self._update_bounds_clicked)
        self.fit_plot.sigRangeUpdated.connect(self._range_changed)
        self.sliders_widget.sigValueChanged.connect(self._sliders_moved)
        self.confidence_list.sigConfidenceChanged.connect(self._confidence_changed)

    def _change_confidence(self):
        if self.selected_fit:
            self.confidence_list.set_level(self.selected_roi.confidence_level)

    def _confidence_changed(self, level: float):
        if self.selected_fit:
            self.app.roi_dict.change_conf_level(self.selected_key, level)

    def _update_bounds_clicked(self):
        fit = self.selected_fit
        if not fit:
            return
        fit = self.fit_holder.set_default_fit(fit.roi)
        self.fit_plot.set_fit(fit)
        self.sliders_widget.set_fit(fit)
        self._emit_move_roi()

    def _sliders_moved(self):
        self.fit_holder.update_fit_data(update_bounds=False)
        self.fit_plot.update_plot()
        self._emit_move_roi()

    def _range_changed(self):
        self.fit_holder.update_fit_data(update_r_range=False)
        self.fit_plot.update_plot(update_range=False)
        self._emit_move_roi()

    def _emit_move_roi(self):
        if self.selected_fit:
            self.app.roi_dict.move_roi(self.selected_roi.key, self._name)

    @pyqtSlot(name='currentFitButtonClicked')
    def _fit_current_clicked(self):
        if self.selected_fit:
            if self.fit_current_button.text() == CurrentFitButtonStatus.fit.value:
                self._fit()
            else:
                self._emit_unfix()

    def _emit_fix(self):
        self.app.roi_dict.fix_roi(self.selected_key)

    def _emit_unfix(self):
        self.app.roi_dict.unfix_roi(self.selected_key)

    def _fit(self):
        if not self.selected_fit:
            return
        self.selected_fit.do_fit()
        self.selected_fit.set_roi_from_params()
        self.fit_plot.update_plot()
        self.sliders_widget.update_values()
        self._emit_move_roi()
        self._emit_fix()

    def _fix(self):
        self.sliders_widget.setEnabled(False)
        self.update_bounds_btn.setEnabled(False)
        self.fit_current_button.setText(CurrentFitButtonStatus.unfix.value)

    def _unfix(self):
        self.sliders_widget.setEnabled(True)
        self.update_bounds_btn.setEnabled(True)
        self.fit_current_button.setText(CurrentFitButtonStatus.fit.value)

    def _update_move(self, keys, name):
        if name != self._name:
            self._update()

    def _update(self):
        selected_rois = self.app.roi_dict.selected_rois

        if len(selected_rois) == 1:
            selected_roi = selected_rois[0]
            key = selected_roi.key
            if key == self.selected_key:
                self.fit_holder.update_fit_data(update_r_range=False)
            else:
                self.fit_holder.new_fit(selected_roi)

            self._set_fit()

        else:
            self._clear()

    def _set_fit(self):
        self.fit_plot.set_fit(self.selected_fit)
        self.sliders_widget.set_fit(self.selected_fit)
        self.confidence_list.set_level(self.selected_roi.confidence_level)
        if self.selected_roi.movable:
            self._unfix()
        else:
            self._fix()

    def _clear(self):
        self.fit_holder.remove_fit()
        self.sliders_widget.remove_fit()
        self.fit_plot.remove_fit()
        self._fix()


# class ControlsWidget(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self._init_ui()
#
#     def _init_ui(self):
#         self.functions_box = QComboBox(self)
#         self.background_box = QComboBox(self)
#
#         self.range_factor_slider = LabeledSlider('Y range factor', (0, 10), parent=self, decimals=2)
#         self.fit_current_button = QPushButton(CurrentFitButtonStatus.fit.value)
#         self.fit_current_button.clicked.connect(self._fit_current_clicked)
#         self.update_data_button = QPushButton('Update fit')
#         self.update_data_button.clicked.connect(self._update_data_button_clicked)
#
#         self.functions_box.currentTextChanged.connect(self._change_function)
#         self.background_box.currentTextChanged.connect(self._change_background)
#         self.range_strategies_box.currentTextChanged.connect(self._change_range_strategy)
#
#         self.functions_box.addItem('Fitting functions')
#         for t in FittingType:
#             self.functions_box.addItem(t.value)
#         self.background_box.addItem('Backgrounds')
#         for t in BackgroundType:
#             self.background_box.addItem(t.value)
#
#     def _connect(self):
#         self.fit_current_button.clicked.connect(self._fit_current_clicked)
#         self.range_factor_slider.valueChanged.connect(self._on_range_slider_moved)


class CurrentFitButtonStatus(Enum):
    fit = 'Fit roi'
    unfix = 'Unfix'


class FitPlot(Custom1DPlot):
    sigRangeUpdated = pyqtSignal()

    log = logging.getLogger(__name__)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.fit: Fit = None
        self.fit_plot = self.plot_item.plot()
        self.profile_plot = self.plot_item.plot()
        self.background_plot = self.plot_item.plot()
        self.fit_plot.setPen(get_pen(color='red', style=Qt.DashDotDotLine, width=4))
        self.background_plot.setPen(get_pen(color='blue', style=Qt.DashDotDotLine, width=4))
        self.profile_plot.setPen(get_pen(color='white', style=Qt.DashDotDotLine, width=2))

        self.range_roi: Roi = Roi(radius=0, width=1, key=-1)
        self.range_widget: Roi1D = Roi1D(self.range_roi, enable_context=False)
        self.range_widget.set_color(QColor(255, 255, 255, 50))

        self.range_widget.sigRoiMoved.connect(self._range_updated)

        self.plot_item.addItem(self.range_widget)

        self.plot_item.setTitle('Fit')
        self.plot_item.getAxis('bottom').setLabel('|Q|', color='white', font_size='large')
        self.plot_item.getAxis('left').setLabel('Intensity', color='white', font_size='large')

    def _update_range(self):
        if not self.fit:
            return
        r1, r2 = self.fit.r_range
        self.range_roi.radius = (r1 + r2) / 2
        self.range_roi.width = r2 - r1
        self.range_widget.move_roi()

    def _range_updated(self):
        r, w = self.range_roi.radius, self.range_roi.width
        self.fit.r_range = r - w / 2, r + w / 2
        self.sigRangeUpdated.emit()

    def set_fit(self, fit: Fit):
        self.fit = fit
        self.update_plot()

    def update_plot(self, update_range: bool = True):
        if not self.fit:
            return
        try:
            self.range_widget.show()
            self.profile_plot.setData(self.fit.x_profile, self.fit.y_profile)
            self.plot.setData(self.fit.x, self.fit.y)
            self.fit_plot.setData(self.fit.x, self.fit.init_curve)
            if self.fit.background_curve is not None:
                self.background_plot.setData(self.fit.x, self.fit.background_curve)
            else:
                self.background_plot.clear()
            if update_range:
                self._update_range()
                self._set_range()

        except Exception as err:
            self.log.exception(err)
            self.clear_plot()

    def _set_range(self, pad: float = 0.4):
        if not self.fit:
            return
        dx = self.fit.x.max() - self.fit.x.min()
        dy = self.fit.y.max() - self.fit.y.min()
        self.plot_item.setRange(
            xRange=[self.fit.x.min() - dx * pad, self.fit.x.max() + dx * pad],
            yRange=[self.fit.y.min() - dy * pad, self.fit.y.max() + dy * pad]
        )

    def remove_fit(self):
        self.fit = None
        self.clear_plot()

    def clear_plot(self):
        self.plot.clear()
        self.fit_plot.clear()
        self.background_plot.clear()
        self.profile_plot.clear()
        self.range_widget.hide()
        self.update()


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

    log = logging.getLogger(__name__)

    def __init__(self, param_names: tuple = (), parent=None):
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
        if self.fit is None:
            self.remove_fit()
            return
        self.set_param_names(fit.param_names)
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
                self._param_labels[i].setText(name)

        if i < len(self.param_names) - 1:
            for j in range(i + 1, len(self.param_names)):
                self._remove_parameter(j)

        self.param_names = param_names

    def update_values(self):
        if not self.fit:
            return
        fit = self.fit
        for idx, (l, i, u) in enumerate(zip(fit.lower_bounds, fit.init_params, fit.upper_bounds)):
            try:
                self._sliders[idx].setValues(l, i, u, new_range=(l, u))
            except ValueError as err:
                self.log.error(f'{self._param_labels[idx].text()} received wrong values.')
                self.log.exception(err)
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
