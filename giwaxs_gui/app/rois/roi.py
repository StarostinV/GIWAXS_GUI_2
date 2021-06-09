from dataclasses import dataclass
from enum import Enum
from typing import Tuple

import numpy as np


class RoiTypes(Enum):
    ring = 1
    segment = 2
    background = 3


# (type, selected, fixed): (r, g, b)
ROI_COLOR_KEY = Tuple[RoiTypes, bool, bool]


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


DTYPES = [('radius', 'f4'), ('width', 'f4'), ('angle', 'f4'), ('angle_std', 'f4'),
          ('key', 'i4'), ('type', 'i4')]

_ROI_NAMES = list(map(lambda x: x[0], DTYPES))


def roi_to_tuple(roi: Roi):
    return (roi.radius, roi.width, roi.angle, roi.angle_std,
            roi.key, roi.name, roi.group, roi.type.value)
