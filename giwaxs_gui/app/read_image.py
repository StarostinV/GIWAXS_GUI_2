# -*- coding: utf-8 -*-

import numpy as np
from PIL import Image
from read_edf import read_edf


def read_image(filepath) -> np.array:
    filepath = str(filepath)
    if filepath.endswith('.edf') or filepath.endswith('.edf.gz'):
        image = read_edf(filepath)
    else:
        image = np.array(Image.open(filepath))
    return image
