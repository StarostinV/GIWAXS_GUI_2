# -*- coding: utf-8 -*-
import logging
from typing import Tuple
from dataclasses import dataclass, asdict
from abc import abstractmethod

from scipy.ndimage import gaussian_filter1d
from scipy import sparse
from scipy.sparse.linalg import spsolve
import numpy as np

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject

logger = logging.getLogger(__name__)


@dataclass
class BaselineParams:
    smoothness: float = 100
    asymmetry: float = 0.01


class SmoothedProfile(QObject):
    sig_sigma_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sigma = 0
        self.baseline_params = BaselineParams()
        self.x_range: Tuple[float, float] or None = None
        self._x = self._y = self._raw_y = self._baseline = None

    @property
    def x(self) -> np.ndarray or None:
        return self._x

    @x.setter
    def x(self, value):
        if value is None:
            return
        if self.y is not None and value.size != self.y.size:
            return
        self._x = value

    @property
    def y(self) -> np.ndarray or None:
        return self._y

    @property
    def raw_y(self) -> np.ndarray or None:
        return self._raw_y

    @property
    def baseline(self) -> np.ndarray or None:
        return self._baseline

    @property
    def sigma(self) -> float:
        return self._sigma

    @pyqtSlot(float, name='setSigma')
    def set_sigma(self, sigma: float):
        if sigma <= 0:
            return
        self._sigma = sigma
        self._y = _smooth_data(self._raw_y, self.sigma)

    def set_parameters(self, smoothness: float, asymmetry: float):
        self.baseline_params.smoothness = smoothness
        self.baseline_params.asymmetry = asymmetry

    def get_parameters(self) -> dict:
        return asdict(self.baseline_params)

    def set_data(self, y: np.ndarray, x: np.ndarray):
        self._raw_y = y
        self._y = _smooth_data(self._raw_y, self.sigma)
        self._x = x

    def update_baseline(self):
        if any(v is None for v in (self.x_range, self.y, self.x)):
            return
        if self.y.size != self.x.size:
            return

        x1, x2 = self._get_coords()

        baseline = _baseline_correction(
            self._y[x1:x2], self.baseline_params.smoothness, self.baseline_params.asymmetry)
        self._baseline = np.zeros_like(self._y)
        self._baseline[x1:x2] = baseline

    def clear_baseline(self):
        self._baseline = None
        self.x_range = None

    def _get_coords(self):
        scale_factor = self.x.size / (self.x.max() - self.x.min())
        x_min = self.x.min()
        min_ind, max_ind = 0, self.x.size
        x1 = int((self.x_range[0] - x_min) * scale_factor)
        x2 = int((self.x_range[1] - x_min) * scale_factor)
        x1 = min((max((x1, min_ind)), max_ind))
        x2 = min((max((x2, min_ind)), max_ind))
        xs = (x1, x2)
        return min(xs), max(xs)


def _smooth_data(y: np.ndarray, sigma: float) -> np.ndarray or None:
    if y is not None:
        if sigma > 0:
            return gaussian_filter1d(y, sigma)
        else:
            return y


def _baseline_correction(y: np.ndarray,
                         smoothness_param: float,
                         asymmetry_param: float,
                         max_niter: int = 1000) -> np.ndarray:
    z = np.zeros_like(y)
    if smoothness_param <= 0 or asymmetry_param <= 0:
        return z
    y_size = y.size
    laplacian = sparse.diags([1, -2, 1], [0, -1, -2], shape=(y_size, y_size - 2))
    laplacian_matrix = laplacian.dot(laplacian.transpose())

    w = np.ones(y_size)
    for i in range(max_niter):
        W = sparse.spdiags(w, 0, y_size, y_size)
        Z = W + smoothness_param * laplacian_matrix
        z = spsolve(Z, w * y)
        w_new = asymmetry_param * (y > z) + (1 - asymmetry_param) * (y < z)
        if np.allclose(w, w_new):
            break
        w = w_new
    else:
        logger.info(f'Solution has not converged, max number of iterations reached.')
    return np.nan_to_num(z)


class BasicProfile(SmoothedProfile):
    sigDataToBeUpdated = pyqtSignal()
    sigDataUpdated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_shown: bool = True
        self._should_update: bool = False

    @property
    def is_shown(self) -> bool:
        return self._is_shown

    @is_shown.setter
    def is_shown(self, value: bool):
        if value == self.is_shown:
            return
        self._is_shown = value
        if value and self._should_update:
            self.update_data()

    def set_show_status(self, value: bool):
        self.is_shown = value

    def update_data(self, *args, **kwargs):
        self.sigDataToBeUpdated.emit()
        self.clear_baseline()
        self.update_data_from_source(*args, **kwargs)
        self.sigDataUpdated.emit()
        self._should_update = False

    @abstractmethod
    def update_data_from_source(self,  *args, **kwargs):
        pass

    @pyqtSlot(name='update')
    def update(self):
        if self.is_shown:
            self.update_data()
        else:
            self._should_update = True
