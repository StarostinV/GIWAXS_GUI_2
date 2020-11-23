import sys
import tempfile
from pathlib import Path
from contextlib import contextmanager

from PyQt5.QtWidgets import QApplication
import qdarkgraystyle

from giwaxs_gui import App
from giwaxs_gui.app.file_manager import ImageKey
from tests.fixures.projects import ProjectInfo


def run_widget(widget_class, project_info: ProjectInfo = None, *,
               args: list = None, kwargs: dict = None, expand_tree: bool = True,
               image_key: ImageKey = None
               ):
    args = args or []
    kwargs = kwargs or {}

    qapp = create_qapp()

    with tempfile.TemporaryDirectory() as tmpdirname:
        init_app(tmpdirname, project_info, expand_tree, image_key)

        widget = widget_class(*args, **kwargs)
        widget.show()
        sys.exit(qapp.exec_())


@contextmanager
def RunWidget(project_info: ProjectInfo = None, expand_tree: bool = True, image_key: ImageKey = None):
    with tempfile.TemporaryDirectory() as tmpdirname:
        qapp = create_qapp()
        init_app(tmpdirname, project_info, expand_tree, image_key)
        yield
        sys.exit(qapp.exec_())


def init_app(tmpdirname, project_info: ProjectInfo, expand_tree: bool = True, image_key: ImageKey = None):
    if project_info:
        app = App()
        app.fm.open_project(Path(tmpdirname))

        if project_info.root_path:
            app.fm.open_project(Path(tmpdirname))
            app.fm.add_root_path_to_project(project_info.root_path)

            if expand_tree:
                app.fm.root.expand_tree()
            if image_key:
                app.fm.change_image(image_key)


def create_qapp():
    qapp = QApplication([])
    qapp.setStyleSheet(qdarkgraystyle.load_stylesheet())
    return qapp
