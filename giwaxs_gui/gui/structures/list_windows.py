# -*- coding: utf-8 -*-

from PyQt5.QtCore import pyqtSignal

from .ring_list import RingsListWidget, CrystalItem, ListColumn
from ...app.structures import CrystalsDatabase, CustomCrystal


class DatabaseWindow(RingsListWidget):
    sigCrystalAddedToSelected = pyqtSignal(CustomCrystal)

    _CRYSTAL_COLUMNS = [
        ListColumn(0, lambda crystal: str(crystal.chemical_formula), 'Material'),
        ListColumn(1, lambda crystal: str(crystal.lattice_system.name), 'Structure'),
        ListColumn(2, lambda crystal: str(crystal.source), 'Source'),
    ]

    _RING_COLUMNS = []

    def __init__(self, parent=None):
        super().__init__(parent,
                         check_boxes=False,
                         expand=False,
                         expand_on_click=False,
                         show_rings_items=False)

        self.doubleClicked.connect(self._on_double_click)

    def _on_double_click(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, CrystalItem):
            self.sigCrystalAddedToSelected.emit(item.crystal)


class SelectedCrystalsWindow(RingsListWidget):
    def __init__(self, parent=None):
        super().__init__(parent, check_boxes=True, expand=True, expand_on_click=False)
