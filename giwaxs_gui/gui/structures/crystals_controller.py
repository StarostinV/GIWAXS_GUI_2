# -*- coding: utf-8 -*-

import logging

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget

from .crystal_image_viewer import CrystalImageWidget
from .list_windows import DatabaseWindow, SelectedCrystalsWindow
from ..viewer_3d import Crystal3DWidget

from ..basic_widgets.progress_bar import ProgressBar
from ..background_tasks import BackgroundTasks

from ...app.app import App
from ...app.utils import UpdateWorker
from ...app.structures import CrystalsDatabase, CustomCrystal

logger = logging.getLogger(__name__)


class CrystalsController(QObject):
    sigRingsUpdated = pyqtSignal(list)
    sigCheckedRingsUpdated = pyqtSignal(list)

    def __init__(self, crystals_database: CrystalsDatabase, main_widget: QWidget, parent: QObject = None):
        super().__init__(parent)
        self.crystals_database = crystals_database
        self.selected_holder = crystals_database.selected_holder
        self.main_widget = main_widget
        self._updating_crystal = None

        self._connect()

    def _connect(self):
        self.selected_holder.sigQMaxChanged.connect(self.update_rings)
        self.selected_holder.sigCrystalAdded.connect(self.update_crystal_rings)

    @pyqtSlot(name='updateRings')
    def update_rings(self):
        logger.debug(f'update_rings called')
        if not self.selected_holder.is_updated:
            worker = self._make_update_rings_worker(self.selected_holder.update_rings)
            worker.signals.finished.connect(self._update_finished)
            BackgroundTasks().tasks.add_worker(worker)
        else:
            self._update_finished()

    def update_crystal_rings(self, crystal: CustomCrystal):
        logger.debug(f'update_crystal_rings called. if statement: {not crystal.is_updated}')
        if not crystal.is_updated:
            self._updating_crystal = crystal
            worker = self._make_update_rings_worker(crystal.update_rings)
            worker.signals.finished.connect(self._crystal_update_finished)
            BackgroundTasks().tasks.add_worker(worker)

    def _make_update_rings_worker(self, func):
        progress_bar = ProgressBar(
            1,
            'Calculating crystal q positions...',
            'Finished!',
            parent=self.main_widget,
            auto_close=True, show=True
        )
        worker = UpdateWorker(func)
        logger.debug(f'UpdateWorker init')

        worker.signals.sigSetMax.connect(progress_bar.set_max)
        worker.signals.sigSetProgress.connect(progress_bar.set_progress)
        worker.signals.finished.connect(progress_bar.finished)

        return worker

    @pyqtSlot(name='crystalUpdateFinished')
    def _crystal_update_finished(self):
        self.sigRingsUpdated.emit([self._updating_crystal])
        self.sigCheckedRingsUpdated.emit([self._updating_crystal])
        self._updating_crystal = None

    @pyqtSlot(name='updateFinished')
    def _update_finished(self):
        if self.selected_holder.crystals:
            self.sigRingsUpdated.emit(self.selected_holder.crystals)
        if self.selected_holder.checked_crystals:
            self.sigCheckedRingsUpdated.emit(self.selected_holder.checked_crystals)

    @pyqtSlot(object, name='addCrystalFromCif')
    def add_crystal_from_cif(self, path):
        self.crystals_database.add_crystal_from_cif(path)

    @pyqtSlot(CustomCrystal, name='addCrystalToDatabase')
    def add_crystal_to_database(self, crystal: CustomCrystal):
        self.crystals_database.add_crystal(crystal=crystal)

    def connect_selected_list(self, viewer: SelectedCrystalsWindow):
        self.selected_holder.sigCrystalAdded.connect(viewer.add_crystal)
        self.selected_holder.sigCrystalRemoved.connect(viewer.remove_crystal)
        self.sigRingsUpdated.connect(viewer.redraw_rings)

        viewer.sigCrystalSelected.connect(self.selected_holder.crystal_selected)
        viewer.sigCrystalRemoved.connect(self.selected_holder.remove_crystal)
        viewer.sigCrystalChecked.connect(self.selected_holder.crystal_checked)
        viewer.sigCrystalUnchecked.connect(self.selected_holder.crystal_unchecked)
        viewer.sigRingSelected.connect(self.selected_holder.ring_selected)

    def connect_database_list(self, viewer: DatabaseWindow):
        self.crystals_database.sigCrystalAdded.connect(viewer.add_crystal)
        self.crystals_database.sigCrystalRemoved.connect(viewer.remove_crystal)

        viewer.sigCrystalSelected.connect(self.crystals_database.crystal_selected)
        viewer.sigCrystalAddedToSelected.connect(self.selected_holder.add_crystal)
        viewer.sigCrystalRemoved.connect(self.crystals_database.remove_crystal)

    def connect_image_widget(self, widget: CrystalImageWidget):
        self.selected_holder.sigCrystalChecked.connect(widget.add_crystal)
        self.selected_holder.sigCrystalUnchecked.connect(widget.remove_crystal)
        self.selected_holder.sigCrystalSelected.connect(widget.select_crystal)
        self.crystals_database.sigCrystalSelected.connect(widget.select_crystal)
        self.selected_holder.sigRingSelected.connect(widget.select_ring)
        self.sigCheckedRingsUpdated.connect(widget.redraw_rings)
        widget.sigUpdateClicked.connect(self._scale_updated)
        widget.send_init_scale()

    def connect_3d_viewer(self, viewer: Crystal3DWidget):
        self.crystals_database.sigCrystalSelected.connect(viewer.set_crystal)
        self.selected_holder.sigCrystalSelected.connect(viewer.set_crystal)

    def _scale_updated(self, scale: float):
        # TODO: fix bug with scales and change this!
        q_max = App().geometry.r_range[1] / App().geometry.scale * scale
        self.crystals_database.set_q_max(q_max)
