from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QFont

from crystals import Crystal


class CrystalLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__('', parent)
        self.setFont(QFont('Helvetica', 14))
        self.setMaximumHeight(50)

    def set_crystal(self, crystal: Crystal):
        label = f'{crystal.international_symbol} ({crystal.lattice_system.name} {crystal.chemical_formula})'
        self.setText(label)
