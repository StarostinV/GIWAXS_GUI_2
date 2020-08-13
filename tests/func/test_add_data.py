import pytest
from giwaxs_gui import App


def test_add_data(empty_project, project_1_info):
    app = App()
    assert app.fm.root.folders_num == 0
    app.fm.add_root_path_to_project(project_1_info.root_path)
    assert app.fm.root.folders_num == 1


def test_update_data(empty_project, project_1_info):
    app = App()
    app.fm.add_root_path_to_project(project_1_info.root_path)
    folder_keys = list(app.fm.root.folder_children)
    assert len(folder_keys) == 1
    folder_key = folder_keys[0]
    assert folder_key.images_num == 0
    folder_key.update()

    images_num = folder_key.images_num
    assert images_num > 0

    project_path = app.fm.project_path
    app.fm.close_project()
    app.fm.open_project(project_path)
    folder_keys = list(app.fm.root.folder_children)
    assert len(folder_keys) == 1
    folder_key = folder_keys[0]
    assert folder_key.images_num == images_num

