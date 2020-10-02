# -*- coding: utf-8 -*-
import sys

from PyQt5.QtWidgets import QApplication

from giwaxs_gui.gui.crystal_viewer import MainCrystalViewer
from giwaxs_gui.app.structures import CrystalsDatabase


if __name__ == '__main__':
    crystals_database = CrystalsDatabase()
    qapp = QApplication([])

    window = MainCrystalViewer(crystals_database)
    window.show()

    sys.exit(qapp.exec_())
