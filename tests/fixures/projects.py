import pytest
from typing import NamedTuple, List, Dict, Generator
from pathlib import Path
from giwaxs_gui import App
from giwaxs_gui.app.file_manager import ImageKey, FolderKey, ImagePathKey, FolderPathKey

# from giwaxs_gui.app.utils import

__all__ = ['empty_project', 'project_1', 'ProjectInfo', 'PROJECT_1_INFO', 'PROJECT_2_INFO']


def lazy_property(func):
    name = f'__lazy_property_{func.__name__}'

    @property
    def wrapper(self):
        if not hasattr(self, name):
            setattr(self, name, func(self))
        return getattr(self, name)

    return wrapper


class ProjectInfo(NamedTuple):
    name: str
    root_path: Path
    path_tree: dict

    @lazy_property
    def root_key(self) -> FolderPathKey:
        return FolderPathKey(None, path=self.root_path)

    @lazy_property
    def all_image_keys(self) -> Generator[ImagePathKey, None, None]:
        paths_dict = self.paths_dict()
        for image_key_list in paths_dict.values():
            yield from image_key_list

    @lazy_property
    def paths_dict(self) -> Dict[FolderKey, List[ImageKey]]:
        root_folder_key = self.root_key
        paths_dict: Dict[FolderKey, List[ImageKey]] = {}
        self._fill_dict(paths_dict, root_folder_key)
        return paths_dict

    def _fill_dict(self, paths_dict: Dict[FolderKey, List[ImageKey]], folder_key: FolderPathKey):
        paths_dict[folder_key] = list(self.get_image_keys_by_folder_key(folder_key))

        for p in folder_key.path.iterdir():
            if p.is_dir():
                folder_key = FolderPathKey(folder_key, path=p)
                self._fill_dict(paths_dict, folder_key)

    @staticmethod
    def get_image_keys_by_folder_key(folder_key: FolderPathKey) -> Generator[ImagePathKey, None, None]:
        yield from (ImagePathKey(folder_key, path=p) for p in folder_key.path.iterdir() if p.suffix == '.tiff')


def _get_project_info(project_name: str):
    root_path = Path(__file__).parents[1] / 'data' / project_name
    path_tree = _get_path_tree(root_path)
    return ProjectInfo(project_name, root_path, path_tree)


def _get_path_tree(root_path: Path, *, _d: dict = None) -> dict:
    if not _d:
        _d = {}

    _d[root_path] = []

    for p in root_path.iterdir():
        if p.is_dir():
            _d[root_path].append(_get_path_tree(p, _d=_d))
    for p in root_path.iterdir():
        if p.is_file():
            _d[root_path].append(p)
    return _d


PROJECT_1_INFO = _get_project_info('project_1_data')
PROJECT_2_INFO = _get_project_info('project_2_data')


@pytest.fixture
def empty_project(tmpdir_factory):
    project_path, project_dir = _start_project(tmpdir_factory)
    yield
    _close_project(project_path, project_dir)


@pytest.fixture
def project_1(tmpdir_factory):
    project_path, project_dir = _start_project(tmpdir_factory, PROJECT_1_INFO)
    yield PROJECT_1_INFO
    _close_project(project_path, project_dir)


def _start_project(tmpdir_factory, project_info: ProjectInfo = None, expand_paths: bool = False) -> tuple:
    if not project_info:
        name: str = 'Empty project'
    else:
        name: str = project_info.name

    project_dir = tmpdir_factory.mktemp(name)
    project_path = Path(project_dir.strpath)
    app = App()
    app.fm.open_project(project_path)

    if project_info:
        app.fm.add_root_path_to_project(project_info.root_path)
        if expand_paths:
            app.fm.root.expand_tree()
    return project_path, project_dir


def _close_project(project_path: Path, project_dir):
    app = App()
    app.fm.close_project()
    app.fm.delete_project(project_path)
    project_dir.remove()
