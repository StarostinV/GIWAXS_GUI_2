from pathlib import Path

from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from ...app.app import App
from ..tools import Icon
from ..basic_widgets import PathLineModes, PathLine, Label, H5PathLine


class LoadFromH5Widget(QWidget):
    sigLoadClicked = pyqtSignal(Path, Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Load Project')
        self.setWindowIcon(Icon('window_icon'))
        self.setWindowFlag(Qt.Window, True)
        self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.app = App()

        self._init_ui()
        self._init_layout()
        self._init_connections()

        if self.app.debug_tracker:
            self.app.debug_tracker.add_object(self, 'LoadFromH5Widget')

    def _init_ui(self):
        path = Path('~').expanduser()

        self.h5_path_line = H5PathLine(str(path), parent=self, mode=PathLineModes.existing_file)
        self.project_path_line = PathLine(str(path), parent=self, mode=PathLineModes.new_dir)
        self.label_h5 = Label('Source h5 file', self)
        self.label_project = Label('New project folder', self)
        self.load_btn = QPushButton('Load', self)
        self.cancel_btn = QPushButton('Cancel', self)

    def _init_layout(self):
        layout = QGridLayout(self)

        layout.addWidget(self.label_h5, 0, 0)
        layout.addWidget(self.h5_path_line, 0, 1)

        layout.addWidget(self.label_project, 1, 0)
        layout.addWidget(self.project_path_line, 1, 1)

        layout.addWidget(self.load_btn, 2, 0)
        layout.addWidget(self.cancel_btn, 2, 1)

    def _init_connections(self):
        self.load_btn.clicked.connect(self._save_clicked)
        self.cancel_btn.clicked.connect(self.close)

    @pyqtSlot(name='saveClicked')
    def _save_clicked(self):
        if self.h5_path_line.is_valid and self.project_path_line.is_valid:
            self.sigLoadClicked.emit(self.project_path_line.path, self.h5_path_line.path)
            self.close()
            return
        if not self.h5_path_line.is_valid:
            self.h5_path_line.not_valid_action()
        if not self.project_path_line.is_valid:
            self.project_path_line.not_valid_action()
