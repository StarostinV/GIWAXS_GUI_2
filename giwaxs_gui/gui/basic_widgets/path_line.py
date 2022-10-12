from typing import Callable
from functools import partial
from pathlib import Path
from enum import Enum, auto

from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import pyqtSlot

from ..tools import Icon, get_folder_filepath, save_file_dialog, color_animation


class PathLineModes(Enum):
    new_dir = auto()
    existing_dir = auto()
    new_file = auto()
    existing_file = auto()


class PathLine(QLineEdit):
    FILE_FORMATS: tuple = ('',)
    FILE_NAME: str = 'File '

    NEW_FILE_TITLE: str = 'New file'
    EXISTING_FILE_TITLE: str = 'Existing file'
    NEW_DIR_TITLE: str = 'New directory'
    EXISTING_DIR_TITLE: str = 'Existing directory'

    def __init__(self, init_path: str = '~', parent=None, *, mode: PathLineModes = PathLineModes.new_file):
        super().__init__(_process_init_path(init_path), parent)
        self._mode: PathLineModes = mode
        self._path_func: Callable = self._get_path_func()
        self._is_valid: bool = False
        self._update_valid_status()

        self.textEdited.connect(self._on_text_edited)
        self._browse_action = self.addAction(Icon('folder'), QLineEdit.LeadingPosition)
        self._browse_action.triggered.connect(self._on_browse_clicked)

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

    @property
    def file_format_str(self):
        formats = ' '.join([f'*.{frm}' for frm in self.FILE_FORMATS])
        return f'{self.FILE_NAME} ({formats})'

    def _get_path_func(self) -> Callable:
        if self.mode.value == PathLineModes.new_file.value:
            return partial(save_file_dialog, self, self.NEW_FILE_TITLE,
                           file_format=self.file_format_str, exists=False)
        elif self.mode.value == PathLineModes.existing_file.value:
            return partial(save_file_dialog, self, self.EXISTING_FILE_TITLE,
                           file_format=self.file_format_str, exists=True)
        elif self.mode.value == PathLineModes.new_dir.value:
            return partial(get_folder_filepath, self, self.NEW_DIR_TITLE, exists=False)
        elif self.mode.value == PathLineModes.existing_dir.value:
            return partial(get_folder_filepath, self, self.EXISTING_DIR_TITLE, exists=True)

    @pyqtSlot(str, name='onTextEdited')
    def _on_text_edited(self, text: str):
        pass

    def _validate_path(self, path: Path) -> bool:
        if not path.parent.is_dir():
            return False

        if self.mode.value == PathLineModes.new_file.value:
            return True
            return ('' in self.FILE_FORMATS or path.suffix in self.FILE_FORMATS) and not path.is_file()
        if self.mode.value == PathLineModes.existing_file.value:
            return True
            return ('' in self.FILE_FORMATS or path.suffix in self.FILE_FORMATS) and path.is_file()
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


class H5PathLine(PathLine):
    FILE_FORMATS = ('h5',)
    FILE_NAME = 'H5 file'
    NEW_FILE_TITLE = 'New h5 file'
    EXISTING_FILE_TITLE = 'Existing h5 file'


def _process_init_path(path_str: str):
    path = Path(path_str)
    if not path.is_dir():
        path = Path('~')
    return str(path.expanduser().resolve())
