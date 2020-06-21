from typing import Dict, Set
from collections import defaultdict

from h5py import Group

from ..file_manager import ImageKey, FolderKey
from .roi_data import RoiData


class RoiMetaData(object):

    H5_NAME = 'roi_metadata'

    def __init__(self, folder_key: FolderKey, *,
                 names: Dict[int, str] = None, groups: Dict[int, str] = None):

        self.folder_key = folder_key.clean_copy()
        self.names: Dict[int, str] = names or {}
        self.groups: Dict[int, str] = groups or {}
        self.keys: Dict[int, Set[ImageKey]] = defaultdict(set)

    def update_metadata(self, roi_data: RoiData, image_key: ImageKey):
        for key in roi_data.keys():
            self.keys[key].add(image_key)

    def to_h5(self, h5_group: Group):
        pass

    @classmethod
    def from_h5(cls, folder_key: FolderKey, h5_group: Group):
        # TODO implement read/save for h5 file
        return cls(folder_key)

    @staticmethod
    def del_h5(h5_group: Group):
        if RoiMetaData.H5_NAME in h5_group.keys():
            del h5_group[RoiMetaData.H5_NAME]
