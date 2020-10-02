# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QMainWindow, QGridLayout, QSplitter
from PyQt5.QtCore import Qt, pyqtSignal

from .structures import DatabaseWindow, SelectedCrystalsWindow, CrystalsController
from .viewer_3d import Crystal3DWidget
from ..app.structures import CustomCrystal
from .tools import get_folder_filepath, get_filepath_dialog


class MainCrystalWidget(QWidget):
    def __init__(self, controller: CrystalsController, parent=None):
        super().__init__(parent)
        self.setMinimumSize(700, 700)
        self.database_window = DatabaseWindow(self)
        self.selected_window = SelectedCrystalsWindow(self)
        self.crystal_3d = Crystal3DWidget()

        self._init_ui()

        controller.connect_3d_viewer(self.crystal_3d)
        controller.connect_database_list(self.database_window)
        controller.connect_selected_list(self.selected_window)

    def _init_ui(self):
        layout = QGridLayout(self)
        q_splitter = QSplitter(Qt.Horizontal, self)
        q_splitter.setStretchFactor(0, 0.2)
        q_splitter.setStretchFactor(2, 0.7)
        q_splitter.addWidget(self.database_window)
        q_splitter.addWidget(self.selected_window)
        q_splitter.addWidget(self.crystal_3d)
        layout.addWidget(q_splitter)


class MainCrystalViewer(QMainWindow):
    sigAddCrystalFromCif = pyqtSignal(object)
    sigAddCrystal = pyqtSignal(CustomCrystal)

    def __init__(self, crystal_controller: CrystalsController = None, parent=None):
        super().__init__(parent)
        self._is_hidden: bool = True
        self.main_widget = MainCrystalWidget(crystal_controller)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('Crystal Viewer')
        self.setMinimumSize(700, 500)
        self.setWindowState(Qt.WindowMaximized)
        self._init_menu()
        self.sigAddCrystal.connect(crystal_controller.add_crystal_to_database)
        self.sigAddCrystalFromCif.connect(crystal_controller.add_crystal_from_cif)

    def _init_menu(self):
        menubar = self.menuBar()
        database = menubar.addMenu('Database')
        add_menu = database.addMenu('Add')
        cif = add_menu.addMenu('Cif files')
        add_cif = cif.addAction('Cif file')
        add_folder = cif.addAction('Folder')
        add_cif.triggered.connect(self._add_cif_file)
        add_folder.triggered.connect(self._add_cif_folder)

        add_crystals_builtins = add_menu.addMenu('Crystals db')
        for name in CustomCrystal.builtins:
            add_crystals_builtins.addAction(name, self._add_builtin(name))

    def _add_cif_file(self):
        path = get_cif_file_dialog(self)
        if path:
            self.sigAddCrystalFromCif.emit(path)

    def _add_cif_folder(self):
        path = get_cif_folder_dialog(self)
        if path:
            for cif in path.rglob('*.cif'):
                self.sigAddCrystalFromCif.emit(cif)

    def _add_builtin(self, name: str):
        def func():
            self.sigAddCrystal.emit(CustomCrystal.from_database(name))
        return func


def get_cif_folder_dialog(parent) -> Path or None:
    return get_folder_filepath(parent, message='Choose folder containing cif files.')


def get_cif_file_dialog(parent) -> Path or None:
    return get_filepath_dialog(parent, 'Select cif file', 'Cif file (*.cif)')
