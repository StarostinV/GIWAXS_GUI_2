# -*- coding: utf-8 -*-
from typing import List
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout,
                             QVBoxLayout, QFileDialog, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot

from .tools import center_widget, show_error, Icon


class InitWindow(QWidget):
    sigOpenProject = pyqtSignal(object)
    sigExit = pyqtSignal()
    sigWidgetClosed = pyqtSignal()

    def __init__(self, recent_projects: List[Path] = None):
        flags = Qt.WindowFlags()
        flags |= Qt.WindowStaysOnTopHint
        super().__init__(flags=flags)
        self.setWindowTitle('GIWAXS analysis')
        self.setWindowIcon(Icon('window_icon'))
        self.__init_ui(recent_projects)
        self.setFixedWidth(300)
        center_widget(self)
        self.show()

    def __init_ui(self, recent_projects: List[Path] or None):
        layout = QVBoxLayout(self)
        new_project = QPushButton('New project')
        new_project.clicked.connect(self._new_project_dialog)
        layout.addWidget(new_project)

        if recent_projects:
            layout.addWidget(QLabel('Recent projects'))
            for path in recent_projects:
                btn = QPushButton(path.name)
                btn.clicked.connect(
                    lambda *x, p=path: self.sigOpenProject.emit(p))
                layout.addWidget(btn)

        exit_button = QPushButton('Exit')
        exit_button.clicked.connect(self.sigExit)
        layout.addWidget(QLabel(''))
        layout.addWidget(exit_button)

    @pyqtSlot(name='NewProjectDialog')
    def _new_project_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, 'New project folder')
        if not folder:
            return
        folder = Path(folder)
        if folder.is_dir():
            self.sigOpenProject.emit(folder)
        else:
            show_error('Invalid folder. Please, select existing folder',
                       'Wrong folder')
