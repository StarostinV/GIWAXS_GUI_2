# -*- coding: utf-8 -*-

import logging
from typing import Iterable, Dict, List

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import (
    pyqtSlot,
    pyqtSignal,
)
from PyQt5.QtGui import QColor

from ...app import App
from ...app.structures import (
    CrystalRing,
    CustomCrystal
)

from ..roi_widgets import BasicRoiRing
from ..basic_widgets import (
    CustomImageViewer,
    LabeledSlider,
    BlackToolBar,
    RoundedPushButton
)

from ..tools import Icon

logger = logging.getLogger(__name__)


class CrystalImageViewer(CustomImageViewer):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ring_dict: Dict[str, BasicRoiRing] = {}

        self.image_plot.getAxis('bottom').setLabel(text='<math>Q<sub>xy</sub>  (A<sup>-1</sup>) </math>', color='white')
        self.image_plot.getAxis('left').setLabel(text='<math>Q<sub>z</sub>  (A<sup>-1</sup>) </math>', color='white')

        self.app = App()
        self.connect_to_app()

    def connect_to_app(self):
        self.app.geometry_holder.sigBeamCenterChanged.connect(self._on_beam_center_changed)
        self.app.geometry_holder.sigRingBoundsChanged.connect(self._on_ring_bounds_changed)

        self.app.image_holder.sigImageChanged.connect(self._on_image_changed)
        self.app.image_holder.sigEmptyImage.connect(self.clear_image)

    @pyqtSlot(tuple, name='onRingsBoundsChanged')
    def _on_ring_bounds_changed(self, bounds: tuple):
        for ring_widget in self._ring_dict.values():
            ring_widget.set_params(angle=bounds[0], angle_std=bounds[1])

    @pyqtSlot(name='onImageChanged')
    def _on_image_changed(self):
        image = self.app.image
        if image is not None:
            self.set_data(image)

    @pyqtSlot(name='onBeamCenterChanged')
    def _on_beam_center_changed(self):
        beam_center = self.app.geometry.beam_center
        self.set_center((beam_center.y, beam_center.z), pixel_units=True)

    def add_ring(self, ring: CrystalRing):
        angle, angle_std = self.app.geometry.ring_bounds
        ring_widget = BasicRoiRing(ring.radius, width=0.0, angle=angle, angle_std=angle_std)
        ring_widget.setPen(QColor('blue'))
        self._ring_dict[ring.key] = ring_widget
        self.image_plot.addItem(ring_widget)

    def add_rings(self, rings: Iterable[CrystalRing]):
        for ring in rings:
            self.add_ring(ring)

    def remove_ring(self, ring: CrystalRing):
        try:
            self.image_plot.removeItem(self._ring_dict.pop(ring.key))
        except KeyError:
            return

    def remove_rings(self, rings: Iterable[CrystalRing] = None):
        if rings:
            for ring in rings:
                self.remove_ring(ring)
        else:
            self._ring_dict, ring_widgets = {}, self._ring_dict.values()
            for ring_widget in ring_widgets:
                self.image_plot.removeItem(ring_widget)


class CrystalImageWidget(QMainWindow):
    sigUpdateClicked = pyqtSignal(float)

    INIT_SCALE: float = 0.002

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_viewer = CrystalImageViewer(self)
        self.setCentralWidget(self.image_viewer)
        self.image_viewer.set_scale(self.INIT_SCALE)
        self._init_toolbar()

    def send_init_scale(self):
        self.sigUpdateClicked.emit(self.INIT_SCALE)

    def _init_toolbar(self):
        scale_toolbar = BlackToolBar('scale', self)
        self.addToolBar(scale_toolbar)

        scale_slider = LabeledSlider('Scale',
                                     (1e-4, 1e2),
                                     value=self.INIT_SCALE,
                                     parent=scale_toolbar,
                                     scientific=True)
        scale_slider.valueChanged.connect(self.image_viewer.set_scale)
        scale_slider.label.setStyleSheet(
            'QLabel { color : white ; }')
        scale_toolbar.addWidget(scale_slider)

        update_button = RoundedPushButton(self, icon=Icon('update'))
        update_button.clicked.connect(lambda *arg, s=scale_slider: self.sigUpdateClicked.emit(s.value))
        scale_toolbar.addWidget(update_button)

    @pyqtSlot(CustomCrystal, name='addCrystal')
    def add_crystal(self, crystal: CustomCrystal):
        self.image_viewer.add_rings(crystal.rings)

    @pyqtSlot(CustomCrystal, name='removeCrystal')
    def remove_crystal(self, crystal: CustomCrystal):
        self.image_viewer.remove_rings(crystal.rings)

    @pyqtSlot(list, name='redrawRings')
    def redraw_rings(self, crystals: List[CustomCrystal]):
        self.image_viewer.remove_rings()
        for crystal in crystals:
            self.add_crystal(crystal)
