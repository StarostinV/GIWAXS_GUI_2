from typing import Type
from copy import deepcopy

from ..app import App
from .background import *
from .functions import *
from .fit import Fit
from .utils import _get_dummy_bounds, Roi
from .range_strategy import RangeStrategy, RangeStrategyType


class FitHolder(object):
    MINIMAL_NUM: int = 5

    def __init__(self):
        self.app = App()
        self.polar_image = None
        self.fit = None
        self.default_fitting: Type[FittingFunction] = Gaussian
        self.default_background: Type[Background] = LinearBackground
        self.default_range_strategy: RangeStrategy = RangeStrategy()

        self.update_data()

    def update_data(self):
        self.polar_image = self.app.polar_image

        if self.polar_image is None:
            return

        self.r_axis = self.app.geometry.r_axis
        self.phi_axis = self.app.geometry.phi_axis
        self.r_delta = (self.r_axis.max() - self.r_axis.min()) / self.r_axis.size
        self.min_range: float = self.r_delta * self.MINIMAL_NUM
        self.phi_delta = (self.phi_axis.max() - self.phi_axis.min()) / self.phi_axis.size
        self.r_profile = self.polar_image.sum(axis=0)
        self.aspect_ratio = self._aspect_ratio()
        self.bounds = self._bounds()

    # fit methods:

    def new_fit(self, roi: Roi):
        self.fit = self.init_fit_from_roi(roi)

        return self.fit

    def set_default_fit(self, roi):
        roi.fitted_parameters = {}
        self.fit = self.init_fit_from_roi(roi)
        return self.fit

    def init_fit_from_roi(self, roi):
        if not roi.fitted_parameters:
            roi.fitted_parameters = {}
        params = roi.fitted_parameters

        if 'r_range' not in params:
            r1, r2 = self._get_r_range(roi, self.default_range_strategy.range_factor)
        else:
            r1, r2 = params['r_range']

        x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
        x, y, x_profile, y_profile = self._get_x_y(roi, x1, x2)

        if 'background' in params:
            background: Background = BACKGROUNDS[params['background']]()
            function: FittingFunction = FITTING_FUNCTIONS[params['fitting_function']]()
        else:
            background: Background = self.default_background()
            function: FittingFunction = self.default_fitting()

        fitted_params = params.get('fitted_params', [])
        fit_errors = params.get('fit_errors', [])

        if x.size:
            (
                default_init_params,
                default_upper_bounds,
                default_lower_bounds,
            ) = function.bounds(x, y, roi, background, params_from_roi=True)
        else:
            (
                default_init_params,
                default_upper_bounds,
                default_lower_bounds,
            ) = _get_dummy_bounds(function.NUM + background.NUM)

        init_params, upper_bounds, lower_bounds = (
            params.get('init_params', default_init_params),
            params.get('upper_bounds', default_upper_bounds),
            params.get('lower_bounds', default_lower_bounds)
        )

        background_curve = background(x, *init_params)
        init_curve = function(x, background, *init_params)

        if fitted_params:
            fitting_curve = function(x, background, *fitted_params)
        else:
            fitting_curve = None

        fit = Fit(roi=roi, r_range=(r1, r2), x_range=(x1, x2),
                  x=x, y=y, init_curve=init_curve, init_params=init_params,
                  lower_bounds=lower_bounds, upper_bounds=upper_bounds,
                  fitted_params=fitted_params, fit_errors=fit_errors, fitting_curve=fitting_curve,
                  fitting_function=function, background=background,
                  background_curve=background_curve, range_strategy=deepcopy(self.default_range_strategy),
                  x_profile=x_profile, y_profile=y_profile)

        fit.update_roi_fit_dict()

        return fit

    def remove_fit(self):
        self.fit = None

    # fit properties:

    def set_range_strategy(self, range_strategy: RangeStrategy, update: bool = True):
        range_strategy.is_default = False
        self.default_range_strategy = range_strategy
        if not self.fit:
            return

        self.fit.range_strategy = range_strategy
        if update:
            self.update_fit_data(update_fit=True)

    def set_background(self, background_type: BackgroundType):
        background = BACKGROUNDS[background_type]
        self.default_background = background
        if not self.fit:
            return
        if self.fit.background.TYPE != background_type:
            self.fit.set_background(background())
            self.fit.background.is_default = False

    def set_function(self, fitting_type: FittingType):
        fitting_function = FITTING_FUNCTIONS[fitting_type]
        self.default_fitting = fitting_function
        if not self.fit:
            return
        if self.fit.fitting_function.TYPE != fitting_function:
            self.fit.set_function(fitting_function())
            self.fit.fitting_function.is_default = False

    # private

    def update_fit_data(self, update_r_range: bool = True, *, update_fit: bool = True, **kwargs):
        fit = self.fit
        if not fit:
            return

        if update_r_range and fit.range_strategy.strategy_type.value == RangeStrategyType.adjust.value:
            fit.r_range = r1, r2 = self._get_r_range(fit.roi, fit.range_strategy.range_factor)
        else:
            r1, r2 = fit.r_range
        x1, x2 = self._get_r_coords(r1), self._get_r_coords(r2)
        fit.x, fit.y, fit.x_profile, fit.y_profile = self._get_x_y(fit.roi, x1, x2)

        if update_fit:
            fit.update_fit(**kwargs)

    # Private methods for calculating geometric properties

    def _get_r_range(self, roi: Roi, factor: float):
        r1, r2 = roi.radius - roi.width * (factor + 1), roi.radius + roi.width * (factor + 1)
        return min(r1, roi.radius - self.min_range / 2), max(r2, roi.radius + self.min_range / 2)

    def _get_x_y(self, roi: Roi, x1: int, x2: int):
        x_profile = self.r_axis.copy()
        x = x_profile[x1:x2]

        if not roi.has_fixed_angles():
            y_profile = self.r_profile.copy()
        else:
            p1, p2 = self._get_p_coords(roi.angle - roi.angle_std / 2), \
                     self._get_p_coords(roi.angle + roi.angle_std / 2)
            y_profile = self.polar_image[max(0, p1):min(p2, self.phi_axis.size - 1)].sum(axis=0)

        y = y_profile[x1:x2]

        if x.size != y.size:
            raise ValueError(f'x.size != y.size: {x.size} != {y.size}')

        return x, y, x_profile, y_profile

    def _get_r_coords(self, r):
        return int(round((r - self.r_axis.min()) / self.r_delta))

    def _get_p_coords(self, p):
        return int(round((p - self.phi_axis.min()) / self.phi_delta))

    def _aspect_ratio(self):
        p, r = self.phi_axis, self.r_axis
        return (p.max() - p.min()) * p.size / (r.max() - r.min()) / r.size

    def _bounds(self):
        p = self.phi_axis
        return (p.max() + p.min()) / 2, (p.max() - p.min())
