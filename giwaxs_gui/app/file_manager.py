import pickle
import logging
from pathlib import Path
from typing import List, Dict
from enum import Enum
import re

import numpy as np

from PyQt5.QtCore import pyqtSignal, QObject

from .read_image import read_image


class AnalysisRegimes(Enum):
    ex_situ = 1
    real_time = 2


class ImageKey(object):
    def __init__(self, path: Path, *, real_time_name: str = None, num: int = None):
        self._path: Path = path
        self._real_time_name: str = real_time_name
        self._num: int or None = num

    @property
    def path(self):
        return self._path

    @property
    def num(self):
        return self._num

    @property
    def name(self):
        return self._path.name

    def file_name(self) -> str:
        if self._real_time_name is None:
            filename = str(self._path.resolve())
        else:
            filename = f'{self._real_time_name}_{self._num}'
        filename = re.sub('[^\w\-_\. ]', '_', filename) + '.giwaxs'
        return filename

    @property
    def regime(self):
        return AnalysisRegimes.ex_situ if self._num is None else AnalysisRegimes.real_time

    def get_previous(self) -> 'ImageKey' or None:
        if self.regime != AnalysisRegimes.real_time or self._num == 0:
            return
        return ImageKey(self._path, real_time_name=self._real_time_name,
                        num=self._num - 1)

    def __eq__(self, other):
        if isinstance(other, ImageKey):
            return self.__dict__ == other.__dict__
        return False


class _ObjectFileManager(object):
    log = logging.getLogger(__name__)

    def __init__(self, folder: Path):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: ImageKey) -> Path:
        return self.folder / key.file_name()

    @staticmethod
    def _set(path: Path, value):
        with open(str(path.resolve()), 'wb') as f:
            pickle.dump(value, f)

    @staticmethod
    def _get(path: Path):
        with open(str(path.resolve()), 'rb') as f:
            return pickle.load(f)

    def __getitem__(self, key):
        path = self._get_path(key)
        if not path.is_file():
            return
        try:
            return self._get(path)
        except Exception as err:
            self.log.exception(err)
            return

    def __delitem__(self, key):
        path = self._get_path(key)
        if not path.is_file():
            return
        path.unlink()

    def __setitem__(self, key, value):
        path = self._get_path(key)
        try:
            self._set(path, value)
        except Exception as err:
            self.log.exception(err)

    def exists(self, key: ImageKey) -> bool:
        path = self._get_path(key)
        if path and path.is_file():
            return True
        return False


class _ReadNpy(_ObjectFileManager):
    @staticmethod
    def _get(path: Path):
        return np.load(str(path.resolve()) + '.npy', allow_pickle=True)

    @staticmethod
    def _set(path: Path, value):
        np.save(str(path.resolve()) + '.npy', value)


class RealTimeFolder(object):
    def __init__(self, name: str, paths: List[Path] = None):
        self.name = name
        self.paths: List[Path] = paths or []

    def add_paths(self, paths: List[Path]):
        self.paths.extend(paths)

    def get_image_keys(self):
        for key, path in enumerate(self.paths):
            yield ImageKey(path, real_time_name=self.name, num=key)

    def __getitem__(self, item):
        return self.paths[item]

    def __len__(self):
        return len(self.paths)


class ProjectStructure(object):
    def __init__(self, project_path: Path):
        self._project_path: Path = project_path
        self._real_time: Dict[str, RealTimeFolder] = {}
        self._root_paths: List[Path] = []

    def new_time_series(self, name: str, paths: List[Path] = None):
        if name in self._real_time:
            return
        self._real_time[name] = RealTimeFolder(name, paths)

    def get_time_series(self, name: str) -> RealTimeFolder:
        return self._real_time[name]

    def add_root_path(self, path: Path):
        self._root_paths.append(path)

    def root_paths(self):
        yield from self._root_paths

    def remove_path(self, path: Path):
        try:
            self._root_paths.remove(path)
        except ValueError:
            return

    @classmethod
    def load(cls, project_path: Path):
        file = project_path / 'project_structure'
        if file.is_file():
            with open(str(file.resolve()), 'rb') as f:
                return pickle.load(f)
        else:
            return cls(project_path)

    def save(self):
        file = self._project_path / 'project_structure'
        with open(str(file.resolve()), 'wb') as f:
            pickle.dump(self, f)


class _DefaultGeometry(_ObjectFileManager):
    def _get_path(self, key: ImageKey) -> Path:
        if key.regime == AnalysisRegimes.real_time:
            return self.folder / f'default_geometry_{key.name}.giwaxs'
        else:
            return self.folder / f'default_geometry_{key.path.parent.name}.giwaxs'


class _ReadGeometry(_ObjectFileManager):
    def __init__(self, folder: Path):
        super().__init__(folder)
        self.default = _DefaultGeometry(folder)


class _ReadImages(_ReadNpy):
    def __init__(self, folder: Path):
        super().__init__(folder)

    def __getitem__(self, key):
        image = super().__getitem__(key)
        if image is not None:
            return image
        else:
            if isinstance(key, Path):
                path = key
            elif isinstance(key, ImageKey):
                path = key.path
            else:
                return

            if not path.is_file():
                return

            return read_image(str(path.resolve()))


class _AppProjectsManager(object):
    config_folder: Path = Path(__file__).parents[1] / 'config'
    log = logging.getLogger(__name__)

    def __init__(self):
        if not self.config_folder.is_dir():
            self.config_folder.mkdir(parents=False)
        self._saved_projects_path = str((self.config_folder / 'recent_projects').resolve())

    def get_project_paths(self) -> List[Path]:
        try:
            with open(self._saved_projects_path, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return []

    def add_project_path(self, path: Path):
        paths: List[Path] = self.get_project_paths()
        paths.append(path)
        with open(self._saved_projects_path, 'wb') as f:
            pickle.dump(paths, f)

    def update_project_paths(self, paths: List[Path]):
        with open(self._saved_projects_path, 'wb') as f:
            pickle.dump(paths, f)

    def __getitem__(self, item):

        try:
            with open(str((self.config_folder / item).resolve()), 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return
        except Exception as err:
            self.log.exception(err)
            return

    def __setitem__(self, key, value):

        with open(str((self.config_folder / key).resolve()), 'wb') as f:
            pickle.dump(value, f)

    def __delitem__(self, key):

        path = self.config_folder / key
        if path.is_file():
            path.unlink()


class FileManager(QObject):
    sigActiveImageChanged = pyqtSignal(object)
    sigProjectClosed = pyqtSignal()
    sigProjectIsClosing = pyqtSignal()
    sigNewTimeSeries = pyqtSignal(str)
    sigEditedTimeSeries = pyqtSignal(str)
    sigNewFile = pyqtSignal(object)
    sigNewFolder = pyqtSignal(object)

    log = logging.getLogger(__name__)

    def __init__(self):
        QObject.__init__(self)
        self.config: _AppProjectsManager = _AppProjectsManager()
        self.recent_projects: List[Path] = self.config.get_project_paths()
        self._project_folder: Path or None = None
        self._project_structure: ProjectStructure = None
        self.project_name: str = None
        self._current_key: ImageKey = None

        self.recent_projects = [p for p in self.recent_projects if p.is_dir()]

        # self.open_latest_available_project()

    def open_latest_available_project(self):
        self.close_project()
        while self.recent_projects:
            try:
                self.open_project(self.recent_projects.pop(-1))
                return
            except Exception as err:
                self.log.exception(err)

    @property
    def project_opened(self):
        return self._project_structure is not None

    def change_image(self, key: ImageKey):
        if key != self._current_key:
            self._current_key = key
            self.sigActiveImageChanged.emit(key)

    def open_project(self, path: Path):
        if path == self._project_folder:
            return
        self.close_project()
        self._init_project(path)

    def add_ex_situ_data(self, path: Path):
        if not self._project_structure:
            return
        if path.is_dir():
            self.sigNewFolder.emit(path)
        elif path.is_file():
            self.sigNewFile.emit(ImageKey(path))
        else:
            return
        self._project_structure.add_root_path(path)

    def remove_path(self, path: Path):
        self._project_structure.remove_path(path)

    def close_project(self):
        if self._project_structure:
            self.sigProjectIsClosing.emit()
            self._project_structure.save()
            self._project_structure = None
            if self._project_folder not in self.recent_projects:
                self.recent_projects.append(self._project_folder)
            self._project_folder = None
            self.sigProjectClosed.emit()

    def _init_project(self, path: Path):
        self._project_folder = path
        self._project_folder.mkdir(parents=False, exist_ok=True)
        self._project_structure = ProjectStructure.load(self._project_folder)

        self.images: _ReadImages = _ReadImages(self._project_folder / 'images')
        self.geometries: _ReadGeometry = _ReadGeometry(self._project_folder / 'geometries')
        self.polar_images: _ReadNpy = _ReadNpy(self._project_folder / 'polar_images')
        self.rois_data: _ObjectFileManager = _ObjectFileManager(self._project_folder / 'rois')
        self.fits: _ObjectFileManager = _ObjectFileManager(self._project_folder / 'fits')
        self.project_name = self._project_folder.name

        for path in self._project_structure.root_paths():
            if path.is_dir():
                self.sigNewFolder.emit(path)
            elif path.is_file():
                self.sigNewFile.emit(ImageKey(path))

    def __len__(self):
        return len(self.paths)

    def close(self):
        self.close_project()
        self.config.update_project_paths(self.recent_projects)
