from typing import List, Tuple

import numpy as np

from .roi import Roi, RoiTypes


class RoiData(dict):
    def __init__(self, rois: List[Roi] = None):
        super().__init__()
        self._new_key = 0
        self._selected_keys = set()
        if rois:
            self.add_rois(rois)

    @property
    def selected_keys(self):
        yield from self._selected_keys

    @property
    def selected_num(self):
        return len(self._selected_keys)

    def select(self, key: int) -> Tuple:
        if len(self._selected_keys) == 1 and key in self._selected_keys:
            return ()
        try:
            for k in self._selected_keys:
                self[k].active = False
            self[key].active = True
            self._selected_keys.add(key)
            change_select = tuple(self._selected_keys)
            self._selected_keys = {key}
            return change_select

        except KeyError:
            raise ValueError(f'The selected roi {key} is missing.')

    def shift_select(self, key: int):
        try:
            self[key].active = not self[key].active
            if self[key].active:
                self._selected_keys.add(key)
            else:
                try:
                    self._selected_keys.remove(key)
                except KeyError:
                    pass
        except KeyError:
            raise ValueError(f'The selected roi {key} is missing.')

    @property
    def selected_rois(self) -> List[Roi]:
        return [self[i] for i in self._selected_keys]

    def select_all(self) -> List[int]:
        to_select = list()
        for roi in self.values():
            if not roi.active:
                roi.active = True
                to_select.append(roi.key)
        self._selected_keys = set(self.keys())
        return to_select

    def unselect_all(self) -> List[int]:
        to_unselect = list()
        for roi in self.values():
            if roi.active:
                roi.active = False
                to_unselect.append(roi.key)
        self._selected_keys = set()
        return to_unselect

    def add_roi(self, roi: Roi) -> None:
        if roi.key is None or roi.key < 0:
            roi.key = self._new_key
            self._new_key += 1
        self[roi.key] = roi

        if roi.active:
            self._selected_keys.add(roi.key)
        if not roi.name:
            roi.name = str(roi.key)

    def add_rois(self, roi_list: List[Roi]) -> List[int]:
        keys = list()
        to_select = list()
        for roi in roi_list:
            self.add_roi(roi)
            if roi.active:
                to_select.append(roi.key)
            keys.append(roi.key)
        return to_select

    def delete_roi(self, k: int):
        del self[k]

        if k in self._selected_keys:
            self._selected_keys.remove(k)

    def create_roi(self, radius: float, width: float, **params) -> Roi:
        roi = Roi(radius, width, **params)
        self.add_roi(roi)
        return roi

    def clear(self):
        super().clear()
        self._selected_keys = set()

    def change_ring_bounds(self, bounds: Tuple[float, float]) -> List[int]:
        angle, angle_std = bounds
        keys = list()
        for k, roi in self.items():
            if roi.type == RoiTypes.ring and (roi.angle != angle or roi.angle_std != angle_std):
                keys.append(k)
                roi.angle, roi.angle_std = bounds
        return keys

    def on_scale_changed(self, scale_change: float):
        for roi in self.values():
            roi.radius *= scale_change
            roi.width *= scale_change

    def apply_fit(self, rois: List[Roi]):
        keys_to_move = []
        rois_to_create = []

        for roi in rois:
            roi.active = True
            roi.movable = False

            if roi.key in self.keys():
                keys_to_move.append(roi.key)
                self[roi.key].update(roi)
                self.select(roi.key)
            else:
                rois_to_create.append(roi)

        self.add_rois(rois_to_create)
        keys_to_create = [roi.key for roi in rois_to_create]

        return tuple(keys_to_create), tuple(keys_to_move)

    def to_array(self) -> np.ndarray:
        return np.array([roi.to_array() for roi in self.values()])

    @classmethod
    def from_array(cls, arr: np.ndarray):
        return cls([Roi.from_array(a) for a in arr])
