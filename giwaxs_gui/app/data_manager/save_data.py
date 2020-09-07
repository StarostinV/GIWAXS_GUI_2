from ..file_manager import FileManager
from .saving_parameters import SavingParameters, SaveFormats
from .save_h5 import SaveH5
from ..image_holder import ImageHolder


class SaveData(object):
    def __init__(self, fm: FileManager, image_holder: ImageHolder):
        self._fm: FileManager = fm
        self._image_holder: ImageHolder = image_holder
        self._save_h5 = SaveH5(fm, image_holder)

    def save(self, params: SavingParameters):
        if params.format.value == SaveFormats.h5.value:
            self._save_h5.save(params)
        elif params.format.value == SaveFormats.object_detection.value:
            self._save_h5.save_for_object_detection(params)
