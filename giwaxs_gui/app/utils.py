import logging
import sys
import traceback

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QRunnable

from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.ndimage import gaussian_filter1d

import numpy as np

logger = logging.getLogger(__name__)


# class ChainProperties(object):
#     """
#     ChainProperties provides a functionality to simplify setting
#     a choice of several options.
#
#     >>> class MyChainProperty(ChainProperties):
#     ...     _PROPERTY_DICT = {'a': 0, 'b': 1, 'c': 2}
#     ...
#     >>>
#     >>> my_chain_property = MyChainProperty()
#     >>> my_chain_property.properties
#     ()
#     >>> my_chain_property.a
#     MyChainProperty(a)
#     >>> my_chain_property.b.c
#     MyChainProperty(a, b, c)
#     >>> my_chain_property.properties
#     (0, 1, 2)
#     >>> MyChainProperty().a.b.c
#     MyChainProperty(a, b, c)
#
#     It can be initialized with a dictionary as a constructor parameter
#     >>> another_chain_property = ChainProperties({'a': 0, 'b': 1, 'c': 2})
#     >>> another_chain_property.a.properties
#     (0,)
#
#     >>> another_chain_property.clear().properties
#     ()
#
#     >>> len(MyChainProperty())
#     0
#     >>> len(MyChainProperty().a.b)
#     2
#     >>> bool(MyChainProperty())
#     False
#     >>> bool(MyChainProperty().a)
#     True
#     """
#
#     _PROPERTY_DICT = {}
#     __slots__ = ('_chosen_params', '_chosen_values')
#
#     def __init__(self, params_dict: dict = None):
#         if params_dict:
#             self._PROPERTY_DICT.update(params_dict)
#         self._chosen_params = []
#         self._chosen_values = []
#
#         for prop in self._PROPERTY_DICT.keys():
#             setattr(self.__class__, prop, property(self._prop_factory(prop)))
#
#     def _prop_factory(self, prop):
#         def func(*args, **kwargs):
#             if prop not in self._chosen_params:
#                 self._chosen_params.append(prop)
#                 self._chosen_values.append(self._PROPERTY_DICT[prop])
#
#             return self
#
#         return func
#
#     @property
#     def properties(self):
#         return tuple(self._chosen_values)
#
#     def __len__(self):
#         return len(self._chosen_values)
#
#     def __bool__(self):
#         return len(self) > 0
#
#     def __repr__(self):
#         properties = ', '.join(self._chosen_params)
#         return f'{self.__class__.__name__}({properties})'
#
#     def clear(self):
#         self._chosen_params.clear()
#         self._chosen_values.clear()
#         return self


class SingletonMeta(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class InternalError(Exception):
    pass


def baseline_correction(y: np.ndarray,
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


def smooth_curve(y: np.ndarray, sigma: float) -> np.ndarray or None:
    if y is not None:
        if sigma > 0:
            return gaussian_filter1d(y, sigma)
        else:
            return y


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


class Worker(QRunnable):
    log = logging.getLogger(__name__)

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):

        try:
            result = self.fn(
                *self.args, **self.kwargs
            )
        except Exception as err:
            self.log.exception(err)
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            try:
                self.signals.error.emit((exctype, value, traceback.format_exc()))
            except RuntimeError:
                return
        else:
            try:
                self.signals.result.emit(result)
            except RuntimeError:
                return
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                return

#
# if __name__ == "__main__":
#     import doctest
#
#     doctest.testmod()
