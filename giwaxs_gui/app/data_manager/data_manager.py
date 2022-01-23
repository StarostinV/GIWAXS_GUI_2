from typing import Dict, List
from pathlib import Path

from ..file_manager import FileManager, ImageKey, FolderKey
from .saving_parameters import SavingParameters
from .save_data import SaveData
from .load_data import (LoadData, FolderData, FolderDataFlags,
                        ImageData, ImageDataFlags)
from ..image_holder import ImageHolder


class DataManager(object):
    def __init__(self, fm: FileManager, image_holder: ImageHolder):
        self._fm = fm
        self._save = SaveData(fm, image_holder)
        self._load = LoadData(fm, image_holder)

    def save(self, params: SavingParameters):
        self._save.save(params)

    def project2h5(self,
                   dest: str or Path,
                   skip_empty_images: bool = True,
                   save_image=True,
                   save_polar_image=True,
                   save_geometries=True,
                   save_roi_keys=True,
                   save_roi_metadata=True,
                   **kwargs):

        dest = Path(dest)

        if not dest.parent.is_dir():
            raise NotADirectoryError(f"Folder {str(dest.parent)} does not exist.")

        if dest.is_file():
            raise FileExistsError(f"File {str(dest)} already exists.")

        params = SavingParameters(
            self.get_paths_dict(self._fm.root, skip_empty_images=skip_empty_images),
            dest,
            save_image=save_image,
            save_polar_image=save_polar_image,
            save_geometries=save_geometries,
            save_roi_keys=save_roi_keys,
            save_roi_metadata=save_roi_metadata,
            **kwargs
        )
        self.save(params)

    def load_project_from_h5(self, h5_path, project_path):
        self._load.load_project_from_h5(h5_path, project_path)

    def load_image_data(self, key: ImageKey,
                        flags: ImageDataFlags = ImageDataFlags.ALL) -> ImageData:
        return self._load.load_image_data(key, flags)

    def load_folder_data(self, key: FolderKey,
                         flags: FolderDataFlags = FolderDataFlags.ALL) -> FolderData:
        return self._load.load_folder_data(key, flags)

    def get_paths_dict(self,
                       folder_key: FolderKey = None,
                       skip_empty_images: bool = True,
                       ) -> Dict[FolderKey, List[ImageKey]]:
        folder_key = folder_key or self._fm.root
        paths_dict: Dict[FolderKey, List[ImageKey]] = {}
        _fill_paths_dict(paths_dict, folder_key, skip_empty_images, self._fm)
        return paths_dict


def _fill_paths_dict(
        paths_dict: Dict[FolderKey, List[ImageKey]],
        folder_key: FolderKey,
        skip_empty_images: bool,
        fm: FileManager,
):
    if folder_key.images_num:
        img_keys = list(folder_key.image_children)

        if skip_empty_images:
            img_keys = [key for key in img_keys if fm.rois_data[key]]

        paths_dict[folder_key] = img_keys

    for folder_child_key in folder_key.folder_children:
        _fill_paths_dict(paths_dict, folder_child_key, skip_empty_images, fm)
