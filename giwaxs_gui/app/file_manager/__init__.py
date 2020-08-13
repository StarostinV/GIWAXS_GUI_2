import logging
from pathlib import Path
from typing import List

from h5py import File, Group

from PyQt5.QtCore import pyqtSignal, QObject

from .keys import (FolderKey, FolderH5Key, FolderPathKey, RemoveWeakrefs,
                   ImageKey, ImageH5Key, ImagePathKey, InvalidKey,
                   PROJECT_KEY, IMAGE_PROJECT_KEY, GLOB_IMAGE_FORMATS)

from .project_structure import ProjectStructure, ProjectRootKey
from .read_images import _ReadImage, _ReadNpy
from .read_polar_images import _ReadPolarImage
from .read_geometry import _ReadGeometry
from .read_roi_data import _ReadRoiData
from .read_meta_roi import _ReadMetaData
from .read_radial_profile import _ReadRadialProfile
from .config_manager import _GlobalConfigManager
from .read_fits import _ReadFits


class FileManager(QObject):
    sigActiveImageChanged = pyqtSignal(object)
    sigActiveFolderChanged = pyqtSignal(object)
    sigProjectClosed = pyqtSignal()
    sigProjectIsClosing = pyqtSignal()
    sigProjectOpened = pyqtSignal()
    sigNewFolder = pyqtSignal(object)
    sigNewFile = pyqtSignal(object)

    log = logging.getLogger(__name__)

    def __init__(self, config_path: Path = None):
        QObject.__init__(self)
        self.config: _GlobalConfigManager = _GlobalConfigManager(config_path)
        self.recent_projects: List[Path] = self.config.get_project_paths()
        self._project_folder: Path or None = None
        self._project_structure: ProjectStructure = ProjectStructure()
        self.project_name: str = None
        self._current_key: ImageKey or None = None

        self.recent_projects = [p for p in self.recent_projects if p.is_dir()]

        # self.open_latest_available_project()

    @property
    def current_key(self) -> ImageKey or None:
        # TODO what class should be in response for this state?
        return self._current_key

    def open_latest_available_project(self):
        self.close_project()
        while self.recent_projects:
            path = self.recent_projects.pop(-1)
            if path.is_dir():
                try:
                    self.open_project(path)
                    return
                except Exception as err:
                    self.log.exception(err)

    @property
    def project_opened(self) -> bool:
        return self._project_structure.project_opened

    @property
    def root(self) -> ProjectRootKey or None:
        return self._project_structure.root

    @property
    def project_path(self) -> Path or None:
        return self._project_folder

    def change_image(self, key: ImageKey) -> None:
        if key != self._current_key:
            if not key or not self._current_key or key.parent != self._current_key.parent:
                new_parent = key.parent if key else None
                self.sigActiveFolderChanged.emit(new_parent)

            self._current_key = key
            self.sigActiveImageChanged.emit(key)

    def open_project(self, path: Path) -> None:
        if path == self._project_folder:
            return
        self.close_project()
        self._init_project(path)
        self.sigProjectOpened.emit()

    def add_root_path_to_project(self, path: Path) -> None:
        if not self.project_opened:
            return
        key = self._project_structure.root.add_path(path)
        if isinstance(key, ImageKey):
            self.sigNewFile.emit(key)
        elif isinstance(key, FolderKey):
            self.sigNewFolder.emit(key)

    def remove_key(self, key) -> None:
        self._project_structure.root.remove_key(key)
        if isinstance(key, ImageKey):
            self._delete_image_data(key)
            if key.parent:
                key.parent.remove_image(key)
        else:
            self._delete_folder(key)
        if self._current_key in key:
            self.change_image(None)

    def _delete_image_data(self, key: ImageKey):
        del self.geometries[key]
        del self.rois_data[key]
        del self.images[key]
        del self.polar_images[key]

        # TODO find all fits by image key (?)

    def _delete_folder(self, key: FolderKey):
        # TODO delete folder-level data

        for folder in key.folder_children:
            self._delete_folder(folder)
        for image in key.image_children:
            self._delete_image_data(image)

    def close_project(self):
        if self.project_opened:
            self.sigProjectIsClosing.emit()
            self._project_structure.save_and_close()
            if self._project_folder not in self.recent_projects:
                self.recent_projects.append(self._project_folder)
            self._project_folder = None
            self.project_name = None
            self.sigProjectClosed.emit()

    def delete_project(self, project_path: Path):
        if self._project_folder == project_path:
            raise ValueError('Cannot delete opened project.')

        if project_path in self.recent_projects:
            self.recent_projects.remove(project_path)

        _delete_project(project_path)

    def _init_project(self, path: Path):
        self._project_folder = path
        self._project_folder.mkdir(parents=False, exist_ok=True)
        self._project_structure.open_project(path)

        self.images: _ReadImage = _ReadImage(self._project_structure)
        self.geometries: _ReadGeometry = _ReadGeometry(self._project_structure)
        self.polar_images: _ReadPolarImage = _ReadPolarImage(self._project_structure)
        self.rois_data: _ReadRoiData = _ReadRoiData(self._project_structure)
        self.rois_meta_data: _ReadMetaData = _ReadMetaData(self._project_structure)
        self.fits: _ReadFits = _ReadFits(self._project_structure)
        self.profiles: _ReadRadialProfile = _ReadRadialProfile(self._project_structure)
        self.project_name = self._project_folder.name

        for key in self._project_structure.root.folder_children:
            self.sigNewFolder.emit(key)
        for key in self._project_structure.root.image_children:
            self.sigNewFile.emit(key)

    def save_as_h5(self, h5path: Path):
        # TODO remove and use data_manager
        with File(str(h5path.resolve()), 'w') as f:
            f.attrs[PROJECT_KEY] = True
        self._save_folder_as_h5(h5path, self._project_structure.root)

    def _save_folder_as_h5(self, h5path: Path, folder_key: FolderKey):
        if folder_key.images_num > 0:
            with File(str(h5path.resolve()), 'a') as f:
                group = f.create_group(_give_h5_name(f, folder_key.name))

                for image in folder_key.image_children:
                    self._save_image_as_h5(group, image)
        for folder in folder_key.folder_children:
            self._save_folder_as_h5(h5path, folder)

    def _save_image_as_h5(self, h5group: Group, image_key: ImageKey):
        img_group = h5group.create_group(_give_h5_name(h5group, image_key.name))
        img_group.attrs[IMAGE_PROJECT_KEY] = True
        self.images.set_h5(img_group, image_key, image_key.get_image())
        roi_data = self.rois_data[image_key]
        if roi_data:
            self.rois_data.set_h5(img_group, image_key, roi_data)
        geometry = self.geometries[image_key] or self.geometries.default[image_key.parent]
        if geometry:
            self.geometries.set_h5(img_group, image_key, geometry)

    def __len__(self):
        return len(self.paths)

    def close(self):
        self.close_project()
        self.config.update_project_paths(self.recent_projects)


def _give_h5_name(h5group: Group, name):
    if name not in h5group.keys():
        return name
    num = 0
    while True:
        new_name = '_'.join((name, str(num)))
        if new_name not in h5group.keys():
            return new_name
        num += 1


def _delete_project(project_path: Path):
    # TODO implement project deletion
    raise NotImplementedError
