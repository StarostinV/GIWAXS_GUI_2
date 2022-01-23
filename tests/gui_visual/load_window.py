from giwaxs_gui.gui.load_window import LoadFromH5Widget
from tests.gui_visual.run_widget import run_widget
from tests.fixures.projects import PROJECT_1_INFO


if __name__ == '__main__':
    run_widget(LoadFromH5Widget, PROJECT_1_INFO)
