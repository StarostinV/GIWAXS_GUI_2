from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from typing import Tuple

import numpy as np


# import giwaxs_gui.app.fitting as fit


class PostponedImport(object):
    def __init__(self):
        self._module = None

    @classmethod
    def init_module(cls):
        pass

    @classmethod
    def __getattr__(cls, item):
        if not hasattr(cls, '_module'):
            cls.init_module()
        return cls._module.__getattr__(item)


class Fit(PostponedImport):
    @classmethod
    def init_module(cls):
        import giwaxs_gui.app.fitting as fit
        cls._module = fit


class RoiTypes(Enum):
    ring = 1
    segment = 2
    background = 3


# (type, selected, fixed): (r, g, b)
ROI_COLOR_KEY = Tuple[RoiTypes, bool, bool]

_CONFIDENCE_LEVELS = OrderedDict([
    ('High', 1.),
    ('Medium', 0.5),
    ('Low', 0.1),
    ('Not set', -1.),
])

_DEFAULT_CONFIDENCE_LEVEL = 'Not set'


@dataclass
class Roi:
    radius: float
    width: float
    angle: float = 180
    angle_std: float = 360
    key: int = None
    name: str = ''
    group: str = ''
    type: RoiTypes = RoiTypes.ring
    movable: bool = True
    fitted_parameters: dict = None
    active: bool = False
    deleted: bool = False
    confidence_level: float = -1.

    CONFIDENCE_LEVELS = _CONFIDENCE_LEVELS
    DEFAULT_CONFIDENCE_LEVEL = _DEFAULT_CONFIDENCE_LEVEL

    @staticmethod
    def confidence_name2level(name: str):
        if name not in _CONFIDENCE_LEVELS.keys():
            return _CONFIDENCE_LEVELS[_DEFAULT_CONFIDENCE_LEVEL]
        for level_name, level in _CONFIDENCE_LEVELS.items():
            if name == level_name:
                return level

    @staticmethod
    def confidence_level2name(level: float):
        values = np.array(list(_CONFIDENCE_LEVELS.values()))
        idx = np.argmin(np.abs(level - values))
        return list(_CONFIDENCE_LEVELS.items())[idx][0]

    @property
    def confidence_level_name(self):
        return self.confidence_level2name(self.confidence_level)

    def set_confidence_level(self, level: float):
        self.confidence_level = level

    def update(self, other: 'Roi'):
        self.__dict__ = other.__dict__

    def to_array(self) -> np.ndarray:
        return np.array([self.radius, self.width, self.angle, self.angle_std,
                         self.key, self.type.value])

    @classmethod
    def from_array(cls, arr: np.ndarray, **meta_data):
        roi = cls(**dict(zip(_ROI_NAMES, arr)), **meta_data)
        roi.type = RoiTypes(roi.type)
        return roi

    def should_adjust_angles(self, angle: float, angle_std: float) -> bool:
        return (
                       self.type == RoiTypes.ring or
                       self.type == RoiTypes.background
               ) and (
                       self.angle != angle or self.angle_std != angle_std
               )

    def has_fixed_angles(self) -> bool:
        return self.type == RoiTypes.segment

    @property
    def intensity(self) -> float or None:
        if self.is_fitted:
            return self.fitted_parameters.get('peak height', None)

    @property
    def is_fitted(self) -> bool:
        return bool(self.fitted_parameters)

    @property
    def color_key(self):
        return self.type, self.active, not self.movable

    def to_dict(self) -> dict:
        roi_dict = dict(self.fitted_parameters or {})

        roi_dict.update({
            key: getattr(self, key) for key in ROI_DICT_KEYS
        })

        roi_dict['type'] = roi_dict['type'].value

        return roi_dict

    @classmethod
    def from_dict(cls, roi_dict: dict, **kwargs):
        cls_params = {key: roi_dict[key] for key in ROI_DICT_KEYS if key in roi_dict}
        cls_params['type'] = RoiTypes(cls_params.get('type', 1))

        if 'fitting_function' in roi_dict:
            fit_func_name = roi_dict['fitting_function']
            fit_func = Fit.FITTING_FUNCTIONS[Fit.FittingType(fit_func_name)]
            fit_param_keys = fit_func.PARAM_NAMES
            fitted_parameters = {'fitting_function': fit_func_name}
            fitted_parameters.update({p: roi_dict[p] for p in fit_param_keys if p in roi_dict})
            cls_params['fitted_parameters'] = fitted_parameters

        return cls(**cls_params, **kwargs)


ROI_DICT_KEYS = (
    'radius',
    'width',
    'angle',
    'angle_std',
    'key',
    'type',
    'confidence_level',
)

DTYPES = [
    ('radius', 'f4'),
    ('width', 'f4'),
    ('angle', 'f4'),
    ('angle_std', 'f4'),
    ('key', 'i4'),
    ('type', 'i4')
]

_ROI_NAMES = list(map(lambda x: x[0], DTYPES))


def roi_to_tuple(roi: Roi):
    return (roi.radius, roi.width, roi.angle, roi.angle_std,
            roi.key, roi.name, roi.group, roi.type.value)
