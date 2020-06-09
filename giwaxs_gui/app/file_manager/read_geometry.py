from h5py import Group

from .object_file_manager import _ObjectFileManager
from ..geometry import Geometry


class _DefaultGeometry(_ObjectFileManager):
    NAME = 'geometries'

    def _get_path(self, key):
        return self.folder / f'default_geometry_{key.parent.name}'

    @staticmethod
    def _get_h5(h5group: Group, key):
        return Geometry.fromdict(dict(h5group.parent.attrs))

    @staticmethod
    def _set_h5(h5group: Group, key, value: Geometry):
        h5group.parent.attrs.update(value.to_dict())

    @staticmethod
    def _del_h5(h5group: Group, key):
        for key in Geometry.keys():
            if key in h5group.parent.attrs.keys():
                del h5group.attrs[key]


class _ReadGeometry(_ObjectFileManager):
    NAME = 'geometries'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default = _DefaultGeometry(*args, **kwargs)

    @staticmethod
    def _get_h5(h5group: Group, key):
        return Geometry.fromdict(dict(h5group.attrs))

    @staticmethod
    def _set_h5(h5group: Group, key, value: Geometry):
        h5group.attrs.update(value.to_dict())

    @staticmethod
    def _del_h5(h5group: Group, key):
        for key in Geometry.keys():
            if key in h5group.attrs.keys():
                del h5group.attrs[key]
