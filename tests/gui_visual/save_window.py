from giwaxs_gui.gui.save_window import SaveWindow
from tests.gui_visual.gui_wrapper import run_widget
from tests.fixures.projects import PROJECT_1_INFO


if __name__ == '__main__':
    run_widget(SaveWindow, PROJECT_1_INFO)
