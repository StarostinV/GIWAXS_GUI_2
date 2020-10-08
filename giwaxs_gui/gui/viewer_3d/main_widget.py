from itertools import product

from PyQt5.QtWidgets import QWidget, QGridLayout
import numpy as np
from crystals import real_coords

from ...app.structures import CustomCrystal
from .legend import CrystalLegend
from .viewer import CrystalViewer
from .info import CrystalLabel
from .auto_rotate_button import AutoRotateButton
from .scene import SceneCrystal, UnitVectors, Atom


class Crystal3DWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._crystal = None

    def _init_ui(self):
        layout = QGridLayout(self)
        self.setMinimumSize(400, 400)
        self.setWindowTitle('Crystal View')
        self.crystal_label = CrystalLabel(self)
        self.crystal_legend = CrystalLegend()
        CrystalViewer.enable_multisampling()
        self.crystal_view = CrystalViewer()
        self.auto_rotate_btn = AutoRotateButton(self)
        # self.crystal_view_widget = QWidget.createWindowContainer(self.crystal_view)
        layout.addWidget(self.crystal_label, 0, 0)
        layout.addWidget(self.auto_rotate_btn, 0, 1)
        layout.addWidget(self.crystal_view, 1, 0)
        layout.addWidget(self.crystal_legend, 1, 1)

        self.auto_rotate_btn.sigStartRotating.connect(self.crystal_view.start_rotation)
        self.auto_rotate_btn.sigStopRotating.connect(self.crystal_view.stop_rotation)
        self.crystal_legend.sigColorChanged.connect(self.crystal_view.update_scene)

    def set_crystal(self, custom_crystal: CustomCrystal):
        if not self._crystal or custom_crystal.key != self._crystal.key:
            self._crystal = custom_crystal
            scene_crystal = _convert_crystal(custom_crystal)

            self.crystal_legend.set_crystal(scene_crystal)
            self.crystal_view.set_crystal(scene_crystal)
            self.crystal_label.set_crystal(custom_crystal)


def _generate_unitcell_atoms(crystal: SceneCrystal, lattice_vectors: tuple):
    for atm in crystal:
        for factors in product(range(-2, 2), range(-2, 2), range(-2, 2)):
            coords = atm.coords_fractional + np.asarray(factors)
            if np.all(coords <= 1.1) and np.all(coords >= -0.1):
                yield Atom(
                    element=atm.element,
                    coords=real_coords(coords, lattice_vectors)
                )


def _convert_crystal(crystal: CustomCrystal) -> SceneCrystal:
    unit_vectors = UnitVectors(*crystal.lattice_vectors)
    atoms = list(_generate_unitcell_atoms(crystal, crystal.lattice_vectors))
    return SceneCrystal(atoms=atoms, unit_vectors=unit_vectors)
