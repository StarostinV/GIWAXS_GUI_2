from giwaxs_gui.gui.save_window.path_line import PathLine, PathLineModes
from tests.gui_visual.gui_wrapper import run_widget


if __name__ == '__main__':
    run_widget(PathLine, kwargs={'mode': PathLineModes.new_h5})
