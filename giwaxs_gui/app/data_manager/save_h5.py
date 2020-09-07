from typing import List
from pathlib import Path

from h5py import File, Group
import numpy as np

from ..geometry import Geometry
from .saving_parameters import SavingParameters, SaveMode
from ..file_manager import (FileManager, FolderKey, ImageKey,
                            IMAGE_PROJECT_KEY, PROJECT_KEY)
from ..image_holder import ImageHolder
from .load_data import LoadData, ImageData, ImageDataFlags


class SaveH5(object):
    def __init__(self, fm: FileManager, image_holder: ImageHolder):
        self._fm: FileManager = fm
        self._load_data = LoadData(fm, image_holder)

    def save(self, params: SavingParameters):
        filepath = _get_h5_path(params.path)

        _init_h5_project_file(filepath, params)

        path_str: str = str(filepath.resolve())

        for folder_key, image_keys in params.selected_images.items():
            self._save_folder_as_h5(path_str, folder_key, image_keys, params)

    def save_for_object_detection(self, params: SavingParameters):
        filepath = _get_h5_path(params.path)
        count: int = 0

        if not filepath.parent.exists():
            raise IOError(f'Parent folder {filepath.parent} does not exist.')

        path_str: str = str(filepath.resolve())

        if filepath.exists():
            with File(path_str, 'r') as f:
                count = len(list(f.keys()))

        with File(path_str, 'a') as f:
            for _, image_keys in params.selected_images.items():
                for image_key in image_keys:
                    if self._save_image_for_object_detection(f, image_key, str(count)):
                        count += 1

    def _save_image_for_object_detection(self, f: File, image_key: ImageKey, name: str) -> bool:
        image_data: ImageData = self._load_data.load_image_data(
            image_key, flags=ImageDataFlags.POLAR_IMAGE | ImageDataFlags.GEOMETRY | ImageDataFlags.ROI_DATA)

        if image_data.polar_image is None or image_data.roi_data is None or image_data.geometry is None:
            return False

        boxes, labels = _get_boxes_n_labels(image_data.roi_data.to_array(), image_data.geometry)

        group = f.create_group(name)
        group.create_dataset('polar_image', data=image_data.polar_image)
        group.create_dataset('boxes', data=boxes)
        group.create_dataset('labels', data=labels)

        return True

    def _save_folder_as_h5(self, path: str, folder_key: FolderKey,
                           image_keys: List[ImageKey], params: SavingParameters):
        if not image_keys:
            return

        with File(path, 'a') as f:
            group = _get_folder_group(f, folder_key.name)

            self._save_folder_data(group, folder_key, params)

            for image_key in image_keys:
                self._save_image_as_h5(group, image_key, params)

    def _save_folder_data(self, group: Group, folder_key: FolderKey, params: SavingParameters):

        if params.save_geometries:
            default_geometry = self._fm.geometries.default[folder_key]
            if default_geometry:
                self._fm.geometries.default.set_h5(group, folder_key, default_geometry)

        if params.save_roi_metadata:
            roi_metadata = self._fm.rois_meta_data[folder_key]
            if roi_metadata:
                self._fm.rois_meta_data.set_h5(group, folder_key, roi_metadata)

    def _save_image_as_h5(self, h5group: Group, image_key: ImageKey,
                          params: SavingParameters):

        if image_key.name in h5group.keys():
            del h5group[image_key.name]

        img_group = h5group.create_group(image_key.name)
        img_group.attrs[IMAGE_PROJECT_KEY] = True

        polar_image = self._load_data.load_image_data(image_key, ImageDataFlags.POLAR_IMAGE).polar_image

        if params.save_image:
            self._fm.images.set_h5(img_group, image_key, image_key.get_image())

        if params.save_polar_image and polar_image is not None:
            self._fm.polar_images.set_h5(img_group, image_key, polar_image)

        roi_data = self._fm.rois_data[image_key]
        if roi_data:
            self._fm.rois_data.set_h5(img_group, image_key, roi_data)

        geometry = self._fm.geometries[image_key]
        if geometry and params.save_geometries:
            self._fm.geometries.set_h5(img_group, image_key, geometry)


def _init_h5_project_file(filepath: Path, params: SavingParameters):
    if not filepath.parent.exists():
        raise IOError(f'Parent folder {filepath.parent} does not exist.')

    path_str: str = str(filepath.resolve())

    if filepath.exists() and params.save_mode.value == SaveMode.create.value:
        raise IOError(f'File {path_str} already exists.')

    if params.save_mode.value == SaveMode.add.value:
        with File(path_str, 'a') as f:
            if PROJECT_KEY not in f.attrs:
                raise IOError(f'Chosen file {path_str} is not an h5 project file!')

    elif params.save_mode.value == SaveMode.create.value:
        with File(path_str, 'w') as f:
            f.attrs[PROJECT_KEY] = True


def _get_h5_path(path: Path) -> Path:
    path = path.resolve()
    if path.suffix != '.h5':
        name = '.'.join([path.name.split('.')[0], '.h5'])
        path = path.parent / name
    return path


def _get_folder_group(f: File, name: str) -> Group:
    # TODO carefully handle name collisions by checking Path attribute (or any others)
    return f.create_group(name) if name not in f.keys() else f[name]


def _get_boxes_n_labels(roi_data: np.ndarray, geometry: Geometry):
    labels, boxes = [], []

    for r, w, a, a_s, key, roi_type in roi_data:
        x1, x2 = geometry.r2p(r - w / 2), geometry.r2p(r + w / 2)
        y1, y2 = geometry.a2p(a - a_s / 2), geometry.a2p(a + a_s / 2)

        labels.append(roi_type)
        boxes.append([x1, y1, x2, y2])

    return np.array(boxes), np.array(labels)

# def _give_h5_name(h5group: Group, name):
#     if name not in h5group.keys():
#         return name
#     num = 0
#     while True:
#         new_name = '_'.join((name, str(num)))
#         if new_name not in h5group.keys():
#             return new_name
#         num += 1
