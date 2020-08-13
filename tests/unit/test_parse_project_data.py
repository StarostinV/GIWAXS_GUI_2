import pytest
from pathlib import Path
from giwaxs_gui import App


def test_project_1_images(project_1):
    """Project 1 should have a certain data"""
    app = App()
    assert app.fm.root.images_num == 0
    assert app.fm.root.folders_num == 1
