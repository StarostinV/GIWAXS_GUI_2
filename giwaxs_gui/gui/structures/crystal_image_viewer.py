# -*- coding: utf-8 -*-

import logging
from typing import Set, Dict, List, Generator

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
from ...app.utils import InternalError

from ..roi_widgets import BasicRoiRing
from ..basic_widgets import (
    CustomImageViewer,
    LabeledSlider,
    BlackToolBar,
    RoundedPushButton
)

from ..tools import Icon

logger = logging.getLogger(__name__)

RingDict = Dict[str, BasicRoiRing]
CrystalsDict = Dict[str, RingDict]


class CrystalImageViewer(CustomImageViewer):
    DEFAULT_CRYSTAL_COLOR: QColor = QColor(0, 0, 255, 180)
    SELECTED_CRYSTAL_COLOR: QColor = QColor(0, 128, 255, 200)
    SELECTED_RING_COLOR: QColor = QColor(255, 128, 0)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._crystals_dict: CrystalsDict = {}
        self._selected_crystals: Set[str] = set()
        self._selected_ring: CrystalRing or None = None

        self.image_plot.getAxis('bottom').setLabel(text='<math>Q<sub>xy</sub>  (A<sup>-1</sup>) </math>', color='white')
        self.image_plot.getAxis('left').setLabel(text='<math>Q<sub>z</sub>  (A<sup>-1</sup>) </math>', color='white')

        self.app = App()
        self.connect_to_app()

    def connect_to_app(self):
        self.app.geometry_holder.sigBeamCenterChanged.connect(self._on_beam_center_changed)
        self.app.geometry_holder.sigRingBoundsChanged.connect(self._on_ring_bounds_changed)

        self.app.image_holder.sigImageChanged.connect(self._on_image_changed)
        self.app.image_holder.sigEmptyImage.connect(self.clear_image)

    def _ring_widgets(self, crystal: CustomCrystal = None) -> Generator[BasicRoiRing, None, None]:
        if crystal:
            yield from self._get_ring_dict(crystal).values()
        else:
            for ring_dict in self._crystals_dict.values():
                yield from ring_dict.values()

    def _get_ring_dict(self, crystal: CustomCrystal or str):
        if isinstance(crystal, CustomCrystal):
            crystal = crystal.key
        try:
            return self._crystals_dict[crystal]
        except KeyError as err:
            raise InternalError(f'Crystal {crystal} is not in the CrystalImageViewer dict.') from err

    @pyqtSlot(tuple, name='onRingsBoundsChanged')
    def _on_ring_bounds_changed(self, bounds: tuple):
        for ring_widget in self._ring_widgets():
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

    def unselect_ring(self):
        if self._selected_ring:
            crystal = self._selected_ring.crystal
            try:
                crystal_color = self._get_crystal_color(crystal)
                self._get_ring_dict(crystal)[self._selected_ring.key].setPen(crystal_color)
            except KeyError as err:
                raise InternalError(f'Ring cannot be unselected: {self._selected_ring}') from err
            finally:
                self._selected_ring = None

    def select_ring(self, ring: CrystalRing):
        self.unselect_ring()
        if ring.crystal.key in self._crystals_dict:
            ring_dict = self._crystals_dict[ring.crystal.key]
            if ring.key in ring_dict:
                ring_dict[ring.key].setPen(self.SELECTED_RING_COLOR)
                self._selected_ring = ring

    def add_crystal(self, crystal: CustomCrystal):
        if crystal.key in self._crystals_dict:
            return
        ring_dict: RingDict = {}
        self._crystals_dict[crystal.key] = ring_dict
        for ring in crystal.rings:
            self._add_ring(ring, ring_dict)

    def update_crystal(self, crystal: CustomCrystal):
        if crystal.key in self._crystals_dict:
            self.remove_crystal(crystal)
        self.add_crystal(crystal)

    def remove_crystal(self, crystal: CustomCrystal):
        ring_dict = self._crystals_dict.pop(crystal.key)
        for widget in ring_dict.values():
            self.image_plot.removeItem(widget)
        if crystal.key in self._selected_crystals:
            self._selected_crystals.remove(crystal.key)

    def remove_crystals(self):
        for ring_dict in self._crystals_dict.values():
            for widget in ring_dict.values():
                self.image_plot.removeItem(widget)
        self._crystals_dict = {}
        self._selected_crystals = set()

    def select_crystal(self, crystal: CustomCrystal):
        if crystal.key in self._crystals_dict and crystal.key not in self._selected_crystals:
            self._color_crystal(crystal, self.SELECTED_CRYSTAL_COLOR)
            self._selected_crystals.add(crystal.key)

    def crystal_selected(self, crystal: CustomCrystal):
        return crystal.key in self._selected_crystals

    def unselect_crystals(self):
        for key in self._selected_crystals:
            self._color_crystal(key, self.DEFAULT_CRYSTAL_COLOR)
        self._selected_crystals = set()

    def _color_crystal(self, crystal: CustomCrystal or str, color: QColor):
        for widget in self._get_ring_dict(crystal).values():
            widget.setPen(color)

    def _get_crystal_color(self, crystal: CustomCrystal or str):
        if isinstance(crystal, CustomCrystal):
            crystal = crystal.key
        if crystal in self._selected_crystals:
            return self.SELECTED_CRYSTAL_COLOR
        else:
            return self.DEFAULT_CRYSTAL_COLOR

    def _add_ring(self, ring: CrystalRing, ring_dict: RingDict):
        angle, angle_std = self.app.geometry.ring_bounds
        ring_widget = BasicRoiRing(ring.radius, width=0.0, angle=angle, angle_std=angle_std)
        ring_widget.setPen(self.DEFAULT_CRYSTAL_COLOR)
        ring_dict[ring.key] = ring_widget
        self.image_plot.addItem(ring_widget)


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
        self.image_viewer.add_crystal(crystal)

    @pyqtSlot(CustomCrystal, name='removeCrystal')
    def remove_crystal(self, crystal: CustomCrystal):
        self.image_viewer.remove_crystal(crystal)

    @pyqtSlot(list, name='redrawRings')
    def redraw_rings(self, crystals: List[CustomCrystal]):
        for crystal in crystals:
            self.image_viewer.update_crystal(crystal)

    @pyqtSlot(CustomCrystal, name='selectCrystal')
    def select_crystal(self, crystal: CustomCrystal):
        self.image_viewer.unselect_ring()
        if not self.image_viewer.crystal_selected(crystal):
            self.image_viewer.unselect_crystals()
            self.image_viewer.select_crystal(crystal)

    @pyqtSlot(CrystalRing, name='selectRing')
    def select_ring(self, ring: CrystalRing):
        self.image_viewer.select_ring(ring)
