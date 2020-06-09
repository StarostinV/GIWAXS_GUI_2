import pickle
import logging
from pathlib import Path
from typing import List


class _GlobalConfigManager(object):
    config_folder: Path = Path(__file__).parents[2] / 'config'
    log = logging.getLogger(__name__)

    def __init__(self):
        if not self.config_folder.is_dir():
            self.config_folder.mkdir(parents=False)
        self._saved_projects_path = str((self.config_folder / 'recent_projects').resolve())

    def get_project_paths(self) -> List[Path]:
        try:
            with open(self._saved_projects_path, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return []

    def add_project_path(self, path: Path):
        paths: List[Path] = self.get_project_paths()
        paths.append(path)
        with open(self._saved_projects_path, 'wb') as f:
            pickle.dump(paths, f)

    def update_project_paths(self, paths: List[Path]):
        with open(self._saved_projects_path, 'wb') as f:
            pickle.dump(paths, f)

    def __getitem__(self, item):

        try:
            with open(str((self.config_folder / item).resolve()), 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return
        except Exception as err:
            self.log.exception(err)
            return

    def __setitem__(self, key, value):

        with open(str((self.config_folder / key).resolve()), 'wb') as f:
            pickle.dump(value, f)

    def __delitem__(self, key):

        path = self.config_folder / key
        if path.is_file():
            path.unlink()
