from typing import Dict
import numpy as np
from copy import deepcopy

from ..file_manager import ImageKey
from ..profiles import SavedProfile
from ..utils import smooth_curve, baseline_correction
from .background import *
from .functions import *
from .fit import Fit
from .utils import _get_dummy_bounds, Roi, RoiTypes
from .range_strategy import RangeStrategy, RangeStrategyType


class FitObject(object):
    MINIMAL_NUM: int = 5

    def __init__(self, image_key: ImageKey, polar_image: np.ndarray,
                 r_axis: np.ndarray, phi_axis: np.ndarray, *, saved_profile: SavedProfile = None,
                 update_baseline: bool = False):
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
        self.name: str = ''
        self.is_fitted: bool = False
        self.saved_profile: SavedProfile or None = None

        self.default_fitting: FittingFunction.__class__ = Gaussian
        self.default_background: Background.__class__ = LinearBackground
        self.default_range_strategy: RangeStrategy = RangeStrategy()

        if saved_profile:
            self.set_profile(saved_profile, update_baseline)

    def set_profile(self, saved_profile: SavedProfile, update_baseline: bool = False):
        if np.any(saved_profile.x != self.r_axis):
            return

        self.saved_profile = saved_profile

        if update_baseline:
            self.update_baseline()
        else:
            self.r_profile = smooth_curve(saved_profile.raw_data, saved_profile.sigma)
            if saved_profile.baseline is not None:
                self.r_profile = self.r_profile - saved_profile.baseline

        self.update_fit_data(update_r_range=False, update_fit=True)

    def update_baseline(self):
        if self.saved_profile:
            self.saved_profile.x = self.r_axis
            r1, r2 = self.saved_profile.x_range
            x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
            self.saved_profile.raw_data = self.polar_image.sum(axis=0)
            self.r_profile = smooth_curve(self.saved_profile.raw_data, self.saved_profile.sigma)

            baseline = np.zeros_like(self.r_profile)

            baseline[x1:x2] = baseline_correction(
                self.r_profile[x1:x2], self.saved_profile.baseline_params.smoothness,
                self.saved_profile.baseline_params.asymmetry)

            self.saved_profile.baseline = baseline
            self.r_profile = self.r_profile - baseline
            self.update_fit_data(update_r_range=False, update_fit=True)

    def clear_profile(self):
        self.saved_profile = None
        self.r_profile = self.polar_image.sum(axis=0)

    def add_fit(self, fit: Fit):
        self.fits[fit.roi.key] = fit
        update_r_range = fit.range_strategy.strategy_type == RangeStrategyType.adjust
        self.update_fit_data(fit, update_r_range, update_fit=True)

    def new_fit(self, roi: Roi):
        r1, r2 = self._get_r_range(roi, self.default_range_strategy.range_factor)

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
                  background_curve=background_curve, range_strategy=deepcopy(self.default_range_strategy))

        self.fits[roi.key] = fit

        return fit

    def update_fit_data(self, fit: Fit = None, update_r_range: bool = True, *, update_fit: bool = False, **kwargs):
        if fit:
            self._update_fit_data(fit, update_r_range, update_fit=update_fit, **kwargs)
        else:
            for fit in self.fits.values():
                self._update_fit_data(fit, update_r_range, update_fit=update_fit, **kwargs)

    def _update_fit_data(self, fit: Fit, update_r_range: bool = True, *, update_fit: bool = False, **kwargs):
        if update_r_range:
            fit.r_range = r1, r2 = self._get_r_range(fit.roi, fit.range_strategy.range_factor)
        else:
            r1, r2 = fit.r_range
        x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
        fit.x, fit.y = self._get_x_y(fit.roi, x1, x2)

        if update_fit:
            fit.update_fit(**kwargs)

    def remove_fit(self, fit: Fit):
        try:
            del self.fits[fit.roi.key]
        except KeyError:
            return

    def set_range_strategy(self, range_strategy: RangeStrategy, fit: Fit = None, update: bool = True):
        if fit:
            range_strategy.is_default = False
            fit.range_strategy = range_strategy
        else:
            self.default_range_strategy = range_strategy
            for fit in self.fits.values():
                if fit.range_strategy.is_default:
                    fit.range_strategy = deepcopy(range_strategy)
                    if update:
                        self.update_fit_data(fit, update_fit=True)

    def set_background(self, background_type: BackgroundType, fit: Fit = None, update: bool = True):
        background = BACKGROUNDS[background_type]
        if fit and fit.background.TYPE != background_type:
            fit.set_background(background())
            fit.background.is_default = False
        elif self.default_background.TYPE != background_type:
            self.default_background = background
            for fit in self.fits.values():
                if fit.background.is_default:
                    fit.set_background(background(), update)

    def set_function(self, fitting_type: FittingType, fit: Fit = None, update: bool = True):
        fitting_function = FITTING_FUNCTIONS[fitting_type]
        if fit and fit.fitting_function.TYPE != fitting_function:
            fit.set_function(fitting_function())
            fit.fitting_function.is_default = False
        elif self.default_fitting.TYPE != fitting_type:
            self.default_fitting = fitting_function
            for fit in self.fits.values():
                if fit.fitting_function.is_default:
                    fit.set_function(fitting_function(), update)

    # Private methods for calculating geometric properties

    def _get_r_range(self, roi: Roi, factor: float):
        r1, r2 = roi.radius - roi.width * (factor + 1), roi.radius + roi.width * (factor + 1)
        return min(r1, roi.radius - self.min_range / 2), max(r2, roi.radius + self.min_range / 2)

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

    def _aspect_ratio(self):
        p, r = self.phi_axis, self.r_axis
        return (p.max() - p.min()) * p.size / (r.max() - r.min()) / r.size

    def _bounds(self):
        p = self.phi_axis
        return (p.max() + p.min()) / 2, (p.max() - p.min())
