import logging
from enum import Enum
from typing import Dict, List, Tuple
from time import sleep

from PyQt5.QtCore import (QObject, pyqtSlot, pyqtSignal,
                          QCoreApplication, Qt, QThread)
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                             QProgressBar, QSlider, QLabel)
from PyQt5.QtGui import QColor, QPen

from pyqtgraph import GraphicsLayoutWidget, FillBetweenItem, InfiniteLine

from ...app import App, Roi
from ...app.file_manager import ImageKey, FolderKey
from ...app.fitting import FitObject, Fit
from ..tools import center_widget, Icon

logger = logging.getLogger(__name__)


class ButtonStates(Enum):
    start = 'Start fit'
    pause = 'Pause fit'
    resume = 'Resume fit here'
    finished = 'Fit is finished'


class MultiFit(QObject):
    sigFit = pyqtSignal(object)
    sigPaused = pyqtSignal()
    # sigError = pyqtSignal(object)
    sigFinished = pyqtSignal()

    log = logging.getLogger(__name__)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.sleep_time: float = 0.
        self._paused: bool = False
        self._stopped: bool = False

    @pyqtSlot(object, name='runFit')
    def run(self, fit_obj: FitObject):
        self._paused = False

        while fit_obj and fit_obj.fits and not self._paused:
            self.log.info(f'Fitting image {fit_obj.image_key}')
            for fit in fit_obj.fits.values():
                try:
                    fit_obj.do_fit(fit)
                except Exception as err:
                    self.log.exception(err)

                fit.roi.movable = True

                if self.sleep_time:
                    sleep(self.sleep_time)

                QCoreApplication.processEvents()

                if self._paused:
                    self.log.debug('Paused!')
                    break

            if self._paused:
                break

            new_fit_obj = get_new_fit(fit_obj, add_fits=True)
            self.sigFit.emit(fit_obj)
            fit_obj = new_fit_obj

        if self._stopped:
            self.deleteLater()
        elif self._paused:
            self.sigPaused.emit()
        else:
            self.sigFinished.emit()

    @pyqtSlot(name='pauseFit')
    def pause(self):
        self.log.debug('Pause signal received')
        self._paused = True

    @pyqtSlot(name='stopFit')
    def stop(self):
        self.log.debug('Stop signal received')
        self._paused = True
        self._stopped = True


def get_new_fit(fit_object: FitObject,
                add_fits: bool = False, new_image_key: ImageKey = None):
    folder_key: FolderKey = fit_object.image_key.parent
    if not folder_key:
        logger.debug('empty folder key')
        return

    if not new_image_key:
        new_image_key: ImageKey = folder_key.get_next_image(fit_object.image_key)
    if not new_image_key:
        logger.debug('empty next image_key')
        return
    image, polar_image, geometry = App().image_holder.get_data_by_key(new_image_key, save=True)
    if polar_image is None:
        logger.debug('empty polar_image')
        return
    new_fit_object: FitObject = fit_object.__class__(
        new_image_key, polar_image, geometry.r_axis, geometry.phi_axis)

    if add_fits:
        for fit in fit_object.fits.values():
            if fit.fitted_params:
                new_fit_object.add(fit.roi)

    return new_fit_object


class MultiFitWindow(QWidget):
    sigPauseFit = pyqtSignal()
    sigDeleteFit = pyqtSignal()
    sigRunFit = pyqtSignal(object)
    sigClosed = pyqtSignal()
    sigFitUpdated = pyqtSignal(object)

    log = logging.getLogger(__name__)

    def __init__(self, fit_object: FitObject, parent=None):
        super().__init__(parent=parent)
        self.current_fit: FitObject = fit_object
        self.fm = App().fm.fits.get_multi_fit()

        self.setGeometry(0, 0, 1200, 700)
        center_widget(self)
        self.setWindowTitle('Fitting parameters')
        self.setWindowIcon(Icon('fit'))
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        # self.setWindowFlag(Qt.Window, True)

        self.fit_thread = QThread()
        self.multi_fit = MultiFit()
        self.multi_fit.moveToThread(self.fit_thread)

        self.multi_fit.sigPaused.connect(self.on_paused)
        self.multi_fit.sigFinished.connect(self.on_finished)
        self.multi_fit.sigFit.connect(self._update_fit)

        self.sigRunFit.connect(self.multi_fit.run)
        self.sigPauseFit.connect(self.multi_fit.pause)
        self.sigDeleteFit.connect(self.multi_fit.stop)

        self.fit_thread.finished.connect(self.multi_fit.deleteLater)
        self.fit_thread.finished.connect(self.fit_thread.deleteLater)

        self._init_ui()
        self.fit_thread.start()

        self.plot_params.add_fit(fit_object)

        if App().debug_tracker:
            App().debug_tracker.add_object(self)
            App().debug_tracker.add_object(self.multi_fit)
            App().debug_tracker.add_object(self.fit_thread)

        self.show()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.plot_params = MultiFitPlot(self)
        self.progress_widget = ProgressWidget(self.current_fit.image_key, self)
        self.control_button = QPushButton(ButtonStates.start.value)
        layout.addWidget(self.plot_params)
        layout.addWidget(self.progress_widget)
        layout.addWidget(self.control_button)

        self.control_button.clicked.connect(self._on_button_clicked)
        self.progress_widget.sigImageChanged.connect(self._change_image)

    @pyqtSlot(name='controlButtonClicked')
    def _on_button_clicked(self):
        self.log.debug('Button clicked')
        if self.control_button.text() == ButtonStates.start.value:
            self._start_fit()
        elif self.control_button.text() == ButtonStates.pause.value:
            self.log.debug('Emitting pause signal')
            self.sigPauseFit.emit()
        elif self.control_button.text() == ButtonStates.resume.value:
            self._start_fit()

    @pyqtSlot(object, name='changeImage')
    def _change_image(self, key: ImageKey):
        if key == self.current_fit.image_key:
            return

        self.save_current_fit()
        self.current_fit = self.fm[key] or get_new_fit(
            self.current_fit, new_image_key=key)
        self.plot_params.change_image(key)

        if (self.control_button.text() == ButtonStates.finished.value and
                key.idx + 1 < key.parent.images_num):

            self.control_button.setText(ButtonStates.resume.value)

        self.sigFitUpdated.emit(self.current_fit)

    def save_current_fit(self):
        if self.current_fit:
            self.fm[self.current_fit.image_key] = self.current_fit

    def update_fit(self, fit: Fit):
        if self.current_fit:
            self.plot_params.update_roi(fit, self.current_fit.image_key.idx)

    def delete_roi(self, roi: Roi):
        if self.current_fit:
            self.plot_params.delete_roi(roi, self.current_fit.image_key.idx)

    @pyqtSlot(name='fitPaused')
    def on_paused(self):
        self.control_button.setText(ButtonStates.resume.value)
        self.progress_widget.set_fixed(False)

    def _start_fit(self):
        self.control_button.setText(ButtonStates.pause.value)
        self.progress_widget.set_fixed(True)
        self.sigRunFit.emit(self.current_fit)

    @pyqtSlot(name='fitFinished')
    def on_finished(self):
        self.control_button.setText(ButtonStates.finished.value)
        self.progress_widget.set_fixed(False)
        # self.control_button.setDisabled(True)

    @pyqtSlot(object, name='updateFit')
    def _update_fit(self, fit_object: FitObject or None):
        self.log.debug('Updating fit ...')
        self.plot_params.add_fit(fit_object)
        self.current_fit = fit_object

        self.save_current_fit()

        self.progress_widget.change_image(fit_object.image_key)
        self.sigFitUpdated.emit(fit_object)

    def close_widget(self) -> None:
        self.log.debug(f'Closing multi fit object...')
        self.fm.delete()
        self.sigDeleteFit.emit()
        if self.fit_thread.isRunning():
            self.fit_thread.quit()
            self.fit_thread.wait()

        self.sigClosed.emit()
        self.deleteLater()


class MultiFitPlot(GraphicsLayoutWidget):
    log = logging.getLogger(__name__)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_item = self.addPlot()
        self.plot_item.setMenuEnabled(False)
        self.inf_line = InfiniteLine(0, pen=self.get_pen(color='red', style=Qt.DashLine))
        self.plot_item.addItem(self.inf_line)
        self.plots = {}
        self.x_axis: Dict[int, List[int]] = {}

    def add_fit(self, fit_obj: FitObject):
        self.log.debug(f'Number of fits = {len(fit_obj.fits)}')
        x = fit_obj.image_key.idx

        for fit in fit_obj.fits.values():
            self._add_fit(fit, x)

        fitted_keys = [k for k in fit_obj.fits.keys() if fit_obj.fits[k].fitted_params]

        for key, x_axis in self.x_axis.items():
            if x in x_axis and (key not in fitted_keys):
                self._delete_fit(key, x)

        self.change_image(fit_obj.image_key)

    def update_roi(self, fit: Fit, x: int):
        self._add_fit(fit, x)

    def delete_roi(self, roi: Roi, x: int):
        self._delete_fit(roi.key, x)

    def _add_fit(self, fit: Fit, x):
        # if not fit.roi.fitted_parameters:
        #     return

        key = fit.roi.key

        if key not in self.plots:
            self._init_plot(key)

        idx, x_axis = self._add_x(key, x)

        plots = self.plots[key]

        radius, width = fit.roi.radius, fit.roi.width

        for name, point in zip(('upper', 'middle', 'lower'),
                               (radius + width, radius, radius - width)):
            plot = plots[name]
            y = plot.yData
            if y is None:
                y = [point]
            else:
                y = y.tolist()
                if len(y) == len(x_axis):
                    # self.log.debug('Moving roi ...')
                    y[idx] = point
                else:
                    # self.log.debug('Inserting roi ...')
                    y.insert(idx, point)
            plot.setData(x_axis, y)

        self._update_fill_between(plots)

    def _add_x(self, key: int, x) -> Tuple[int, list]:
        if key not in self.x_axis:
            self.x_axis[key] = [x]
            return 0, self.x_axis[key]

        x_axis: list = self.x_axis[key]
        if x not in x_axis:
            if not len(x_axis) or x_axis[-1] < x:
                x_axis.append(x)
                return len(x_axis) - 1, x_axis
            else:
                # TODO implement binary search
                for i, other_x in enumerate(x_axis):
                    if x < other_x:
                        x_axis.insert(i, x)
                        return i, x_axis
        else:
            return x_axis.index(x), x_axis

    def _delete_fit(self, key: int, x: int):
        try:
            plots = self.plots[key]
            x_axis = self.x_axis[key]
            idx = x_axis.index(x)
        except (KeyError, ValueError):
            return

        # self.log.debug('Deleting fit ... ')

        x_axis.remove(x)

        for name in ('upper', 'middle', 'lower'):
            plot = plots[name]
            y = plot.yData.tolist()
            del y[idx]
            plot.setData(x_axis, y)

        self._update_fill_between(plots)

    def _init_plot(self, key):
        self.plots[key] = {}
        self.plots[key]['upper'] = self.plot_item.plot(pen=self.get_pen(color='blue'))
        self.plots[key]['middle'] = self.plot_item.plot(
            pen=self.get_pen(style=Qt.DashLine)
        )
        self.plots[key]['lower'] = self.plot_item.plot(pen=self.get_pen(color='blue'))

    def _update_fill_between(self, plots):
        if 'fill' not in plots:
            plots['fill'] = FillBetweenItem(plots['upper'], plots['lower'],
                                            brush=[63, 63, 63, 191])
            self.plot_item.addItem(plots['fill'])
        else:
            plots['fill'].setCurves(plots['upper'], plots['lower'])

    @pyqtSlot(object, name='changeImage')
    def change_image(self, key: ImageKey):
        self.inf_line.setValue(key.idx)
        self.plot_item.autoRange()

    @staticmethod
    def get_pen(width: int = 1, color: str or QColor = 'white', style=Qt.SolidLine):
        if isinstance(color, str):
            color = QColor(color)
        pen = QPen(color)
        pen.setStyle(style)
        pen.setWidth(width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCosmetic(True)
        return pen


class ProgressWidget(QWidget):
    sigImageChanged = pyqtSignal(object)

    def __init__(self, image_key: ImageKey, parent=None):
        super().__init__(parent)
        self.current_key: ImageKey = image_key
        self.folder_key: FolderKey = image_key.parent
        self._init_ui()
        self.set_fixed(False)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.progress_bar = QProgressBar(self)
        self.slider = QSlider(orientation=Qt.Horizontal, parent=self)
        self.label = QLabel(self.current_key.name)

        self.progress_bar.setMaximum(self.folder_key.images_num - 1)
        self.slider.setMaximum(self.folder_key.images_num - 1)
        self.slider.valueChanged.connect(self._on_slider_moved)

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.slider)

    @pyqtSlot(bool, name='setFixed')
    def set_fixed(self, fixed: bool):
        if fixed:
            self.progress_bar.show()
            self.slider.hide()
        else:
            self.progress_bar.hide()
            self.slider.show()

    @pyqtSlot(int, name='sliderMoved')
    def _on_slider_moved(self, value: int):
        image_key = self.folder_key.image_by_key(value)
        self.label.setText(image_key.name)
        if image_key and image_key != self.current_key:
            self.current_key = image_key
            self.sigImageChanged.emit(image_key)

    @pyqtSlot(object, name='changeImage')
    def change_image(self, image_key: ImageKey):
        self.current_key = image_key
        self.progress_bar.setValue(image_key.idx)
        self.label.setText(image_key.name)
        self.slider.setValue(image_key.idx)
