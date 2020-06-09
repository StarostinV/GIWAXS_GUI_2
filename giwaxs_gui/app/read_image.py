# -*- coding: utf-8 -*-
from typing import Union
from pathlib import Path

import numpy as np
from PIL import Image
from read_edf import read_edf


def read_image(filepath: Union[Path, str]) -> np.array:
    if isinstance(filepath, Path):
        filepath = str(filepath.resolve())

    if filepath.endswith('.edf') or filepath.endswith('.edf.gz'):
        image = read_edf(filepath)
    else:
        image = np.array(Image.open(filepath))
    return image
