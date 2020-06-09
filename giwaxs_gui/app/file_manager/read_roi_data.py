from h5py import Group

from .object_file_manager import _ObjectFileManager
from ..rois.roi_data import RoiData


class _ReadRoiData(_ObjectFileManager):
    NAME = 'roi_data'

    @staticmethod
    def _get_h5(h5group: Group, key):
        if 'roi_data' in h5group.keys():
            return RoiData.from_array(h5group['roi_data'][()])

    @staticmethod
    def _set_h5(h5group: Group, key, value: RoiData):
        if 'roi_data' in h5group.keys():
            del h5group['roi_data']
        h5group.create_dataset('roi_data', data=value.to_array())

    @staticmethod
    def _del_h5(h5group: Group, key):
        if 'roi_data' in h5group.keys():
            del h5group['roi_data']
