from typing import Dict
import numpy as np

from ..file_manager import ImageKey
from .background import *
from .functions import *
from .fit import Fit
from .utils import _get_dummy_bounds, Roi, RoiTypes


class FitObject(object):
    PADDING: float = 2
    MINIMAL_NUM: int = 5

    def __init__(self, image_key: ImageKey, polar_image: np.ndarray, r_axis: np.ndarray, phi_axis: np.ndarray):
        self.image_key = image_key

        self.polar_image = polar_image
        self.r_axis = r_axis
        self.phi_axis = phi_axis
        self.r_delta = (r_axis.max() - r_axis.min()) / r_axis.size
        self.min_range: float = self.r_delta * self.MINIMAL_NUM
        self.phi_delta = (phi_axis.max() - phi_axis.min()) / phi_axis.size
        self.r_profile = polar_image.sum(axis=0)
        self.aspect_ratio = self._aspect_ratio()
        self.bounds = self._bounds()

        self.fits: Dict[int, Fit] = {}
        self.name = ''
        self.is_fitted: bool = False

        self.default_fitting: FittingFunction.__class__ = Gaussian
        self.default_background: Background.__class__ = LinearBackground

    def _aspect_ratio(self):
        p, r = self.phi_axis, self.r_axis
        return (p.max() - p.min()) * p.size / (r.max() - r.min()) / r.size

    def _bounds(self):
        p = self.phi_axis
        return (p.max() + p.min()) / 2, (p.max() - p.min())

    def add_fit(self, fit: Fit):
        self.fits[fit.roi.key] = fit
        self.update_fit_data(fit, False)
        fit.update_fit()

    def new_fit(self, roi: Roi):
        r1, r2 = self._get_r_range(roi)

        x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
        x, y = self._get_x_y(roi, x1, x2)

        background: Background = self.default_background()
        function: FittingFunction = self.default_fitting()

        if x.size:
            init_params, upper_bounds, lower_bounds = function.bounds(x, y, roi, background, params_from_roi=True)
        else:
            init_params, upper_bounds, lower_bounds = _get_dummy_bounds(function.NUM + background.NUM)

        background_curve = background(x, *init_params)
        init_curve = function(x, background, *init_params)

        fit = Fit(roi=roi, r_range=(r1, r2), x_range=(x1, x2),
                  x=x, y=y, init_curve=init_curve, init_params=init_params,
                  lower_bounds=lower_bounds, upper_bounds=upper_bounds,
                  fitted_params=[], fit_errors=[], fitting_curve=None,
                  fitting_function=function, background=background,
                  background_curve=background_curve)

        self.fits[roi.key] = fit

        return fit

    def update_fit_data(self, fit: Fit, update_r_range: bool = True):
        if update_r_range:
            fit.r_range = r1, r2 = self._get_r_range(fit.roi)
        else:
            r1, r2 = fit.r_range
        x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
        fit.x, fit.y = self._get_x_y(fit.roi, x1, x2)

    def _get_r_range(self, roi: Roi):
        r1, r2 = roi.radius - roi.width * self.PADDING, roi.radius + roi.width * self.PADDING
        return min(r1, roi.radius - self.min_range / 2), max(r2, roi.radius + self.min_range / 2)

    def remove_fit(self, fit: Fit):
        try:
            del self.fits[fit.roi.key]
        except KeyError:
            return

    def _get_x_y(self, roi: Roi, x1: int, x2: int):
        x = self.r_axis[x1:x2]

        if roi.type == RoiTypes.ring:
            y = self.r_profile[x1:x2]
        else:
            p1, p2 = self._get_p_coords(roi.angle - roi.angle_std / 2), \
                     self._get_p_coords(roi.angle + roi.angle_std / 2)
            y = self.polar_image[max(0, p1):min(p2, self.phi_axis.size - 1), x1:x2].sum(axis=0)

        return x, y

    def _get_r_coords(self, r):
        return int((r - self.r_axis.min()) / self.r_delta)

    def _get_p_coords(self, p):
        return int((p - self.phi_axis.min()) / self.phi_delta)
