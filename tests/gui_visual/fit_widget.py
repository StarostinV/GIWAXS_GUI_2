from giwaxs_gui.app import App
from giwaxs_gui.gui.fitting import FitWidget
from tests.gui_visual.run_widget import RunWidget
from tests.fixures.projects import PROJECT_1_INFO


if __name__ == '__main__':
    image_key = list(PROJECT_1_INFO.all_image_keys)[0]

    with RunWidget(PROJECT_1_INFO, expand_tree=True, image_key=image_key):
        app = App()
        fit_obj = app.image_holder.create_fit_object(list(app.roi_dict.values()))
        widget = FitWidget(fit_obj)
        widget.show()
