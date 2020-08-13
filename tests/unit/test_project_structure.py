from typing import List, Dict
from giwaxs_gui.app.file_manager import FolderKey, ImageKey


def test_image_keys(project_1, project_1_info):
    paths_dict: Dict[FolderKey, List[ImageKey]] = project_1_info.paths_dict()
