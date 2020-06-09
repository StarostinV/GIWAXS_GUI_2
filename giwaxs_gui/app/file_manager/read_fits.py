from .object_file_manager import _ObjectFileManager

# TODO save fits to h5


class _ReadFits(_ObjectFileManager):
    NAME = 'fits'

    def _get_path(self, fit_key: tuple):
        key, name = fit_key
        return self.folder / key.file_name(name)

    def __getitem__(self, item):
        key, name = item
        # if not key.is_project:
        #     return self._get_pickle(self._get_path(key))
        # if self.project_structure.config[key.h5path]:
        #     return self._process_h5_group(key.h5path, key.h5key, self._get_h5, key)
        return self._get_pickle(self._get_path(item))
        # if res is not None:
        #     return res
        # return self._process_h5_group(key.h5path, key.h5key, self._get_h5, key)

    def __delitem__(self, item):
        key, name = item
        # if not key.is_project:
        #     return self._del_pickle(self._get_path(key))
        # if self.project_structure.config[key.h5path]:
        #     return self._process_h5_group(key.h5path, key.h5key, self._del_h5, key)
        # else:
        return self._del_pickle(self._get_path(item))

    def __setitem__(self, item, value):
        # key, name = item
        # if key.is_project and self.project_structure.config[key.h5path]:
        #     return self._process_h5_group(key.h5path, key.h5key, self._set_h5, key, value)
        # else:
        try:
            return self._set_pickle(self._get_path(item), value)
        except Exception as err:
            self.log.exception(err)
            return