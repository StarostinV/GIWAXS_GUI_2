from h5py import Group

from .npy_file_manager import _ReadNpy


class _ReadPolarImage(_ReadNpy):
    NAME = 'polar_images'

    @staticmethod
    def _get_h5(h5group: Group, key):
        if 'polar_image' in h5group.keys():
            return h5group['polar_image'][()]

    @staticmethod
    def _set_h5(h5group: Group, key, image):
        _ReadPolarImage._del_h5(h5group)
        h5group.create_dataset('polar_image', data=image)

    @staticmethod
    def _del_h5(h5group: Group, key):
        if 'image' in h5group.keys():
            del h5group['polar_image']
