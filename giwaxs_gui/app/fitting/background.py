from enum import Enum
from abc import abstractmethod
from typing import Dict, Callable

import numpy as np

from .utils import Roi, _update_bounds
from ..utils import baseline_correction

__all__ = ['BackgroundType', 'BACKGROUNDS', 'Background', 'LinearBackground', 'ConstantBackground']


class BackgroundType(Enum):
    constant = 'Constant'
    linear = 'Linear'


class Background(object):
    PARAM_NAMES: tuple = ()
    NUM: int = 0
    TYPE: BackgroundType = None

    is_default: bool = True

    @staticmethod
    @abstractmethod
    def _bounds(x: np.ndarray, y: np.ndarray) -> tuple:
        pass

    def bounds(self, x: np.ndarray, y: np.ndarray, roi: Roi):
        init, upper, lower = self._bounds(x, y)
        return _update_bounds(roi, self.PARAM_NAMES, init, upper, lower)

    @abstractmethod
    def __call__(self, x: np.ndarray, *params) -> np.ndarray:
        pass

    @abstractmethod
    def amp_bounds(self, x: np.ndarray, y: np.ndarray, params: list) -> tuple:
        pass


class ConstantBackground(Background):
    PARAM_NAMES = ('constant background',)
    NUM = 1
    TYPE = BackgroundType.constant

    @staticmethod
    def _bounds(x: np.ndarray, y: np.ndarray) -> tuple:
        max_y = y.max()
        min_y = y.min()

        return [min_y], [max_y], [0]

    def __call__(self, x: np.ndarray, *params) -> np.ndarray:
        return params[-1] * np.ones_like(x)

    def amp_bounds(self, x: np.ndarray, y: np.ndarray, params: list) -> tuple:
        return y.max() - params[0], y.max(), 0


class LinearBackground(Background):
    PARAM_NAMES = ('background (slope)', 'background (level)')
    NUM = 2
    TYPE = BackgroundType.linear

    @staticmethod
    def _bounds(x: np.ndarray, y: np.ndarray) -> tuple:
        dx = (x[-1] - x[0]) or 1
        b1 = (y[-1] - y[0]) / dx
        b2 = y[0] - x[0] * b1

        return [b1, b2], [b1 + abs(b1) / 2, b2 + abs(b2) / 2], [b1 - abs(b1) / 2, b2 - abs(b2) / 2]

    def __call__(self, x: np.ndarray, *params) -> np.ndarray:
        return params[-2] * x + params[-1]

    def amp_bounds(self, x: np.ndarray, y: np.ndarray, params: list) -> tuple:
        return y.max() - (y[0] + y[-1]) / 2, y.max(), 0


class BaselineCorrection(Background):
    PARAM_NAMES = ()
    NUM = 0
    TYPE = BackgroundType.auto

    def __init__(self, y: np.ndarray, get_r: Callable, smoothness: float = 1, asymmetry: float = 1):
        self.y = y
        self.get_r = get_r
        self.smoothness: float = smoothness
        self.asymmetry: float = asymmetry
        self.curve = np.zeros_like(y)
        self.update_curve()

    def set_params(self, *, smoothness: float = None, asymmetry: float = None):
        if smoothness:
            self.smoothness = smoothness
        if asymmetry:
            self.asymmetry = asymmetry
        self.update_curve()

    def update_curve(self):
        self.curve = baseline_correction(self.y, self.smoothness, self.asymmetry)

    @staticmethod
    def _bounds(x: np.ndarray, y: np.ndarray) -> tuple:
        return [], [], []

    def __call__(self, x: np.ndarray, *params) -> np.ndarray:
        return self.curve[self.get_r(x[0]):self.get_r(x[-1])]

    def amp_bounds(self, x: np.ndarray, y: np.ndarray, params: list) -> tuple:
        return y.max() - (y[0] + y[-1]) / 2, y.max(), 0


BACKGROUNDS: Dict[BackgroundType, Background.__class__] = {
    BackgroundType.constant: ConstantBackground,
    BackgroundType.linear: LinearBackground,
}
