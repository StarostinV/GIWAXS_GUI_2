import logging
from scipy import sparse
from scipy.sparse.linalg import spsolve
import numpy as np

logger = logging.getLogger(__name__)


class SingletonMeta(type):
    _instance = None

    def __call__(cls):
        if cls._instance is None:
            cls._instance = super().__call__()
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
