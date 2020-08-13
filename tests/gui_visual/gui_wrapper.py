import sys
import tempfile
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from giwaxs_gui import App
from tests.fixures.projects import ProjectInfo


def run_widget(widget_class, project_info: ProjectInfo = None, *,
               args: list = None, kwargs: dict = None, expand_tree: bool = True):
    args = args or []
    kwargs = kwargs or {}

    qapp = QApplication([])
    app = App()

    with tempfile.TemporaryDirectory() as tmpdirname:
        if project_info:
            app.fm.open_project(Path(tmpdirname))

            if project_info.root_path:
                app.fm.open_project(Path(tmpdirname))
                app.fm.add_root_path_to_project(project_info.root_path)

                if expand_tree:
                    app.fm.root.expand_tree()

        widget = widget_class(*args, **kwargs)
        widget.show()
        sys.exit(qapp.exec_())
