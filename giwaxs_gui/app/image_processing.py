import cv2 as cv
import numpy as np


def clahe(img, limit: float = 5000):
    return cv.createCLAHE(clipLimit=limit, tileGridSize=(1, 1)).apply(img.astype('uint16')).astype(np.float32)


def norm_img(img):
    return (img - img.min()) / (img.max() - img.min())


def standard_contrast_correction(
        img,
        limit: float = 2000,
        coef: float = 5000,
        log: bool = True,
):
    if log:
        img = np.log10(norm_img(img) * coef + 1)

    return norm_img(clahe(norm_img(img) * coef, limit))
