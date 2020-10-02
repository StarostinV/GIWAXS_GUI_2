# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThreadPool

from .custom_crystal import CustomCrystal


class CrystalsHolder(QObject):
    sigCrystalAdded = pyqtSignal(CustomCrystal)
    sigCrystalRemoved = pyqtSignal(CustomCrystal)
    sigErrorCrystalAlreadyExists = pyqtSignal(CustomCrystal)
    sigCrystalSelected = pyqtSignal(CustomCrystal)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._crystals: dict = {}
        self._q_max: float = 1

    @property
    def q_max(self):
        return self._q_max

    def __getitem__(self, item):
        return self._crystals[item]

    def __iter__(self):
        yield from self._crystals.values()

    @pyqtSlot(CustomCrystal, name='crystalSelected')
    def crystal_selected(self, crystal: CustomCrystal):
        self.sigCrystalSelected.emit(crystal)

    @pyqtSlot(CustomCrystal, name='addCrystal')
    def add_crystal(self, crystal: CustomCrystal):
        if crystal.key not in self._crystals:
            crystal.set_q_max(self._q_max)
            self._crystals[crystal.key] = crystal
            self.sigCrystalAdded.emit(crystal)
        else:
            self.sigErrorCrystalAlreadyExists.emit(crystal)

    @pyqtSlot(CustomCrystal, name='removeCrystal')
    def remove_crystal(self, crystal: CustomCrystal):
        try:
            self.sigCrystalRemoved.emit(self._crystals.pop(crystal.key))
        except KeyError as err:
            raise KeyError(f'Crystal {crystal.key} not found') from err

    @pyqtSlot(Path, name='addCrystalFromCif')
    def add_crystal_from_cif(self, cif_path: Path):
        crystal = CustomCrystal.from_cif(str(cif_path.resolve()))
        self.add_crystal(crystal)

    @property
    def crystals(self) -> List[CustomCrystal]:
        return list(self._crystals.values())

    @pyqtSlot(float, name='setQMax')
    def set_q_max(self, q_max: float):
        if q_max != self._q_max:
            self._q_max = q_max
            for crystal in self._crystals.values():
                crystal.set_q_max(q_max)


class SelectedCrystalsHolder(CrystalsHolder):
    sigQMaxChanged = pyqtSignal()
    sigCrystalChecked = pyqtSignal(CustomCrystal)
    sigCrystalUnchecked = pyqtSignal(CustomCrystal)

    def __init__(self, parent):
        super().__init__(parent)
        self._checked_crystals = {}
        self._q_thread_pool = QThreadPool(self)

    def crystal_is_checked(self, crystal: CustomCrystal):
        return crystal.key in self._checked_crystals

    @pyqtSlot(CustomCrystal, name='crystalChecked')
    def crystal_checked(self, crystal: CustomCrystal):
        if crystal.key not in self._checked_crystals:
            self._checked_crystals[crystal.key] = crystal
            self.sigCrystalChecked.emit(crystal)

    @pyqtSlot(CustomCrystal, name='crystalUnchecked')
    def crystal_unchecked(self, crystal: CustomCrystal):
        try:
            del self._checked_crystals[crystal.key]
            self.sigCrystalUnchecked.emit(crystal)
        except KeyError:
            pass

    @pyqtSlot(CustomCrystal, name='addCrystal')
    def add_crystal(self, crystal: CustomCrystal):
        super().add_crystal(crystal)
        self.crystal_checked(crystal)

    @pyqtSlot(CustomCrystal, name='removeCrystal')
    def remove_crystal(self, crystal: CustomCrystal):
        if self.crystal_is_checked(crystal):
            self.crystal_unchecked(crystal)
        super().remove_crystal(crystal)

    @property
    def is_updated(self):
        return all(map(lambda c: c.is_updated, self.crystals))

    def update_rings(self, *args, **kwargs):
        for crystal in self.crystals:
            crystal.update_rings(*args, **kwargs)

    @property
    def checked_crystals(self) -> List[CustomCrystal]:
        return list(self._checked_crystals.values())

    @pyqtSlot(float, name='setQMax')
    def set_q_max(self, q_max: float):
        if q_max != self._q_max:
            self._q_max = q_max
            if self._crystals:
                for crystal in self._crystals.values():
                    crystal.set_q_max(q_max)
                self.sigQMaxChanged.emit()


class CrystalsDatabase(CrystalsHolder):

    def __init__(self, parent=None):
        super(CrystalsDatabase, self).__init__(parent)
        self.selected_holder = SelectedCrystalsHolder(self)

    @pyqtSlot(object, name='addToSelected')
    def add_to_selected(self, key: CustomCrystal or str):
        if isinstance(key, CustomCrystal):
            key = key.key
        self.selected_holder.add_crystal(self[key])

    @pyqtSlot(float, name='setQMax')
    def set_q_max(self, q_max: float):
        super().set_q_max(q_max)
        self.selected_holder.set_q_max(q_max)
