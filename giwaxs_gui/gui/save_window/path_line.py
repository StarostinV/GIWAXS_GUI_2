from typing import Callable
from functools import partial
from pathlib import Path
from enum import Enum, auto

from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import pyqtSlot

from ...app.data_manager import SavingParameters
from ..tools import Icon, get_folder_filepath, save_file_dialog, color_animation


class PathLineModes(Enum):
    new_dir = auto()
    existing_dir = auto()
    new_h5 = auto()
    existing_h5 = auto()


class PathLine(QLineEdit):
    def __init__(self, init_path: str = '~', parent=None, *, mode: PathLineModes = PathLineModes.new_h5):
        super().__init__(_process_init_path(init_path), parent)
        self._mode: PathLineModes = mode
        self._path_func: Callable = self._get_path_func()
        self._is_valid: bool = False
        self._update_valid_status()

        self.textEdited.connect(self._on_text_edited)
        self._browse_action = self.addAction(Icon('folder'), QLineEdit.LeadingPosition)
        self._browse_action.triggered.connect(self._on_browse_clicked)

    def update_params(self, saving_params: SavingParameters):
        saving_params.path = self.path

    @property
    def mode(self):
        return self._mode

    @property
    def path(self) -> Path:
        return Path(self.text())

    @property
    def is_valid(self) -> bool:
        self._update_valid_status()
        return self._is_valid

    def not_valid_action(self):
        color_animation(self)

    def _update_valid_status(self):
        self._is_valid = self._validate_path(self.path)

    @pyqtSlot(PathLineModes, name='setMode')
    def set_mode(self, mode: PathLineModes):
        if self.mode != mode:
            self._mode = mode
            self._update_path_func()

    def _update_path_func(self):
        self._path_func = self._get_path_func()

    def _get_path_func(self) -> Callable:
        if self.mode.value == PathLineModes.new_h5.value:
            return partial(save_file_dialog, self, 'New h5 file', exists=False)
        elif self.mode.value == PathLineModes.existing_h5.value:
            return partial(save_file_dialog, self, 'Existing h5 file', exists=True)
        elif self.mode.value == PathLineModes.new_dir.value:
            return partial(get_folder_filepath, self, 'New directory', exists=False)
        elif self.mode.value == PathLineModes.existing_dir.value:
            return partial(get_folder_filepath, self, 'Existing directory', exists=True)

    @pyqtSlot(str, name='onTextEdited')
    def _on_text_edited(self, text: str):
        pass

    def _validate_path(self, path: Path) -> bool:
        if not path.parent.is_dir():
            return False

        if self.mode.value == PathLineModes.new_h5.value:
            return (path.suffix in ('.h5', 'hdf5')) and not path.is_file()
        if self.mode.value == PathLineModes.existing_h5.value:
            return (path.suffix in ('.h5', 'hdf5')) and path.is_file()
        if self.mode.value == PathLineModes.new_dir.value or self.mode.value == PathLineModes.existing_dir.value:
            return path.is_dir()

    @pyqtSlot(name='onBrowseClicked')
    def _on_browse_clicked(self):
        if self.path.is_dir():
            directory = str(self.path.expanduser().resolve())
        elif self.path.parent.is_dir():
            directory = str(self.path.parent.expanduser().resolve())
        else:
            directory = str(Path.home())
        path: Path or None = self._path_func(directory=directory)
        self._update_path_func()
        if path:
            self.setText(str(path.resolve()))


def _process_init_path(path_str: str):
    path = Path(path_str)
    if not path.is_dir():
        path = Path('~')
    return str(path.expanduser().resolve())
