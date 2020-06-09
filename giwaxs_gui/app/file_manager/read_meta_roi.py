from h5py import Group

from .object_file_manager import _ObjectFileManager
from ..rois.roi_meta_data import RoiMetaData


class _ReadMetaData(_ObjectFileManager):

    def _get_path(self, key):
        return super()._get_path(key.parent)

    @staticmethod
    def _get_h5(h5group: Group, key):
        folder_key = key.parent
        if not folder_key:
            return

        return RoiMetaData.from_h5(folder_key, h5group.parent)

    @staticmethod
    def _set_h5(h5group: Group, key, value: RoiMetaData):
        value.to_h5(h5group.parent)

    @staticmethod
    def _del_h5(h5group: Group, key):
        RoiMetaData.del_h5(h5group.parent)
