from h5py import Group

from .npy_file_manager import _ReadNpy


class _ReadImage(_ReadNpy):
    NAME = 'images'

    @staticmethod
    def _get_h5(h5group: Group, key):
        pass

    @staticmethod
    def _set_h5(h5group: Group, key, image):
        _ReadImage._del_h5(h5group, key)
        h5group.create_dataset('image', data=image)

    @staticmethod
    def _del_h5(h5group: Group, key):
        if 'image' in h5group.keys():
            del h5group['image']

    def __getitem__(self, key):
        return key.get_image()

