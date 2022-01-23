from giwaxs_gui.gui.save_window.path_line import SavePathLine, PathLineModes
from tests.gui_visual.run_widget import run_widget


if __name__ == '__main__':
    run_widget(SavePathLine, kwargs={'mode': PathLineModes.new_file})
