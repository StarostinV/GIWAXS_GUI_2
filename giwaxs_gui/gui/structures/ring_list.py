# -*- coding: utf-8 -*-


from typing import Any, List
from collections import namedtuple

from PyQt5.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QMenu
)

from PyQt5.QtCore import Qt, pyqtSignal

from ...app.structures import CrystalRing, CustomCrystal

ListColumn = namedtuple('ListColumn', 'col func title')


class RingWidgetItem(QTreeWidgetItem):

    def __init__(self, columns: List[ListColumn],
                 num_of_columns: int,
                 ring: CrystalRing,
                 parent_item: QTreeWidgetItem):

        super().__init__(parent_item)
        self.key = ring.key
        self._ring = ring
        self._num_of_columns = num_of_columns
        for column in columns:
            self.setText(column.col, column.func(self._ring))

    @property
    def crystal(self):
        return self._ring.crystal

    @property
    def ring(self):
        return self._ring

    @property
    def row(self):
        return self.treeWidget().indexFromItem(self).row()

    def set_color(self, color):
        for col_num in range(self._num_of_columns):
            self.setBackground(col_num, color)


class CrystalItem(QTreeWidgetItem):
    def __init__(self, parent,
                 crystal_columns: List[ListColumn],
                 ring_columns: List[ListColumn],
                 crystal: CustomCrystal,
                 expand_when_init: bool = True,
                 check_boxes: bool = True,
                 expand_on_click: bool = True,
                 show_rings: bool = True):

        super().__init__(parent)
        self.key = crystal.key
        self.crystal = crystal

        for column in crystal_columns:
            self.setText(column.col, column.func(self.crystal))

        self._updated: bool = False
        self._check_boxes: bool = check_boxes
        self._expand_on_click: bool = expand_on_click
        self._show_rings: bool = show_rings
        self._num_of_columns: int = len(crystal_columns) + len(ring_columns)
        self._ring_columns: List[ListColumn] = ring_columns

        if self._check_boxes:
            self.setFlags(self.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
            self.setCheckState(0, Qt.Checked)

        if expand_when_init:
            self.on_click()

    def on_click(self):
        if not self._show_rings:
            return
        if not self._updated:
            self._updated = True
            for ring in self.crystal.rings:
                self.add_ring(ring)
        if self._expand_on_click:
            self.setExpanded(not self.isExpanded())

    def redraw_rings(self):
        for idx in range(self.childCount()):
            self.removeChild(self.child(idx))
        for ring in self.crystal.rings:
            self.add_ring(ring)

    def add_ring(self, ring: CrystalRing):
        ring_item = RingWidgetItem(self._ring_columns, self._num_of_columns, ring, self)
        ring_item.setFlags(ring_item.flags() & ~ Qt.ItemIsUserCheckable)
        if self._check_boxes:
            ring_item.setCheckState(0, Qt.Checked)

    def setData(self, column: int, role: int, value: Any) -> None:
        is_check_change: bool = (column == 0 and
                                 role == Qt.CheckStateRole and
                                 self.data(column, role) is not None and
                                 self.checkState(0) != value)
        super().setData(column, role, value)
        if is_check_change:
            self.on_check_changed(self.is_checked)

    @property
    def is_checked(self):
        return self.checkState(0) == Qt.Checked

    def on_check_changed(self, is_checked: bool):
        if is_checked:
            self.treeWidget().sigCrystalChecked.emit(self.crystal)
        else:
            self.treeWidget().sigCrystalUnchecked.emit(self.crystal)

    @property
    def row(self):
        return self.treeWidget().indexFromItem(self).row()


class CrystalItemDict(dict):
    def __init__(self):
        super().__init__()
        self._group_dict = {}

    def add_crystal(self, group_item: CrystalItem):
        if group_item.key in self._group_dict:
            raise KeyError(f'Group {group_item.key} already exists.')
        self._group_dict[group_item.key] = group_item

    def pop_crystal(self, key: str) -> CrystalItem:
        try:
            return self._group_dict.pop(key)
        except KeyError as err:
            raise KeyError(f'Group {key} does not exist') from err


class RingsListWidget(QTreeWidget):
    sigCrystalSelected = pyqtSignal(CustomCrystal)
    sigRingSelected = pyqtSignal(CrystalRing)
    sigCrystalChecked = pyqtSignal(CustomCrystal)
    sigCrystalUnchecked = pyqtSignal(CustomCrystal)
    sigCrystalRemoved = pyqtSignal(CustomCrystal)

    _CRYSTAL_COLUMNS = [
        ListColumn(0, lambda crystal: str(crystal.chemical_formula), 'Material'),
        ListColumn(1, lambda crystal: str(crystal.lattice_system.name), 'Structure'),
        ListColumn(5, lambda crystal: str(crystal.source), 'Source'),
    ]

    _RING_COLUMNS = [
        ListColumn(2, lambda ring: f'{ring.radius:.2e}', 'Q'),
        ListColumn(3, lambda ring: ', '.join(map(str, ring.miller_indices)), 'Miller indices'),
        ListColumn(4, lambda ring: f'{ring.intensity:.2e}', 'Structure factor'),
    ]

    def __init__(self, parent=None, check_boxes: bool = True, expand: bool = True,
                 expand_on_click: bool = True, show_rings_items: bool = True):
        super().__init__(parent)
        self.setHeaderLabels(self._get_column_titles())
        self.setEditTriggers(QTreeWidget.NoEditTriggers)

        self._check_boxes: bool = check_boxes
        self._expand: bool = expand
        self._expand_on_click: bool = expand_on_click
        self._show_rings_items: bool = show_rings_items
        self._group_dict = {}

        self.itemClicked.connect(self._on_item_selected)
        self.itemSelectionChanged.connect(self._on_item_selected)
        self.customContextMenuRequested.connect(self._context_menu)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def add_crystal(self, crystal: CustomCrystal):
        if crystal.key not in self._group_dict:
            self._group_dict[crystal.key] = CrystalItem(self,
                                                        crystal_columns=self._CRYSTAL_COLUMNS,
                                                        ring_columns=self._RING_COLUMNS,
                                                        crystal=crystal,
                                                        expand_when_init=self._expand,
                                                        check_boxes=self._check_boxes,
                                                        expand_on_click=self._expand_on_click,
                                                        show_rings=self._show_rings_items
                                                        )
        else:
            item = self._group_dict[crystal.key]
            item.setSelected(True)
            self.sigCrystalSelected.emit(crystal.key)

    def remove_crystal(self, crystal: CustomCrystal):
        self.model().removeRow(self._group_dict.pop(crystal.key).row)

    def crystal_is_checked(self, crystal: CustomCrystal):
        return self._group_dict[crystal.key].is_checked

    def redraw_rings(self, crystals: List[CustomCrystal]):
        for crystal in crystals:
            if crystal.key not in self._group_dict:
                self.add_crystal(crystal)
            self._group_dict[crystal.key].redraw_rings()

    def _get_column_titles(self):
        columns = sorted(self._CRYSTAL_COLUMNS + self._RING_COLUMNS, key=lambda x: x.col)
        return list(map(lambda x: x.title, columns))

    def _on_item_selected(self):
        try:
            item = self.selectedItems()[0]
            if isinstance(item, RingWidgetItem):
                self.sigRingSelected.emit(item.ring)
            elif isinstance(item, CrystalItem):
                item.on_click()
                self.sigCrystalSelected.emit(item.crystal)
        except (IndexError, AttributeError):
            return

    def _context_menu(self, position):
        item = self.itemFromIndex(self.indexAt(position))
        if isinstance(item, CrystalItem):
            menu = QMenu()
            menu.addAction(
                'Remove', lambda *x, crystal=item.crystal:
                self.sigCrystalRemoved.emit(crystal)
            )
            menu.exec_(self.viewport().mapToGlobal(position))
