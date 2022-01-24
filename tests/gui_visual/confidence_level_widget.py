from giwaxs_gui.gui.roi_widgets.confidence_level_widget import SetConfidenceLevelWidget
from tests.gui_visual.run_widget import run_widget
from tests.fixures.projects import PROJECT_1_INFO


if __name__ == '__main__':
    run_widget(SetConfidenceLevelWidget, PROJECT_1_INFO, args=['Not set', ])
