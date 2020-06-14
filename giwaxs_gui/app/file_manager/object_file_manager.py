import logging
import pickle
from pathlib import Path

from h5py import Group, File

from ..utils import InternalError
from .keys import ImageKey, AbstractKey, ImageH5Key
from .project_structure import ProjectStructure


def _check_empty_project(func):
    def wrapper(self, *args, **kwargs):
        if self.project_structure.project_opened:
            return func(*args, **kwargs)
        else:
            return

    return wrapper


class _ObjectFileManager(object):
    log = logging.getLogger(__name__)

    NAME = ''

    def __init__(self, project_structure: ProjectStructure):
        self.project_structure = project_structure
        self.folder: Path = None
        self.init()

    def init(self):
        path = self.project_structure.path

        if path:
            self.folder: Path = path / self.NAME
            self.folder.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: AbstractKey) -> Path:
        return self.folder / key.file_name()

    @staticmethod
    def _set_pickle(path: Path, value):
        with open(str(path.resolve()), 'wb') as f:
            pickle.dump(value, f)

    @staticmethod
    def _get_pickle(path: Path):
        if path.is_file():
            with open(str(path.resolve()), 'rb') as f:
                return pickle.load(f)

    @staticmethod
    def _del_pickle(path: Path):
        if path.is_file():
            path.unlink()

    @staticmethod
    def _get_h5(h5group: Group, key: ImageKey):
        pass

    @staticmethod
    def _set_h5(h5group: Group, key: ImageKey, *args, **kwargs):
        pass

    @staticmethod
    def _del_h5(h5group: Group, key: ImageKey):
        pass

    def _process_h5_group(self, h5path: Path, h5key: str, func, *args, **kwargs):
        try:
            with File(str(h5path.resolve()), 'r') as f:
                return func(f[h5key], *args, **kwargs)
        except FileNotFoundError:
            raise FileNotFoundError(f'H5 file {h5path} is not found!')
        except (KeyError, IOError):
            raise IOError(f'Project H5 file {h5path} is corrupted!')
        except Exception as err:
            self.log.exception(err)
            raise InternalError(f'An error occurred while reading project'
                                f'h5 file {h5path}.')

    # def _process_pickle_file(self, path: Path, func, *args, **kwargs):
    #     if not path.is_file():
    #         return
    #     try:
    #         return func(path, *args, **kwargs)
    #     except Exception as err:
    #         self.log.exception(err)
    #         raise InternalError(f'An error occurred while reading project'
    #                             f' internal files.')

    def __getitem__(self, key):
        if not key.is_project:
            return self._get_pickle(self._get_path(key))
        if self.project_structure.config[key.h5path]:
            return self._process_h5_group(key.h5path, key.h5key, self._get_h5, key)
        res = self._get_pickle(self._get_path(key))
        if res is not None:
            return res
        return self._process_h5_group(key.h5path, key.h5key, self._get_h5, key)

    def __delitem__(self, key):
        if not key.is_project:
            return self._del_pickle(self._get_path(key))
        if self.project_structure.config[key.h5path]:
            return self._process_h5_group(key.h5path, key.h5key, self._del_h5, key)
        else:
            return self._del_pickle(self._get_path(key))

    def __setitem__(self, key, value):
        if key.is_project and self.project_structure.config[key.h5path]:
            return self._process_h5_group(key.h5path, key.h5key, self._set_h5, key, value)
        else:
            try:
                return self._set_pickle(self._get_path(key), value)
            except Exception as err:
                self.log.exception(err)
                return
            # return self._process_pickle_file(self._get_path(key), self._set_pickle, value)

    def _check_save_to_h5(self, key) -> bool:
        if key.is_project and self.project_structure.config[key.h5path]:
            return True
        return False
