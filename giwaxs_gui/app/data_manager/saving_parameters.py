from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
from pathlib import Path

from ..file_manager import FolderKey, ImageKey


class SaveFormats(Enum):
    h5_project = 'Save as h5 project'
    object_detection = 'Save as dataset'
    h5 = 'Generic h5 format'
    text = 'Text formats'


class TextFormats(Enum):
    csv = 'csv'
    txt = 'txt'


class MetaTextFormats(Enum):
    json = 'json'
    yaml = 'yaml'


class RoiSavingType(Enum):
    group_by_image = 'Group segments by image'
    group_by_time = 'Group segments by time'


class SaveMode(Enum):
    create = 'New save'
    add = 'Update save'


@dataclass
class SavingParameters:
    selected_images: Dict[FolderKey, List[ImageKey]]
    path: Path
    save_mode: SaveMode = SaveMode.create

    save_image: bool = False
    save_polar_image: bool = False
    save_geometries: bool = True
    save_baselines: bool = False
    save_positions: bool = True
    save_roi_types: bool = True
    save_roi_keys: bool = False
    save_roi_metadata: bool = False

    format: SaveFormats = SaveFormats.h5
    text_format: TextFormats = TextFormats.csv
    meta_text_format: MetaTextFormats = MetaTextFormats.yaml
    roi_saving_type: RoiSavingType = RoiSavingType.group_by_image

    BOOL_FLAGS = {'save_image': 'Save images',
                  'save_polar_image': 'Save polar images',
                  'save_geometries': 'Save geometries',
                  'save_baselines': 'Save baselines',
                  'save_positions': 'Save roi positions',
                  'save_roi_types': 'Save roi types',
                  'save_roi_keys': 'Save roi keys',
                  'save_roi_metadata': 'Save roi names',
                  }

    def set_h5_project_params(self):
        self.save_image = True
        self.save_polar_image = True
        self.save_geometries = True
        self.save_baselines = False  # ?
        self.save_positions = True
        self.save_roi_types = True
        self.save_roi_keys = True
        self.save_roi_metadata = True

    @property
    def num_images(self) -> int:
        return sum(map(len, self.selected_images.values()))
