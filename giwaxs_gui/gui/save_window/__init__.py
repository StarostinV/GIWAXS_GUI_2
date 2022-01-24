from typing import List, Dict
from pathlib import Path
from copy import deepcopy

from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from ...app.app import App
from ...app.file_manager import ImageKey, FolderKey
from ...app.data_manager import SaveFormats, SaveMode, SavingParameters
from ..tools import Icon, show_info

from .select_images import SelectImagesWindow
from .options_widgets import OptionsWidget
from .path_line import SavePathLine, PathLineModes
from .format_box import FormatBox
from .save_mode_box import SaveModeBox
from .num_selected_widget import NumSelectedWidget


class SaveWindow(QWidget):
    sigSaveClicked = pyqtSignal(SavingParameters)

    def __init__(self, parent=None, saving_params: SavingParameters = None):
        super().__init__(parent)
        self.setWindowTitle('Save Project')
        self.setWindowIcon(Icon('window_icon'))
        self.setWindowFlag(Qt.Window, True)
        self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.app = App()
        self._all_images = self.app.data_manager.get_paths_dict(skip_empty_images=False)
        self._all_labeled_images = self.app.data_manager.get_paths_dict(skip_empty_images=True)

        self._params: SavingParameters = saving_params or SavingParameters(
            deepcopy(self._all_labeled_images), Path('~').expanduser()
        )

        self._init_ui()
        self._init_layout()
        self._init_connections()

        if self.app.debug_tracker:
            self.app.debug_tracker.add_object(self, 'SaveWindow')

    def _init_ui(self):
        self._select_images_window = None
        self.save_mode_box = SaveModeBox(self)
        self.path_line = SavePathLine(str(self._params.path.resolve()), parent=self)

        self.format_box = FormatBox(self)
        self.options_widget = OptionsWidget(self._params, self)
        self.num_select_widget = NumSelectedWidget(self._params, self)

        self.save_button = QPushButton('Save', self)
        self.cancel_button = QPushButton('Cancel', self)

    def _init_layout(self):
        layout = QGridLayout(self)
        layout.addWidget(self.save_mode_box, 0, 0)
        layout.addWidget(self.path_line, 0, 1, 1, 2)

        layout.addWidget(self.format_box, 1, 0)
        layout.addWidget(self.options_widget.bool_options, 2, 0)
        layout.addWidget(self.options_widget.text_options, 2, 1)
        layout.addWidget(self.num_select_widget, 2, 2)
        layout.addWidget(self.save_button, 3, 0)
        layout.addWidget(self.cancel_button, 3, 1)

    def _init_connections(self):
        self.num_select_widget.sigSelectManuallyClicked.connect(self._select_images_clicked)
        self.num_select_widget.sigSkipUnlabelledClicked.connect(self._select_images_auto)
        self.format_box.sigFormatChanged.connect(self._format_changed)
        self.save_mode_box.sigSaveModeChanged.connect(self._save_mode_changed)
        self.save_button.clicked.connect(self._save_clicked)
        self.cancel_button.clicked.connect(self.close)

    @pyqtSlot(int)
    def _select_images_auto(self, skip_unlabelled_imgs):
        if skip_unlabelled_imgs:
            self._params.selected_images = deepcopy(self._all_labeled_images)
        else:
            self._params.selected_images = deepcopy(self._all_images)
        self.num_select_widget.update_params()

    @pyqtSlot(name='selectImagesClicked')
    def _select_images_clicked(self):
        select_images_window = SelectImagesWindow(deepcopy(self._all_images), self)
        select_images_window.show()
        select_images_window.sigApplyClicked.connect(self._set_selected_images)

    def update_params(self):
        self.path_line.update_params(self._params)
        self.format_box.update_params(self._params)
        self.options_widget.update_params(self._params)

    def is_valid(self) -> bool:
        return self.path_line.is_valid

    def not_valid_action(self):
        self.path_line.not_valid_action()

    @pyqtSlot(name='saveClicked')
    def _save_clicked(self):
        self.update_params()
        if self.is_valid():
            self.sigSaveClicked.emit(self._params)
            show_info(
                title='Data is saved',
                txt=f'{self._params.num_images} images saved to {str(self._params.path)}'
            )
            self.close()
        else:
            self.not_valid_action()

    @pyqtSlot(dict, name='setSelectedImages')
    def _set_selected_images(self, path_dict: Dict[FolderKey, List[ImageKey]]):
        self._params.selected_images = dict(path_dict)
        self.num_select_widget.update_params()

    @pyqtSlot(SaveFormats, name='formatChanged')
    def _format_changed(self, save_format: SaveFormats):
        self.options_widget.set_format(save_format)
        self.path_line.set_mode(_get_path_line_mode(save_format, self.save_mode_box.mode))

    @pyqtSlot(SaveMode, name='saveModeChanged')
    def _save_mode_changed(self, save_mode: SaveMode):
        self.path_line.set_mode(_get_path_line_mode(self.format_box.save_format, save_mode))


_PATH_MODE_DICT: Dict[tuple, PathLineModes] = {
    (SaveFormats.h5.value, SaveMode.create.value): PathLineModes.new_file,
    (SaveFormats.h5.value, SaveMode.add.value): PathLineModes.existing_file,
    (SaveFormats.text.value, SaveMode.create.value): PathLineModes.new_dir,
    (SaveFormats.text.value, SaveMode.add.value): PathLineModes.existing_dir,

}


def _get_path_line_mode(save_format: SaveFormats, save_mode: SaveMode):
    if save_format.value in (SaveFormats.object_detection.value, SaveFormats.h5_project.value):
        sf = SaveFormats.h5.value
    else:
        sf = save_format.value

    return _PATH_MODE_DICT[(sf, save_mode.value)]
