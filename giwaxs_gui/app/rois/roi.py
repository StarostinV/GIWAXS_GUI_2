from dataclasses import dataclass
from enum import Enum


class RoiTypes(Enum):
    ring = 'ring'
    segment = 'segment'


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
    fitted: bool = False
    fitted_parameters: dict = None
    active: bool = False
    deleted: bool = False

    def update(self, other: 'Roi'):
        self.__dict__ = other.__dict__
