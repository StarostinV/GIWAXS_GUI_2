# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Tuple, Dict

import numpy as np
from scipy.optimize import curve_fit

from .rois.roi import Roi, RoiTypes
from .file_manager import ImageKey


@dataclass
class Fit:
    roi: Roi
    image_key: ImageKey
    r_range: Tuple[float, float]
    x_range: Tuple[int, int]
    x: np.ndarray
    y: np.ndarray
    init_curve: np.ndarray
    init_params: list
    lower_bounds: list
    upper_bounds: list
    fitted_params: list
    fit_errors: list
    fitting_curve: np.ndarray
    param_names: list
    fitting_method: str

    @property
    def bounds(self):
        return tuple(self.lower_bounds), tuple(self.upper_bounds)

    def update(self, **params):
        for k, v in params.items():
            setattr(self, k, v)


class GaussianFit(object):
    PARAM_NAMES = ('peak height', 'radius', 'width', 'background')
    METHOD = 'Gaussian'
    PADDING = 0.7

    def __init__(self, image_key: ImageKey, polar_image: np.ndarray, r_axis: np.ndarray, phi_axis: np.ndarray):
        self.image_key = image_key
        self.polar_image = polar_image
        self.r_axis = r_axis
        self.phi_axis = phi_axis
        self.r_delta = (r_axis.max() - r_axis.min()) / r_axis.size
        self.phi_delta = (phi_axis.max() - phi_axis.min()) / phi_axis.size
        self.r_profile = polar_image.sum(axis=0)
        self.fits: Dict[int, Fit] = {}
        self.aspect_ratio = self._aspect_ratio()
        self.bounds = self._bounds()
        self.name = ''

    def _aspect_ratio(self):
        p, r = self.phi_axis, self.r_axis
        return (p.max() - p.min()) * p.size / (r.max() - r.min()) / r.size

    def _bounds(self):
        p = self.phi_axis
        return (p.max() + p.min()) / 2, (p.max() - p.min())

    def add(self, roi: Roi):
        r1, r2 = roi.radius - roi.width * self.PADDING, roi.radius + roi.width * self.PADDING

        x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
        x, y = self._get_x_y(roi, x1, x2)

        init_params, lower_bounds, upper_bounds = self._default_bounds(roi, y)
        init_curve = self.gauss(x, *init_params)

        fit = Fit(roi=roi, image_key=self.image_key, r_range=(r1, r2), x_range=(x1, x2),
                  x=x, y=y, init_curve=init_curve, init_params=init_params,
                  lower_bounds=lower_bounds, upper_bounds=upper_bounds,
                  fitted_params=[], fit_errors=[], fitting_curve=None,
                  param_names=list(self.PARAM_NAMES), fitting_method=self.METHOD)
        self.fits[roi.key] = fit

        return fit

    def update_r_range(self, fit: Fit):
        roi = fit.roi
        fit.r_range = roi.radius - roi.width * self.PADDING, roi.radius + roi.width * self.PADDING

    def update_fit(self, fit: Fit, update_bounds: bool = True):
        roi = fit.roi
        r1, r2 = fit.r_range
        x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
        x, y = self._get_x_y(roi, x1, x2)

        init_params, lower_bounds, upper_bounds = (fit.init_params,
                                                   fit.lower_bounds,
                                                   fit.upper_bounds)

        if update_bounds and roi.movable:
            try:
                init_params, lower_bounds, upper_bounds = self._default_bounds(roi, y)
            except ValueError:
                pass
        else:
            fit.roi.radius = fit.init_params[1]
            fit.roi.width = fit.init_params[2]

        init_curve = self.gauss(x, *init_params)

        fit.update(r_range=(r1, r2), x_range=(x1, x2),
                   x=x, y=y, init_curve=init_curve, init_params=init_params,
                   lower_bounds=lower_bounds, upper_bounds=upper_bounds)

        if fit.fitted_params:
            fit.fitting_curve = self.gauss(x, *fit.fitted_params)

    def remove_fit(self, fit: Fit):
        try:
            del self.fits[fit.roi.key]
        except KeyError:
            return

    @staticmethod
    def _default_bounds(roi: Roi, y: np.ndarray):
        max_y = y.max()
        min_y = y.min()

        lower_bounds = [0, roi.radius - roi.width / 2, 0, min(0, min_y)]
        upper_bounds = [max_y, roi.radius + roi.width / 2, roi.width * 2, max_y]
        init_params = [max_y - min_y, roi.radius, roi.width, min_y]

        if roi.fitted_parameters and roi.fitted_parameters.get('method', None) == GaussianFit.METHOD:
            try:
                new_init_params = [roi.fitted_parameters[k] for k in GaussianFit.PARAM_NAMES]
                for j, (l, i, u) in enumerate(zip(lower_bounds, new_init_params, upper_bounds)):
                    if l <= i <= u:
                        init_params[j] = i
            except KeyError:
                pass

        return init_params, lower_bounds, upper_bounds

    def _get_x_y(self, roi: Roi, x1: int, x2: int):
        x = self.r_axis[x1:x2]

        if roi.type == RoiTypes.ring:
            y = self.r_profile[x1:x2]
        else:
            p1, p2 = self._get_p_coords(roi.angle - roi.angle_std / 2), \
                     self._get_p_coords(roi.angle + roi.angle_std / 2)
            y = self.polar_image[max(0, p1):min(p2, self.phi_axis.size - 1), x1:x2].sum(axis=0)

        return x, y

    def do_fit(self, fit: Fit = None) -> None:
        if fit:
            self._fit(fit)
        else:
            for fit in self.fits.values():
                self._fit(fit)

    def _fit(self, fit: Fit) -> None:
        try:
            popt, pcov = curve_fit(self.gauss, fit.x, fit.y, fit.init_params,
                                   bounds=fit.bounds)
            perr = np.sqrt(np.diag(pcov))

            fit.fitted_params = popt.tolist()
            fit.init_params = fit.fitted_params
            fit.fit_errors = perr.tolist()
            fit.fitting_curve = self.gauss(fit.x, *popt)
            fit.init_curve = self.gauss(fit.x, *fit.fitted_params)
            fit.roi.fitted_parameters = dict(zip(self.PARAM_NAMES, fit.fitted_params))
            fit.roi.fitted_parameters['method'] = self.METHOD
            fit.roi.radius = fit.roi.fitted_parameters['radius']
            fit.roi.width = fit.roi.fitted_parameters['width']

        except RuntimeError:
            pass

    @staticmethod
    def gauss(x, *p):
        amp, mu, sigma, base = p
        return amp * np.exp(- 2 * (x - mu) ** 2 / sigma ** 2) + base

    def _get_r_coords(self, r):
        return int((r - self.r_axis.min()) / self.r_delta)

    def _get_p_coords(self, p):
        return int((p - self.phi_axis.min()) / self.phi_delta)
