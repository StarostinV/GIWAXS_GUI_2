import logging
from enum import Enum
from typing import Dict, List, Tuple
from time import sleep
from copy import deepcopy

from PyQt5.QtCore import (QObject, pyqtSlot, pyqtSignal,
                          QCoreApplication, Qt, QThread)
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                             QProgressBar, QSlider, QLabel, QMessageBox)

from pyqtgraph import GraphicsLayoutWidget, FillBetweenItem, InfiniteLine

from ...app import App, Roi, RoiData
from ...app.file_manager import ImageKey, FolderKey
from ...app.fitting import FitObject, Fit

from ..tools import get_pen, center_widget, Icon

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
    sigSaved = pyqtSignal(int)
    sigSavedFinished = pyqtSignal()

    log = logging.getLogger(__name__)

    def __init__(self, fm_multi_fit, parent=None):
        super().__init__(parent=parent)
        self.sleep_time: float = 0.002
        self._paused: bool = True
        self._stopped: bool = False
        self.fm_multi_fit = fm_multi_fit

    @pyqtSlot(list, name='runSave')
    def run_save(self, image_key_list: list):
        rois_data_fm = App().fm.rois_data

        for i, image_key in enumerate(image_key_list):

            fit_obj = self.fm_multi_fit[image_key]
            if not fit_obj:
                self.sigSaved.emit(i)
                continue

            rois = [fit.roi for fit in fit_obj.fits.values() if fit.fitted_params]

            if rois:
                roi_data = rois_data_fm[image_key] or RoiData()
                roi_data.apply_fit(rois)
                rois_data_fm[image_key] = roi_data

            self.sigSaved.emit(i)

            if self.sleep_time:
                sleep(self.sleep_time)

        self.sigSavedFinished.emit()

    @pyqtSlot(object, name='runFit')
    def run_fit(self, fit_obj: FitObject):
        self._paused = False
        fit_obj = deepcopy(fit_obj)

        while fit_obj and fit_obj.fits and not self._paused:

            self.log.info(f'Fitting image {fit_obj.image_key}')
            for fit in fit_obj.fits.values():
                if fit.fitted_params:
                    continue
                try:
                    fit.do_fit()
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

            fit_obj.is_fitted = True
            new_key = fit_obj.image_key.parent.get_next_image(fit_obj.image_key)

            if not new_key:
                self.sigFit.emit(fit_obj)
                break

            saved_fit = self.fm_multi_fit[new_key]
            self.sigFit.emit(deepcopy(fit_obj))
            new_fit_obj = get_new_fit(fit_obj, saved_fit=saved_fit,
                                      add_fits=True, new_image_key=new_key)
            fit_obj = new_fit_obj

        if self._stopped:
            self.deleteLater()
        elif self._paused:
            self.sigPaused.emit()
        else:
            self._paused = True
            self.sigFinished.emit()

    @property
    def is_paused(self):
        return self._paused

    @pyqtSlot(name='pauseFit')
    def pause(self):
        self.log.debug('Pause signal received')
        self._paused = True

    @pyqtSlot(name='stopFit')
    def stop(self):
        self.log.debug('Stop signal received')
        self._paused = True
        self._stopped = True


def get_new_fit(previous_fit: FitObject, saved_fit: FitObject = None,
                add_fits: bool = False, new_image_key: ImageKey = None):

    if not saved_fit:
        if not new_image_key:
            folder_key: FolderKey = previous_fit.image_key.parent
            if not folder_key:
                logger.debug('empty folder key')
                return
            new_image_key: ImageKey = folder_key.get_next_image(previous_fit.image_key)
        if not new_image_key:
            logger.debug('empty next image_key')
            return

        image, polar_image, geometry = App().image_holder.get_data_by_key(new_image_key, save=True)

        if polar_image is None:
            logger.debug('empty polar_image')
            return

        saved_fit: FitObject = FitObject(new_image_key, polar_image, geometry.r_axis, geometry.phi_axis)

    if not saved_fit.saved_profile:

        saved_profile = App().fm.profiles[new_image_key]

        if saved_profile:
            saved_fit.set_profile(saved_profile, update_baseline=False)
        elif previous_fit.saved_profile:
            saved_fit.set_profile(previous_fit.saved_profile, update_baseline=True)
            App().fm.profiles[new_image_key] = saved_fit.saved_profile

    if add_fits:
        for fit in previous_fit.fits.values():
            if fit.fitted_params and fit.roi.key not in saved_fit.fits.keys():
                saved_fit.add_fit(fit)
                fit.fitted_params = None

    return saved_fit


class MultiFitWindow(QWidget):
    sigPauseFit = pyqtSignal()
    sigDeleteFit = pyqtSignal()
    sigRunFit = pyqtSignal(object)
    sigClosed = pyqtSignal()
    sigFitUpdated = pyqtSignal(object)
    sigRunSave = pyqtSignal(list)

    log = logging.getLogger(__name__)

    def __init__(self, fit_object: FitObject, parent=None):
        super().__init__(parent=parent)
        self.current_fit: FitObject = fit_object
        self.fm = App().fm.fits.get_multi_fit()

        self.fit_thread = QThread()
        self.multi_fit = MultiFit(self.fm)
        self.multi_fit.moveToThread(self.fit_thread)

        self.multi_fit.sigPaused.connect(self.on_paused)
        self.multi_fit.sigFinished.connect(self.on_finished)
        self.multi_fit.sigFit.connect(self._update_fit)

        self.sigRunFit.connect(self.multi_fit.run_fit)
        self.sigPauseFit.connect(self.multi_fit.pause)
        self.sigDeleteFit.connect(self.multi_fit.stop)
        self.sigRunSave.connect(self.multi_fit.run_save)

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
        layout.addWidget(QLabel('Image series'))
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

        add_fits: bool = self.current_fit.image_key.idx + 1 == key.idx if self.current_fit else False

        self.save_current_fit()
        self.current_fit = get_new_fit(
            self.current_fit, saved_fit=self.fm[key], new_image_key=key, add_fits=add_fits)
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

    def save_fits(self, image_keys: list):
        self.log.info(f'Saving {len(image_keys)} fits ...')
        if not self.multi_fit.is_paused:
            msg_box = QMessageBox()
            msg_box.setWindowTitle('Saving fits')
            msg_box.setWindowIcon(Icon('error'))
            msg_box.setText("Please, stop the auto fitting process before saving the images.")
            msg_box.setDefaultButton(QMessageBox.Close)
            msg_box.exec()
            return
        widget = SaveProgressWidget(len(image_keys), parent=self)

        if image_keys:
            self.multi_fit.sigSaved.connect(widget.set_progress)
            self.multi_fit.sigSavedFinished.connect(widget.finished)
            self.sigRunSave.emit(image_keys)

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

    def select_fit(self, key: int):
        self.plot_params.select_fit(key)

    def unselect_fit(self, key: int):
        self.plot_params.unselect_fit(key)

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

    INACTIVE_COLOR = [63, 63, 63, 190]
    ACTIVE_COLOR = [50, 250, 50, 240]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_item = self.addPlot()
        self.plot_item.setMenuEnabled(False)
        self.inf_line = InfiniteLine(0, pen=get_pen(color='red', style=Qt.DashLine))
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

    def select_fit(self, key: int):
        try:
            self.plots[key]['fill'].setBrush(self.ACTIVE_COLOR)
        except KeyError:
            pass

    def unselect_fit(self, key: int):
        try:
            self.plots[key]['fill'].setBrush(self.INACTIVE_COLOR)
        except KeyError:
            pass

    def _init_plot(self, key):
        self.plots[key] = {}
        self.plots[key]['upper'] = self.plot_item.plot(pen=get_pen(color='blue'))
        self.plots[key]['middle'] = self.plot_item.plot(
            pen=get_pen(style=Qt.DashLine)
        )
        self.plots[key]['lower'] = self.plot_item.plot(pen=get_pen(color='blue'))

    def _update_fill_between(self, plots):
        if 'fill' not in plots:
            plots['fill'] = FillBetweenItem(plots['upper'], plots['lower'],
                                            brush=self.INACTIVE_COLOR)
            self.plot_item.addItem(plots['fill'])
        else:
            plots['fill'].setCurves(plots['upper'], plots['lower'])

    @pyqtSlot(object, name='changeImage')
    def change_image(self, key: ImageKey):
        self.inf_line.setValue(key.idx)
        self.plot_item.autoRange()


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
        self.label = QLabel(self._label_text())

        self.progress_bar.setMaximum(self.folder_key.images_num - 1)
        self.slider.setMaximum(self.folder_key.images_num - 1)
        self.slider.valueChanged.connect(self._on_slider_moved)
        if self.current_key:
            self.slider.setValue(self.current_key.idx)

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
        if image_key and image_key != self.current_key:
            self.current_key = image_key
            self.sigImageChanged.emit(image_key)
            self.label.setText(self._label_text())

    @pyqtSlot(object, name='changeImage')
    def change_image(self, image_key: ImageKey):
        self.current_key = image_key
        self.progress_bar.setValue(image_key.idx)
        self.label.setText(self._label_text())
        self.slider.setValue(image_key.idx)

    def _label_text(self):
        return f'Image {self.current_key.idx}: {self.current_key.name}'


class SaveProgressWidget(QWidget):
    def __init__(self, num: int, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.Window)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._init_ui(num)
        center_widget(self)
        self.show()

    def _init_ui(self, num: int):
        layout = QVBoxLayout(self)
        self.progress = QProgressBar()
        self.progress.setMaximum(num)
        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.close)
        self.label = QLabel('Applying fitting ...')
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.close_button)
        self.close_button.hide()

        if not num:
            self.progress.setMaximum(1)
            self.progress.setValue(1)
            self.finished()

    @pyqtSlot(int, name='setProgress')
    def set_progress(self, value: int):
        self.progress.setValue(value)

    @pyqtSlot(name='finished')
    def finished(self):
        self.label.setText('Fits are saved!')
        self.progress.setValue(self.progress.maximum())
        self.close_button.show()
