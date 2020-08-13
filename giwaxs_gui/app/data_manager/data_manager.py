from typing import Dict, List

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

    def load_image_data(self, key: ImageKey,
                        flags: ImageDataFlags = ImageDataFlags.ALL) -> ImageData:
        return self._load.load_image_data(key, flags)

    def load_folder_data(self, key: FolderKey,
                         flags: FolderDataFlags = FolderDataFlags.ALL) -> FolderData:
        return self._load.load_folder_data(key, flags)

    def get_paths_dict(self, folder_key: FolderKey = None) -> Dict[FolderKey, List[ImageKey]]:
        folder_key = folder_key or self._fm.root
        paths_dict: Dict[FolderKey, List[ImageKey]] = {}
        _fill_paths_dict(paths_dict, folder_key)
        return paths_dict


def _fill_paths_dict(paths_dict: Dict[FolderKey, List[ImageKey]], folder_key: FolderKey):
    if folder_key.images_num:
        paths_dict[folder_key] = list(folder_key.image_children)

    for folder_child_key in folder_key.folder_children:
        _fill_paths_dict(paths_dict, folder_child_key)
