# -*- coding: utf-8 -*-

import os
import logging
from typing import List
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QPushButton, QGridLayout,
                             QVBoxLayout, QFileDialog, QLabel,
                             QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from .tools import center_widget, show_error, Icon, color_animation
from .basic_widgets import Label
from ..__version import __version__


class InitWindow(QWidget):
    sigOpenProject = pyqtSignal(object)
    sigExit = pyqtSignal()

    log = logging.getLogger(__name__)

    def __init__(self,
                 recent_projects: List[Path] = None,
                 is_updated: bool = False):
        flags = Qt.WindowFlags()
        flags |= Qt.FramelessWindowHint
        super().__init__(flags=flags)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle('GIWAXS analysis')
        self.setWindowIcon(Icon('window_icon'))
        self.project_name: str = 'untitled'
        self.project_path: Path = Path('~/GIWAXS projects').expanduser().resolve() / self.project_name

        self.__init_ui(recent_projects, is_updated)
        self.setFixedWidth(600)
        self.setFixedHeight(400)
        center_widget(self)
        self.show()

    def __init_ui(self, recent_projects: List[Path] or None, is_updated: bool = False):
        layout = QGridLayout(self)
        layout.setContentsMargins(40, 20, 40, 40)
        self.file_line = QLineEdit(str(self.project_path), self)
        self.file_line.textEdited.connect(self._on_text_editing)

        browse_action = self.file_line.addAction(Icon('folder'), QLineEdit.LeadingPosition)

        browse_action.triggered.connect(self._new_project_dialog)
        self.create_button = QPushButton(f'Create project "{self.project_name}"', self)
        self.create_button.clicked.connect(self._create)

        if is_updated:
            title = f'GIWAXS analysis. Updated to the latest version {__version__}!'
        else:
            title = f'GIWAXS analysis (version {__version__})'

        layout.addWidget(Label(title, self, 11, True), 0, 0, 1, 3, alignment=Qt.AlignHCenter)
        layout.addWidget(Label('New project', self, 9), 1, 0, 1, 3)
        layout.addWidget(self.file_line, 2, 0, 1, 2)
        layout.addWidget(self.create_button, 2, 2)

        if recent_projects:
            r_layout = QVBoxLayout()
            r_layout.addWidget(QLabel('', self))
            r_layout.addWidget(Label('Recent projects', self, 9))
            for path in recent_projects:
                btn = QPushButton(path.name)
                btn.clicked.connect(
                    lambda *x, p=path: self.sigOpenProject.emit(p))
                r_layout.addWidget(btn)
            layout.addLayout(r_layout, 3, 0, 1, 3)

        e_layout = QVBoxLayout()

        exit_button = QPushButton('Exit')
        exit_button.clicked.connect(self.sigExit)
        e_layout.addWidget(QLabel(''))
        e_layout.addWidget(exit_button)

        layout.addLayout(e_layout, 4, 0, 1, 3)

    @pyqtSlot(str, name='onTextEditing')
    def _on_text_editing(self, path: str):
        self.project_name = path.split(os.sep)[-1]
        self.project_path = self.project_path.parent / self.project_name
        self.create_button.setText(f'Create project "{self.project_name}"')

    @pyqtSlot(name='NewProjectDialog')
    def _new_project_dialog(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'New project folder', options=
            QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
        )
        if not folder:
            return
        folder = Path(folder).resolve()
        if folder.is_dir():
            self.project_path = folder / self.project_name
            self.file_line.setText(str(self.project_path))
        else:
            color_animation(self.file_line)
            show_error('Invalid folder. Please, select existing folder',
                       error_title='Wrong path')

    def _create(self):
        try:
            self.project_path.mkdir(parents=True, exist_ok=False)
            self.sigOpenProject.emit(self.project_path.resolve())
        except FileExistsError:
            show_error(f'The folder {str(self.project_path.resolve())} already exists', error_title='Folder exists')
            color_animation(self.file_line)
        except Exception as err:
            self.log.exception(err)
