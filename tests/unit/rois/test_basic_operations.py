import pytest
from giwaxs_gui import App


def test_create_rois(empty_project, project_1_info):
    paths_dict = project_1_info.paths_dict()
    image_keys = list(project_1_info.get_all_image_keys())

    app = App()
    app.fm.add_root_path_to_project(project_1_info.root_path)
    assert image_keys[0] is not None
    app.fm.change_image(image_keys[0])

    assert app.roi_dict._current_key is not None

    assert len(app.roi_dict) == 0
    app.roi_dict.create_roi(radius=1, width=2)
    app.roi_dict.create_roi(radius=3, width=3)
    assert len(app.roi_dict) == 2
