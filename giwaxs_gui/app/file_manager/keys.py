import logging
from pathlib import Path
from typing import List, Union
import re
import weakref
from abc import abstractmethod
from copy import deepcopy

from ..read_image import read_image

from h5py import File, Group, Dataset

AVAILABLE_IMAGE_FORMATS = tuple('.tif .tiff .edf .edf.gz'.split())
GLOB_IMAGE_FORMATS = 'edf, tiff, h5 files (*.tiff *.edf *.tif *.edf.gz *.h5 *.hdf5)'
H5_FORMAT = tuple('.h5 .hdf5'.split())

PROJECT_KEY = '__GIWAXS_PROJECT__'
IMAGE_PROJECT_KEY = '__GIWAXS_IMAGE_GROUP__'

logger = logging.getLogger(__name__)


def _check_project(h5path: Path) -> bool or None:
    try:
        with File(str(h5path.resolve()), 'r') as f:
            if PROJECT_KEY in f.attrs.keys():
                return True
            else:
                return False
    except Exception as err:
        logger.exception(err)
        return


def _file_name(key: str, name: str = ''):
    return f'{key}{"_" if name else ""}{name}.giwaxs'


class InvalidKey(Exception):
    """The corresponding data does not exist or corrupted."""


class AbstractKey(object):
    is_project = False

    def __init__(self, parent=None, **kwargs):
        self._parent = weakref.ref(parent) if parent else None

    def file_name(self, name: str = '') -> str:
        return re.sub('[^\w\-_\. ]', '_', _file_name(self._file_key(), name))

    @abstractmethod
    def _file_key(self) -> str:
        pass

    @property
    def name(self):
        return

    @property
    def parent(self) -> 'AbstractKey' or None:
        return self._parent() if self._parent else None

    def remove_parent(self) -> 'AbstractKey' or None:
        parent = self.parent
        self._parent = None
        return parent

    def set_parent(self, parent: 'AbstractKey'):
        self._parent = weakref.ref(parent)

    @abstractmethod
    def __eq__(self, other):
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        pass


class FolderKey(AbstractKey):
    def __init__(self, parent: 'FolderKey', **kwargs):
        super().__init__(parent, **kwargs)
        self._image_children: List[ImageKey] = []
        self._folder_children: List[FolderKey] = []
        self._updated: bool = False

    def is_updated(self) -> bool:
        return self._updated

    @property
    def image_children(self):
        yield from self._image_children

    @property
    def folder_children(self):
        yield from self._folder_children

    @property
    def images_num(self):
        return len(self._image_children)

    @property
    def folders_num(self):
        return len(self._folder_children)

    def update(self):
        self.clear()
        self._updated = True

    def clear(self):
        self._image_children: List[ImageKey] = []
        self._folder_children: List[FolderKey] = []

    def detach_subfolders(self) -> List['FolderKey']:
        subfolders, self._folder_children = self._folder_children, []
        return subfolders

    def attach_subfolders(self, subfolders):
        self._folder_children = subfolders

    def clean_copy(self):
        with RemoveWeakrefs(self, restore=True, remove_subfolders=True):
            return deepcopy(self)

    def image_idx(self, key: 'ImageKey'):
        try:
            return self._image_children.index(key)
        except ValueError:
            return

    def image_by_key(self, idx: int):
        try:
            return self._image_children[idx]
        except IndexError:
            return

    def get_next_image(self, key: 'ImageKey') -> 'ImageKey' or None:
        if not self._image_children:
            return
        idx = key.idx
        if idx is None:
            idx = key.idx = self.image_idx(key)
            if idx is None:
                return
        if idx + 1 < len(self._image_children):
            return self._image_children[idx + 1]

    def remove_image(self, key: 'ImageKey'):
        idx = self.image_idx(key)
        if idx is None:
            return
        self._image_children.remove(key)
        for i in range(idx, len(self._image_children)):
            self._image_children[i].idx = i

    def __contains__(self, item):
        if not (isinstance(item, AbstractKey)):
            return False
        if item == self:
            return True
        for image in self.image_children:
            if image == item:
                return True
        return any((item in folder for folder in self.folder_children))


class ImageKey(AbstractKey):
    def __init__(self, parent=None, idx: int = None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.idx = idx

    @abstractmethod
    def get_image(self):
        pass

    def __contains__(self, item):
        if self == item:
            return True
        return False


class PathKey(AbstractKey):
    def __init__(self, parent, *, path: Path, **kwargs):
        self._path = path
        super().__init__(parent, **kwargs)

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._path.name

    def _file_key(self) -> str:
        return str(self._path.resolve())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._path == other._path
        else:
            return False

    def __repr__(self):
        return self.name


class H5Key(AbstractKey):
    def __init__(self, parent, *, h5path: Path, h5key: str = '', is_project: bool = None, **kwargs):
        super().__init__(parent, **kwargs)
        self._h5path: Path = h5path
        self._h5key: str = h5key
        self._is_project = is_project
        if self._is_project is None:
            self._is_project = _check_project(h5path)

    @property
    def h5path(self):
        return self._h5path

    @property
    def h5key(self):
        return self._h5key

    @property
    def is_project(self):
        return self._is_project

    @property
    def name(self):
        return self._h5key.split('/')[-1] if self._h5key else self._h5path.name

    def _file_key(self) -> str:
        return '-'.join((str(self._h5path.resolve()), self._h5key))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self._h5path == other._h5path and
                    self._h5key == other._h5key)
        else:
            return False

    def __repr__(self):
        return self.name


class FolderH5Key(FolderKey, H5Key):
    def __init__(self, parent: FolderKey, *,
                 h5path: Path, h5key: str = '', is_project: bool = None):
        super().__init__(parent, h5path=h5path, h5key=h5key, is_project=is_project)

    def update(self):
        super().update()
        try:
            with File(str(self._h5path.resolve()), 'r') as f:
                if self._h5key:
                    f = f[self._h5key]
                for key in sorted(list(f.keys())):
                    item = f[key]
                    if isinstance(item, Group):
                        if self.is_project and IMAGE_PROJECT_KEY in item.attrs.keys():
                            self._image_children.append(
                                ImageH5Key(self, h5path=self._h5path,
                                           h5key='/'.join((self._h5key, key)), is_project=True,
                                           idx=len(self._image_children)))
                        else:
                            self._folder_children.append(
                                FolderH5Key(self, h5path=self._h5path,
                                            h5key='/'.join((self._h5key, key)),
                                            is_project=self.is_project))
                    elif isinstance(item, Dataset) and len(item.shape) == 2:
                        self._image_children.append(
                            ImageH5Key(self, h5path=self._h5path,
                                       h5key='/'.join((self._h5key, key)),
                                       is_project=False, idx=len(self._image_children)))
        except Exception as err:
            raise InvalidKey(err)

    def is_valid(self) -> bool:
        try:
            with File(str(self._h5path.resolve()), 'r') as f:
                if self._h5key:
                    f = f[self._h5key]
                if isinstance(f, Group):
                    return True
                else:
                    return False
        except (FileNotFoundError, KeyError, IOError):
            return False
        except Exception as err:
            logger.exception(err)
            return False


class FolderPathKey(FolderKey, PathKey):
    def __init__(self, parent: 'FolderKey', *, path: Path):
        super().__init__(parent, path=path)

    def update(self):
        super().update()
        try:
            for p in sorted(list(self._path.iterdir())):
                if p.is_dir():
                    self._folder_children.append(FolderPathKey(self, path=p))
                elif p.suffix in H5_FORMAT:
                    self._folder_children.append(FolderH5Key(self, h5path=p))
                elif p.suffix in AVAILABLE_IMAGE_FORMATS:
                    self._image_children.append(ImagePathKey(self, path=p, idx=len(self._image_children)))
        except Exception as err:
            raise InvalidKey(err)

    def is_valid(self) -> bool:
        return self._path.is_dir()


class ImagePathKey(ImageKey, PathKey):
    def __init__(self, parent: FolderPathKey, *,
                 path: Path, idx: int = None):
        super().__init__(parent, path=path, idx=idx)

    def get_image(self):
        try:
            return read_image(self._path)
        except Exception as err:
            logger.exception(err)
            return

    def is_valid(self) -> bool:
        return self._path.is_file()


class ImageH5Key(ImageKey, H5Key):
    def __init__(self, parent: FolderKey, *,
                 h5path: Path, h5key: str, is_project: bool = False, idx: int = None):
        super().__init__(
            parent, h5path=h5path, h5key=h5key, is_project=is_project, idx=idx)

    def get_image(self):
        try:
            with File(str(self._h5path.resolve()), 'r') as f:
                image = f[self._h5key]
                if self.is_project:
                    return image['image'][()]
                elif len(image.shape) == 2:
                    return image[()]
        except Exception as err:
            logger.exception(err)
            return

    def is_valid(self) -> bool:
        try:
            with File(str(self._h5path.resolve()), 'r') as f:
                dset = f[self._h5key]
                if not self.is_project and isinstance(dset, Dataset) and len(dset.shape) == 2:
                    return True
                elif self.is_project and isinstance(dset, Group):
                    return True
                return False
        except (FileNotFoundError, KeyError, IOError):
            return False
        except Exception as err:
            logger.exception(err)
            return False


class RemoveWeakrefs(object):
    def __init__(self, key: Union[FolderKey, ImageKey], *,
                 remove_subfolders: bool = False,
                 restore: bool = True):
        self.__key = key
        self.__parent = None
        self.__remove_subfolders: bool = remove_subfolders
        self.__restore: bool = restore
        self.__subfolders: List[FolderKey] = []

    def __enter__(self):
        if self.__remove_subfolders:
            try:
                self.__subfolders = self.__key.detach_subfolders()
            except AttributeError:
                self.__remove_subfolders = False
        self.__parent = self.remove(self.__key)
        return self.__key

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__restore:
            self.restore(self.__key, self.__parent)

            if self.__remove_subfolders:
                self.__key.attach_subfolders(self.__subfolders)
        self.__subfolders = []
        self.__parent = None

    @staticmethod
    def restore(key: Union[FolderKey, ImageKey], parent: FolderKey = None) -> None:
        if parent:
            key.set_parent(parent)
        if isinstance(key, FolderKey):
            _restore_parents(key, parent)

    @staticmethod
    def remove(key: Union[FolderKey, ImageKey]) -> FolderKey or None:
        if isinstance(key, FolderKey):
            _remove_parents(key)
        return key.remove_parent()


def _remove_parents(key: FolderKey):
    for image_key in key.image_children:
        image_key.remove_parent()

    for folder_key in key.folder_children:
        folder_key.remove_parent()
        _remove_parents(folder_key)


def _restore_parents(key: FolderKey, parent: FolderKey = None):
    if parent:
        key.set_parent(parent)

    for image_key in key.image_children:
        image_key.set_parent(key)

    for folder_key in key.folder_children:
        folder_key.set_parent(folder_key)
        _restore_parents(folder_key)
